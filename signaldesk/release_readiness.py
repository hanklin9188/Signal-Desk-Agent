from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def verify(shadow_report: Path, locked_audit: Path) -> dict[str, Any]:
    errors: list[str] = []
    shadow = _json(shadow_report)
    if not shadow.get("release_eligible"):
        errors.append("shadow_mode_gates_not_met")
    records = _jsonl(locked_audit)
    if len(records) < 300:
        errors.append("fewer_than_300_audit_samples")
    for record in records:
        review = record.get("review") or {}
        if review.get("decision") not in {"approved", "rejected"}:
            errors.append("audit_contains_unreviewed_samples")
            break
        if not review.get("reviewer") or not review.get("reviewed_at"):
            errors.append("audit_review_provenance_missing")
            break
    return {
        "ready": not errors,
        "errors": errors,
        "shadow_report": str(shadow_report),
        "audit_samples": len(records),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify non-signing v1.0 release gates")
    parser.add_argument("--shadow-report", type=Path, required=True)
    parser.add_argument("--locked-audit", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.shadow_report, args.locked_audit)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ready"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
