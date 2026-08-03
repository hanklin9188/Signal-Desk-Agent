from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from signaldesk.models import UnifiedEvent

NOW = datetime(2026, 8, 3, 8, 0, tzinfo=ZoneInfo("Asia/Taipei"))


def gmail_event(account: str, message_id: str, thread_id: str) -> UnifiedEvent:
    return UnifiedEvent(
        event_id=f"gmail_{account}_{message_id}_10",
        source="gmail",
        source_app_id="gmail",
        account_id=account,
        sender="sender@example.com",
        conversation_id=thread_id,
        title="Test",
        content="Please reply.",
        content_completeness="full",
        received_at=NOW,
        privacy_class="sensitive",
        metadata={"message_id": message_id, "history_id": "10"},
    )


def test_cleanup_removes_only_legacy_gmail_rows(pipeline, database):
    primary = pipeline.process(gmail_event("primary", "old-primary", "primary-thread"))
    wrong_personal = pipeline.process(
        gmail_event("personal", "school-message", "wrong-personal-thread")
    )
    retained_school = pipeline.process(gmail_event("nycu", "school-message", "school-thread"))
    retained_personal = pipeline.process(
        gmail_event("personal", "personal-message", "personal-thread")
    )

    assert database.audit_legacy_gmail_data() == {
        "primary_events": 1,
        "personal_events_overlapping_nycu": 1,
        "affected_threads": 2,
        "affected_cards": 2,
        "mixed_threads": 0,
    }

    removed = database.cleanup_legacy_gmail_data()

    assert removed == {
        "primary_events": 1,
        "personal_events_overlapping_nycu": 1,
        "threads": 2,
        "cards": 2,
    }
    assert database.card_detail(primary.card_id) is None
    assert database.card_detail(wrong_personal.card_id) is None
    assert database.card_detail(retained_school.card_id) is not None
    assert database.card_detail(retained_personal.card_id) is not None
    assert database.audit_legacy_gmail_data()["primary_events"] == 0
    assert database.audit_legacy_gmail_data()["personal_events_overlapping_nycu"] == 0
