from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class Source(StrEnum):
    GMAIL = "gmail"
    LINE = "line_notification"
    MESSENGER = "messenger_notification"
    WINDOWS = "windows_notification"
    LINE_OFFICIAL = "line_official_webhook"
    MESSENGER_PAGE = "messenger_page_webhook"


class ContentCompleteness(StrEnum):
    FULL = "full"
    THREAD_DELTA = "thread_delta"
    PREVIEW = "notification_preview"
    METADATA_ONLY = "metadata_only"
    MIXED = "mixed"


class MediaKind(StrEnum):
    IMAGE = "image"
    SCREENSHOT = "screenshot"
    STICKER = "sticker"
    ANIMATED_IMAGE = "animated_image"
    DOCUMENT_PREVIEW = "document_preview"


class MediaAvailability(StrEnum):
    AVAILABLE = "available"
    METADATA_ONLY = "metadata_only"
    MISSING = "missing"
    BLOCKED = "blocked"


class MediaAssetRef(StrictModel):
    """Safe, portable media metadata; local filesystem paths never cross the API."""

    asset_id: str = Field(pattern=r"^media_[a-f0-9]{24,64}$")
    kind: MediaKind
    mime_type: str | None = Field(
        default=None, pattern=r"^image/(?:jpeg|png|webp|gif)$"
    )
    original_name: str | None = Field(default=None, max_length=240)
    byte_size: int | None = Field(default=None, ge=0, le=20_000_000)
    width: int | None = Field(default=None, ge=1, le=32_768)
    height: int | None = Field(default=None, ge=1, le=32_768)
    availability: MediaAvailability = MediaAvailability.AVAILABLE
    sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    alt_text: str | None = Field(default=None, max_length=500)


class Priority(StrEnum):
    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    NOISE = "noise"
    UNKNOWN = "unknown"


class ReplyRequirement(StrEnum):
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


