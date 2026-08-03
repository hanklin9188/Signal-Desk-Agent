from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from signaldesk.models import GroupedMessage, GroupedThread, TriageResult
from signaldesk.pipeline import calibrate_model_triage
from signaldesk.rules import RuleEngine


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Re-score privacy-safe model labels after deterministic policy changes."
    )
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--input-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    cases: list[dict[str, Any]] = yaml.safe_load(args.dataset.read_text(encoding="utf-8"))
    source_report = json.loads(args.input_report.read_text(encoding="utf-8"))
    predictions = {row["id"]: row for row in source_report["results"]}
    rules = RuleEngine("Asia/Taipei")
    results = []
    for index, case in enumerate(cases):
        prior = predictions[case["id"]]
        now = datetime(2026, 8, 3, 9, index, tzinfo=UTC)
        thread = GroupedThread(
            thread_id=f"calibration-{case['id']}",
            source=case["source"],
            sender=case["sender"],
            event_ids=[f"event-{case['id']}"],
            content_completeness=case["completeness"],
            messages=[
                GroupedMessage(
                    event_id=f"event-{case['id']}",
                    received_at=now,
                    sender=case["sender"],
                    content=case["content"],
                )
            ],
            updated_at=now,
        )
        signals = rules.signals(thread, [])
        baseline = rules.triage(thread, signals)
        if prior["backend"] == "rule-constraint":
            triage = baseline
        else:
            actual = prior["actual"]
            model_triage = TriageResult(
                summary="privacy-safe re-score",
                priority=actual["priority"],
                requires_reply=actual["requires_reply"],
                category=actual["category"],
            )
            triage = calibrate_model_triage(model_triage, baseline, signals)
        expected = dict(case["expected"])
        expected["requires_reply"] = (
            "yes"
            if expected["requires_reply"] is True
            else "no"
            if expected["requires_reply"] is False
            else str(expected["requires_reply"])
        )
        actual = {
            "priority": str(triage.priority),
            "requires_reply": str(triage.requires_reply),
            "category": str(triage.category),
        }
        checks = {key: actual[key] == value for key, value in expected.items()}
        results.append(
            {
                "id": case["id"],
                "expected": expected,
                "actual": actual,
                "checks": checks,
                "backend": prior["backend"],
                "model_inference_reused": True,
                "private_content_recorded": False,
            }
        )

    label_checks = [check for row in results for check in row["checks"].values()]
    report = {
        **{key: value for key, value in source_report.items() if key != "results"},
        "rescored_at": datetime.now(UTC).isoformat(),
        "source_report": args.input_report.name,
        "model_inference_reused": True,
        "exact_case_accuracy": round(
            sum(all(row["checks"].values()) for row in results) / len(results), 4
        ),
        "label_accuracy": round(sum(label_checks) / len(label_checks), 4),
        "priority_accuracy": round(
            sum(row["checks"]["priority"] for row in results) / len(results), 4
        ),
        "reply_accuracy": round(
            sum(row["checks"]["requires_reply"] for row in results) / len(results), 4
        ),
        "category_accuracy": round(
            sum(row["checks"]["category"] for row in results) / len(results), 4
        ),
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in report.items() if key != "results"}, indent=2))


if __name__ == "__main__":
    main()
