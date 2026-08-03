from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from .database import Database
from .events import EventBus
from .models import CardActionRequest
from .preference import PreferenceRanker


class ActionError(ValueError):
    pass


class CardActions:
    """Only local and reversible actions. There is deliberately no send operation."""

    def __init__(
        self, database: Database, bus: EventBus, preference_ranker: PreferenceRanker | None = None
    ):
        self.database = database
        self.bus = bus
        self.preferences = preference_ranker or PreferenceRanker(database)

    def perform(self, card_id: str, request: CardActionRequest) -> dict[str, Any]:
        card = self.database.card_detail(card_id)
        if not card:
            raise ActionError("card not found")
        action, value = request.action, request.value
        feedback_action = {
            "open": "opened",
            "snooze": "snoozed",
            "mark_done": "marked_done",
            "dismiss": "dismissed",
            "mark_important": "marked_important",
            "mark_not_important": "marked_not_important",
        }.get(action)
        result: dict[str, Any] = {"card_id": card_id, "action": action}

        if action == "open":
            result["source_url"] = card["events"][-1].get("source_url")
            result["safe_to_open"] = bool(result["source_url"])
        elif action == "snooze":
            until = self._date_value(value, fallback=datetime.now(UTC) + timedelta(hours=1))
            self.database.update_card_status(card_id, "snoozed", snoozed_until=until)
            result["snoozed_until"] = until.isoformat()
        elif action == "mark_done":
            self.database.update_card_status(card_id, "done")
        elif action == "dismiss":
            self.database.update_card_status(card_id, "dismissed")
        elif action == "create_reminder":
            fallback = None
            if card.get("deadlines"):
                normalized = card["deadlines"][0].get("normalized_at")
                fallback = datetime.fromisoformat(normalized) if normalized else None
            remind_at = self._date_value(
                value, fallback=fallback or datetime.now(UTC) + timedelta(hours=1)
            )
            reminder_id = f"rem_{uuid.uuid4().hex}"
            note = value.get("note") if isinstance(value, dict) else None
            self.database.create_reminder(reminder_id, card_id, remind_at, note)
            result.update({"reminder_id": reminder_id, "remind_at": remind_at.isoformat()})
        elif action == "draft_reply":
            if card["source"] != "gmail":
                raise ActionError("v1 reply drafts are only available for Gmail")
            body = self._draft_body(value)
            latest = card["events"][-1]
            draft_id = f"draft_{uuid.uuid4().hex}"
            subject = latest.get("title") or card.get("title")
            if subject and not subject.lower().startswith("re:"):
                subject = f"Re: {subject}"
            self.database.create_draft(
                draft_id,
                card_id,
                latest.get("sender"),
                subject,
                body,
            )
            result.update(
                {
                    "draft_id": draft_id,
                    "recipient": latest.get("sender"),
                    "subject": subject,
                    "body": body,
                    "status": "local_preview",
                    "sent": False,
                }
            )
        elif action in {"mark_important", "mark_not_important"}:
            kind = "vip_sender" if action == "mark_important" else "mute_sender"
            sender = card.get("sender")
            if not sender:
                raise ActionError("card has no sender")
            self.database.add_rule(f"rule_{uuid.uuid4().hex}", kind, sender, None)
        else:
            raise ActionError("unsupported action")

        if feedback_action:
            self.database.create_feedback(
                f"feedback_{uuid.uuid4().hex}", card_id, feedback_action, value
            )
            self.preferences.observe(card, feedback_action)
        self.bus.publish("card_updated", {"card_id": card_id, "action": action})
        return result

    @staticmethod
    def _date_value(value: Any, fallback: datetime) -> datetime:
        raw = value.get("at") if isinstance(value, dict) else value
        if raw:
            parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed
        return fallback

    @staticmethod
    def _draft_body(value: Any) -> str:
        if isinstance(value, dict) and value.get("body"):
            return str(value["body"])[:10_000]
        return "您好，\n\n謝謝您的訊息，我已收到。我確認內容後會再回覆您。\n\n謝謝。"
