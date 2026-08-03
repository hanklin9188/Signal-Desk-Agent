from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
import time
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

from signaldesk.media_store import MediaStore
from signaldesk.model_gateway import TransformersGateway
from signaldesk.models import GroupedMessage, GroupedThread
from signaldesk.pipeline import calibrate_model_triage
from signaldesk.rules import RuleEngine
from signaldesk.runtime_memory import release_cuda_memory
from signaldesk.vision import PaddleOcrVlAnalyzer


def _contains_any(value: str, expected: list[str]) -> bool:
    folded = value.casefold().replace(" ", "")
    return any(term.casefold().replace(" ", "") in folded for term in expected)


def _token_recall(value: str, expected: list[str]) -> float:
    expected_tokens = set(
        re.findall(r"[\w]+", unicodedata.normalize("NFKC", " ".join(expected)).casefold())
    )
    actual_tokens = set(
        re.findall(r"[\w]+", unicodedata.normalize("NFKC", value).casefold())
    )
    return (
        len(expected_tokens & actual_tokens) / len(expected_tokens)
        if expected_tokens
        else 1.0 if not actual_tokens else 0.0
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Exercise the sequential OCR-to-Qwen image path without storing model text."
    )
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--include-synthetic-output", action="store_true")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    fixtures = [
        {
            "id": "document-deadline",
            "path": project_root / "benchmarks/multimodal/assets/mm-001.png",
            "expected_ocr": ["Aug 9, 2026"],
            "expected_summary": ["Aug 9, 2026", "2026年8月9日", "8月9日"],
        },
        {
            "id": "no-text-smile",
            "path": project_root / "benchmarks/calibration/no-text-photo.png",
            "expected_ocr": [],
            "expected_summary": ["笑臉", "微笑", "smile", "smiley"],
        },
    ]
    store = MediaStore(Path(tempfile.mkdtemp(prefix="signaldesk-image-pipeline-")))
    analyzer = PaddleOcrVlAnalyzer(
        "PaddlePaddle/PaddleOCR-VL-1.6",
        "66317acc4c9fc17bd154591ce650735cd2855f3e",
        store,
    )
    gateway = TransformersGateway(
        "Qwen/Qwen3.5-4B",
        media_store=store,
        revision="851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a",
        quantization="nf4",
    )
    rules = RuleEngine("Asia/Taipei")
    prepared = []
    started = time.perf_counter()
    try:
        for fixture in fixtures:
            media = store.import_bytes(
                fixture["path"].read_bytes(),
                declared_mime="image/png",
                original_name=fixture["path"].name,
            )
            analysis = analyzer.analyze(media)
            prepared.append((fixture, media, analysis))
        analyzer.release()
        for fixture, media, analysis in prepared:
            now = datetime.now(UTC)
            thread = GroupedThread(
                thread_id=f"image-pipeline-{fixture['id']}",
                source="gmail",
                sender="synthetic@example.test",
                event_ids=[f"event-{fixture['id']}"],
                content_completeness="full",
                messages=[
                    GroupedMessage(
                        event_id=f"event-{fixture['id']}",
                        received_at=now,
                        sender="synthetic@example.test",
                        content="Attached image",
                        media=[media],
                    )
                ],
                updated_at=now,
            )
            signals = rules.signals(thread, [])
            baseline = rules.triage(thread, signals)
            prediction = gateway.analyze(thread, signals, [analysis])
            triage = (
                calibrate_model_triage(prediction.triage, baseline, signals)
                if prediction.triage
                else None
            )
            ocr_recall = _token_recall(analysis.raw_text, fixture["expected_ocr"])
            fixture["result"] = {
                "id": fixture["id"],
                "ocr_completed": analysis.status == "completed",
                "ocr_token_recall": round(ocr_recall, 4),
                "ocr_expected_found": ocr_recall >= 0.8,
                "qwen_completed": triage is not None,
                "summary_expected_found": bool(
                    triage and _contains_any(triage.summary, fixture["expected_summary"])
                ),
                "priority": str(triage.priority) if triage else None,
                "requires_reply": str(triage.requires_reply) if triage else None,
                "model_error_code": prediction.error_code,
                "model_output_sha256": hashlib.sha256(
                    (prediction.raw_output or "").encode("utf-8")
                ).hexdigest(),
                "private_content_recorded": False,
            }
            if args.include_synthetic_output:
                fixture["result"]["synthetic_ocr_output"] = analysis.raw_text
                fixture["result"]["synthetic_summary_output"] = (
                    triage.summary if triage else None
                )
    finally:
        analyzer.release()
        gateway.release()
        release_cuda_memory()

    results = [fixture["result"] for fixture in fixtures]
    report = {
        "schema_version": "1.0",
        "measured_at": datetime.now(UTC).isoformat(),
        "workflow": "PaddleOCR-VL-1.6 -> release -> Qwen3.5-4B NF4 -> release",
        "case_count": len(results),
        "passed_count": sum(
            row["ocr_completed"]
            and row["ocr_expected_found"]
            and row["qwen_completed"]
            and row["summary_expected_found"]
            for row in results
        ),
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
