from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import zipfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time
from pathlib import Path, PurePosixPath
from typing import Any, Literal
from zoneinfo import ZoneInfo

from ..media_store import MAX_MEDIA_BYTES, MediaError, MediaStore
from ..models import MediaAssetRef, UnifiedEvent

ArchiveSource = Literal["line", "messenger"]
MediaLoader = Callable[[str], MediaAssetRef | None]

MAX_ARCHIVE_FILES = 500
MAX_ARCHIVE_BYTES = 2 * 1024 * 1024 * 1024
MAX_JSON_MEMBER_BYTES = 256 * 1024 * 1024
MAX_MESSAGES = 250_000
MAX_MESSAGE_CHARS = 400_000


class ChatArchiveError(ValueError):
    pass


@dataclass(slots=True)
class ArchiveParseResult:
    source: ArchiveSource
    files: int
    events: list[UnifiedEvent] = field(default_factory=list)
    conversations: set[str] = field(default_factory=set)
    skipped: int = 0
    warnings: list[str] = field(default_factory=list)


def load_chat_archives(
    source: ArchiveSource,
    paths: Iterable[str | Path],
    *,
    timezone: str,
    media_store: MediaStore | None = None,
) -> ArchiveParseResult:
    files = _validated_files(source, paths)
    result = ArchiveParseResult(source=source, files=len(files))
    zone = ZoneInfo(timezone)
    if source == "line":
        for path in files:
            _parse_line_file(path, zone, result)
    else:
        for path in files:
            _parse_messenger_path(path, result, media_store=media_store)
    if not result.events:
        raise ChatArchiveError("封存檔中找不到可匯入的訊息")
    if len(result.events) > MAX_MESSAGES:
        raise ChatArchiveError(f"單次最多可匯入 {MAX_MESSAGES:,} 則訊息；請把封存檔分批選取")
    result.events.sort(key=lambda item: (item.received_at, item.event_id))
    return result


def _validated_files(source: ArchiveSource, paths: Iterable[str | Path]) -> list[Path]:
    values = [Path(value).expanduser() for value in paths]
    if not values:
        raise ChatArchiveError("請至少選擇一個聊天封存檔")
    if len(values) > MAX_ARCHIVE_FILES:
        raise ChatArchiveError(f"單次最多選擇 {MAX_ARCHIVE_FILES} 個檔案")
    allowed = {".txt"} if source == "line" else {".json", ".zip"}
    total = 0
    for path in values:
        if not path.is_file():
            raise ChatArchiveError(f"找不到封存檔：{path.name}")
        if path.suffix.casefold() not in allowed:
            formats = "、".join(sorted(allowed))
            raise ChatArchiveError(f"{source} 封存只接受 {formats}：{path.name}")
        total += path.stat().st_size
    if total > MAX_ARCHIVE_BYTES:
        raise ChatArchiveError("單次選取的封存檔超過 2 GB，請分批匯入")
    return values


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "cp950", "cp932"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ChatArchiveError(f"無法辨識文字編碼：{path.name}")


