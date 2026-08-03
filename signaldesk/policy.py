from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

from .config import Settings
from .models import AgentDecision, TriageResult
from .rules import RuleSignals

PRIORITY_SCORE = {
    "urgent": 0.9,
    "high": 0.68,
    "normal": 0.38,
    "low": 0.15,
    "noise": 0.0,
    "unknown": 0.22,
}


def _parse_clock(value: str) -> time:
    hour, minute = value.split(":", 1)
    return time(int(hour), int(minute))


def _in_quiet_hours(now: datetime, start: str, end: str) -> bool:
    current = now.time().replace(tzinfo=None)
    start_time, end_time = _parse_clock(start), _parse_clock(end)
    if start_time <= end_time:
        return start_time <= current < end_time
    return current >= start_time or current < end_time


class InterruptionPolicy:
    def __init__(self, config: Settings):
        self.config = config

    def decide(
        self,
        triage: TriageResult,
        signals: RuleSignals,
        user_settings: dict[str, object],
        *,
        now: datetime | None = None,
        preference_score: float | None = None,
        interruptions_last_hour: int = 0,
    ) -> AgentDecision:
        zone = ZoneInfo(self.config.timezone)
        now = (now or datetime.now(zone)).astimezone(zone)
        reasons = list(dict.fromkeys(signals.reason_codes))

        if signals.is_noise:
            return AgentDecision(
                decision="ignore_as_noise",
                reason_codes=reasons or ["noise_rule"],
                calibrated_score=0,
            )
        if signals.muted:
            return AgentDecision(
                decision="include_in_digest",
                reason_codes=reasons or ["user_mute_rule"],
                calibrated_score=0.1,
            )

        score = PRIORITY_SCORE[str(triage.priority)]
        if triage.requires_reply == "yes":
            score += 0.14
        if triage.deadlines:
            score += 0.12
        if signals.is_vip:
            score += 0.16
        score -= min(0.18, 0.06 * len(triage.uncertainty_flags))
        if preference_score is not None:
            score += (preference_score - 0.5) * 0.22
            if abs(preference_score - 0.5) >= 0.08:
                reasons.append("personal_preference")
        score = max(0.0, min(1.0, score))

        quiet_start = str(user_settings.get("quiet_start", self.config.quiet_start))
        quiet_end = str(user_settings.get("quiet_end", self.config.quiet_end))
        quiet = _in_quiet_hours(now, quiet_start, quiet_end)
        focus = bool(user_settings.get("focus_mode", False))
        surface_threshold = self.config.surface_threshold + (0.08 if focus else 0)

        allowed_quiet_override = (
            triage.priority == "urgent"
            and (signals.category == "security" or "explicit_urgency" in signals.reason_codes)
        ) or signals.is_vip
        if quiet and not allowed_quiet_override:
            score = max(0, score - 0.35)
            reasons.append("quiet_hours")
        if focus:
            reasons.append("focus_mode")
        if triage.requires_reply == "yes":
            reasons.append("reply_needed")
        if triage.deadlines:
            reasons.append("deadline_detected")
        if triage.uncertainty_flags:
            reasons.append("source_limitation")

        if score >= surface_threshold:
            decision = "surface_now"
        elif score >= self.config.review_threshold:
            decision = "needs_review" if triage.uncertainty_flags else "store_in_inbox"
        elif triage.priority in {"low", "normal"}:
            decision = "include_in_digest"
        else:
            decision = "store_in_inbox"

        if (
            decision == "surface_now"
            and interruptions_last_hour >= self.config.max_interruptions_per_hour
            and not allowed_quiet_override
        ):
            decision = "include_in_digest"
            reasons.append("interruption_budget")

        if bool(user_settings.get("shadow_mode", True)) and decision == "surface_now":
            decision = "store_in_inbox"
            reasons.extend(["shadow_mode", "would_surface_now"])
        return AgentDecision(
            decision=decision,
            reason_codes=list(dict.fromkeys(reasons)),
            calibrated_score=round(score, 3),
        )


def display_mode(decision: str) -> str:
    return {
        "surface_now": "surface_now",
        "store_in_inbox": "inbox",
        "include_in_digest": "digest",
        "needs_review": "review",
        "ignore_as_noise": "hidden",
        "request_confirmation": "review",
    }[decision]
