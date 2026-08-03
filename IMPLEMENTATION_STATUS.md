# Implementation Status

Last verified: 2026-08-03 · Desktop build: `0.1.0.38`

## Implemented and verified

| Area | Status | Evidence |
|---|---|---|
| Native desktop shell | Complete | WinUI 3, Mica/Acrylic, system tray, Orb, Glance, responsive Inbox, source badges, native file pickers |
| Focus mode | Complete | Clickable outside the title-bar drag region; persists through the settings API and raises interruption thresholds |
| Gmail connector | Complete | Official OAuth, multi-account support, initial + 60-second incremental sync, readonly default, optional confirmed draft scope |
| Windows notification connector | Complete | Packaged `UserNotificationListener`, permission state, allowlist, polling reconciliation, stable replay suppression |
| LINE grouping | Complete for visible previews | Per visible user/conversation cards, group-title parsing, stable timestamps, duplicate-toast cleanup |
| Messenger grouping | Complete for visible previews | Browser/app classification, visible sender extraction, background-status filtering, duplicate-thread repair |
| Chat archives | Complete | LINE TXT and Messenger JSON/ZIP imports, stable hashes, incremental re-import, attachment markers |
| Agent pipeline | Complete | Normalize → deduplicate → group → triage → validate → policy → card/action |
| Safety baseline | Complete | Deterministic evidence-backed rules; optional local model with validated fallback |
| Attention policy | Complete | Focus, quiet hours, VIP/mute, uncertainty penalty, preference score, interruption budget, Shadow Mode |
| Actions | Complete | Open source, snooze, done, local reminder, editable draft; no auto-send route |
| Privacy controls | Complete | Retention worker, safe export, preference reset, confirmed private-data deletion |
| Validation | Passing | 41 tests, Ruff clean, 300 locked scenarios / 1,800 checks, native build with 0 compile errors |

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

## Safety invariants

- No send, source-delete, or arbitrary-shell API endpoint.
- Draft creation always requires a separate explicit confirmation.
- Message text cannot change tool or policy permissions.
- OAuth tokens are stored in the OS credential manager and are excluded from diagnostics and exports.
- Private databases, notification traces, credentials, and user screenshots are excluded from the public repository.
