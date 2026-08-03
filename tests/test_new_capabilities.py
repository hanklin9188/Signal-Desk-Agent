from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from signaldesk.actions import CardActions
from signaldesk.api import _default_gmail_credentials, create_app
from signaldesk.connectors.gmail import GmailConnector
from signaldesk.events import EventBus
from signaldesk.models import CardActionRequest, UnifiedEvent
from signaldesk.preference import PreferenceRanker


def test_two_optional_gmail_accounts_can_be_registered(test_config, database):
    with TestClient(create_app(test_config, database)) as client:
        client.get("/")
        for alias, draft_scope in (("work", True), ("nycu", False)):
            response = client.post(
                "/api/v1/connectors/gmail/accounts",
                json={"account_id": alias, "draft_scope": draft_scope},
            )
            assert response.status_code == 201
        connectors = client.get("/api/v1/connectors").json()["items"]
        ids = {item["connector_id"] for item in connectors}
        assert {"gmail:personal", "gmail:work", "gmail:nycu"} <= ids
        assert next(item for item in connectors if item["connector_id"] == "gmail:work")[
            "capabilities"
        ] == ["read", "read_images", "create_draft"]


def test_existing_gmail_account_can_be_configured_before_oauth(test_config, database, tmp_path):
    credentials = tmp_path / "desktop-oauth.json"
    with TestClient(create_app(test_config, database)) as client:
        client.get("/")
        response = client.patch(
            "/api/v1/connectors/gmail/accounts/personal",
            json={"credentials_path": str(credentials), "draft_scope": True},
        )
        assert response.status_code == 200
        assert response.json() == {
            "account_id": "personal",
            "connector_id": "gmail:personal",
            "credentials_path": str(credentials),
            "draft_scope": True,
            "authorization_required": True,
        }
        configured = database.connector_accounts("gmail")[0]
        assert configured["config"]["credentials_path"] == str(credentials)
        assert configured["config"]["draft_scope"] is True


def test_gmail_account_data_reset_is_scoped_and_requires_confirmation(
    test_config, database
):
    with TestClient(create_app(test_config, database)) as client:
        client.get("/")
        added = client.post(
            "/api/v1/connectors/gmail/accounts",
            json={"account_id": "nycu", "draft_scope": False},
        )
        assert added.status_code == 201
        ingested = client.post(
            "/api/v1/events",
            json={
                "event_id": "wrong-account-message",
                "source": "gmail",
                "account_id": "nycu",
                "sender": "sender@example.com",
                "conversation_id": "thread-1",
                "title": "Wrong account",
                "content": "This event should be removed",
                "content_completeness": "full",
                "received_at": "2026-08-03T12:00:00Z",
                "metadata": {"message_id": "m1", "history_id": "h1"},
            },
        )
        assert ingested.status_code == 201

        rejected = client.post(
            "/api/v1/connectors/gmail/accounts/nycu/reset-data",
            json={"confirmation": "reset"},
        )
        assert rejected.status_code == 400
        reset = client.post(
            "/api/v1/connectors/gmail/accounts/nycu/reset-data",
            json={"confirmation": "RESET GMAIL ACCOUNT DATA"},
        )
        assert reset.status_code == 200
        assert reset.json()["removed"] == {"events": 1, "threads": 1}
        assert database.event("wrong-account-message") is None


def test_windows_default_gmail_credentials_live_outside_app_package(tmp_path, monkeypatch):
    monkeypatch.delenv("SIGNALDESK_GMAIL_CREDENTIALS", raising=False)
    expected = tmp_path / "SignalDesk" / "oauth" / "credentials.json"
    assert _default_gmail_credentials(platform="nt", local_app_data=str(tmp_path)) == expected


def test_explicit_gmail_credentials_path_takes_precedence(tmp_path, monkeypatch):
    selected = tmp_path / "selected-client.json"
    monkeypatch.setenv("SIGNALDESK_GMAIL_CREDENTIALS", str(selected))
    assert _default_gmail_credentials(platform="nt", local_app_data="ignored") == selected


def test_gmail_source_link_targets_the_authenticated_account(tmp_path):
    body = base64.urlsafe_b64encode("請回覆".encode()).decode()
    message = {
        "id": "message-1",
        "threadId": "thread-1",
        "historyId": "history-1",
        "internalDate": "1785718800000",
        "labelIds": ["INBOX"],
        "payload": {
            "mimeType": "text/plain",
            "body": {"data": body},
            "headers": [
                {"name": "From", "value": "Sender <sender@example.com>"},
                {"name": "Subject", "value": "Question"},
            ],
        },
    }

    class Request:
        @staticmethod
        def execute():
            return message

    class Messages:
        @staticmethod
        def get(**_values):
            return Request()

    class Users:
        @staticmethod
        def messages():
            return Messages()

    class Service:
        @staticmethod
        def users():
            return Users()

    connector = GmailConnector("nycu", tmp_path / "credentials.json")
    connector._service = Service()
    connector.authenticated_email = "student@example.edu"
    event = connector._message_event("message-1")

    assert event.account_id == "nycu"
    assert event.source_url == (
        "https://mail.google.com/mail/?authuser=student%40example.edu#inbox/thread-1"
    )


def test_digest_and_model_residency_settings_validate(test_config, database):
    with TestClient(create_app(test_config, database)) as client:
        client.get("/")
        response = client.patch(
            "/api/v1/settings",
            json={
                "digest_time": "19:30",
                "focus_digest_minutes": 45,
                "model_residency": "on_demand",
            },
        )
        assert response.status_code == 200
        assert response.json()["digest_time"] == "19:30"
        assert response.json()["focus_digest_minutes"] == 45


