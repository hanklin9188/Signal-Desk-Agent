from __future__ import annotations

import argparse
import json
import re
import tempfile
import time
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

from signaldesk.media_store import MediaStore
from signaldesk.runtime_memory import release_cuda_memory
from signaldesk.vision import PaddleOcrVlAnalyzer


def _tokens(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return set(re.findall(r"[\w]+", normalized, flags=re.UNICODE))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Measure local PaddleOCR-VL on synthetic images without saving OCR output."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="PaddlePaddle/PaddleOCR-VL-1.6")
    parser.add_argument("--revision")
    parser.add_argument("--no-text-image", type=Path)
    parser.add_argument(
        "--ids",
        nargs="+",
        default=["mm-001", "mm-002", "mm-005", "mm-006", "mm-007", "mm-010"],
    )
    args = parser.parse_args()

    wanted = set(args.ids)
    records = [
        json.loads(line)
        for line in args.manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    records = [record for record in records if record["id"] in wanted]
    if args.no_text_image:
        records.append(
            {
                "id": "genuine-no-text-photo",
                "asset": str(args.no_text_image),
                "slice": "photo_or_sticker",
                "expected": {"ocr_text": ""},
                "absolute_asset": True,
            }
        )
    store = MediaStore(Path(tempfile.mkdtemp(prefix="signaldesk-ocr-calibration-")))
    analyzer = PaddleOcrVlAnalyzer(args.model, args.revision, store)
    results = []
    started = time.perf_counter()
    try:
        for record in records:
            asset_path = (
                Path(record["asset"])
                if record.get("absolute_asset")
                else args.root / record["asset"]
            )
            media = store.import_bytes(
                asset_path.read_bytes(),
                declared_mime="image/png",
                original_name=asset_path.name,
            )
            analysis = analyzer.analyze(media)
            expected = record["expected"]["ocr_text"]
            expected_tokens = _tokens(expected)
            actual_tokens = _tokens(analysis.raw_text)
            recall = (
                len(expected_tokens & actual_tokens) / len(expected_tokens)
                if expected_tokens
                else 1.0 if not actual_tokens else 0.0
            )
            results.append(
                {
                    "id": record["id"],
                    "slice": record["slice"],
                    "status": analysis.status,
                    "token_recall": round(recall, 4),
                    "expected_text_present": bool(expected_tokens),
                    "block_count": len(analysis.blocks),
                    "error_code": analysis.error_code,
                    "ocr_text_recorded": False,
                }
            )
    finally:
        analyzer.release()
        release_cuda_memory()

    text_cases = [row for row in results if row["expected_text_present"]]
    no_text_cases = [row for row in results if not row["expected_text_present"]]
    report = {
        "schema_version": "1.0",
        "measured_at": datetime.now(UTC).isoformat(),
        "model_id": args.model,
        "revision": args.revision,
        "case_count": len(results),
        "mean_text_token_recall": round(
            sum(row["token_recall"] for row in text_cases) / max(1, len(text_cases)), 4
        ),
        "no_text_accuracy": round(
            sum(row["token_recall"] == 1.0 for row in no_text_cases)
            / max(1, len(no_text_cases)),
            4,
        ),
        "completed_count": sum(row["status"] == "completed" for row in results),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "ocr_text_recorded": False,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in report.items() if key != "results"}, indent=2))


if __name__ == "__main__":
    main()
