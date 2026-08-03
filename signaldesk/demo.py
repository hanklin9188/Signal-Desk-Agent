from __future__ import annotations

from datetime import timedelta
from zoneinfo import ZoneInfo

from .models import UnifiedEvent
from .pipeline import Pipeline


def seed_demo(pipeline: Pipeline) -> list[dict[str, object]]:
    zone = ZoneInfo(pipeline.config.timezone)
    now = __import__("datetime").datetime.now(zone).replace(microsecond=0)
    events = [
        UnifiedEvent(
            event_id="demo_gmail_professor",
            source="gmail",
            source_app_id="gmail",
            account_id="demo_work",
            sender="陳教授 <professor@example.edu>",
            conversation_id="demo_thread_research",
            title="實驗進度與圖表",
            content="請在今晚前把目前的實驗結果與圖表寄給我，另外附上異常樣本的說明，謝謝。",
            content_completeness="full",
            received_at=now - timedelta(minutes=12),
            source_url="https://mail.google.com/",
            privacy_class="sensitive",
            metadata={"message_id": "demo-professor", "history_id": "1", "labels": ["IMPORTANT"]},
        ),
        UnifiedEvent(
            event_id="demo_line_lab_1",
            source="line_notification",
            source_app_id="LINE",
            account_id="demo_windows",
            sender="實驗室群組",
            title="實驗室群組",
            content="明天會議改到下午三點",
            content_completeness="notification_preview",
            received_at=now - timedelta(minutes=7, seconds=10),
            raw_notification_id="demo-line-1",
            privacy_class="private",
            metadata={},
        ),
        UnifiedEvent(
            event_id="demo_line_lab_2",
            source="line_notification",
            source_app_id="LINE",
            account_id="demo_windows",
            sender="實驗室群組",
            title="實驗室群組",
            content="教授也會參加，你可以嗎？",
            content_completeness="notification_preview",
            received_at=now - timedelta(minutes=7),
            raw_notification_id="demo-line-2",
            privacy_class="private",
            metadata={},
        ),
        UnifiedEvent(
            event_id="demo_messenger_photo",
            source="messenger_notification",
            source_app_id="Microsoft Edge",
            account_id="demo_windows",
            sender="王小明",
            title="Messenger · 王小明",
            content="傳送了一張相片",
            content_completeness="notification_preview",
            received_at=now - timedelta(minutes=3),
            raw_notification_id="demo-messenger-1",
            privacy_class="private",
            metadata={"origin": "messenger.com"},
        ),
        UnifiedEvent(
            event_id="demo_security",
            source="gmail",
            source_app_id="gmail",
            account_id="demo_personal",
            sender="Google Accounts <no-reply@accounts.google.com>",
            conversation_id="demo_security_thread",
            title="Security alert",
            content="偵測到新的可疑登入活動。若這不是你，請立即檢查帳戶安全性。",
            content_completeness="full",
            received_at=now - timedelta(minutes=1),
            source_url="https://myaccount.google.com/notifications",
            privacy_class="sensitive",
            metadata={"message_id": "demo-security", "history_id": "1"},
        ),
        UnifiedEvent(
            event_id="demo_newsletter",
            source="gmail",
            source_app_id="gmail",
            account_id="demo_personal",
            sender="AI Weekly <weekly@example.com>",
            conversation_id="demo_newsletter_thread",
            title="本週 AI 精選與限時優惠",
            content="本週精選文章與限時優惠，現在訂閱可獲得折扣碼。取消訂閱請點頁尾連結。",
            content_completeness="full",
            received_at=now - timedelta(hours=2),
            source_url="https://mail.google.com/",
            privacy_class="normal",
            metadata={"message_id": "demo-news", "history_id": "1"},
        ),
    ]
    return [pipeline.process(event).model_dump(mode="json") for event in events]
