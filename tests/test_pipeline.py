from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from signaldesk.models import UnifiedEvent

ZONE = ZoneInfo("Asia/Taipei")
NOW = datetime(2026, 8, 2, 18, 0, tzinfo=ZONE)


def event(**updates):
    values = {
        "event_id": "event-1",
        "source": "gmail",
        "source_app_id": "gmail",
        "account_id": "work",
        "sender": "professor@example.edu",
        "conversation_id": "thread-1",
        "title": "實驗進度",
        "content": "請在今晚前把目前的實驗結果寄給我。",
        "content_completeness": "full",
        "received_at": NOW,
        "privacy_class": "sensitive",
        "metadata": {"message_id": "message-1", "history_id": "10"},
    }
    values.update(updates)
    return UnifiedEvent(**values)


def test_gmail_deadline_creates_evidence_backed_card(pipeline, database):
    result = pipeline.process(event())
    card = database.card_detail(result.card_id)

    assert card["priority"] == "high"
    assert card["requires_reply"] == "yes"
    assert card["deadlines"][0]["original_text"] == "今晚前"
    assert card["deadlines"][0]["supporting_span"] in card["events"][0]["content"]
    assert card["action_items"][0]["supporting_span"] in card["events"][0]["content"]
    assert "draft_reply" in card["actions"]
    assert card["validation"]["valid"] is True


def test_duplicate_event_is_idempotent(pipeline, database):
    first = pipeline.process(event())
    second = pipeline.process(event())

    assert second.duplicate is True
    assert second.card_id == first.card_id
    assert len(database.list_cards()) == 1


def test_line_burst_groups_and_preserves_preview_limit(pipeline, database):
    first = event(
        event_id="line-1",
        source="line_notification",
        source_app_id="LINE",
        account_id="windows",
        sender="實驗室群組",
        conversation_id=None,
        title="實驗室群組",
        content="明天會議改到三點",
        content_completeness="notification_preview",
        received_at=NOW,
        raw_notification_id="win-1",
        metadata={},
    )
    second = first.model_copy(
        update={
            "event_id": "line-2",
            "content": "教授也會參加，你可以嗎？",
            "received_at": NOW + timedelta(seconds=10),
            "raw_notification_id": "win-2",
        }
    )
    first_result = pipeline.process(first)
    second_result = pipeline.process(second)
    card = database.card_detail(second_result.card_id)

    assert second_result.thread_id == first_result.thread_id
    assert len(card["events"]) == 2
    assert card["requires_reply"] == "yes"
    assert "incomplete_preview" in card["uncertainty_flags"]
    assert "needs_review" in card["actions"]


def test_image_only_preview_does_not_invent_content(pipeline, database):
    image_event = event(
        event_id="messenger-photo",
        source="messenger_notification",
        source_app_id="Microsoft Edge",
        account_id="windows",
        sender="王小明",
        conversation_id=None,
        title="Messenger",
        content="傳送了一張相片",
        content_completeness="notification_preview",
        received_at=NOW,
        raw_notification_id="win-photo",
        metadata={"origin": "messenger.com"},
    )
    result = pipeline.process(image_event)
    card = database.card_detail(result.card_id)

    assert card["priority"] == "unknown"
    assert card["requires_reply"] == "unknown"
    assert card["action_items"] == []
    assert card["deadlines"] == []
    assert set(card["uncertainty_flags"]) >= {"incomplete_preview", "missing_context"}


