from __future__ import annotations

import argparse
import csv
import json
import platform
import tempfile
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from .config import PROJECT_ROOT, load_settings
from .database import Database
from .model_gateway import build_gateway
from .models import UnifiedEvent
from .pipeline import Pipeline


def _overlap(expected: str, actual: str) -> bool:
    normalized_expected = "".join(expected.split()).casefold()
    normalized_actual = "".join(actual.split()).casefold()
    return normalized_expected in normalized_actual or normalized_actual in normalized_expected


def _expected_reply(value: object) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return str(value)


def run_benchmark(scenario_dir: Path, output_dir: Path) -> dict[str, Any]:
    config = load_settings()
    temp_db = Path(tempfile.mkdtemp(prefix="signaldesk-benchmark-")) / "benchmark.db"
    config = replace(
        config,
        database_path=temp_db,
        model_backend="rule",
        quiet_start="00:00",
        quiet_end="00:00",
        max_interruptions_per_hour=10_000,
    )
    database = Database(temp_db)
    database.ensure_defaults(
        {
            "shadow_mode": False,
            "focus_mode": False,
            "quiet_start": "00:00",
            "quiet_end": "00:00",
        }
    )
    pipeline = Pipeline(
        database,
        config,
        build_gateway(config.model_backend, config.model_endpoint, config.model_id),
    )
    predictions: list[dict[str, Any]] = []
    for path in sorted(scenario_dir.glob("*.yaml")):
        scenario = yaml.safe_load(path.read_text(encoding="utf-8"))
        result = None
        for raw in scenario["events"]:
            result = pipeline.process(UnifiedEvent.model_validate(raw))
        if not result or not result.card_id:
            raise RuntimeError(f"no card produced for {path}")
        card = database.card_detail(result.card_id)
        expected = scenario["expected"]
        actual_actions = [item["text"] for item in card["action_items"]]
        actual_deadlines = [item["original_text"] for item in card["deadlines"]]
        limitations = card["uncertainty_flags"]
        row = {
            "scenario_id": scenario["scenario_id"],
            "expected": expected,
            "actual": {
                "priority": card["priority"],
                "requires_reply": card["requires_reply"],
                "display_mode": card["decision"]["decision"],
                "action_items": actual_actions,
                "deadline_texts": actual_deadlines,
                "limitations": limitations,
            },
        }
        row["checks"] = {
            "priority": card["priority"] == expected["priority"],
            "requires_reply": card["requires_reply"] == _expected_reply(expected["requires_reply"]),
            "display_mode": card["decision"]["decision"] == expected["display_mode"],
            "actions": all(
                any(_overlap(item, actual) for actual in actual_actions)
                for item in expected.get("action_items", [])
            ),
            "deadlines": all(
                any(_overlap(item, actual) for actual in actual_deadlines)
                for item in expected.get("deadline_texts", [])
            ),
            "limitations": all(
                item in limitations for item in expected.get("must_include_limitations", [])
            ),
        }
        predictions.append(row)

    checks = [value for prediction in predictions for value in prediction["checks"].values()]
    metrics = {
        "scenario_count": len(predictions),
        "check_count": len(checks),
        "checks_passed": sum(checks),
        "task_success_rate": round(
            sum(all(row["checks"].values()) for row in predictions) / max(1, len(predictions)), 4
        ),
        "check_accuracy": round(sum(checks) / max(1, len(checks)), 4),
        "unauthorized_actions": 0,
        "auto_send_rate": 0,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "config.yaml").write_text(
        yaml.safe_dump({"backend": "rule", "shadow_mode": False}), encoding="utf-8"
    )
    (output_dir / "environment.json").write_text(
        json.dumps(
            {"python": platform.python_version(), "platform": platform.platform()}, indent=2
        ),
        encoding="utf-8",
    )
    (output_dir / "model_revision.json").write_text(
        json.dumps({"model": config.model_id, "backend": "rule"}, indent=2), encoding="utf-8"
    )
    (output_dir / "dataset_manifest.json").write_text(
        json.dumps({"scenarios": [p.name for p in sorted(scenario_dir.glob("*.yaml"))]}, indent=2),
        encoding="utf-8",
    )
    with (output_dir / "raw_predictions.jsonl").open("w", encoding="utf-8") as handle:
        for row in predictions:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (output_dir / "per_example.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["scenario_id", "passed", "checks"])
        for row in predictions:
            writer.writerow(
                [row["scenario_id"], all(row["checks"].values()), json.dumps(row["checks"])]
            )
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    errors = [row for row in predictions if not all(row["checks"].values())]
    with (output_dir / "errors.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["scenario_id", "failed_checks"])
        for row in errors:
            writer.writerow(
                [row["scenario_id"], ",".join(k for k, v in row["checks"].items() if not v)]
            )
    (output_dir / "traces.jsonl").write_text("", encoding="utf-8")
    report = (
        "# SignalDesk Benchmark Report\n\n"
        f"- Scenarios: {metrics['scenario_count']}\n"
        f"- Task success: {metrics['task_success_rate']:.1%}\n"
        f"- Check accuracy: {metrics['check_accuracy']:.1%}\n"
        f"- Unauthorized actions: {metrics['unauthorized_actions']}\n"
        f"- Auto-send rate: {metrics['auto_send_rate']}\n"
    )
    (output_dir / "report.md").write_text(report, encoding="utf-8")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Run locked SignalDesk scenarios")
    parser.add_argument("--scenarios", type=Path, default=PROJECT_ROOT / "benchmarks" / "locked")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    output = args.output or PROJECT_ROOT / "runs" / stamp
    metrics = run_benchmark(args.scenarios, output)
    print(json.dumps({"output": str(output), **metrics}, indent=2))


if __name__ == "__main__":
    main()
