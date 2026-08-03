from __future__ import annotations

import base64
import hashlib
import json
from datetime import UTC, datetime
from email.header import decode_header, make_header
from email.mime.text import MIMEText
from email.utils import parseaddr
from pathlib import Path
from typing import Any
from urllib.parse import quote

from ..models import UnifiedEvent
from ..normalizer import clean_text
from .base import Connector, ConnectorHealth, SyncBatch

READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
DRAFT_SCOPE = "https://www.googleapis.com/auth/gmail.compose"


class GmailConnector(Connector):
    """Official Gmail API connector. Credentials live in the OS keyring, never SQLite."""

    source = "gmail"

    def __init__(
        self,
        account_id: str,
        client_secrets: Path,
        *,
        draft_scope: bool = False,
        keyring_service: str = "SignalDesk.Gmail",
    ):
        self.account_id = account_id
        self.connector_id = f"gmail:{account_id}"
        self.client_secrets = client_secrets
        self.draft_scope = draft_scope
        self.keyring_service = keyring_service
        self._service: Any = None
        self._error: str | None = None
        self.authenticated_email: str | None = None

    @property
    def scopes(self) -> list[str]:
        return [READONLY_SCOPE, *([DRAFT_SCOPE] if self.draft_scope else [])]

    def _imports(self) -> tuple[Any, Any, Any, Any]:
        try:
            import keyring
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError as error:
            raise RuntimeError("install SignalDesk with the 'gmail' extra") from error
        return keyring, Credentials, InstalledAppFlow, build

    def authenticate(self, *, interactive: bool = True) -> bool:
        try:
            keyring, credentials_type, flow_type, build = self._imports()
            stored = keyring.get_password(self.keyring_service, self.account_id)
            credentials = (
                credentials_type.from_authorized_user_info(json.loads(stored), self.scopes)
                if stored
                else None
            )
            if not credentials or not credentials.valid:
                if credentials and credentials.expired and credentials.refresh_token:
                    from google.auth.transport.requests import Request

                    credentials.refresh(Request())
                elif interactive:
                    flow = flow_type.from_client_secrets_file(str(self.client_secrets), self.scopes)
                    credentials = flow.run_local_server(
                        host="127.0.0.1",
                        port=0,
                        open_browser=True,
                        prompt="select_account",
                    )
                else:
                    self._error = "OAuth authorization is required"
                    return False
                keyring.set_password(self.keyring_service, self.account_id, credentials.to_json())
            self._service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
            profile = self._service.users().getProfile(userId="me").execute()
            self.authenticated_email = str(profile.get("emailAddress", "")).strip() or None
            self._error = None
            return True
        except Exception as error:
            self._service = None
            self.authenticated_email = None
            self._error = f"{type(error).__name__}: {error}"
            return False

    def initial_sync(self) -> SyncBatch:
        service = self._require_service()
        profile = service.users().getProfile(userId="me").execute()
        self.authenticated_email = str(profile.get("emailAddress", "")).strip() or None
        response = (
            service.users()
            .messages()
            .list(userId="me", labelIds=["INBOX"], maxResults=50)
            .execute()
        )
        events = [self._message_event(message["id"]) for message in response.get("messages", [])]
        return SyncBatch(events=events, cursor=str(profile.get("historyId")))

    def incremental_sync(self, cursor: str | None) -> SyncBatch:
        if not cursor:
            return self.initial_sync()
        service = self._require_service()
        try:
            response = (
                service.users()
                .history()
                .list(userId="me", startHistoryId=cursor, historyTypes=["messageAdded"])
                .execute()
            )
        except Exception as error:
            if (
                getattr(error, "status_code", None) == 404
                or getattr(getattr(error, "resp", None), "status", None) == 404
            ):
                return SyncBatch(events=[], cursor=None, full_sync_required=True)
            raise
        ids = {
            item["message"]["id"]
            for history in response.get("history", [])
            for item in history.get("messagesAdded", [])
        }
        return SyncBatch(
            events=[self._message_event(message_id) for message_id in ids],
            cursor=str(response.get("historyId", cursor)),
        )

    def health(self) -> ConnectorHealth:
        status = "error" if self._error else ("healthy" if self._service else "not_configured")
        detail = (
            f"Connected as {self.authenticated_email}"
            if self._service and self.authenticated_email
            else "Gmail connected"
            if self._service
            else "OAuth not completed"
        )
        return ConnectorHealth(
            connector_id=self.connector_id,
            source=self.source,
            status=status,
            detail=self._error or detail,
            capabilities=["read", *(["create_draft"] if self.draft_scope else [])],
        )

    def revoke(self) -> None:
        keyring, *_ = self._imports()
        try:
            keyring.delete_password(self.keyring_service, self.account_id)
        except Exception:
            pass
        self._service = None
        self.authenticated_email = None

    def create_draft(
        self,
        *,
        recipient: str,
        subject: str,
        body: str,
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        if not self.draft_scope:
            raise RuntimeError("Gmail draft scope is not enabled for this account")
        address = parseaddr(recipient)[1] or recipient
        if not address or "@" not in address:
            raise ValueError("draft recipient is not a valid email address")
        message = MIMEText(body, _charset="utf-8")
        message["to"] = address
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        draft_body: dict[str, Any] = {"message": {"raw": raw}}
        if thread_id:
            draft_body["message"]["threadId"] = thread_id
        return (
            self._require_service().users().drafts().create(userId="me", body=draft_body).execute()
        )

    def _require_service(self) -> Any:
        if self._service is None and not self.authenticate():
            raise RuntimeError(self._error or "Gmail authentication failed")
        return self._service

    def _message_event(self, message_id: str) -> UnifiedEvent:
        message = (
            self._require_service()
            .users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        headers = {
            item["name"].lower(): str(make_header(decode_header(item["value"])))
            for item in message.get("payload", {}).get("headers", [])
        }
        content = self._extract_body(message.get("payload", {}))
        received_at = datetime.fromtimestamp(int(message["internalDate"]) / 1000, tz=UTC)
        history_id = str(message.get("historyId", "initial"))
        thread_id = message.get("threadId")
        source_url = (
            f"https://mail.google.com/mail/?authuser={quote(self.authenticated_email)}"
            f"#inbox/{thread_id}"
            if self.authenticated_email and thread_id
            else f"https://mail.google.com/mail/#inbox/{thread_id}"
            if thread_id
            else "https://mail.google.com/mail/"
        )
        return UnifiedEvent(
            event_id=f"gmail_{self.account_id}_{message_id}_{history_id}",
            source="gmail",
            source_app_id="gmail",
            account_id=self.account_id,
            sender=headers.get("from", "Unknown sender"),
            conversation_id=thread_id,
            title=headers.get("subject"),
            content=content or message.get("snippet", ""),
            content_completeness="full",
            received_at=received_at,
            source_url=source_url,
            privacy_class="sensitive",
            metadata={
                "message_id": message_id,
                "history_id": history_id,
                "labels": message.get("labelIds", []),
            },
            checksum=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        )

    @classmethod
    def _extract_body(cls, payload: dict[str, Any]) -> str:
        mime = payload.get("mimeType", "")
        body_data = payload.get("body", {}).get("data")
        if body_data and mime in {"text/plain", "text/html"}:
            decoded = base64.urlsafe_b64decode(body_data + "==").decode("utf-8", errors="replace")
            return clean_text(decoded)
        parts = payload.get("parts", [])
        plain = [cls._extract_body(part) for part in parts if part.get("mimeType") == "text/plain"]
        if any(plain):
            return "\n".join(item for item in plain if item)
        html_parts = [
            cls._extract_body(part) for part in parts if part.get("mimeType") == "text/html"
        ]
        return "\n".join(item for item in html_parts if item)
