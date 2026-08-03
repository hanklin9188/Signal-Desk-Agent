from __future__ import annotations

from dataclasses import dataclass, field

from .models import ALLOWED_ACTIONS, GroupedThread, TriageResult
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
    def validate(
        self, triage: TriageResult, thread: GroupedThread, signals: RuleSignals
    ) -> tuple[TriageResult, ValidationReport]:
        report = ValidationReport()
        source = combined_text(thread)
        cleaned = triage.model_copy(deep=True)

        valid_items = []
        for item in cleaned.action_items:
            if item.supporting_span and item.supporting_span in source:
                valid_items.append(item)
            else:
                report.removed_action_items += 1
                report.errors.append("action_item_missing_supporting_span")
        cleaned.action_items = valid_items

        valid_deadlines = []
        for deadline in cleaned.deadlines:
            if (
                deadline.original_text in source
                and deadline.supporting_span in source
                and deadline.original_text
            ):
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
