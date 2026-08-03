from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from .config import Settings
from .database import Database
from .events import EventBus
from .grouping import ThreadGrouper
from .model_gateway import Gateway
from .models import IngestResult, NotificationCard, UnifiedEvent
from .normalizer import idempotency_key, normalize_event, payload_checksum
from .policy import InterruptionPolicy, display_mode
from .preference import PreferenceRanker
from .rules import RuleEngine
from .validator import TriageValidator


class Pipeline:
    def __init__(
        self,
        database: Database,
        config: Settings,
        gateway: Gateway,
        bus: EventBus | None = None,
        preference_ranker: PreferenceRanker | None = None,
    ):
        self.database = database
        self.config = config
        self.gateway = gateway
        self.bus = bus or EventBus()
        self.grouper = ThreadGrouper(database, config.notification_window_seconds)
        self.rules = RuleEngine(config.timezone)
        self.validator = TriageValidator()
        self.policy = InterruptionPolicy(config)
        self.preferences = preference_ranker or PreferenceRanker(database)

    def process(
        self,
        incoming: UnifiedEvent,
        *,
        analyze: bool = True,
        archive_import: bool = False,
    ) -> IngestResult:
        trace_id = f"trace_{uuid.uuid4().hex}"
        self.database.trace_start(
            trace_id,
            incoming.event_id,
            "ingestion",
            {"source": incoming.source, "content_logged": False},
        )
        try:
            event = normalize_event(incoming)
            raw = incoming.model_dump(mode="json")
            similar = self.database.similar_chat_event(event)
            if similar:
                self.database.trace_complete(
                    trace_id,
                    thread_id=similar["thread_id"],
                    status="duplicate",
                    stage="archive_notification_reconciliation",
                    details={"duplicate": True, "content_logged": False},
                )
                return IngestResult(
                    event_id=event.event_id,
                    thread_id=similar["thread_id"],
                    card_id=similar["card_id"],
                    duplicate=True,
                    trace_id=trace_id,
                )
            checksum = event.checksum or payload_checksum(raw)
            inserted = self.database.insert_event(
                event,
                idempotency_key=idempotency_key(event),
                checksum=checksum,
                raw=raw,
            )
            if not inserted:
                existing = self.database.card_for_event(event.event_id)
                self.database.trace_complete(
                    trace_id,
                    thread_id=existing["thread_id"] if existing else None,
                    status="duplicate",
                    stage="deduplication",
                    details={"duplicate": True, "content_logged": False},
                )
                return IngestResult(
                    event_id=event.event_id,
                    thread_id=existing["thread_id"] if existing else None,
                    card_id=existing["card_id"] if existing else None,
                    duplicate=True,
                    trace_id=trace_id,
                )
            self.bus.publish("event_ingested", {"event_id": event.event_id, "source": event.source})

            thread_id = self.grouper.group(event)
            if not analyze:
                self.database.trace_complete(
                    trace_id,
                    thread_id=thread_id,
                    status="completed",
                    stage="archive_stored",
                    details={"archive_import": archive_import, "content_logged": False},
                )
                return IngestResult(
                    event_id=event.event_id,
                    thread_id=thread_id,
                    trace_id=trace_id,
                )
            return self._analyze_thread(
                thread_id,
                event_id=event.event_id,
                trace_id=trace_id,
                archive_import=archive_import,
            )
        except Exception as error:
            self.database.trace_complete(
                trace_id,
                thread_id=None,
                status="failed",
                stage="failure",
                details={"error_type": type(error).__name__, "content_logged": False},
            )
            raise

    def analyze_thread(self, thread_id: str, *, archive_import: bool = False) -> IngestResult:
        """Analyze an already persisted thread once after a bulk archive import."""
        thread = self.database.grouped_thread(thread_id, limit=50)
        if thread is None or not thread.event_ids:
            raise RuntimeError("grouped thread was not persisted")
        event_id = thread.event_ids[-1]
        trace_id = f"trace_{uuid.uuid4().hex}"
        self.database.trace_start(
            trace_id,
            event_id,
            "archive_analysis" if archive_import else "analysis",
            {"archive_import": archive_import, "content_logged": False},
        )
        try:
            return self._analyze_thread(
                thread_id,
                event_id=event_id,
                trace_id=trace_id,
                archive_import=archive_import,
            )
        except Exception as error:
            self.database.trace_complete(
                trace_id,
                thread_id=thread_id,
                status="failed",
                stage="failure",
                details={"error_type": type(error).__name__, "content_logged": False},
            )
            raise

    def _analyze_thread(
        self,
        thread_id: str,
        *,
        event_id: str,
        trace_id: str,
        archive_import: bool,
    ) -> IngestResult:
        # Analysis is deliberately bounded to the latest messages. All archive events remain
        # in SQLite and card detail, while stale questions do not become current tasks.
        thread = self.database.grouped_thread(thread_id, limit=50)
        if thread is None:
            raise RuntimeError("grouped thread was not persisted")
        self.bus.publish(
            "thread_grouped",
            {"thread_id": thread_id, "event_count": len(thread.event_ids)},
        )

        user_rules = self.database.rules()
        signals = self.rules.signals(thread, user_rules)
        baseline = self.rules.triage(thread, signals)
        source_events = [self.database.event(event_id) for event_id in thread.event_ids]
        if any(
            event and event.metadata.get("source_resolution_uncertain") for event in source_events
        ):
            baseline.uncertainty_flags.append("source_resolution_uncertain")
        if any(event and event.metadata.get("truncated") for event in source_events):
            baseline.uncertainty_flags.append("truncated_content")
        self.bus.publish("triage_started", {"thread_id": thread_id})
        model_result = self.gateway.analyze(thread, signals)
        candidate = model_result.triage or baseline
        has_available_media = any(
            str(media.availability) == "available"
            for message in thread.messages
            for media in message.media
        )
        if has_available_media and model_result.triage is None:
            if "visual_evidence_unverified" not in candidate.uncertainty_flags:
                candidate.uncertainty_flags.append("visual_evidence_unverified")
        validated, report = self.validator.validate(candidate, thread, signals)

        # An unsafe model output falls back to the deterministic baseline and is audited.
        model_backend = model_result.backend
        if model_result.triage is not None and not report.valid:
            validated, baseline_report = self.validator.validate(baseline, thread, signals)
            report.warnings.append("unsafe_model_output_replaced_by_rule_baseline")
            report.valid = baseline_report.valid
            model_backend += "+rule-fallback"
        elif model_result.error and model_result.backend != "rule":
            report.warnings.append("model_unavailable_rule_baseline_used")
            model_backend += "+rule-fallback"

        now = datetime.now(UTC)
        preference_score = self.preferences.score(
            source=str(thread.source),
            sender=thread.sender,
            category=validated.category,
            requires_reply=str(validated.requires_reply),
            has_deadline=bool(validated.deadlines),
            at=now,
        )
        decision = self.policy.decide(
            validated,
            signals,
            self.database.settings(),
            now=now,
            preference_score=preference_score,
            interruptions_last_hour=self.database.interruption_count_since(
                now - timedelta(hours=1)
            ),
        )
        if archive_import:
            decision = decision.model_copy(
                update={
                    "decision": "store_in_inbox",
                    "reason_codes": list(dict.fromkeys([*decision.reason_codes, "archive_import"])),
                }
            )
        card_id = "card_" + hashlib.sha256(thread_id.encode()).hexdigest()[:20]
        first_event = self.database.event(thread.event_ids[0])
        card_time = thread.updated_at if archive_import else now
        card_sender = (
            first_event.title
            if archive_import and first_event and first_event.title
            else thread.sender
        )
        card = NotificationCard(
            card_id=card_id,
            thread_id=thread_id,
            source=thread.source,
            sender=card_sender,
            title=first_event.title if first_event else None,
            summary=validated.summary,
            priority=validated.priority,
            category=validated.category,
            requires_reply=validated.requires_reply,
            deadline_text=validated.deadlines[0].original_text if validated.deadlines else None,
            actions=validated.suggested_actions,
            display_mode=display_mode(decision.decision),
            why_shown=decision.reason_codes,
            content_completeness=thread.content_completeness,
            uncertainty_flags=validated.uncertainty_flags,
            created_at=card_time,
            updated_at=card_time,
        )
        self.database.save_analysis(
            thread=thread,
            triage=validated,
            validation=report.dump(),
            decision=decision,
            card=card,
            model_backend=model_backend,
        )
        if decision.decision == "surface_now" and not archive_import:
            self.database.record_interruption(card_id)
        self.database.trace_complete(
            trace_id,
            thread_id=thread_id,
            status="completed",
            stage="card_created",
            details={
                "model_backend": model_backend,
                "validation": report.dump(),
                "decision": decision.model_dump(mode="json"),
                "content_logged": False,
            },
        )
        self.bus.publish(
            "triage_completed",
            {
                "thread_id": thread_id,
                "priority": validated.priority,
                "decision": decision.decision,
            },
        )
        self.bus.publish("card_updated", {"card_id": card_id, "thread_id": thread_id})
        return IngestResult(
            event_id=event_id,
            thread_id=thread_id,
            card_id=card_id,
            trace_id=trace_id,
        )
