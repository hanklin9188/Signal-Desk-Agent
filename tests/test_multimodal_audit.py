from __future__ import annotations

import hashlib
import json
from pathlib import Path


def test_multimodal_audit_queue_has_300_honest_hash_bound_samples():
    root = Path(__file__).resolve().parents[1] / "benchmarks" / "multimodal"
    records = [
        json.loads(line)
        for line in (root / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]

    assert len(records) == 300
    assert len({record["id"] for record in records}) == 300
    assert {record["slice"] for record in records} == {
        "chat_screenshot",
        "document",
        "event_poster",
        "photo_or_sticker",
        "unavailable_or_blocked",
    }
    for record in records:
        asset = root / record["asset"]
        assert asset.is_file()
        assert hashlib.sha256(asset.read_bytes()).hexdigest() == record["asset_sha256"]
        assert record["review"]["status"] == "unreviewed"
        assert record["review"]["reviewer"] is None
