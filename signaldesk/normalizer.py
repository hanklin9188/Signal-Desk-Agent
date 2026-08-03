from __future__ import annotations

import hashlib
import html
import re
import unicodedata
from typing import Any
from urllib.parse import urlparse

from .models import Source, UnifiedEvent, WindowsNotificationPayload

TAG_RE = re.compile(r"<[^>]+>")
MULTISPACE_RE = re.compile(r"[ \t\u00a0]+")
TRACKING_RE = re.compile(r"https?://\S+(?:utm_[a-z]+|fbclid|gclid)=\S+", re.IGNORECASE)
QUOTED_RE = re.compile(
    r"(?:\n[- ]*Original Message[- ]*\n|\nOn .{0,180} wrote:\s*\n|\n在 .{0,180}寫道：\s*\n)",
    re.IGNORECASE,
)
SIGNATURE_RE = re.compile(r"\n(?:--\s*\n|Sent from my |從我的\S+傳送)", re.IGNORECASE)
BROWSER_BACKGROUND_NOTICES = (
    "此網站已在背景更新",
    "這個網站已在背景更新",
    "此网站已在后台更新",
    "该网站已在后台更新",
    "this website has been updated in the background",
    "this site has been updated in the background",
    "this website was updated in the background",
    "this site was updated in the background",
)
MESSENGER_GENERIC_TITLES = {"messenger", "messenger.com", "www.messenger.com"}
MESSENGER_SENDER_RE = re.compile(
    r"^(.{1,100}?)(?:\s+(?:傳送了|傳了一|sent\b)|\s*[:：])",
    re.IGNORECASE,
)
LINE_GROUP_TITLE_RE = re.compile(
    r"^(?P<sender>.+?)\s*[\[［【](?P<context>.+?)[\]］】]\s*$"
)


def clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = TAG_RE.sub(" ", value)
    value = unicodedata.normalize("NFKC", value)
    value = TRACKING_RE.sub("[tracking link removed]", value)
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = "\n".join(MULTISPACE_RE.sub(" ", line).strip() for line in value.splitlines())
    return re.sub(r"\n{3,}", "\n\n", value).strip()


def clean_label(value: str) -> str:
    """Normalize a sender/title without treating <email@example.com> as HTML."""
    value = html.unescape(value or "")
    value = unicodedata.normalize("NFKC", value)
    return MULTISPACE_RE.sub(" ", value).strip()


def is_browser_background_notice(value: str) -> bool:
    normalized = clean_text(value).casefold()
    return any(notice in normalized for notice in BROWSER_BACKGROUND_NOTICES)


def messenger_sender_from_preview(value: str) -> str | None:
    first_line = clean_text(value).splitlines()[0] if clean_text(value) else ""
    match = MESSENGER_SENDER_RE.match(first_line)
    return clean_label(match.group(1)) if match else None


def line_identity_from_title(value: str) -> tuple[str, str, str]:
    """Return display sender, stable per-user identity, and conversation label.

    LINE desktop group notifications commonly use ``Sender [Group]``. The sender
    must remain the card owner while the complete label remains the grouping key,
    otherwise unrelated people can appear to share one generic group card.
    """
    label = clean_label(value)
    match = LINE_GROUP_TITLE_RE.match(label)
    if not match:
        return label, label, label
    sender = clean_label(match.group("sender"))
    context = clean_label(match.group("context"))
    identity = f"{sender} [{context}]"
    return sender, identity, context


