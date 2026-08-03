from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any, Protocol

from PIL import Image

from .media_store import MediaStore
from .models import MediaAssetRef, OcrBlock, OcrRegion, VisualAnalysis


def _region(values: list[float], width: int, height: int) -> OcrRegion | None:
    if len(values) != 4 or width <= 0 or height <= 0:
        return None
    x1, y1, x2, y2 = values
    # Paddle spotting commonly emits a 0..1000 coordinate space. JSON adapters may
    # return source pixels or normalized coordinates; all are accepted and normalized.
    if max(values) <= 1:
        scale_x = scale_y = 1.0
    elif max(values) <= 1000 and (width > 1000 or height > 1000):
        scale_x = scale_y = 1000.0
    else:
        scale_x, scale_y = float(width), float(height)
    x1, x2 = sorted((max(0.0, x1 / scale_x), min(1.0, x2 / scale_x)))
    y1, y2 = sorted((max(0.0, y1 / scale_y), min(1.0, y2 / scale_y)))
    if x2 <= x1 or y2 <= y1:
        return None
    return OcrRegion(x=x1, y=y1, width=x2 - x1, height=y2 - y1)


def _block(asset_id: str, text: str, region: OcrRegion | None, confidence: Any) -> OcrBlock:
    key = f"{asset_id}\0{text}\0{region.model_dump_json() if region else ''}"
    block_id = "ocr_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    try:
        parsed_confidence = float(confidence) if confidence is not None else None
    except (TypeError, ValueError):
        parsed_confidence = None
    if parsed_confidence is not None and not 0 <= parsed_confidence <= 1:
        parsed_confidence = None
    return OcrBlock(
        block_id=block_id,
        text=text.strip()[:4000],
        region=region,
        confidence=parsed_confidence,
    )


def parse_spotting_output(
    raw: str, *, asset_id: str, width: int, height: int
) -> list[OcrBlock]:
    """Parse Paddle spotting JSON and its reference/detection token format."""
    raw = raw.strip()[:200_000]
    blocks: list[OcrBlock] = []
    candidate = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.DOTALL)
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        payload = None
    records: list[Any] = []
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        for key in ("blocks", "items", "results", "ocr"):
            if isinstance(payload.get(key), list):
                records = payload[key]
                break
    for record in records:
        if not isinstance(record, dict):
            continue
        text = str(record.get("text") or record.get("content") or "").strip()
        coords = record.get("bbox") or record.get("box") or record.get("coordinate")
        if text and isinstance(coords, list):
            flat = coords
            if coords and isinstance(coords[0], list):
                xs = [float(point[0]) for point in coords if len(point) >= 2]
                ys = [float(point[1]) for point in coords if len(point) >= 2]
                flat = [min(xs), min(ys), max(xs), max(ys)] if xs and ys else []
            blocks.append(
                _block(
                    asset_id,
                    text,
                    _region([float(value) for value in flat], width, height),
                    record.get("confidence") or record.get("score"),
                )
            )
    if blocks:
        return blocks

    token_pattern = re.compile(
        r"<\|ref\|>(.*?)<\|/ref\|>\s*<\|det\|>\s*\[?\["
        r"\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)"
        r"\s*\]\]?\s*<\|/det\|>",
        re.DOTALL,
    )
    for match in token_pattern.finditer(raw):
        text = re.sub(r"\s+", " ", match.group(1)).strip()
        if text:
            coords = [float(match.group(index)) for index in range(2, 6)]
            blocks.append(_block(asset_id, text, _region(coords, 1000, 1000), None))
    if blocks:
        return blocks

    # PaddleOCR-VL-1.6 spotting emits one text line followed by four polygon
    # coordinates as eight <|LOC_n|> tokens.
    loc_pattern = re.compile(r"^(.*?)(?:(<\|LOC_[0-9]+\|>){8})", re.MULTILINE)
    for match in loc_pattern.finditer(raw):
        text = match.group(1).strip()
        tokens = [float(value) for value in re.findall(r"LOC_([0-9]+)", match.group(0))]
        if not text or len(tokens) != 8:
            continue
        xs, ys = tokens[0::2], tokens[1::2]
        coords = [min(xs), min(ys), max(xs), max(ys)]
        blocks.append(_block(asset_id, text, _region(coords, 1000, 1000), None))
    return blocks


