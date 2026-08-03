from __future__ import annotations

import json
import tempfile
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from signaldesk.config import load_settings
from signaldesk.database import Database
from signaldesk.media_store import MediaStore
from signaldesk.model_gateway import build_gateway
from signaldesk.models import UnifiedEvent
from signaldesk.pipeline import Pipeline
from signaldesk.rules import RuleEngine


def main() -> None:
    """Exercise the complete local-model JSON contract using fictional data only."""
    with tempfile.TemporaryDirectory(prefix="signaldesk-model-smoke-") as directory:
        root = Path(directory)
        config = replace(
            load_settings(),
            database_path=root / "smoke.db",
            model_backend="rule",
            quiet_start="00:00",
            quiet_end="00:00",
        )
        database = Database(config.database_path)
        database.ensure_defaults(
            {
                "shadow_mode": False,
                "focus_mode": False,
                "quiet_start": "00:00",
                "quiet_end": "00:00",
                "notification_allowlist": ["LINE", "Messenger", "Edge"],
            }
        )
        pipeline = Pipeline(
            database,
            config,
            build_gateway("rule", config.model_endpoint, config.model_id),
        )
        ingest = pipeline.process(
            UnifiedEvent(
                event_id="fictional-model-smoke",
                source="gmail",
                source_app_id="gmail",
                account_id="fictional",
                sender="Alex Example <alex@example.test>",
                conversation_id="fictional-thread",
                title="Project Atlas review",
                content="Please review Project Atlas before Aug 9, 2026 and reply when ready.",
                content_completeness="full",
                received_at=datetime(2026, 8, 3, 9, 0, tzinfo=UTC),
                privacy_class="sensitive",
                metadata={"message_id": "fictional-message", "history_id": "1"},
            )
        )
        thread = database.grouped_thread(ingest.thread_id)
        if thread is None:
            raise RuntimeError("fictional thread was not created")
        signals = RuleEngine(config.timezone).signals(thread, database.rules())
        gateway = build_gateway(
            "transformers",
            config.model_endpoint,
            config.model_id,
            media_store=MediaStore(root / "media"),
            revision=config.model_revision,
        )
        result = gateway.analyze(thread, signals)
        report = {
            "success": result.triage is not None,
            "backend": result.backend,
            "error": result.error,
            "triage": result.triage.model_dump(mode="json") if result.triage else None,
            "private_data": False,
        }
        print(json.dumps(report, ensure_ascii=False))
        if result.triage is None:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
