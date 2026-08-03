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
- [~] Content-addressed thumbnails and immutable OCR/visual evidence are implemented; a separate derivative metadata table is optional follow-up work.

## Epic 2 — Windows shell

- [x] WinUI 3, package identity, notification listener, tray, Orb, Glance and deep-link open.
- [x] Native file pickers, Focus Mode and authenticated local service lifecycle.
- [~] Development MSIX; production signing and upgrade/rollback remain.
- [x] Authenticated thumbnails, detail image viewer, explicit analysis action and media error labels.

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
- [~] Sequential on-demand OCR/Qwen route, safe fallback and model release are implemented; explicit cancellation/timeout UI remains.

## Epic 5 — Qwen and multimodal runtime

- [x] Optional model gateway with deterministic rule fallback.
- [x] OpenAI-compatible and Transformers message paths can carry one image.
- [x] Bounded 640-token text and 768-token visual output budgets plus one in-memory schema-repair pass.
- [x] Pinned Qwen3.5-4B NF4 revision and verified Windows CUDA runtime.
- [x] Pinned PaddleOCR-VL-1.6 local runtime and hash/region-bound evidence.
- [~] Bounded pixel/context compiler, sequential queue, on-demand residency, health and smoke metrics; cancellation UI remains.
- [x] BF16/INT8/NF4 latency and peak-VRAM smoke comparison on RTX 4080 SUPER.

## Epic 6 — Validation and safety

- [x] Text span/deadline validator, preview limitation and action allowlist.
- [x] Image availability states and safe format/signature/size validation.
- [x] OCR-region validator for visual action items and exact deadlines.
- [x] Decoded-pixel/decompression-bomb limits and hardened thumbnail generation.
- [~] Deterministic 300-item multimodal queue and review/lock runner exist; human calibration is 0/300.

## Epic 7 — UI and UX

- [x] Orb, Glance, Inbox/detail, source icons, relative time and actions.
- [x] Source Center, Attention Policy, Privacy Controls and Daily Digest.
- [~] Keyboard/responsive design implemented; formal accessibility audit remains.
- [~] Inbox/Glance thumbnails, detail viewer and analysis status are implemented; OCR region highlighting and explicit cancellation remain.
- [ ] Current professional screenshot set and short visual demo.

## Epic 8 — Dataset and training

- [x] Synthetic locked text-scenario generator and 300-scenario baseline.
- [x] Annotation/dataset/training contracts documented.
- [~] Local annotation/review-lock tooling exists; 300+ reviewed real-world/anonymized text events remain.
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

1. Verify Gmail and Messenger media variants in the packaged app.
2. Human-review the prepared 300-item multimodal queue and compare zero-shot quality.
3. Complete 7–14 day Shadow Mode and real-account reliability observation.
4. Finish accessibility, cancellation, soak and upgrade/rollback gates.
5. Add production signing, release artifacts and public v1.0 documentation.

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