class UnifiedEvent(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    event_id: str = Field(min_length=1, max_length=240)
    source: Source
    source_app_id: str | None = None
    account_id: str = Field(min_length=1, max_length=240)
    sender: str = Field(min_length=1, max_length=500)
    conversation_id: str | None = None
    title: str | None = None
    content: str
    content_completeness: ContentCompleteness
    received_at: datetime
    source_url: str | None = None
    raw_notification_id: str | None = None
    privacy_class: Literal["private", "sensitive", "normal"] = "private"
    metadata: dict[str, Any] = Field(default_factory=dict)
    media: list[MediaAssetRef] = Field(default_factory=list, max_length=8)
    checksum: str | None = None

    @field_validator("content")
    @classmethod
    def content_size(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 512_000:
            raise ValueError("content exceeds 512 KB")
        return value


class GroupedMessage(StrictModel):
    event_id: str
    received_at: datetime
    sender: str | None = None
    content: str
    media: list[MediaAssetRef] = Field(default_factory=list, max_length=8)


class GroupedThread(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    thread_id: str
    source: Source
    conversation_id: str | None = None
    sender: str | None = None
    event_ids: list[str]
    content_completeness: ContentCompleteness
    messages: list[GroupedMessage]
    verified_memory: str | None = None
    updated_at: datetime


class OcrRegion(StrictModel):
    """Normalized image coordinates, independent of the original resolution."""

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)


class OcrBlock(StrictModel):
    block_id: str = Field(pattern=r"^ocr_[a-f0-9]{12,64}$")
    text: str = Field(min_length=1, max_length=4000)
    region: OcrRegion | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class VisualAnalysis(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    asset_id: str = Field(pattern=r"^media_[a-f0-9]{24,64}$")
    asset_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    status: Literal["pending", "completed", "failed"]
    ocr_model_id: str
    ocr_model_revision: str | None = None
    blocks: list[OcrBlock] = Field(default_factory=list, max_length=1000)
    raw_text: str = Field(default="", max_length=200_000)
    error_code: str | None = Field(default=None, max_length=120)
    started_at: datetime
    completed_at: datetime | None = None


class Deadline(StrictModel):
    original_text: str
    normalized_at: datetime | None = None
    precision: Literal["exact", "minute", "hour", "day", "day_part", "week", "unknown"]
    timezone: str | None = None
    explicit: bool
    supporting_span: str
    evidence_asset_id: str | None = Field(
        default=None, pattern=r"^media_[a-f0-9]{24,64}$"
    )
    evidence_block_ids: list[str] = Field(default_factory=list, max_length=20)


class ActionItem(StrictModel):
    text: str = Field(min_length=1)
    owner: str | None = None
    supporting_span: str = Field(min_length=1)
    source_event_ids: list[str] = Field(min_length=1)
    deadline_ref: int | None = Field(default=None, ge=0)
    status: Literal["open", "done", "unknown"] = "open"
    evidence_asset_id: str | None = Field(
        default=None, pattern=r"^media_[a-f0-9]{24,64}$"
    )
    evidence_block_ids: list[str] = Field(default_factory=list, max_length=20)


ALLOWED_ACTIONS = {
    "open_source",
    "draft_reply",
    "create_reminder",
    "snooze",
    "mark_done",
    "needs_review",
}


class TriageResult(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    summary: str = Field(min_length=1, max_length=320)
    category: Literal[
        "work",
        "research",
        "meeting",
        "social",
        "security",
        "transaction",
        "system",
        "promotion",
        "other",
        "unknown",
    ]
    priority: Priority
    requires_reply: ReplyRequirement
    action_items: list[ActionItem] = Field(default_factory=list)
    deadlines: list[Deadline] = Field(default_factory=list)
    suggested_actions: list[
        Literal[
            "open_source",
            "draft_reply",
            "create_reminder",
            "snooze",
            "mark_done",
            "needs_review",
        ]
    ] = Field(default_factory=list)
    supporting_spans: list[str] = Field(default_factory=list)
    uncertainty_flags: list[
        Literal[
            "incomplete_preview",
            "truncated_content",
            "ambiguous_sender",
            "ambiguous_deadline",
            "missing_context",
            "source_resolution_uncertain",
            "conflicting_information",
            "image_unavailable",
            "image_analysis_failed",
            "visual_evidence_unverified",
        ]
    ] = Field(default_factory=list)


class AgentDecision(StrictModel):
    decision: Literal[
        "surface_now",
        "store_in_inbox",
        "include_in_digest",
        "needs_review",
        "ignore_as_noise",
        "request_confirmation",
    ]
    reason_codes: list[str]
    policy_version: str = "interruption-v1"
    calibrated_score: float | None = Field(default=None, ge=0, le=1)


class NotificationCard(StrictModel):
    card_id: str
    thread_id: str
    source: Source
    sender: str | None = None
    title: str | None = None
    summary: str
    priority: Priority
    category: str
    requires_reply: ReplyRequirement
    deadline_text: str | None = None
    actions: list[str]
    display_mode: Literal["surface_now", "inbox", "digest", "review", "hidden"]
    why_shown: list[str] = Field(default_factory=list)
    content_completeness: ContentCompleteness
    uncertainty_flags: list[str] = Field(default_factory=list)
    media_preview: MediaAssetRef | None = None
    created_at: datetime
    updated_at: datetime
    status: Literal["open", "snoozed", "done", "dismissed"] = "open"
    snoozed_until: datetime | None = None


class IngestResult(StrictModel):
    event_id: str
    thread_id: str | None = None
    card_id: str | None = None
    duplicate: bool = False
    quarantined: bool = False
    trace_id: str | None = None


class WindowsNotificationPayload(StrictModel):
    notification_id: str
    app_id: str
    app_name: str
    title: str | None = None
    body: str | None = None
    sender: str | None = None
    account_id: str = "windows_user"
    received_at: datetime
    origin: str | None = None
    launch_uri: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CardActionRequest(StrictModel):
    action: Literal[
        "open",
        "snooze",
        "mark_done",
        "dismiss",
        "create_reminder",
        "draft_reply",
        "mark_important",
        "mark_not_important",
    ]
    value: Any = None


class RuleCreate(StrictModel):
    kind: Literal["vip_sender", "mute_sender", "mute_category", "priority_sender"]
    pattern: str = Field(min_length=1, max_length=500)
    value: str | None = None


class UserSettingsPatch(StrictModel):
    theme: Literal["system", "light", "dark"] | None = None
    focus_mode: bool | None = None
    shadow_mode: bool | None = None
    onboarding_complete: bool | None = None
    quiet_start: str | None = None
    quiet_end: str | None = None
    model_residency: Literal["always_on", "on_demand", "auto_sleep", "paused"] | None = None
    raw_retention_days: int | None = Field(default=None, ge=1, le=365)
    notification_allowlist: list[str] | None = None
    digest_time: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    focus_digest_minutes: int | None = Field(default=None, ge=15, le=240)
    now_window_hours: int | None = Field(default=None, ge=1, le=24)
