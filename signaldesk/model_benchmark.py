from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image


def _quantization_config(mode: str, transformers: Any) -> tuple[dict[str, Any], str]:
    import torch

    if mode == "bf16":
        return {"torch_dtype": torch.bfloat16, "device_map": "cuda"}, "bf16"
    if mode == "8bit":
        return {
            "quantization_config": transformers.BitsAndBytesConfig(load_in_8bit=True),
            "device_map": "cuda",
        }, "bitsandbytes-int8"
    return {
        "quantization_config": transformers.BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        ),
        "device_map": "cuda",
    }, "bitsandbytes-nf4"


def benchmark(args: argparse.Namespace) -> dict[str, Any]:
    import torch
    import transformers
    from transformers import AutoModelForImageTextToText, AutoProcessor

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available")
    image_path = Path(args.image).resolve()
    with Image.open(image_path) as source:
        image = source.convert("RGB")
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    load_kwargs, quant_backend = _quantization_config(args.quantization, transformers)
    if args.revision:
        load_kwargs["revision"] = args.revision
    started = time.perf_counter()
    processor = AutoProcessor.from_pretrained(
        args.model, revision=args.revision or None, trust_remote_code=False
    )
    if args.family == "qwen":
        from transformers import Qwen3_5ForConditionalGeneration

        model = Qwen3_5ForConditionalGeneration.from_pretrained(args.model, **load_kwargs).eval()
        prompt = args.prompt or (
            "Describe only the visible text and any explicit deadline. Return concise JSON."
        )
    else:
        model = AutoModelForImageTextToText.from_pretrained(args.model, **load_kwargs).eval()
        prompt = args.prompt or "Spotting:"
    load_seconds = time.perf_counter() - started
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt},
            ],
        }
    ]
    template_kwargs: dict[str, Any] = {
        "tokenize": True,
        "add_generation_prompt": True,
        "return_dict": True,
        "return_tensors": "pt",
    }
    if args.family == "qwen":
        template_kwargs["enable_thinking"] = False
    inputs = processor.apply_chat_template(messages, **template_kwargs).to(model.device)
    latencies: list[float] = []
    output_text = ""
    output_tokens = 0
    for _ in range(args.warmup + args.iterations):
        torch.cuda.synchronize()
        run_started = time.perf_counter()
        with torch.inference_mode():
            output = model.generate(
                **inputs,
                max_new_tokens=args.max_new_tokens,
                do_sample=False,
            )
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - run_started
        generated = output[:, inputs["input_ids"].shape[-1] :]
        output_tokens = int(generated.shape[-1])
        output_text = processor.batch_decode(generated, skip_special_tokens=False)[0]
        if len(latencies) >= args.warmup:
            latencies.append(elapsed)
        else:
            latencies.append(elapsed)
    measured = latencies[args.warmup :]
    peak_bytes = int(torch.cuda.max_memory_allocated())
    normalized_output = " ".join(unicodedata.normalize("NFKC", output_text).split())
    normalized_expected = (
        " ".join(unicodedata.normalize("NFKC", args.expected_text).split())
        if args.expected_text
        else ""
    )
    result = {
        "schema_version": "1.0",
        "measured_at": datetime.now(UTC).isoformat(),
        "model_id": args.model,
        "revision": args.revision or getattr(model.config, "_commit_hash", None),
        "family": args.family,
        "quantization": args.quantization,
        "quantization_backend": quant_backend,
        "gpu": torch.cuda.get_device_name(0),
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "load_seconds": round(load_seconds, 3),
        "peak_vram_gib": round(peak_bytes / 1024**3, 3),
        "iterations": args.iterations,
        "latency_seconds": [round(value, 3) for value in measured],
        "median_latency_seconds": round(statistics.median(measured), 3),
        "output_tokens": output_tokens,
        "median_tokens_per_second": round(
            output_tokens / statistics.median(measured), 3
        ),
        "output_sha256": hashlib.sha256(output_text.encode("utf-8")).hexdigest(),
        "expected_text_found": (
            normalized_expected.casefold() in normalized_output.casefold()
            if args.expected_text
            else None
        ),
        "private_input_recorded": False,
    }
    if args.include_output:
        result["output"] = output_text
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark local multimodal models on CUDA")
    parser.add_argument("--family", choices=["qwen", "paddle"], required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--revision")
    parser.add_argument("--image", required=True)
    parser.add_argument("--prompt")
    parser.add_argument("--expected-text")
    parser.add_argument("--quantization", choices=["bf16", "8bit", "4bit"], default="bf16")
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--max-new-tokens", type=int, default=128)
    parser.add_argument("--include-output", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = benchmark(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(rendered, encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