def test_reclassifies_existing_browser_messenger_card(pipeline, database):
    old_event = event(
        event_id="old-browser-messenger",
        source="windows_notification",
        source_app_id="Chrome",
        account_id="windows_user",
        sender="Messenger",
        conversation_id=None,
        title="Messenger",
        content="Meta AI 傳送了 1 張相片。",
        content_completeness="notification_preview",
        received_at=NOW,
        raw_notification_id="old-toast",
        metadata={"native_app_id": "Chrome", "native_app_name": "Google Chrome"},
    )
    result = pipeline.process(old_event)
    second = pipeline.process(
        old_event.model_copy(
            update={
                "event_id": "old-browser-messenger-2",
                "received_at": NOW + timedelta(minutes=7),
                "raw_notification_id": "old-toast-2",
            }
        )
    )
    assert database.card_detail(result.card_id)["source"] == "windows_notification"
    assert second.thread_id != result.thread_id

    assert database.reclassify_messenger_browser_cards() == 2
    merged = database.merge_duplicate_messenger_threads()
    assert len(merged) == 1
    repaired_card = database.list_cards(source="messenger_notification")[0]
    repaired = database.card_detail(repaired_card["card_id"])
    assert repaired["source"] == "messenger_notification"
    assert repaired["sender"] == "Meta AI"
    assert len(repaired["events"]) == 2
    assert all(
        source_event["source"] == "messenger_notification"
        for source_event in repaired["events"]
    )


def test_collapses_repeated_line_notification_snapshots(pipeline, database):
    repeated = event(
        event_id="line-replay-1",
        source="line_notification",
        source_app_id="LINE",
        account_id="windows_user",
        sender="群組",
        conversation_id="群組",
        title="群組",
        content="完全相同的舊通知",
        content_completeness="notification_preview",
        received_at=NOW,
        raw_notification_id="replay-1",
        metadata={"native_app_id": "NAVER.LINE", "native_app_name": "LINE"},
    )
    first = pipeline.process(repeated)
    for index, minutes in enumerate((40, 80), start=2):
        pipeline.process(
            repeated.model_copy(
                update={
                    "event_id": f"line-replay-{index}",
                    "received_at": NOW + timedelta(minutes=minutes),
                    "raw_notification_id": f"replay-{index}",
                }
            )
        )

    assert len(database.card_detail(first.card_id)["events"]) == 1
    assert database.collapse_duplicate_notification_replays() == 0
    cleaned = database.card_detail(first.card_id)
    assert len(cleaned["events"]) == 1
    assert cleaned["events"][0]["received_at"] == NOW.isoformat()


def test_shadow_mode_records_would_surface(pipeline, database):
    database.update_settings({"shadow_mode": True})
    result = pipeline.process(event())
    card = database.card_detail(result.card_id)

    assert card["display_mode"] == "inbox"
    assert card["decision"]["decision"] == "store_in_inbox"
    assert "shadow_mode" in card["why_shown"]
    assert "would_surface_now" in card["why_shown"]


def test_noise_does_not_become_reply_or_visible_card(pipeline, database):
    newsletter = event(
        event_id="newsletter",
        conversation_id="newsletter-thread",
        title="限時優惠",
        content="限時優惠與折扣碼。取消訂閱請點頁尾連結。",
        metadata={"message_id": "newsletter", "history_id": "1"},
    )
    result = pipeline.process(newsletter)
    card = database.card_detail(result.card_id)

    assert card["priority"] == "noise"
    assert card["requires_reply"] == "no"
    assert card["display_mode"] == "hidden"
    assert database.list_cards() == []


def test_sender_email_is_not_removed_as_html(pipeline, database):
    result = pipeline.process(event(sender="陳教授 <professor@example.edu>"))
    card = database.card_detail(result.card_id)

    assert card["sender"] == "陳教授 <professor@example.edu>"


def test_hourly_interruption_budget_routes_excess_to_digest(pipeline, database):
    results = []
    for index in range(5):
        results.append(
            pipeline.process(
                event(
                    event_id=f"budget-{index}",
                    conversation_id=f"budget-thread-{index}",
                    metadata={"message_id": f"budget-{index}", "history_id": "1"},
                )
            )
        )
    first_four = [database.card_detail(result.card_id) for result in results[:4]]
    fifth = database.card_detail(results[4].card_id)
    assert all(card["decision"]["decision"] == "surface_now" for card in first_four)
    assert fifth["decision"]["decision"] == "include_in_digest"
    assert "interruption_budget" in fifth["why_shown"]
