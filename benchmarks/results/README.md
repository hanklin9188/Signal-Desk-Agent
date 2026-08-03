# RTX 4080 SUPER multimodal smoke results

Measured on 2026-08-03 with PyTorch 2.13.0+cu130 and Transformers 5.14.1. The input is the
fictional `mm-001` audit card. These are one-image hardware/runtime smoke tests, not the 300-item
human-reviewed quality audit.

| Model | Mode | Peak VRAM | Latency | Tokens/s | Found visible deadline |
|---|---:|---:|---:|---:|---:|
| Qwen3.5-4B | BF16 | 8.671 GiB | 5.655 s | 16.621 | Yes |
| Qwen3.5-4B | NF4 | 3.290 GiB | 5.371 s | 14.337 | Yes |
| Qwen3.5-4B | INT8 | 5.054 GiB | 17.416 s | 3.904 | Yes |
| PaddleOCR-VL-1.6 | BF16 | 1.809 GiB | 7.067 s | 11.179 | Yes |

First Qwen BF16 load was 221.383 seconds because the model weights were downloaded. Cached loads
were 11–12 seconds for the quantized runs. NF4 is the current residency candidate because it used
38% of BF16 peak VRAM with similar one-image latency. INT8 was substantially slower on this stack.

The JSON files intentionally store no input path, prompt, or decoded model output. They include the
model revision, output hash, software versions and the exact-text smoke result.
