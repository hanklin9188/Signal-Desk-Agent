from __future__ import annotations

import json

from signaldesk.release_readiness import verify


def test_release_gate_rejects_unreviewed_audit_and_incomplete_shadow(tmp_path):
    shadow = tmp_path / "shadow.json"
    audit = tmp_path / "audit.jsonl"
    shadow.write_text(json.dumps({"release_eligible": False}), encoding="utf-8")
    audit.write_text(
        "".join(
            json.dumps({"id": index, "review": {"status": "unreviewed"}}) + "\n"
            for index in range(300)
        ),
        encoding="utf-8",
    )

    result = verify(shadow, audit)

    assert result["ready"] is False
    assert "shadow_mode_gates_not_met" in result["errors"]
    assert "audit_contains_unreviewed_samples" in result["errors"]
