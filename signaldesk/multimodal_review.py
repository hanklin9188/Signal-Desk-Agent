from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _status(manifest: Path, reviews: Path) -> dict[str, int]:
    records = _read_jsonl(manifest)
    decisions = {item["id"]: item for item in _read_jsonl(reviews)}
    counts = {"total": len(records), "reviewed": 0, "approved": 0, "rejected": 0}
    for record in records:
        decision = decisions.get(record["id"])
        if decision:
            counts["reviewed"] += 1
            counts[str(decision["decision"])] += 1
    counts["remaining"] = counts["total"] - counts["reviewed"]
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Human review ledger for visual audit samples")
    parser.add_argument(
        "--manifest", type=Path, default=Path("benchmarks/multimodal/manifest.jsonl")
    )
    parser.add_argument("--reviews", type=Path, default=Path("data/multimodal-reviews.jsonl"))
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status")
    review = subparsers.add_parser("review")
    review.add_argument("--id", required=True)
    review.add_argument("--decision", choices=["approved", "rejected"], required=True)
    review.add_argument("--reviewer", required=True)
    review.add_argument("--notes", default="")
    lock = subparsers.add_parser("lock")
    lock.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records = _read_jsonl(args.manifest)
    ids = {record["id"] for record in records}
    if args.command == "status":
        print(json.dumps(_status(args.manifest, args.reviews), ensure_ascii=False, indent=2))
        return
    if args.command == "review":
        if args.id not in ids:
            raise SystemExit(f"unknown sample: {args.id}")
        decisions = {item["id"]: item for item in _read_jsonl(args.reviews)}
        decisions[args.id] = {
            "id": args.id,
            "decision": args.decision,
            "reviewer": args.reviewer,
            "notes": args.notes,
            "reviewed_at": datetime.now(UTC).isoformat(),
        }
        args.reviews.parent.mkdir(parents=True, exist_ok=True)
        args.reviews.write_text(
            "".join(
                json.dumps(value, ensure_ascii=False) + "\n"
                for _, value in sorted(decisions.items())
            ),
            encoding="utf-8",
        )
        print(json.dumps(_status(args.manifest, args.reviews), ensure_ascii=False, indent=2))
        return
    status = _status(args.manifest, args.reviews)
    if status["total"] < 300 or status["remaining"]:
        raise SystemExit(
            f"cannot lock: {status['remaining']} of {status['total']} samples remain unreviewed"
        )
    reviews = {item["id"]: item for item in _read_jsonl(args.reviews)}
    locked = [{**record, "review": reviews[record["id"]]} for record in records]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in locked),
        encoding="utf-8",
    )
    print(f"locked {len(locked)} human-reviewed samples at {args.output}")


if __name__ == "__main__":
    main()