def safe_source_url(source: Source, value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme != "https":
        return None
    host = (parsed.hostname or "").casefold()
    allowed_hosts = {
        Source.GMAIL: {"mail.google.com", "myaccount.google.com", "accounts.google.com"},
        Source.LINE: {"line.me", "access.line.me"},
        Source.MESSENGER: {
            "messenger.com",
            "www.messenger.com",
            "facebook.com",
            "www.facebook.com",
        },
        Source.LINE_OFFICIAL: {"line.me"},
        Source.MESSENGER_PAGE: {"facebook.com", "www.facebook.com"},
    }
    return value if host in allowed_hosts.get(source, set()) else None


def strip_gmail_history(value: str) -> tuple[str, dict[str, bool]]:
    flags = {"quoted_history_removed": False, "signature_removed": False}
    match = QUOTED_RE.search(value)
    if match:
        value = value[: match.start()].strip()
        flags["quoted_history_removed"] = True
    match = SIGNATURE_RE.search(value)
    if match:
        value = value[: match.start()].strip()
        flags["signature_removed"] = True
    return value, flags


def payload_checksum(payload: dict[str, Any] | str) -> str:
    if isinstance(payload, dict):
        import json

        value = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    else:
        value = payload
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_event(event: UnifiedEvent) -> UnifiedEvent:
    content = clean_text(event.content)
    metadata = dict(event.metadata)
    if event.source == Source.GMAIL:
        content, flags = strip_gmail_history(content)
        metadata["normalization"] = flags
    sender = clean_label(event.sender)
    title = clean_label(event.title) if event.title else None
    return event.model_copy(
        update={
            "content": content,
            "sender": sender,
            "title": title,
            "metadata": metadata,
            "checksum": event.checksum or payload_checksum(content),
            "source_url": safe_source_url(event.source, event.source_url),
        }
    )


def idempotency_key(event: UnifiedEvent) -> str:
    explicit = event.metadata.get("idempotency_key")
    if explicit:
        return str(explicit)
    if event.source == Source.GMAIL:
        history = event.metadata.get("history_id", "initial")
        message_id = event.metadata.get("message_id", event.event_id)
        return f"gmail:{event.account_id}:{message_id}:{history}"
    if event.source in {Source.LINE, Source.MESSENGER, Source.WINDOWS}:
        notification_id = event.raw_notification_id or event.event_id
        return f"windows:{event.source_app_id or event.source}:{notification_id}:{event.checksum}"
    webhook_id = event.metadata.get("webhook_event_id", event.event_id)
    return f"{event.source}:{webhook_id}"


def normalize_windows(payload: WindowsNotificationPayload) -> UnifiedEvent:
    app = f"{payload.app_id} {payload.app_name}".lower()
    app_id = payload.app_id.casefold()
    app_name = payload.app_name.strip().casefold()
    origin = (payload.origin or "").lower()
    notification_title = clean_label(payload.title or "")
    browser_app = any(browser in app for browser in ("chrome", "edge", "firefox"))
    messenger_browser_title = (
        browser_app and notification_title.casefold() in MESSENGER_GENERIC_TITLES
    )
    is_line_app = (
        app_name == "line"
        or app_id == "line"
        or app_id.endswith("!line")
        or "win32_line" in app_id
    )
    if is_line_app:
        source = Source.LINE
    elif (
        "messenger" in app
        or "messenger" in origin
        or "facebook" in origin
        or messenger_browser_title
    ):
        source = Source.MESSENGER
    else:
        source = Source.WINDOWS

    content = clean_text(payload.body or "")
    metadata = dict(payload.metadata)
    if payload.origin:
        metadata["origin"] = payload.origin
    if source == Source.MESSENGER and browser_app:
        metadata["source_resolution_uncertain"] = not bool(
            payload.origin or messenger_browser_title
        )
    metadata["native_app_name"] = payload.app_name
    metadata["native_app_id"] = payload.app_id

    checksum = payload_checksum(
        {
            "app": payload.app_id,
            "title": payload.title,
            "body": payload.body,
            "received": payload.received_at.isoformat(),
        }
    )
    event_seed = f"{payload.app_id}|{payload.notification_id}|{checksum}"
    event_id = "win_" + hashlib.sha256(event_seed.encode()).hexdigest()[:24]
    preview_sender = (
        messenger_sender_from_preview(content) if messenger_browser_title else None
    )
    sender = preview_sender or clean_label(payload.sender or payload.title or payload.app_name)
    title = sender if messenger_browser_title and preview_sender else notification_title
    if source == Source.LINE:
        sender, conversation_id, title = line_identity_from_title(
            notification_title or sender
        )
    elif source == Source.MESSENGER:
        conversation_id = (
            sender
            if messenger_browser_title
            else clean_label(payload.title or payload.sender or "")
        ) or None
    else:
        conversation_id = None
    launch_uri = payload.launch_uri
    if messenger_browser_title and not launch_uri:
        launch_uri = "https://www.messenger.com/"
    return UnifiedEvent(
        event_id=event_id,
        source=source,
        source_app_id=payload.app_id,
        account_id=payload.account_id,
        sender=sender,
        conversation_id=conversation_id,
        title=title or clean_label(payload.app_name),
        content=content,
        content_completeness="notification_preview" if content else "metadata_only",
        received_at=payload.received_at,
        source_url=safe_source_url(source, launch_uri),
        raw_notification_id=payload.notification_id,
        privacy_class="private",
        metadata=metadata,
        checksum=checksum,
    )
