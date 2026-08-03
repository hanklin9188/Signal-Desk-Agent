# Implementation Plan

Legend: `[x]` verified · `[~]` implemented but release verification remains · `[ ]` not implemented.

## Epic 0 — Repository and portfolio

- [x] Independent repository, MIT license, code ownership map and contribution guide.
- [x] CI for schemas, Python lint/tests, benchmark smoke and Windows build.
- [~] Professional screenshots and architecture presentation; refresh after multimodal UI.
- [ ] Signed release artifact verifier, issue templates and public v1.0 release.

## Epic 1 — Core event model

- [x] UnifiedEvent, connector cursor, idempotency, raw/normalized store and migrations.
- [x] Per-conversation grouping and notification replay repair.
- [x] MediaAsset contract, content-addressed store and per-event association.
- [ ] Thumbnail/derivative table and immutable OCR/visual evidence contract.

## Epic 2 — Windows shell

- [x] WinUI 3, package identity, notification listener, tray, Orb, Glance and deep-link open.
- [x] Native file pickers, Focus Mode and authenticated local service lifecycle.
- [~] Development MSIX; production signing and upgrade/rollback remain.
- [~] Authenticated detail image viewer and media error labels implemented; thumbnails/OCR remain.

## Epic 3 — Connectors

- [x] Gmail OAuth, readonly sync, history cursor, MIME text parser and health.
- [x] LINE TXT and Messenger JSON/ZIP history import.
- [x] Windows-visible LINE/Messenger preview capture and honest limitations.
- [~] Gmail image attachment acquisition implemented; live-account/Windows package verification remains.
- [~] Messenger archive media acquisition and traversal/size limits implemented; real-export matrix remains.
- [ ] Optional official LINE OA/Messenger Page media acquisition after provider setup.

## Epic 4 — Message pipeline

- [x] Normalize, deduplicate, group, rule triage, validation, policy and actions.
- [x] Quiet hours, interruption budget, Shadow Mode and local preference ranker.
- [~] Event isolation and quarantine exist; extended crash/soak validation remains.
- [ ] Visual route queue, cancellation, retry, GPU OOM fallback and derived-media cleanup.

## Epic 5 — Qwen and multimodal runtime

- [x] Optional model gateway with deterministic rule fallback.
- [x] OpenAI-compatible and Transformers message paths can carry one image.
- [x] Separate 128-token text and 256-token visual output budgets.
- [ ] Pin Qwen3.5-4B revision and verified Windows runtime.
- [ ] PaddleOCR-VL-1.6 local service and hash-bound evidence.
- [ ] Pixel/context compiler, batch queue, GPU modes, health and metrics.
- [ ] Compare BF16/8-bit/4-bit quality, latency and peak VRAM on RTX 4080 SUPER.

## Epic 6 — Validation and safety

- [x] Text span/deadline validator, preview limitation and action allowlist.
- [x] Image availability states and safe format/signature/size validation.
- [ ] OCR-region validator for visual action items and exact deadlines.
- [ ] Decoded-pixel/decompression-bomb limits and hardened thumbnail worker.
- [ ] Multimodal calibration and end-to-end locked scenario runner.

## Epic 7 — UI and UX

- [x] Orb, Glance, Inbox/detail, source icons, relative time and actions.
- [x] Source Center, Attention Policy, Privacy Controls and Daily Digest.
- [~] Keyboard/responsive design implemented; formal accessibility audit remains.
- [~] Detail image viewer implemented; thumbnail card, OCR highlight and retry states remain.
- [ ] Current professional screenshot set and short visual demo.

## Epic 8 — Dataset and training

- [x] Synthetic locked text-scenario generator and 300-scenario baseline.
- [x] Annotation/dataset/training contracts documented.
- [ ] Human annotation tool and 300+ reviewed real-world/anonymized text events.
- [ ] 300+ reviewed multimodal audit set with screenshot/document/photo/missing slices.
- [ ] Zero-shot Qwen audit, calibration and Shadow Mode report.
- [ ] Conditional QLoRA/SFT, only if the audit justifies it.
- [ ] Dataset manifest, experiment record and model card.

## Epic 9 — Public v1.0

- [ ] 7–14 day Shadow Mode field evaluation.
- [ ] Performance, GPU, privacy and accessibility reports.
- [ ] Production certificate, clean-machine installer and release channel.
- [ ] Upgrade, rollback, crash recovery and one-day soak validation.
- [ ] Demo video, release notes, checksums and GitHub v1.0 release.

## Current execution sequence

1. Multimodal foundation: contracts, safe store, local API and model request path.
2. Gmail/Messenger media acquisition and WinUI thumbnail/detail presentation.
3. PaddleOCR-VL + Qwen runtime, evidence validator and GPU measurements.
4. Annotation/audit tooling, 300+ multimodal audit and 7–14 day Shadow Mode.
5. Accessibility/soak/upgrade gates, production signing and public v1.0.

## Definition of done v1.0

- Supported connectors work without duplicate cards.
- Personal LINE/Messenger limitations are accurate and visible.
- Images render only from validated local bytes; missing pixels are never guessed.
- Text and visual deadlines/actions retain verifiable evidence.
- Locked text and multimodal benchmarks pass release gates.
- No auto-send, source-delete or arbitrary-shell path exists.
- Local privacy export/delete and retention cover originals and derivatives.
- Native UI passes keyboard, screen-reader, contrast and one-day soak tests.
- Signed installer, rollback instructions, reports and public documentation are reproducible.