def test_preference_ranker_keeps_content_out_and_requires_calibration(database):
    ranker = PreferenceRanker(database)
    card = {
        "source": "gmail",
        "sender": "Professor Example <private@example.edu>",
        "category": "work",
        "requires_reply": "yes",
        "deadline_text": "tomorrow",
        "created_at": datetime.now(UTC).isoformat(),
    }
    for _ in range(7):
        assert ranker.observe(card, "opened") is False
    assert database.preference_weights() == {}
    ranker.observe(card, "opened")
    observations = database.preference_observations()
    serialized = str(observations)
    assert "private@example.edu" not in serialized
    assert database.preference_weights()


def test_gmail_cloud_draft_requires_exact_confirmation(test_config, database, pipeline):
    event = {
        "event_id": "draft-confirm-event",
        "source": "gmail",
        "source_app_id": "gmail",
        "account_id": "primary",
        "sender": "person@example.com",
        "conversation_id": "draft-thread",
        "title": "Please reply",
        "content": "Can you reply tomorrow?",
        "content_completeness": "full",
        "received_at": "2026-08-03T09:00:00+08:00",
    }
    result = pipeline.process(UnifiedEvent(**event))
    draft = CardActions(database, EventBus()).perform(
        result.card_id, CardActionRequest(action="draft_reply", value={"body": "Thanks"})
    )
    with TestClient(create_app(test_config, database)) as client:
        client.get("/")
        rejected = client.post(
            f"/api/v1/drafts/{draft['draft_id']}/gmail", json={"confirmation": "yes"}
        )
        assert rejected.status_code == 400


def test_confirmed_gmail_cloud_draft_is_created_but_never_sent(test_config, database, pipeline):
    event = UnifiedEvent(
        event_id="cloud-draft-event",
        source="gmail",
        source_app_id="gmail",
        account_id="primary",
        sender="Person <person@example.com>",
        conversation_id="cloud-draft-thread",
        title="Question",
        content="Can you reply tomorrow?",
        content_completeness="full",
        received_at="2026-08-03T09:00:00+08:00",
    )
    result = pipeline.process(event)
    draft = CardActions(database, EventBus()).perform(
        result.card_id, CardActionRequest(action="draft_reply", value={"body": "Thanks"})
    )

    class FakeGmail:
        account_id = "primary"
        connector_id = "gmail:primary"
        draft_scope = True

        @staticmethod
        def create_draft(**values):
            assert values["recipient"] == "Person <person@example.com>"
            assert values["body"] == "Thanks"
            return {"id": "provider-draft-1"}

    app = create_app(test_config, database)
    app.state.gmail_connectors["primary"] = FakeGmail()
    with TestClient(app) as client:
        client.get("/")
        response = client.post(
            f"/api/v1/drafts/{draft['draft_id']}/gmail",
            json={"confirmation": "CREATE GMAIL DRAFT"},
        )
        assert response.status_code == 200
        assert response.json() == {
            "created": True,
            "draft_id": draft["draft_id"],
            "gmail_draft_id": "provider-draft-1",
            "sent": False,
        }


def test_line_official_webhook_requires_signature(test_config, database, monkeypatch):
    secret = "line-test-secret"
    monkeypatch.setenv("SIGNALDESK_LINE_CHANNEL_SECRET", secret)
    payload = {
        "events": [
            {
                "type": "message",
                "timestamp": 1785718800000,
                "webhookEventId": "line-hook-1",
                "source": {"type": "user", "userId": "user-1"},
                "message": {"type": "text", "id": "line-message-1", "text": "明天請回覆"},
            }
        ]
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    signature = base64.b64encode(hmac.new(secret.encode(), raw, hashlib.sha256).digest()).decode()
    with TestClient(create_app(test_config, database)) as client:
        rejected = client.post("/webhooks/line", content=raw)
        accepted = client.post(
            "/webhooks/line",
            content=raw,
            headers={"X-Line-Signature": signature, "Content-Type": "application/json"},
        )
        assert rejected.status_code == 401
        assert accepted.status_code == 200
        assert accepted.json()["processed"] == 1


def test_messenger_page_webhook_verify_and_signature(test_config, database, monkeypatch):
    secret = "meta-test-secret"
    verify = "verify-test-token"
    monkeypatch.setenv("SIGNALDESK_META_APP_SECRET", secret)
    monkeypatch.setenv("SIGNALDESK_META_VERIFY_TOKEN", verify)
    raw = json.dumps(
        {
            "object": "page",
            "entry": [
                {
                    "id": "page-1",
                    "messaging": [
                        {
                            "sender": {"id": "person-1"},
                            "timestamp": 1785718800000,
                            "message": {"mid": "meta-message-1", "text": "Please reply tomorrow"},
                        }
                    ],
                }
            ],
        },
        separators=(",", ":"),
    ).encode()
    signature = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    with TestClient(create_app(test_config, database)) as client:
        verified = client.get(
            "/webhooks/messenger",
            params={"hub.mode": "subscribe", "hub.verify_token": verify, "hub.challenge": "42"},
        )
        accepted = client.post(
            "/webhooks/messenger",
            content=raw,
            headers={"X-Hub-Signature-256": signature, "Content-Type": "application/json"},
        )
        assert verified.text == "42"
        assert accepted.status_code == 200
        assert accepted.json()["processed"] == 1
