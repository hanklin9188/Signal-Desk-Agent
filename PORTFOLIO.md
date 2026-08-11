# SignalDesk Engineering Portfolio

## Problem

Message overload is not only a summarization problem. A useful desktop agent must decide what deserves attention while preserving source limitations, privacy, evidence, and user authority.

## Engineering contribution

SignalDesk combines:

- a native WinUI 3 desktop shell;
- official Gmail OAuth and incremental synchronization;
- honest LINE/Messenger archive and notification-preview boundaries;
- a local FastAPI decision service with SQLite state;
- evidence-backed deterministic triage;
- optional on-device Qwen assistance with schema validation;
- explicit attention policy and no automatic-send authority;
- Linux/Windows CI, locked regression scenarios, packaging, and privacy controls.

## Key design decisions

### Local-first process boundary

Private messages and model inference remain on the device. The shell and service communicate through an authenticated loopback API.

### Evidence before inference

Action items and deadlines retain supporting source spans. Preview-only content remains uncertain instead of being promoted to a complete fact.

### Deterministic safety authority

The model cannot grant itself permissions. Invalid model output falls back to bounded rules, and the original event is never discarded.

### Attention as policy

Surfacing is controlled by quiet hours, Focus mode, VIP/mute rules, uncertainty penalties, user preferences, and an interruption budget—not only a classifier score.

## What is verified

- 41 automated tests in the last recorded main-branch verification;
- 300 fictional locked scenarios and 1,800 policy checks;
- zero unauthorized or auto-send actions in that benchmark;
- native WinUI build with zero compile errors in the recorded verification;
- development MSIX installation on Windows 11.

These are engineering and regression results. Real-world product accuracy remains gated by the human-reviewed Shadow Mode study described in [`EVALUATION.md`](EVALUATION.md).

## Five-minute interview demo

1. Start SignalDesk in fictional demo mode.
2. Ingest a message with an explicit question and deadline.
3. Show the grouped card, supporting evidence, and “why shown” explanation.
4. Enable Focus mode and show the policy change without deleting the card.
5. Prepare an editable draft and demonstrate the absence of an auto-send path.
6. Disable optional model inference and show deterministic fallback.
7. Open the local trace and explain the shell/service trust boundary.

## Code review path

- `signaldesk/pipeline.py` or the current pipeline entry point: event-to-card flow.
- `signaldesk/connectors/`: source-specific completeness and parsing.
- `signaldesk/policy.py` or current policy modules: interruption decisions.
- `schemas/`: versioned untrusted-input and model-output contracts.
- `tests/`: negative, privacy, API, archive, and pipeline coverage.
- `native/SignalDesk.Shell/`: native Windows integration.

## Honest limitations

- Personal LINE/Messenger synchronization is incomplete by platform design.
- Current locked scenarios are fictional and visible to the repository.
- Optional model calibration is not yet a representative held-out study.
- Production publisher signing and stable public distribution are pending.
- Real user benefit and interruption reduction require Shadow Mode evidence.
