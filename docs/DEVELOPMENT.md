# Development Guide

## Local service

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e '.[dev,gmail]'
.venv/bin/ruff check signaldesk tests
.venv/bin/pytest
SIGNALDESK_DEMO=1 .venv/bin/signaldesk
```

Demo mode only seeds fictional fixtures when the selected database is empty.

## Native Windows shell

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows-prerequisites.ps1 -Install
.\scripts\build-windows.ps1 -Configuration Release
```

The project targets .NET 8, Windows App SDK 1.6, and x64 packaged MSIX. `UserNotificationListener` requires package identity, so notification access must be tested from the installed package.

## Configuration

Runtime configuration is supplied through `configs/*.yaml` and environment variables. Copy `.env.example` only for local development; never commit `.env`, OAuth JSON, tokens, certificates, SQLite databases, or captured private messages.

## Validation expectations

Every behavior change should include:

1. A fictional regression fixture.
2. A focused unit/API test.
3. Ruff and Pytest success.
4. Native build verification for XAML/C# changes.
5. A privacy-safe screenshot for visible UI changes.
6. Updated architecture/status documentation when responsibilities or product boundaries change.

## Release build notes

Development MSIX output is written under `native/SignalDesk.Shell/bin/.../AppPackages/` and is ignored by Git. Public releases require a production publisher identity; do not publish local development certificates or unsigned binaries as trusted releases.
