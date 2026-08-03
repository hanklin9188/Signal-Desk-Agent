# Implementation Status

Last verified: 2026-08-03 · Desktop build: `0.1.0.39`

## Honest completion estimate

These percentages measure different scopes and must not be added together:

| Scope | Baseline | Current estimate | Meaning |
|---|---:|---:|---|
| Desktop App and core messaging | 80% | 82% | Daily-use shell, inbox, connectors, grouping/actions and first image viewer exist |
| Original complete technical plan | 65% | 69% | Multimodal foundation/acquisition added; model, audit and release engineering remain |
| Public v1.0 release | 55% | 57% | Production signing, installer QA, model audit and field validation remain |
| Qwen and dataset/training | 20% | 24% | Multimodal route exists; measured local runtime and reviewed data do not |
| Multimodal image capability | — | 30% | Store/acquisition/detail viewer exist; thumbnails, OCR, evidence and audit remain |

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
| Validation | Passing | 49 tests, Ruff clean, 300 locked scenarios / 1,800 checks; native compile pending Windows verification for 0.1.0.39 |
| Media foundation | In progress | Safe media contract/store/API and multimodal model request path implemented; connector/UI/OCR work remains |

## Deliberate product boundaries

- Personal LINE and Messenger do not offer a supported full private-chat sync API. SignalDesk uses official archives for history and Windows-visible notification previews for new inbound messages.
- Notification previews may omit context, images, stickers, muted chats, and messages dismissed before Windows exposes them. The UI preserves this uncertainty instead of inventing content.
- The default engine is deterministic and local. Optional Qwen integration remains opt-in until it passes a human-labeled audit.
- Development MSIX signing is implemented; a public release still requires a production publisher certificate and release channel.

## Remaining release gates

- Human-label 300+ anonymized events and run a 7–14 day Shadow Mode evaluation.
- Measure optional local-model quality and GPU behavior against the deterministic baseline.
- Complete production signing, installer distribution, upgrade/rollback testing, and release notes.
- Run provider review and deploy public HTTPS endpoints only if LINE Official Account or Messenger Page webhooks are enabled.

## Remaining implementation, in delivery order

### Multimodal images

- Verify supported Gmail MIME image acquisition against both connected Windows accounts and packaged builds.
- Verify Messenger ZIP media acquisition against real export variants and decompression-bomb cases.
- Add thumbnail generation and WinUI Inbox/Glance previews; authenticated detail viewing is implemented.
- Run PaddleOCR-VL-1.6 locally and persist hash-bound OCR regions.
- Run Qwen3.5-4B with real image input, bounded pixel/context budgets and GPU telemetry.
- Validate visual action/deadline evidence; add retry, cancellation and OOM fallback.
- Build and human-review a 300+ item multimodal locked audit.

### Qwen and learning

- Pin a known-good model revision and runtime stack on Windows.
- Complete model load, 20-step smoke, latency/VRAM and deterministic-baseline comparison.
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
