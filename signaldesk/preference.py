from __future__ import annotations

import hashlib
import math
import uuid
from datetime import datetime
from typing import Any

from .database import Database

ACTION_LABELS = {
    "opened": 0.85,
    "marked_done": 0.75,
    "marked_important": 1.0,
    "snoozed": 0.35,
    "dismissed": 0.0,
    "marked_not_important": 0.0,
}


class PreferenceRanker:
    """Small local logistic ranker trained only on privacy-minimized behavior features."""

    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def features(
        *,
        source: str,
        sender: str | None,
        category: str,
        requires_reply: str,
        has_deadline: bool,
        at: datetime,
    ) -> dict[str, float]:
        sender_hash = hashlib.sha256((sender or "unknown").casefold().encode()).hexdigest()[:12]
        hour_bucket = at.astimezone().hour // 6
        return {
            "bias": 1.0,
            f"source:{source}": 1.0,
            f"sender_hash:{sender_hash}": 1.0,
            f"category:{category}": 1.0,
            f"reply:{requires_reply}": 1.0,
            f"deadline:{int(has_deadline)}": 1.0,
            f"time_bucket:{hour_bucket}": 1.0,
        }

    def score(
        self,
        *,
        source: str,
        sender: str | None,
        category: str,
        requires_reply: str,
        has_deadline: bool,
        at: datetime,
    ) -> float | None:
        weights = self.database.preference_weights()
        if not weights:
            return None
        features = self.features(
            source=source,
            sender=sender,
            category=category,
            requires_reply=requires_reply,
            has_deadline=has_deadline,
            at=at,
        )
        return self._predict(weights, features)

    def observe(self, card: dict[str, Any], action: str) -> bool:
        if action not in ACTION_LABELS:
            return False
        created = datetime.fromisoformat(card.get("created_at") or datetime.now().isoformat())
        features = self.features(
            source=str(card.get("source", "unknown")),
            sender=card.get("sender"),
            category=str(card.get("category", "unknown")),
            requires_reply=str(card.get("requires_reply", "unknown")),
            has_deadline=bool(card.get("deadline_text")),
            at=created,
        )
        self.database.add_preference_observation(
            f"pref_{uuid.uuid4().hex}", features, ACTION_LABELS[action], action
        )
        return self.retrain_if_calibrated()

    def retrain_if_calibrated(self) -> bool:
        observations = self.database.preference_observations()
        if len(observations) < 8:
            return False
        split = max(6, int(len(observations) * 0.8))
        training, validation = observations[:split], observations[split:]
        if not validation:
            return False
        candidate: dict[str, float] = {}
        learning_rate = 0.12
        for _ in range(45):
            for item in training:
                prediction = self._predict(candidate, item["features"])
                error = float(item["label"]) - prediction
                for feature, value in item["features"].items():
                    candidate[feature] = candidate.get(feature, 0.0) + learning_rate * (
                        error * float(value) - 0.002 * candidate.get(feature, 0.0)
                    )
        existing = self.database.preference_weights()
        current_loss = self._brier(existing, validation) if existing else 0.25
        candidate_loss = self._brier(candidate, validation)
        if candidate_loss + 0.001 >= current_loss:
            return False
        self.database.save_preference_weights(candidate)
        return True

    @classmethod
    def _brier(cls, weights: dict[str, float], rows: list[dict[str, Any]]) -> float:
        return sum(
            (cls._predict(weights, row["features"]) - float(row["label"])) ** 2 for row in rows
        ) / len(rows)

    @staticmethod
    def _predict(weights: dict[str, float], features: dict[str, float]) -> float:
        value = sum(weights.get(feature, 0.0) * amount for feature, amount in features.items())
        value = max(-12.0, min(12.0, value))
        return 1.0 / (1.0 + math.exp(-value))
