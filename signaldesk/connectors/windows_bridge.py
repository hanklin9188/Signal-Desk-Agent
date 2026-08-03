from __future__ import annotations

from ..models import UnifiedEvent, WindowsNotificationPayload
from ..normalizer import normalize_windows
from .base import Connector, ConnectorHealth, SyncBatch


class WindowsBridgeConnector(Connector):
    """Receives payloads captured by the packaged Windows native shell."""

    connector_id = "windows-notifications"
    source = "windows_notification"

    def __init__(self) -> None:
        self.last_error: str | None = None
        self.permission = "bridge_waiting"

    def set_permission(self, permission: str, detail: str | None = None) -> None:
        self.permission = permission
        self.last_error = detail if permission == "error" else None

    def normalize(self, payload: WindowsNotificationPayload) -> UnifiedEvent:
        return normalize_windows(payload)

    def authenticate(self) -> bool:
        # Permission is requested by UserNotificationListener in the native shell.
        return self.permission == "allowed"

    def initial_sync(self) -> SyncBatch:
        return SyncBatch(events=[], cursor=None)

    def incremental_sync(self, cursor: str | None) -> SyncBatch:
        return SyncBatch(events=[], cursor=cursor)

    def health(self) -> ConnectorHealth:
        states = {
            "allowed": ("healthy", "Windows notification bridge connected"),
            "denied": ("denied", "Windows notification access denied"),
            "unspecified": ("degraded", "Windows notification permission not decided"),
            "error": ("error", self.last_error or "Windows notification bridge failed"),
            "bridge_waiting": ("degraded", "Waiting for Windows shell permission and bridge"),
        }
        status, detail = states.get(
            self.permission,
            ("degraded", "Waiting for Windows shell permission and bridge"),
        )
        return ConnectorHealth(
            connector_id=self.connector_id,
            source=self.source,
            status=status,
            detail=detail,
            capabilities=["notification_preview", "line_preview", "messenger_preview"],
        )
