from __future__ import annotations

import base64
import json
import zipfile
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from signaldesk.api import create_app
from signaldesk.connectors.chat_archive import load_chat_archives
from signaldesk.connectors.gmail import GmailConnector
from signaldesk.media_store import MediaError, MediaStore
from signaldesk.model_gateway import _multimodal_user_content
from signaldesk.models import GroupedThread, UnifiedEvent

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def test_media_store_rejects_declared_type_mismatch(tmp_path):
    store = MediaStore(tmp_path / "media")

    with pytest.raises(MediaError, match="does not match"):
        store.import_bytes(PNG_1X1, declared_mime="image/jpeg")


def test_model_content_uses_endpoint_and_transformers_image_contracts(tmp_path):
    store = MediaStore(tmp_path / "media")
    media = store.import_bytes(PNG_1X1, declared_mime="image/png")
    thread = GroupedThread(
        thread_id="thread-image",
        source="gmail",
        sender="sender@example.com",
        event_ids=["event-image"],
        content_completeness="full",
        messages=[
            {
                "event_id": "event-image",
                "received_at": datetime(2026, 8, 3, 9, 0, tzinfo=UTC),
                "content": "請看圖片",
                "media": [media],
            }
        ],
        updated_at=datetime(2026, 8, 3, 9, 0, tzinfo=UTC),
    )

    endpoint = _multimodal_user_content(thread, "prompt", store)
    transformers = _multimodal_user_content(
        thread, "prompt", store, openai_style=False
    )

    assert isinstance(endpoint, list)
    assert endpoint[1]["type"] == "image_url"
    assert endpoint[1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert isinstance(transformers, list)
    assert transformers[1]["type"] == "image"
    assert transformers[1]["url"].startswith("data:image/png;base64,")


def test_gmail_connector_imports_supported_inline_image(tmp_path):
    store = MediaStore(tmp_path / "media")
    connector = GmailConnector(
        "personal",
        tmp_path / "credentials.json",
        media_store=store,
    )
    payload = {
        "mimeType": "multipart/mixed",
        "parts": [
            {
                "mimeType": "image/png",
                "filename": "schedule.png",
                "body": {
                    "size": len(PNG_1X1),
                    "data": base64.urlsafe_b64encode(PNG_1X1).decode("ascii"),
                },
            }
        ],
    }

    media = connector._extract_media(payload, "gmail-message-1")

    assert len(media) == 1
    assert media[0].availability == "available"
    assert media[0].mime_type == "image/png"
    assert store.path_for(media[0]).read_bytes() == PNG_1X1


def test_messenger_zip_imports_referenced_image_without_extracting_archive(tmp_path):
    store = MediaStore(tmp_path / "media")
    payload = {
        "participants": [{"name": "Alice"}],
        "title": "Alice",
        "messages": [
            {
                "sender_name": "Alice",
                "timestamp_ms": 1785578520000,
                "photos": [{"uri": "messages/inbox/alice/photo.png"}],
            }
        ],
    }
    archive_path = tmp_path / "messenger.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "messages/inbox/alice/message_1.json",
            json.dumps(payload),
        )
        archive.writestr("messages/inbox/alice/photo.png", PNG_1X1)

    parsed = load_chat_archives(
        "messenger",
        [archive_path],
        timezone="Asia/Taipei",
        media_store=store,
    )

    assert len(parsed.events) == 1
    assert parsed.events[0].content_completeness == "full"
    assert parsed.events[0].media[0].availability == "available"
    assert store.path_for(parsed.events[0].media[0]).read_bytes() == PNG_1X1


def test_messenger_zip_blocks_parent_path_media_reference(tmp_path):
    store = MediaStore(tmp_path / "media")
    payload = {
        "participants": [{"name": "Alice"}],
        "title": "Alice",
        "messages": [
            {
                "sender_name": "Alice",
                "timestamp_ms": 1785578520000,
                "photos": [{"uri": "../outside.png"}],
            }
        ],
    }
    archive_path = tmp_path / "unsafe-messenger.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("messages/alice/message_1.json", json.dumps(payload))
        archive.writestr("messages/outside.png", PNG_1X1)

    parsed = load_chat_archives(
        "messenger",
        [archive_path],
        timezone="Asia/Taipei",
        media_store=store,
    )

    assert parsed.events[0].media[0].availability == "blocked"
    assert list((tmp_path / "media").glob("media_*")) == []


def test_media_is_content_addressed_and_available_to_authenticated_ui(
    test_config, database, pipeline
):
    store = MediaStore(test_config.data_dir / "media")
    media = store.import_bytes(
        PNG_1X1,
        declared_mime="image/png",
        kind="screenshot",
        original_name="../../private/screenshot.png",
    )
    event = UnifiedEvent(
        event_id="gmail-with-image",
        source="gmail",
        source_app_id="gmail",
        account_id="personal",
        sender="sender@example.com",
        conversation_id="image-thread",
        title="請確認截圖",
        content="附件是本週排程截圖，請協助確認。",
        content_completeness="full",
        received_at=datetime(2026, 8, 3, 9, 0, tzinfo=UTC),
        media=[media],
        metadata={"message_id": "image-1", "history_id": "1"},
    )

    result = pipeline.process(event)
    detail = database.card_detail(result.card_id)
    assert detail["events"][0]["media"][0]["asset_id"] == media.asset_id
    assert database.media_for_event(event.event_id) == [media]
    assert media.original_name == "screenshot.png"

    with TestClient(create_app(test_config, database)) as client:
        assert client.get(f"/api/v1/media/{media.asset_id}").status_code == 401
        client.get("/")
        response = client.get(f"/api/v1/media/{media.asset_id}")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert response.content == PNG_1X1
    assert response.headers["cache-control"] == "private, no-store"
    assert "visual_evidence_unverified" in detail["uncertainty_flags"]


def test_private_data_delete_removes_media_files(test_config, database):
    store = MediaStore(test_config.data_dir / "media")
    media = store.import_bytes(PNG_1X1, declared_mime="image/png")
    assert store.path_for(media).exists()

    with TestClient(create_app(test_config, database)) as client:
        client.get("/")
        response = client.post(
            "/api/v1/privacy/delete",
            json={"confirmation": "DELETE MY SIGNALDESK DATA"},
        )
        assert response.status_code == 200

    assert list((test_config.data_dir / "media").glob("media_*")) == []


def test_account_data_cleanup_returns_orphaned_media(test_config, database, pipeline):
    store = MediaStore(test_config.data_dir / "media")
    media = store.import_bytes(PNG_1X1, declared_mime="image/png")
    event = UnifiedEvent(
        event_id="gmail-cleanup-image",
        source="gmail",
        account_id="personal",
        sender="sender@example.com",
        conversation_id="cleanup-thread",
        content="image",
        content_completeness="full",
        received_at=datetime(2026, 8, 3, 9, 0, tzinfo=UTC),
        media=[media],
        metadata={"message_id": "cleanup", "history_id": "1"},
    )
    pipeline.process(event)
    media_path = store.path_for(media)

    database.delete_source_account_data("gmail", "personal")
    orphaned = database.delete_orphan_media()

    assert orphaned == [media]
    assert store.delete(orphaned[0]) is True
    assert media_path.exists() is False
