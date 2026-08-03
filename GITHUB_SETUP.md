# GitHub Publishing Policy

## Repository

SignalDesk is published at [`hanklin9188/signaldesk-agent`](https://github.com/hanklin9188/signaldesk-agent). The `main` branch is the reviewed portfolio baseline; subsequent work should use focused `feature/*` or `fix/*` branches and pass both Python and native Windows CI before merge.

## What belongs in the public portfolio

- Native WinUI 3 shell, local Python service, schemas, tests, and reproducible scripts.
- Architecture, product boundaries, privacy guarantees, validation results, and screenshots made from non-private views.
- Accurate implementation status and roadmap items that distinguish verified behavior from future work.

## What must never be committed

- Gmail credentials, OAuth tokens, passwords, or Windows Credential Manager exports.
- Private messages, notification traces, local SQLite databases, exports, or user-specific reports.
- Signing certificates, packaged service binaries, MSIX build output, model weights, or absolute user paths.

The repository `.gitignore`, CI secret-file gate, and `scripts/build_manifest.py` enforce these boundaries. A manual staged-file and secret-signature review is still required before every public push.

## Release policy

Development-signed packages are for local validation only. A downloadable public MSIX will be attached to a GitHub release only after production signing, clean-machine installation, upgrade/rollback testing, and release-note review are complete.

## Portfolio presentation

The README is the public entry point. It presents the real native interface, the bounded agent loop, connector limitations, repository ownership map, and reproducible quality gates. Any screenshot containing private inbox content must remain under the ignored `outputs/` directory.
