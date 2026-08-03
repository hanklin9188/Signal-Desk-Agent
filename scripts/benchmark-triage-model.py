from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from signaldesk.model_gateway import TransformersGateway
from signaldesk.models import GroupedMessage, GroupedThread
from signaldesk.pipeline import calibrate_model_triage
from signaldesk.rules import RuleEngine
from signaldesk.runtime_memory import release_cuda_memory


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Measure local Qwen triage labels without recording message text or summaries."
    )
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="Qwen/Qwen3.5-4B")
    parser.add_argument("--revision")
    parser.add_argument("--quantization", choices=["none", "nf4", "4bit"], default="nf4")
    args = parser.parse_args()

    cases: list[dict[str, Any]] = yaml.safe_load(args.dataset.read_text(encoding="utf-8"))
    gateway = TransformersGateway(
        args.model,
        revision=args.revision,
        quantization=args.quantization,
    )
    rules = RuleEngine("Asia/Taipei")
    results: list[dict[str, Any]] = []
    started = time.perf_counter()
    try:
        for index, case in enumerate(cases):
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
            model_eligible = bool(case["content"].strip()) and not (
                signals.is_noise or signals.image_only or case["completeness"] == "metadata_only"
            )
            prediction = (
                gateway.analyze(thread, signals)
                if model_eligible
                else None
            )
            expected = dict(case["expected"])
            expected["requires_reply"] = (
                "yes"
                if expected["requires_reply"] is True
                else "no"
                if expected["requires_reply"] is False
                else str(expected["requires_reply"])
            )
            triage = (
                calibrate_model_triage(prediction.triage, baseline, signals)
                if prediction and prediction.triage
                else baseline
            )
            actual = {
                "priority": str(triage.priority) if triage else None,
                "requires_reply": str(triage.requires_reply) if triage else None,
                "category": str(triage.category) if triage else None,
            }
            checks = {key: actual[key] == value for key, value in expected.items()}
            results.append(
                {
                    "id": case["id"],
                    "expected": expected,
                    "actual": actual,
                    "checks": checks,
                    "backend": prediction.backend if prediction else "rule-constraint",
                    "error_code": prediction.error_code if prediction else None,
                    "private_content_recorded": False,
                }
            )
    finally:
        gateway.release()
        release_cuda_memory()

    label_checks = [check for row in results for check in row["checks"].values()]
    exact = [all(row["checks"].values()) for row in results]
    report = {
        "schema_version": "1.0",
        "measured_at": datetime.now(UTC).isoformat(),
        "model_id": args.model,
        "revision": args.revision,
        "quantization": args.quantization,
        "case_count": len(results),
        "exact_case_accuracy": round(sum(exact) / max(1, len(exact)), 4),
        "label_accuracy": round(sum(label_checks) / max(1, len(label_checks)), 4),
        "priority_accuracy": round(
            sum(row["checks"]["priority"] for row in results) / max(1, len(results)), 4
        ),
        "reply_accuracy": round(
            sum(row["checks"]["requires_reply"] for row in results)
            / max(1, len(results)),
            4,
        ),
        "category_accuracy": round(
            sum(row["checks"]["category"] for row in results) / max(1, len(results)), 4
        ),
        "fallback_count": sum(row["actual"]["priority"] is None for row in results),
        "qwen_case_count": sum(row["backend"].startswith("qwen-") for row in results),
        "calibration_policy": "qwen_semantics_with_high_precision_constraints_v1",
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "private_content_recorded": False,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in report.items() if key != "results"}, indent=2))


if __name__ == "__main__":
    main()
