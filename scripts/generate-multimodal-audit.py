from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SLICES = (
    "chat_screenshot",
    "document",
    "event_poster",
    "photo_or_sticker",
    "unavailable_or_blocked",
)
COLORS = ((43, 39, 58), (239, 242, 248), (28, 53, 72), (45, 45, 45), (38, 40, 44))


def _font(size: int):
    candidates = (
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "C:/Windows/Fonts/msjh.ttc",
        "C:/Windows/Fonts/segoeui.ttf",
    )
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _record(index: int, asset_path: str) -> dict[str, object]:
    slice_name = SLICES[index % len(SLICES)]
    day = 8 + index % 20
    text = f"Project Atlas {index:03d} | Submit review by Aug {day}, 2026 | Owner: Alex"
    contains_actionable_text = slice_name in {
        "chat_screenshot",
        "document",
        "event_poster",
    }
    return {
        "id": f"mm-{index:03d}",
        "asset": asset_path,
        "slice": slice_name,
        "source": "synthetic_fictional",
        "expected": {
            "ocr_text": text if contains_actionable_text else "",
            "deadline_text": f"Aug {day}, 2026" if contains_actionable_text else None,
            "action_text": "Submit review" if contains_actionable_text else None,
            "image_available": slice_name != "unavailable_or_blocked",
        },
        "review": {
            "status": "unreviewed",
            "reviewer": None,
            "reviewed_at": None,
            "notes": None,
        },
    }


def _render(record: dict[str, object], destination: Path) -> None:
    index = int(str(record["id"]).split("-")[1])
    slice_index = SLICES.index(str(record["slice"]))
    background = COLORS[slice_index]
    image = Image.new("RGB", (960, 540), background)
    draw = ImageDraw.Draw(image)
    light = slice_index in {1}
    foreground = (34, 37, 44) if light else (246, 246, 250)
    accent = (94, 174, 255) if not light else (83, 78, 194)
    draw.rounded_rectangle((45, 45, 915, 495), radius=30, outline=accent, width=4)
    draw.text((80, 82), str(record["slice"]).replace("_", " ").upper(), font=_font(26), fill=accent)
    expected = record["expected"]
    assert isinstance(expected, dict)
    if expected["ocr_text"]:
        lines = str(expected["ocr_text"]).split(" | ")
        for offset, line in enumerate(lines):
            draw.text((80, 165 + offset * 75), line, font=_font(34), fill=foreground)
    elif record["slice"] == "photo_or_sticker":
        draw.ellipse((315, 145, 645, 455), fill=(242, 190, 62), outline=accent, width=5)
        draw.ellipse((390, 235, 430, 275), fill=(28, 32, 40))
        draw.ellipse((530, 235, 570, 275), fill=(28, 32, 40))
        draw.arc((400, 240, 560, 380), 20, 160, fill=(28, 32, 40), width=10)
    else:
        draw.rounded_rectangle((320, 160, 640, 410), radius=24, outline=(128, 132, 142), width=5)
        draw.line((350, 375, 610, 195), fill=(205, 90, 90), width=10)
        draw.text((350, 420), "IMAGE UNAVAILABLE", font=_font(24), fill=(205, 90, 90))
    draw.text(
        (80, 430),
        f"Fictional audit sample {index:03d} — no personal data",
        font=_font(20),
        fill=accent,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the 300-item fictional audit queue")
    parser.add_argument("--output", type=Path, default=Path("benchmarks/multimodal"))
    parser.add_argument("--count", type=int, default=300)
    args = parser.parse_args()
    if args.count < 300:
        raise SystemExit("the release audit queue must contain at least 300 items")
    records = []
    for index in range(1, args.count + 1):
        relative = f"assets/mm-{index:03d}.png"
        record = _record(index, relative)
        destination = args.output / relative
        _render(record, destination)
        expected_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
        record["asset_sha256"] = expected_hash
        records.append(record)
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = args.output / "manifest.jsonl"
    manifest.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    print(f"generated {len(records)} unreviewed fictional samples at {args.output}")


if __name__ == "__main__":
    main()