class VisionAnalyzer(Protocol):
    backend_name: str

    def analyze(self, media: MediaAssetRef) -> VisualAnalysis: ...


class DisabledVisionAnalyzer:
    backend_name = "disabled"

    def analyze(self, media: MediaAssetRef) -> VisualAnalysis:
        raise RuntimeError("vision analysis is disabled")


class PaddleOcrVlAnalyzer:
    """Lazy, local Transformers runtime for PaddleOCR-VL-1.6 text spotting."""

    backend_name = "paddleocr-vl-transformers"

    def __init__(self, model_id: str, revision: str | None, media_store: MediaStore):
        self.model_id = model_id
        self.revision = revision
        self.media_store = media_store
        self._model: Any = None
        self._processor: Any = None

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            import torch
            from transformers import AutoModelForImageTextToText, AutoProcessor
        except ImportError as error:
            raise RuntimeError("install SignalDesk with the 'vision' extra") from error
        if not torch.cuda.is_available():
            raise RuntimeError("PaddleOCR-VL requires a CUDA GPU in this configuration")
        kwargs = {"revision": self.revision} if self.revision else {}
        self._processor = AutoProcessor.from_pretrained(self.model_id, **kwargs)
        self._model = AutoModelForImageTextToText.from_pretrained(
            self.model_id,
            torch_dtype=torch.bfloat16,
            device_map="cuda",
            **kwargs,
        ).eval()

    def analyze(self, media: MediaAssetRef) -> VisualAnalysis:
        if not media.sha256:
            raise RuntimeError("media hash is required")
        started = datetime.now(UTC)
        try:
            self._load()
            path = self.media_store.path_for(media)
            with Image.open(path) as image:
                image = image.convert("RGB")
                width, height = image.size
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image", "image": image},
                            {"type": "text", "text": "Spotting:"},
                        ],
                    }
                ]
                inputs = self._processor.apply_chat_template(
                    messages,
                    tokenize=True,
                    add_generation_prompt=True,
                    return_dict=True,
                    return_tensors="pt",
                ).to(self._model.device)
                output = self._model.generate(**inputs, max_new_tokens=1024, do_sample=False)
                raw = self._processor.batch_decode(
                    output[:, inputs["input_ids"].shape[-1] :], skip_special_tokens=False
                )[0]
            blocks = parse_spotting_output(
                raw, asset_id=media.asset_id, width=width, height=height
            )
            if not blocks:
                raise RuntimeError("OCR output did not contain localized text blocks")
            return VisualAnalysis(
                asset_id=media.asset_id,
                asset_sha256=media.sha256,
                status="completed",
                ocr_model_id=self.model_id,
                ocr_model_revision=self.revision,
                blocks=blocks,
                raw_text="\n".join(block.text for block in blocks),
                started_at=started,
                completed_at=datetime.now(UTC),
            )
        except Exception as error:
            return VisualAnalysis(
                asset_id=media.asset_id,
                asset_sha256=media.sha256,
                status="failed",
                ocr_model_id=self.model_id,
                ocr_model_revision=self.revision,
                error_code=type(error).__name__,
                started_at=started,
                completed_at=datetime.now(UTC),
            )


def build_vision_analyzer(
    backend: str, model_id: str, revision: str | None, media_store: MediaStore
) -> VisionAnalyzer:
    if backend in {"paddleocr-vl", "transformers"}:
        return PaddleOcrVlAnalyzer(model_id, revision, media_store)
    return DisabledVisionAnalyzer()
