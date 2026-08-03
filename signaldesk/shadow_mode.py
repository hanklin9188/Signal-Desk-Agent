from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .database import Database

POSITIVE = {"open", "create_reminder", "draft_reply", "mark_important"}
NEGATIVE = {"dismiss", "mark_not_important"}


def start(database: Database, *, reset: bool = False) -> str:
    settings = database.settings()
    existing = settings.get("shadow_evaluation_started_at")
    if existing and not reset:
        return str(existing)
    started_at = datetime.now(UTC).isoformat()
    database.update_settings(
        {"shadow_mode": True, "shadow_evaluation_started_at": started_at}
    )
    return started_at


def report(database: Database, *, days: int = 14, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    settings = database.settings()
    started_raw = settings.get("shadow_evaluation_started_at")
    started = datetime.fromisoformat(started_raw) if started_raw else None
    window_start = max(
        now - timedelta(days=days),
        started or now,
    )
    with database.connect() as connection:
        rows = connection.execute(
            """
            SELECT tr.thread_id, tr.decision_json, tr.validation_json, tr.model_backend,
                   tr.updated_at, c.card_id, c.source
            FROM triage_results tr
            JOIN notification_cards c ON c.thread_id=tr.thread_id
            WHERE tr.updated_at>=? AND tr.updated_at<=?
            """,
            (window_start.isoformat(), now.isoformat()),
        ).fetchall()
        feedback = connection.execute(
            """
            SELECT f.card_id, f.action
            FROM feedback_events f
            WHERE f.created_at>=? AND f.created_at<=?
            """,
            (window_start.isoformat(), now.isoformat()),
        ).fetchall()
    feedback_by_card: dict[str, set[str]] = {}
    for item in feedback:
        feedback_by_card.setdefault(str(item["card_id"]), set()).add(str(item["action"]))
    sources: Counter[str] = Counter()
    backends: Counter[str] = Counter()
    would_surface = 0
    validation_errors = 0
    positive = negative = 0
    for row in rows:
        decision = json.loads(row["decision_json"])
        validation = json.loads(row["validation_json"])
        sources[str(row["source"])] += 1
        backends[str(row["model_backend"])] += 1
        if validation.get("errors"):
            validation_errors += 1
        if "would_surface_now" not in decision.get("reason_codes", []):
            continue
        would_surface += 1
        actions = feedback_by_card.get(str(row["card_id"]), set())
        if actions & NEGATIVE:
            negative += 1
        elif actions & POSITIVE:
            positive += 1
    elapsed_days = max(0.0, (now - started).total_seconds() / 86400) if started else 0.0
    labeled = positive + negative
    precision = positive / labeled if labeled else None
    gates = {
        "minimum_elapsed_days": elapsed_days >= 7,
        "recommended_elapsed_days": elapsed_days >= 14,
        "minimum_total_decisions": len(rows) >= 300,
        "minimum_labeled_interruptions": labeled >= 50,
        "precision_at_least_0_90": precision is not None and precision >= 0.90,
        "validation_error_rate_below_0_01": (
            validation_errors / len(rows) < 0.01 if rows else False
        ),
    }
    required = (
        "minimum_elapsed_days",
        "minimum_total_decisions",
        "minimum_labeled_interruptions",
        "precision_at_least_0_90",
        "validation_error_rate_below_0_01",
    )
    return {
        "schema_version": "1.0",
        "generated_at": now.isoformat(),
        "shadow_started_at": started.isoformat() if started else None,
        "window_start": window_start.isoformat(),
        "elapsed_days": round(elapsed_days, 3),
        "total_decisions": len(rows),
        "would_surface": would_surface,
        "labeled_would_surface": labeled,
        "positive": positive,
        "negative": negative,
        "estimated_precision": round(precision, 4) if precision is not None else None,
        "validation_errors": validation_errors,
        "sources": dict(sources),
        "model_backends": dict(backends),
        "gates": gates,
        "release_eligible": all(gates[name] for name in required),
        "contains_message_content": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage the SignalDesk shadow evaluation")
    parser.add_argument("--database", type=Path, default=Path("data/signaldesk.db"))
    subparsers = parser.add_subparsers(dest="command", required=True)
    start_parser = subparsers.add_parser("start")
    start_parser.add_argument("--reset", action="store_true")
    report_parser = subparsers.add_parser("report")
    report_parser.add_argument("--days", type=int, choices=range(7, 15), default=14)
    report_parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    database = Database(args.database)
    if args.command == "start":
        print(json.dumps({"shadow_started_at": start(database, reset=args.reset)}, indent=2))
        return
    result = report(database, days=args.days)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
