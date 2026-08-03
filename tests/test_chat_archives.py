from __future__ import annotations

import json
import zipfile

from fastapi.testclient import TestClient

from signaldesk.api import create_app
from signaldesk.connectors.chat_archive import load_chat_archives


def test_line_text_archive_parses_multiline_and_dates(tmp_path):
    archive = tmp_path / "實驗室群組_chat.txt"
    archive.write_text(
        """[LINE] 與 實驗室群組 的聊天記錄
儲存日期：2026/08/03
2026/08/01（六）
上午 10:00\tAlice\t早安
上午 10:01\tHank\t請在明天以前回覆
這是同一則訊息的第二行
""",
        encoding="utf-8",
    )

    parsed = load_chat_archives("line", [archive], timezone="Asia/Taipei")

    assert len(parsed.events) == 2
    assert parsed.conversations == {"實驗室群組"}
    assert parsed.events[0].conversation_id == "實驗室群組"
    assert parsed.events[1].content == "請在明天以前回覆\n這是同一則訊息的第二行"
    assert parsed.events[1].received_at.isoformat() == "2026-08-01T10:01:00+08:00"


def test_messenger_zip_archive_parses_messages_and_attachment_placeholders(tmp_path):
    payload = {
        "participants": [{"name": "Hank"}, {"name": "Alice"}],
        "messages": [
            {
                "sender_name": "Alice",
                "timestamp_ms": 1785578520000,
                "content": "可以明天回覆嗎？",
            },
            {
                "sender_name": "Hank",
                "timestamp_ms": 1785578460000,
                "photos": [{"uri": "messages/inbox/photo.jpg"}],
            },
        ],
        "title": "Alice",
        "thread_path": "inbox/alice_123",
    }
    archive = tmp_path / "facebook-export.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr(
            "your_facebook_activity/messages/inbox/alice_123/message_1.json",
            json.dumps(payload, ensure_ascii=False),
        )

    parsed = load_chat_archives("messenger", [archive], timezone="Asia/Taipei")

    assert len(parsed.events) == 2
    assert parsed.conversations == {"Alice"}
    assert parsed.events[0].content == "[圖片]"
    assert parsed.events[0].content_completeness == "metadata_only"
    assert parsed.events[1].content == "可以明天回覆嗎？"


def test_messenger_secure_storage_zip_uses_camel_case_fields(tmp_path):
    payload = {
        "participants": ["Hank", "Alice"],
        "threadName": "Alice_15",
        "messages": [
            {
                "senderName": "Alice",
                "timestamp": 1785578520000,
                "text": "新版安全儲存格式",
                "media": [],
                "isUnsent": False,
            },
            {
                "senderName": "Hank",
                "timestamp": 1785578580000,
                "text": "",
                "media": [{"type": "IMAGE", "uri": "media/photo.jpeg"}],
                "isUnsent": False,
            },
            {
                "senderName": "Alice",
                "timestamp": 1785578640000,
                "text": "不應匯入",
                "media": [],
                "isUnsent": True,
            },
        ],
    }
    archive = tmp_path / "messages.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("Alice_15.json", json.dumps(payload, ensure_ascii=False))

    parsed = load_chat_archives("messenger", [archive], timezone="Asia/Taipei")

    assert len(parsed.events) == 2
    assert parsed.conversations == {"Alice"}
    assert parsed.events[0].conversation_id == "Alice"
    assert parsed.events[0].sender == "Alice"
    assert parsed.events[0].content == "新版安全儲存格式"
    assert parsed.events[1].content == "[圖片]"
    assert parsed.skipped == 1


def test_archive_api_imports_deduplicates_and_joins_future_notification(
    test_config, database, tmp_path
):
    archive = tmp_path / "朋友_chat.txt"
    archive.write_text(
        """[LINE] 與 朋友 的聊天記錄
2026/08/01
10:00\t朋友\t舊訊息
10:01\tHank\t收到
""",
        encoding="utf-8",
    )

    with TestClient(create_app(test_config, database)) as client:
        client.get("/")
        first = client.post(
            "/api/v1/connectors/chat-archives/import",
            json={"source": "line", "paths": [str(archive)]},
        )
        assert first.status_code == 200
        assert first.json()["imported"] == 2
        assert first.json()["conversations"] == 1

        second = client.post(
            "/api/v1/connectors/chat-archives/import",
            json={"source": "line", "paths": [str(archive)]},
        )
        assert second.status_code == 200
        assert second.json()["imported"] == 0
        assert second.json()["duplicates"] == 2

        cards = client.get("/api/v1/cards").json()["items"]
        assert len(cards) == 1
        archive_thread = cards[0]["thread_id"]
        historical_search = client.get("/api/v1/cards", params={"search": "舊訊息"})
        assert historical_search.status_code == 200
        assert historical_search.json()["items"][0]["thread_id"] == archive_thread
        matching_toast = client.post(
            "/api/v1/connectors/windows/notifications",
            json={
                "notification_id": "line-existing-1",
                "app_id": "LINE",
                "app_name": "LINE",
                "title": "朋友",
                "body": "舊訊息",
                "received_at": "2026-08-01T10:02:00+08:00",
            },
        )
        assert matching_toast.status_code == 201
        assert matching_toast.json()["duplicate"] is True
        assert matching_toast.json()["thread_id"] == archive_thread
        notification = client.post(
            "/api/v1/connectors/windows/notifications",
            json={
                "notification_id": "line-future-1",
                "app_id": "LINE",
                "app_name": "LINE",
                "title": "朋友",
                "body": "這是匯入後的新訊息",
                "received_at": "2026-08-03T12:00:00+08:00",
            },
        )
        assert notification.status_code == 201
        assert notification.json()["thread_id"] == archive_thread


def test_archive_api_rejects_wrong_format(test_config, database, tmp_path):
    archive = tmp_path / "messages.csv"
    archive.write_text("not supported", encoding="utf-8")
    with TestClient(create_app(test_config, database)) as client:
        client.get("/")
        response = client.post(
            "/api/v1/connectors/chat-archives/import",
            json={"source": "line", "paths": [str(archive)]},
        )
    assert response.status_code == 400
    assert ".txt" in response.json()["detail"]
