from datetime import datetime
from zoneinfo import ZoneInfo

from signaldesk.models import WindowsNotificationPayload
from signaldesk.normalizer import normalize_windows


def test_edge_messenger_person_notification_is_classified_by_visible_preview():
    event = normalize_windows(
        WindowsNotificationPayload(
            notification_id="edge-1",
            app_id="Microsoft.MicrosoftEdge.Stable_8wekyb3d8bbwe!App",
            app_name="Microsoft Edge",
            title="劉威廷",
            sender="劉威廷",
            body="3 則同一對話訊息：測試訊息。傳送了 1 張貼圖。",
            received_at=datetime(2026, 8, 3, 16, 52, tzinfo=ZoneInfo("Asia/Taipei")),
        )
    )

    assert event.source == "messenger_notification"
    assert event.sender == "劉威廷"
    assert event.conversation_id == "劉威廷"
    assert event.source_url == "https://www.messenger.com/"


def test_ordinary_edge_notification_is_not_reclassified_as_messenger():
    event = normalize_windows(
        WindowsNotificationPayload(
            notification_id="edge-2",
            app_id="Microsoft.MicrosoftEdge.Stable_8wekyb3d8bbwe!App",
            app_name="Microsoft Edge",
            title="網站通知",
            body="新文章已經發布。",
            received_at=datetime(2026, 8, 3, 16, 53, tzinfo=ZoneInfo("Asia/Taipei")),
        )
    )

    assert event.source == "windows_notification"