def _line_title(text: str, path: Path) -> str:
    for line in text.splitlines()[:8]:
        cleaned = line.strip().lstrip("\ufeff")
        patterns = (
            r"^\[LINE\]\s*(?:與|和)\s*(.+?)\s*的聊天(?:記錄|紀錄)",
            r"^\[LINE\]\s*Chat history (?:with|for)\s+(.+)$",
            r"^\[LINE\]\s*(.+?)\s*(?:聊天(?:記錄|紀錄)|chat history)$",
        )
        for pattern in patterns:
            match = re.search(pattern, cleaned, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    name = re.sub(r"(?:_chat|chat[_ -]?history|聊天(?:記錄|紀錄))", "", path.stem, flags=re.I)
    return name.strip(" _-") or path.stem


def _parse_date(value: str) -> date | None:
    match = re.search(r"(?<!\d)(\d{4})\s*[年./-]\s*(\d{1,2})\s*[月./-]\s*(\d{1,2})\s*日?", value)
    if match:
        try:
            return date(*(int(part) for part in match.groups()))
        except ValueError:
            return None
    match = re.search(r"(?<!\d)(\d{1,2})[/-](\d{1,2})[/-](\d{4})(?!\d)", value)
    if match:
        month, day, year = (int(part) for part in match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None
    return None


def _parse_time(value: str) -> time | None:
    cleaned = value.strip().strip("[]")
    match = re.search(
        r"(?:(AM|PM|上午|下午)\s*)?(\d{1,2}):(\d{2})(?::\d{2})?\s*(AM|PM|上午|下午)?",
        cleaned,
        re.IGNORECASE,
    )
    if not match:
        return None
    marker = (match.group(1) or match.group(4) or "").casefold()
    hour, minute = int(match.group(2)), int(match.group(3))
    if minute > 59 or hour > 23:
        return None
    if marker in {"pm", "下午"} and hour < 12:
        hour += 12
    elif marker in {"am", "上午"} and hour == 12:
        hour = 0
    try:
        return time(hour, minute)
    except ValueError:
        return None


def _attachment_only(content: str) -> bool:
    return bool(
        re.fullmatch(
            r"\[?(?:照片|相片|圖片|貼圖|影片|檔案|語音訊息|photo|image|sticker|"
            r"video|file|audio|voice message)\]?",
            content.strip(),
            re.IGNORECASE,
        )
    )


def _archive_event(
    *,
    source: Literal["line_notification", "messenger_notification"],
    source_name: str,
    conversation: str,
    sender: str,
    content: str,
    received_at: datetime,
    provider_key: str,
    file_name: str,
    metadata: dict[str, Any] | None = None,
    media: list[MediaAssetRef] | None = None,
) -> UnifiedEvent:
    content = content.strip()
    truncated = len(content) > MAX_MESSAGE_CHARS
    if truncated:
        content = content[:MAX_MESSAGE_CHARS].rstrip() + "…"
    digest = hashlib.sha256(
        f"{source}|{provider_key}|{received_at.isoformat()}|{sender}|{content}".encode()
    ).hexdigest()
    values = {
        "archive_import": True,
        "archive_source": source_name,
        "archive_file": file_name,
        "idempotency_key": f"archive:{source_name}:{digest}",
        "truncated": truncated,
        **(metadata or {}),
    }
    prefix = "line_archive" if source_name == "line" else "messenger_archive"
    media = media or []
    has_available_media = any(str(item.availability) == "available" for item in media)
    return UnifiedEvent(
        event_id=f"{prefix}_{digest[:32]}",
        source=source,
        source_app_id=f"{source_name}_archive",
        account_id="windows_user",
        sender=sender.strip() or source_name.title(),
        conversation_id=conversation.strip() or source_name.title(),
        title=conversation.strip() or source_name.title(),
        content=content or "[無文字內容]",
        content_completeness=(
            "metadata_only" if _attachment_only(content) and not has_available_media else "full"
        ),
        received_at=received_at,
        privacy_class="private",
        metadata=values,
        media=media,
    )


def _parse_line_file(path: Path, zone: ZoneInfo, result: ArchiveParseResult) -> None:
    text = _read_text(path)
    title = _line_title(text, path)
    result.conversations.add(title)
    fallback_date = datetime.fromtimestamp(path.stat().st_mtime, zone).date()
    current_date = fallback_date
    pending: dict[str, Any] | None = None
    parsed_before = len(result.events)

    def flush() -> None:
        nonlocal pending
        if pending is None:
            return
        content = "\n".join(pending["content"]).strip()
        if content:
            event = _archive_event(
                source="line_notification",
                source_name="line",
                conversation=title,
                sender=pending["sender"],
                content=content,
                received_at=pending["received_at"],
                provider_key=title,
                file_name=path.name,
                metadata={"line_export": "text"},
            )
            result.events.append(event)
        else:
            result.skipped += 1
        pending = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        parsed_date = _parse_date(line)
        if parsed_date and "\t" not in line:
            flush()
            current_date = parsed_date
            continue
        parts = line.split("\t", 2)
        parsed_time = _parse_time(parts[0]) if parts else None
        if parsed_time and len(parts) >= 2:
            flush()
            sender = parts[1].strip() if len(parts) == 3 else "LINE"
            content = parts[2] if len(parts) == 3 else parts[1]
            pending = {
                "sender": sender or "LINE",
                "content": [content],
                "received_at": datetime.combine(current_date, parsed_time, tzinfo=zone),
            }
        elif pending is not None and line.strip():
            pending["content"].append(line)
    flush()
    if len(result.events) == parsed_before:
        result.warnings.append(f"{path.name}：沒有辨識到 LINE 訊息列")


def _fix_meta_text(value: Any) -> str:
    text = str(value or "")
    if any(marker in text for marker in ("Ã", "Â", "â", "ð")):
        try:
            return text.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return text


def _conversation_objects(value: Any, *, depth: int = 0) -> Iterable[dict[str, Any]]:
    if depth > 8:
        return
    if isinstance(value, dict):
        messages = value.get("messages")
        if isinstance(messages, list) and any(isinstance(item, dict) for item in messages):
            yield value
            return
        for nested in value.values():
            yield from _conversation_objects(nested, depth=depth + 1)
    elif isinstance(value, list):
        for nested in value:
            yield from _conversation_objects(nested, depth=depth + 1)


def _messenger_timestamp(message: dict[str, Any]) -> datetime | None:
    value = message.get("timestamp_ms", message.get("timestamp", message.get("time")))
    if isinstance(value, (int, float)):
        seconds = float(value) / 1000 if float(value) > 10_000_000_000 else float(value)
        try:
            return datetime.fromtimestamp(seconds, tz=UTC)
        except (OSError, OverflowError, ValueError):
            return None
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            return None
    return None


def _messenger_content(message: dict[str, Any]) -> tuple[str, list[str]]:
    content = _fix_meta_text(message.get("content") or message.get("text"))
    attachment_types: list[str] = []
    fields = {
        "photos": "圖片",
        "videos": "影片",
        "audio_files": "語音",
        "audioFiles": "語音",
        "files": "檔案",
        "gifs": "GIF",
        "sticker": "貼圖",
        "share": "分享連結",
    }
    for field_name, label in fields.items():
        value = message.get(field_name)
        if value:
            attachment_types.append(label)
    media = message.get("media")
    if isinstance(media, list):
        media_labels = {
            "photo": "圖片",
            "image": "圖片",
            "video": "影片",
            "audio": "語音",
            "voice": "語音",
            "gif": "GIF",
            "sticker": "貼圖",
            "file": "檔案",
        }
        for item in media:
            if not isinstance(item, dict):
                continue
            kind = str(item.get("type") or "file").casefold()
            label = next(
                (value for marker, value in media_labels.items() if marker in kind),
                "檔案",
            )
            if label not in attachment_types:
                attachment_types.append(label)
    if not content and attachment_types:
        content = "[" + "、".join(attachment_types) + "]"
    if not content and message.get("call_duration") is not None:
        content = "[通話紀錄]"
        attachment_types.append("通話")
    return content, attachment_types


def _messenger_image_uris(message: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for field_name in ("photos", "gifs"):
        for item in message.get(field_name) or []:
            if isinstance(item, dict) and item.get("uri"):
                values.append(str(item["uri"]))
    sticker = message.get("sticker")
    if isinstance(sticker, dict) and sticker.get("uri"):
        values.append(str(sticker["uri"]))
    for item in message.get("media") or []:
        if not isinstance(item, dict) or not item.get("uri"):
            continue
        kind = str(item.get("type") or "").casefold()
        if any(marker in kind for marker in ("image", "photo", "gif", "sticker")):
            values.append(str(item["uri"]))
    return list(dict.fromkeys(values))[:8]


def _messenger_media_refs(
    message: dict[str, Any], loader: MediaLoader | None
) -> list[MediaAssetRef]:
    results: list[MediaAssetRef] = []
    for uri in _messenger_image_uris(message):
        placeholder_id = f"media_{hashlib.sha256(uri.encode()).hexdigest()[:40]}"
        mime_type = mimetypes.guess_type(uri)[0]
        mime_type = (
            mime_type
            if mime_type in {"image/jpeg", "image/png", "image/webp", "image/gif"}
            else None
        )
        try:
            imported = loader(uri) if loader else None
        except Exception as error:
            results.append(
                MediaAssetRef(
                    asset_id=placeholder_id,
                    kind="image",
                    mime_type=mime_type,
                    original_name=PurePosixPath(uri.replace("\\", "/")).name,
                    availability="blocked",
                    alt_text=f"Archive image import failed: {type(error).__name__}",
                )
            )
            continue
        results.append(
            imported
            or MediaAssetRef(
                asset_id=placeholder_id,
                kind="image",
                mime_type=mime_type,
                original_name=PurePosixPath(uri.replace("\\", "/")).name,
                availability="metadata_only",
            )
        )
    return results


def _parse_messenger_conversation(
    conversation: dict[str, Any],
    *,
    origin: str,
    result: ArchiveParseResult,
    media_loader: MediaLoader | None = None,
) -> None:
    participants: list[str] = []
    for item in conversation.get("participants", []):
        if isinstance(item, dict) and item.get("name"):
            participants.append(_fix_meta_text(item.get("name")))
        elif isinstance(item, str) and item.strip():
            participants.append(_fix_meta_text(item))
    exported_title = _fix_meta_text(
        conversation.get("title") or conversation.get("threadName")
    )
    # Messenger secure-storage downloads append an export index (for example
    # "Alice_15") to threadName. Remove it so future notification titles join
    # the imported conversation instead of creating a second thread.
    title = re.sub(r"_\d+$", "", exported_title).strip() if exported_title else ""
    title = title or "、".join(participants) or "Messenger 對話"
    thread_path = _fix_meta_text(
        conversation.get("thread_path") or conversation.get("threadPath")
    )
    provider_thread = thread_path or "|".join(sorted(participants)) or title
    result.conversations.add(title)
    for message in conversation.get("messages", []):
        if not isinstance(message, dict):
            result.skipped += 1
            continue
        if message.get("isUnsent") is True:
            result.skipped += 1
            continue
        received_at = _messenger_timestamp(message)
        content, attachment_types = _messenger_content(message)
        media = _messenger_media_refs(message, media_loader)
        if received_at is None or not content:
            result.skipped += 1
            continue
        sender = _fix_meta_text(
            message.get("sender_name") or message.get("senderName")
        ) or "Messenger"
        event = _archive_event(
            source="messenger_notification",
            source_name="messenger",
            conversation=title,
            sender=sender,
            content=content,
            received_at=received_at,
            provider_key=(
                f"{provider_thread}|"
                f"{message.get('message_id') or message.get('messageId') or ''}"
            ),
            file_name=Path(origin).name,
            metadata={
                "messenger_export": "json",
                "thread_path": thread_path or None,
                "exported_thread_name": exported_title or None,
                "attachment_types": attachment_types,
            },
            media=media,
        )
        result.events.append(event)


def _parse_messenger_json(
    raw: bytes,
    *,
    origin: str,
    result: ArchiveParseResult,
    media_loader: MediaLoader | None = None,
) -> None:
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ChatArchiveError(f"Messenger JSON 無法解析：{Path(origin).name}") from error
    found = False
    for conversation in _conversation_objects(payload):
        found = True
        _parse_messenger_conversation(
            conversation,
            origin=origin,
            result=result,
            media_loader=media_loader,
        )
    if not found:
        result.warnings.append(f"{Path(origin).name}：找不到 Messenger messages 結構")


def _parse_messenger_path(
    path: Path,
    result: ArchiveParseResult,
    *,
    media_store: MediaStore | None = None,
) -> None:
    if path.suffix.casefold() == ".json":
        if path.stat().st_size > MAX_JSON_MEMBER_BYTES:
            raise ChatArchiveError(f"單一 Messenger JSON 超過 256 MB：{path.name}")
        media_loader: MediaLoader | None = None
        if media_store:
            root = path.parent.resolve()

            def load_file(uri: str) -> MediaAssetRef | None:
                normalized = PurePosixPath(uri.replace("\\", "/"))
                if normalized.is_absolute() or ".." in normalized.parts:
                    raise MediaError("unsafe archive media path")
                candidate = (root / Path(*normalized.parts)).resolve()
                try:
                    candidate.relative_to(root)
                except ValueError as error:
                    raise MediaError("unsafe archive media path") from error
                if not candidate.is_file():
                    return None
                if candidate.stat().st_size > MAX_MEDIA_BYTES:
                    raise MediaError("archive image exceeds 20 MB")
                mime_type = mimetypes.guess_type(candidate.name)[0] or ""
                return media_store.import_bytes(
                    candidate.read_bytes(),
                    declared_mime=mime_type,
                    original_name=candidate.name,
                )

            media_loader = load_file
        _parse_messenger_json(
            path.read_bytes(),
            origin=path.name,
            result=result,
            media_loader=media_loader,
        )
        return
    try:
        with zipfile.ZipFile(path) as archive:
            members = {
                PurePosixPath(item.filename.replace("\\", "/")).as_posix(): item
                for item in archive.infolist()
                if not item.is_dir()
            }
            candidates = [
                item
                for item in archive.infolist()
                if not item.is_dir()
                and item.filename.casefold().endswith(".json")
                and (
                    "/messages/" in f"/{item.filename.casefold()}"
                    or "message_" in Path(item.filename).name.casefold()
                )
            ]
            if not candidates:
                candidates = [
                    item
                    for item in archive.infolist()
                    if not item.is_dir() and item.filename.casefold().endswith(".json")
                ]
            total = sum(item.file_size for item in candidates)
            if total > MAX_ARCHIVE_BYTES:
                raise ChatArchiveError(f"Messenger ZIP 內的 JSON 超過 2 GB：{path.name}")
            for item in candidates:
                if item.file_size > MAX_JSON_MEMBER_BYTES:
                    raise ChatArchiveError(
                        f"ZIP 中單一 JSON 超過 256 MB：{Path(item.filename).name}"
                    )
                media_loader = None
                if media_store:
                    json_parent = PurePosixPath(item.filename.replace("\\", "/")).parent

                    def load_member(
                        uri: str, parent: PurePosixPath = json_parent
                    ) -> MediaAssetRef | None:
                        normalized = PurePosixPath(uri.replace("\\", "/"))
                        if normalized.is_absolute() or ".." in normalized.parts:
                            raise MediaError("unsafe archive media path")
                        names = [normalized.as_posix(), (parent / normalized).as_posix()]
                        media_info = next(
                            (members.get(name) for name in names if name in members),
                            None,
                        )
                        if media_info is None:
                            return None
                        if media_info.file_size > MAX_MEDIA_BYTES:
                            raise MediaError("archive image exceeds 20 MB")
                        mime_type = mimetypes.guess_type(media_info.filename)[0] or ""
                        with archive.open(media_info) as handle:
                            content = handle.read(MAX_MEDIA_BYTES + 1)
                        if len(content) > MAX_MEDIA_BYTES:
                            raise MediaError("archive image exceeds 20 MB")
                        return media_store.import_bytes(
                            content,
                            declared_mime=mime_type,
                            original_name=PurePosixPath(media_info.filename).name,
                        )

                    media_loader = load_member
                _parse_messenger_json(
                    archive.read(item),
                    origin=f"{path.name}/{item.filename}",
                    result=result,
                    media_loader=media_loader,
                )
    except zipfile.BadZipFile as error:
        raise ChatArchiveError(f"Messenger ZIP 已損壞或格式不正確：{path.name}") from error
