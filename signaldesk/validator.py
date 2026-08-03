from __future__ import annotations

from dataclasses import dataclass, field

from .models import ALLOWED_ACTIONS, GroupedThread, TriageResult, VisualAnalysis
from .rules import RuleSignals, combined_text


@dataclass(slots=True)
class ValidationReport:
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    removed_actions: list[str] = field(default_factory=list)
    removed_action_items: int = 0
    removed_deadlines: int = 0

    def dump(self) -> dict[str, object]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "removed_actions": self.removed_actions,
            "removed_action_items": self.removed_action_items,
            "removed_deadlines": self.removed_deadlines,
        }


class TriageValidator:
    @staticmethod
    def _visual_supports(
        span: str,
        asset_id: str | None,
        block_ids: list[str],
        analyses: list[VisualAnalysis],
        thread_asset_ids: set[str],
    ) -> bool:
        if not span or not asset_id or asset_id not in thread_asset_ids or not block_ids:
            return False
        analysis = next(
            (
                item
                for item in analyses
                if item.asset_id == asset_id and item.status == "completed"
            ),
            None,
        )
        if analysis is None:
            return False
        requested = set(block_ids)
        blocks = [block for block in analysis.blocks if block.block_id in requested]
        # OCR-derived actions and dates must point to real coordinates. A whole-image
        # fallback transcription is useful for search, but is not strong enough evidence.
        if not blocks or requested != {block.block_id for block in blocks}:
            return False
        if any(block.region is None for block in blocks):
            return False
        return span in "\n".join(block.text for block in blocks)

    def validate(
        self,
        triage: TriageResult,
        thread: GroupedThread,
        signals: RuleSignals,
        visual_analyses: list[VisualAnalysis] | None = None,
    ) -> tuple[TriageResult, ValidationReport]:
        report = ValidationReport()
        source = combined_text(thread)
        analyses = visual_analyses or []
        thread_asset_ids = {
            asset.asset_id for message in thread.messages for asset in message.media
        }
        cleaned = triage.model_copy(deep=True)

        valid_items = []
        for item in cleaned.action_items:
            if item.supporting_span and (
                item.supporting_span in source
                or self._visual_supports(
                    item.supporting_span,
                    item.evidence_asset_id,
                    item.evidence_block_ids,
                    analyses,
                    thread_asset_ids,
                )
            ):
                valid_items.append(item)
            else:
                report.removed_action_items += 1
                report.errors.append("action_item_missing_supporting_span")
        cleaned.action_items = valid_items

        valid_deadlines = []
        for deadline in cleaned.deadlines:
            in_messages = (
                deadline.original_text in source and deadline.supporting_span in source
            )
            in_visual_evidence = self._visual_supports(
                deadline.supporting_span,
                deadline.evidence_asset_id,
                deadline.evidence_block_ids,
                analyses,
                thread_asset_ids,
            ) and deadline.original_text in deadline.supporting_span
            if deadline.original_text and (in_messages or in_visual_evidence):
                valid_deadlines.append(deadline)
            else:
                report.removed_deadlines += 1
                report.errors.append("deadline_missing_supporting_span")
        cleaned.deadlines = valid_deadlines

        actions = []
        for action in cleaned.suggested_actions:
            if action in ALLOWED_ACTIONS:
                actions.append(action)
            else:
                report.removed_actions.append(action)
                report.errors.append("unsupported_action")
        cleaned.suggested_actions = list(dict.fromkeys(actions))

        valid_spans = [span for span in cleaned.supporting_spans if span and span in source]
        if len(valid_spans) != len(cleaned.supporting_spans):
            report.warnings.append("invalid_general_supporting_span_removed")
        cleaned.supporting_spans = list(dict.fromkeys(valid_spans))

        media = [asset for message in thread.messages for asset in message.media]
        if media and any(str(asset.availability) != "available" for asset in media):
            if "image_unavailable" not in cleaned.uncertainty_flags:
                cleaned.uncertainty_flags.append("image_unavailable")
            report.warnings.append("image_content_unavailable")

        is_preview = thread.content_completeness in {
            "notification_preview",
            "metadata_only",
            "mixed",
        }
        if is_preview and "incomplete_preview" not in cleaned.uncertainty_flags:
            cleaned.uncertainty_flags.append("incomplete_preview")
            report.warnings.append("preview_limitation_added")
        if (
            is_preview
            and cleaned.priority == "urgent"
            and not (
                signals.is_vip
                or "explicit_urgency" in signals.reason_codes
                or signals.category == "security"
            )
        ):
            cleaned.priority = "high"
            report.warnings.append("preview_urgent_downgraded")
        if thread.content_completeness == "metadata_only":
            cleaned.priority = "unknown"
            cleaned.requires_reply = "unknown"
            cleaned.action_items = []
            cleaned.deadlines = []
            cleaned.suggested_actions = ["open_source", "needs_review"]
            if "missing_context" not in cleaned.uncertainty_flags:
                cleaned.uncertainty_flags.append("missing_context")

        # Any evidence error makes the model result unsafe. The pipeline can still use the
        # cleaned form, or replace it with the deterministic baseline.
        report.valid = not report.errors
        return cleaned, report
