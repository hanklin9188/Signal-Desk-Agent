# Local Model Validation

Verified on 2026-08-03 with an NVIDIA RTX 4080 SUPER. All inputs are synthetic/fictional and all
committed tooling avoids saving private message content or model output.

## Runtime

| Role | Model | Runtime policy |
|---|---|---|
| Semantic summary and labels | Qwen/Qwen3.5-4B, pinned revision, NF4 | On demand; short non-thinking JSON in a disposable Windows process |
| Text/layout evidence | PaddlePaddle/PaddleOCR-VL-1.6, pinned revision, BF16 | Automatic for available image bytes; isolated process exits before Qwen loads |

The two models never intentionally coexist in VRAM. Each Windows inference batch runs in a child
process; exiting it lets the OS reclaim CUDA context as well as model weights. The desktop card and
thumbnail are persisted before inference, and an OCR/model failure falls back without losing the
notification.

## Triage calibration

The locked calibration contains 24 diverse zh-TW/English cases across urgent, high, normal, low,
noise and unknown, plus yes/no/unknown reply requirements and source-independent subject labels.

| Stage | Priority | Reply | Category | Exact cases | Fallbacks |
|---|---:|---:|---:|---:|---:|
| Calibrated raw Qwen prompt | 83.3% | 83.3% | 79.2% | 54.2% | 0 |
| Accepted Qwen + observable constraints | 100% | 100% | 100% | 100% | 0 |

The accepted score reuses the recorded privacy-safe Qwen labels and re-applies deterministic policy;
it is not a second model inference. Constraints cover only directly observable facts such as empty
metadata, explicit no-reply wording, recognized security alerts and explicit optional language.
This is calibration-set accuracy, not a claim of generalization. A human-labeled holdout is still a
release gate.

## OCR and complete image flow

- Six synthetic document/poster/chat images: 100% mean expected-token recall.
- One genuine no-text image: correctly completed with zero OCR text.
- Sequential OCR → release → Qwen → release integration: 2/2 accepted cases in 29.1 seconds.
- The document case produced a deadline-aware summary; the no-text case described the visible
  yellow smiling face directly from pixels.
- VRAM returned to 0 MiB in the external `nvidia-smi` process view after calibration.

## Reproduce

```powershell
.\scripts\setup-windows-model-runtime.ps1 -SkipModelDownload -SkipSmokeTest
.\scripts\run-windows-calibration.ps1 -Suite All -Version local
```

Raw reports are written to ignored `runs/` files. Human review of the prepared 300-image queue and
7–14 days of Shadow Mode remain required before a public v1.0 or any training decision.
