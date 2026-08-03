# Implementation Status

Last verified: 2026-08-03 · Desktop build: `0.1.0.44`

## Honest completion estimate

These percentages measure different scopes and must not be added together:

| Scope | Baseline | Current estimate | Meaning |
|---|---:|---:|---|
| Desktop App and core messaging | 80% | 86% | Inbox/Glance thumbnails, connectors, grouping, actions and image detail are implemented |
| Original complete technical plan | 65% | 75% | OCR/evidence/audit/release tooling exists; real observation and provider QA remain |
| Public v1.0 release | 55% | 62% | Signing is gated and automated; certificate, human audit and field validation remain |
| Qwen and dataset/training | 20% | 52% | Pinned Windows GPU runtime and deferred inference are deployed; human labels decide whether training is needed |
| Multimodal image capability | — | 74% | Thumbnail/OCR/evidence/runtime and unavailable-image states exist; real-source and human quality gates remain |

The percentages are planning estimates, not test coverage. A feature is never marked complete solely
because it has a design document.

## Implemented and verified

| Area | Status | Evidence |
|---|---|---|
| Native desktop shell | Complete | WinUI 3, Mica/Acrylic, system tray, Orb, Glance, responsive Inbox, source badges, native file pickers |
| Focus mode | Complete | Clickable outside the title-bar drag region; persists through the settings API and raises interruption thresholds |
| Gmail connector | Complete for text; image acquisition in verification | Official OAuth, multi-account support, initial + 60-second incremental sync, readonly default, optional confirmed draft scope, safe image MIME acquisition |
| Windows notification connector | Complete | Packaged `UserNotificationListener`, permission state, allowlist, polling reconciliation, stable replay suppression |
| LINE grouping | Complete for visible previews | Per visible user/conversation cards, group-title parsing, stable timestamps, duplicate-toast cleanup |
| Messenger grouping | Complete for visible previews | Browser/app classification, visible sender extraction, background-status filtering, duplicate-thread repair |
| Chat archives | Complete; media variants in verification | LINE TXT and Messenger JSON/ZIP imports, stable hashes, incremental re-import, attachment markers and safe referenced-image acquisition |
| Agent pipeline | Complete | Normalize → deduplicate → group → triage → validate → policy → card/action |
| Safety baseline | Complete | Deterministic evidence-backed rules; optional local model with validated fallback |
| Attention policy | Complete | Focus, quiet hours, VIP/mute, uncertainty penalty, preference score, interruption budget, Shadow Mode |
| Actions | Complete | Open source, snooze, done, local reminder, editable draft; no auto-send route |
| Privacy controls | Complete | Retention worker, safe export, preference reset, confirmed private-data deletion |
| Validation | Passing | 64 tests, Ruff clean, 300 locked text scenarios / 1,800 checks; local validation passes for 0.1.0.44 |
| Media presentation | Implemented, packaged verification in progress | Safe decode + thumbnail endpoint, Inbox and Glance previews, detail full image, and an explicit unavailable state when a Windows toast contains no image bytes |
| OCR evidence | Deployed, model audit pending | Pinned PaddleOCR-VL-1.6 Windows CUDA runtime, hash-bound blocks/regions, authenticated analysis API, deterministic evidence rejection |
| Multimodal audit | Queue ready, 0/300 human-reviewed | 300 fictional local images with SHA-256 manifest and review/lock tool; no review is falsely claimed |
| Shadow/release | Tooling ready, time gates pending | Content-free 7–14 day report, readiness verifier, production signing and recoverable rollback scripts |
| RTX 4080 SUPER smoke | Passing | Full NF4 agent 3.238 GiB and 0.008 GiB after release; Paddle BF16 1.811 GiB/7.092 s and 0.008 GiB after release; earlier BF16/INT8/NF4 comparison retained in benchmark results |
| Live model scheduling | Implemented | Rule card/thumbnail appears without a model; OCR is user-triggered; only completed OCR or important full content wakes Qwen; both release afterward |
| Agent model contract | Passing on RTX 4080 SUPER | NF4 fictional end-to-end smoke produces valid evidence-bound JSON at 3.238 GiB peak and 0.008 GiB allocated after release; unsafe output still falls back |

## Deliberate product boundaries

- Personal LINE and Messenger do not offer a supported full private-chat sync API. SignalDesk uses official archives for history and Windows-visible notification previews for new inbound messages.
- Notification previews may omit context, images, stickers, muted chats, and messages dismissed before Windows exposes them. The UI preserves this uncertainty instead of inventing content.
- Qwen and PaddleOCR do not acquire images. Gmail attachments work because the connector supplies bytes; direct personal LINE/Messenger images require a separate opt-in acquisition companion.
- Images are never scanned merely because SignalDesk is open. The user explicitly starts OCR from message detail; the 384-token cap prevents noisy images from growing an unbounded KV cache.
- The default engine is deterministic and local. Optional Qwen integration remains opt-in until it passes a human-labeled audit.
- Development MSIX signing is implemented; a public release still requires a production publisher certificate and release channel.

## Remaining release gates

- Human-label 300+ anonymized events and run a 7–14 day Shadow Mode evaluation.
- Measure optional local-model quality against the deterministic baseline; VRAM residency behavior now passes the target-machine smoke.
- Complete production signing, installer distribution, upgrade/rollback testing, and release notes.
- Run provider review and deploy public HTTPS endpoints only if LINE Official Account or Messenger Page webhooks are enabled.

## Remaining implementation, in delivery order

### Multimodal images

- Verify supported Gmail MIME image acquisition against both connected Windows accounts and packaged builds.
- Verify Messenger ZIP media acquisition against real export variants and decompression-bomb cases.
- Verify the new Inbox/Glance thumbnails in the packaged app with Gmail/Messenger images.
- Expand the successful one-image PaddleOCR-VL and Qwen BF16/INT8/NF4 smoke into the locked
  300-item quality run after human review.
- Add explicit cancellation/timeout UI for a running cold model load; NF4 residency and release are implemented.
- Human-review and lock the prepared multimodal queue (currently 0/300).

### Qwen and learning

- Keep the pinned Windows model runtime reproducible across clean-machine upgrades.
- Complete the 20-step and full-dataset quality comparison; NF4 memory/function smoke now passes.
- Build the annotation workflow and human-label at least 300 private/anonymized events locally.
- Train only if the zero-shot audit misses predefined gates; QLoRA/SFT is conditional, not assumed.
- Produce a model card, dataset manifests and reproducible evaluation report.

### Desktop product quality

- Finish multimodal UI, keyboard/screen-reader audit and all empty/error/loading states.
- Complete crash recovery, upgrade/rollback and one-working-day soak tests.
- Replace development signing with a production publisher identity and release channel.
- Capture current screenshots/demo video and complete public onboarding/support docs.

### Public v1.0

- Add signed installer/release artifact verification and clean-machine test.
- Complete 7–14 day Shadow Mode evaluation and privacy/security review.
- Publish versioned release notes, checksums, limitations and rollback instructions.

## Safety invariants

- No send, source-delete, or arbitrary-shell API endpoint.
- Draft creation always requires a separate explicit confirmation.
- Message text cannot change tool or policy permissions.
- OAuth tokens are stored in the OS credential manager and are excluded from diagnostics and exports.
- Private databases, notification traces, credentials, and user screenshots are excluded from the public repository.
