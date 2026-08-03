from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _truthy(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    host: str
    port: int
    database_path: Path
    timezone: str
    model_backend: str
    model_endpoint: str
    model_id: str
    reload: bool
    demo: bool
    notification_window_seconds: int
    max_group_events: int
    surface_threshold: float
    review_threshold: float
    max_interruptions_per_hour: int
    quiet_start: str
    quiet_end: str
    raw_retention_days: int
    normalized_retention_days: int
    summary_retention_days: int
    max_request_bytes: int = 1_000_000
    vision_backend: str = "disabled"
    ocr_model_id: str = "PaddlePaddle/PaddleOCR-VL-1.6"
    ocr_model_revision: str | None = "66317acc4c9fc17bd154591ce650735cd2855f3e"
    model_revision: str | None = "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a"

    @property
    def data_dir(self) -> Path:
        return self.database_path.parent


def load_settings() -> Settings:
    agent = _load_yaml(PROJECT_ROOT / "configs" / "agent.yaml")
    privacy = _load_yaml(PROJECT_ROOT / "configs" / "privacy.yaml")
    grouping = agent.get("grouping", {})
    interruption = agent.get("interruption", {})
    quiet = interruption.get("quiet_hours", {})
    privacy_config = privacy.get("privacy", {})

    db_value = os.getenv("SIGNALDESK_DATABASE", "data/signaldesk.db")
    database_path = Path(db_value)
    if not database_path.is_absolute():
        database_path = PROJECT_ROOT / database_path

    return Settings(
        host=os.getenv("SIGNALDESK_HOST", "127.0.0.1"),
        port=int(os.getenv("SIGNALDESK_PORT", "8765")),
        database_path=database_path,
        timezone=os.getenv("SIGNALDESK_TIMEZONE", "Asia/Taipei"),
        model_backend=os.getenv("SIGNALDESK_MODEL_BACKEND", "rule").lower(),
        model_endpoint=os.getenv(
            "SIGNALDESK_MODEL_ENDPOINT", "http://127.0.0.1:8766/v1/chat/completions"
        ),
        model_id=os.getenv("SIGNALDESK_MODEL_ID", "Qwen/Qwen3.5-4B"),
        reload=_truthy(os.getenv("SIGNALDESK_RELOAD")),
        demo=_truthy(os.getenv("SIGNALDESK_DEMO")),
        notification_window_seconds=int(grouping.get("notification_window_seconds", 30)),
        max_group_events=int(grouping.get("max_group_events", 12)),
        surface_threshold=float(interruption.get("surface_threshold", 0.82)),
        review_threshold=float(interruption.get("review_threshold", 0.55)),
        max_interruptions_per_hour=int(interruption.get("max_interruptions_per_hour", 4)),
        quiet_start=str(quiet.get("start", "23:00")),
        quiet_end=str(quiet.get("end", "08:00")),
        raw_retention_days=int(privacy_config.get("raw_event_retention_days", 7)),
        normalized_retention_days=int(privacy_config.get("normalized_event_retention_days", 30)),
        summary_retention_days=int(privacy_config.get("summary_retention_days", 180)),
        vision_backend=os.getenv("SIGNALDESK_VISION_BACKEND", "disabled").lower(),
        ocr_model_id=os.getenv(
            "SIGNALDESK_OCR_MODEL_ID", "PaddlePaddle/PaddleOCR-VL-1.6"
        ),
        ocr_model_revision=os.getenv(
            "SIGNALDESK_OCR_MODEL_REVISION",
            "66317acc4c9fc17bd154591ce650735cd2855f3e",
        )
        or None,
        model_revision=os.getenv(
            "SIGNALDESK_MODEL_REVISION",
            "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a",
        )
        or None,
    )
