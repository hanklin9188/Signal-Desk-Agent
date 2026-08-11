<div align="center">

# SignalDesk

### A local-first Windows agent that turns message overload into an explainable, actionable inbox.

<p>
  <a href="https://github.com/hanklin9188/Signal-Desk-Agent/actions/workflows/spec-validation.yml"><img alt="CI" src="https://github.com/hanklin9188/Signal-Desk-Agent/actions/workflows/spec-validation.yml/badge.svg"></a>
  <a href="https://www.microsoft.com/windows/windows-11"><img alt="Windows 11" src="https://img.shields.io/badge/Windows-11-0078D4?logo=windows11&amp;logoColor=white"></a>
  <a href="https://learn.microsoft.com/windows/apps/winui/winui3/"><img alt="WinUI 3" src="https://img.shields.io/badge/UI-WinUI%203-5B5FC7"></a>
  <a href="https://www.python.org/"><img alt="Python 3.12" src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&amp;logoColor=white"></a>
  <a href="SECURITY_PRIVACY.md"><img alt="Local-first privacy" src="https://img.shields.io/badge/privacy-local--first-25B889"></a>
  <a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/badge/license-MIT-7770F2"></a>
</p>

<img src="docs/screenshots/signaldesk-hero.png" alt="SignalDesk Inbox Center and Glance window on Windows 11" width="100%">

<p>
  SignalDesk brings Gmail and Windows-visible notification previews from LINE and Messenger into one native workspace. It groups conversations, identifies reply needs and deadlines, explains why an item matters, and keeps every action under explicit user control.
</p>

<p>
  <a href="#quick-start"><strong>Quick start</strong></a> ·
  <a href="PORTFOLIO.md"><strong>Engineering portfolio</strong></a> ·
  <a href="#architecture"><strong>Architecture</strong></a> ·
  <a href="EVALUATION.md"><strong>Evaluation</strong></a> ·
  <a href="IMPLEMENTATION_STATUS.md"><strong>Implementation status</strong></a>
</p>

</div>

---

## Thirty-second product tour

1. Connect Gmail, import official LINE/Messenger archives, or allow Windows notification access.
2. SignalDesk normalizes, deduplicates, and groups incoming events into conversation cards.
3. Evidence-backed rules—and optionally a local Qwen model—extract priority, reply needs, actions, and deadlines.
4. Focus mode, quiet hours, VIP/mute rules, uncertainty penalties, and an interruption budget determine what may surface.
5. The user can open, snooze, mark done, create a local reminder, or prepare an editable draft. There is **no automatic-send path**.

## Why SignalDesk

<table>
  <tr>
    <td width="33%" valign="top">
      <h3>One calm inbox</h3>
      <p>Multiple sources become consistent conversation cards instead of separate notification streams.</p>
    </td>
    <td width="33%" valign="top">
      <h3>Evidence before inference</h3>
      <p>Actions and deadlines retain the source spans that support them; incomplete previews remain visibly incomplete.</p>
    </td>
    <td width="33%" valign="top">
      <h3>Private and bounded</h3>
      <p>Processing stays local, model output must validate, and deterministic rules remain available when inference fails.</p>
    </td>
  </tr>
</table>

> [!IMPORTANT]
> Personal LINE and Messenger accounts do not provide a supported API for complete private-chat synchronization. SignalDesk uses official exports for history and only the previews that Windows exposes for new inbound notifications. It does not scrape UI state, reverse-engineer private databases, steal sessions, or invent missing context.

## Current evidence

SignalDesk separates **engineering regression evidence** from **real-world product validation**.

### Engineering regression evidence

| Gate | Current repository evidence |
| :--- | :--- |
| Automated tests | **41 passing** in the last recorded verification |
| Locked benchmark | **300 fictional scenarios / 1,800 policy checks** |
| Unauthorized actions | **0** in the locked benchmark |
| Auto-send paths | **0 by design** |
| Native WinUI build | **0 compile errors** in the last recorded verification |
| Development packaging | MSIX installed and exercised on Windows 11 |

These results protect implementation and policy invariants. The 300 scenarios are deliberately fictional regression fixtures; they are not presented as a representative human-message accuracy study.

### Product validation not yet claimed

The repository does not yet claim production-level triage accuracy or user benefit. Remaining release evidence includes:

- 300+ anonymized, human-reviewed real-world events;
- a 7–14 day Shadow Mode study with correction and interruption metrics;
- optional local-model comparison against the deterministic baseline;
- clean-machine install, upgrade, rollback, and production publisher signing.

Read [`EVALUATION.md`](EVALUATION.md) for the measurement plan and [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) for the release gate.

## What makes it an agent

Every event moves through a bounded, auditable loop:

![SignalDesk bounded agent decision loop](docs/assets/agent-loop.svg)

```text
observe → normalize → group → triage → validate → apply attention policy → assist
```

- **Evidence-bound extraction:** actionable claims retain supporting source spans.
- **Validated model output:** malformed, unsupported, or unavailable local-model output is rejected.
- **Deterministic fallback:** safe rules provide a baseline rather than silently dropping events.
- **Explicit action boundary:** drafts remain editable and sending is outside the product's v1 authority.
- **Local feedback only:** preference changes come from explicit local user actions.

The global agent contract is documented in [`AGENT.md`](AGENT.md).

## Desktop experience

The primary interface is a native **WinUI 3** application, not a web wrapper.

| Surface | Purpose |
| :--- | :--- |
| **Inbox Center** | Search, filter, batch-manage, and inspect evidence-rich message details. |
| **Glance** | Keep recent useful items in a compact always-on-top window. |
| **Focus mode** | Raise the interruption threshold without hiding cards from the inbox. |
| **Daily Digest** | Review urgent items, deadlines, reply needs, and lower-priority information. |
| **Source Center** | Inspect Gmail OAuth, Windows notification access, and archive-import health. |
| **Attention Policy** | Manage explainable VIP, priority, and mute rules. |
| **Privacy Controls** | Export local data, configure retention, reset preferences, and confirm deletion. |

## Connector coverage

| Source | Integration | Honest content boundary |
| :--- | :--- | :--- |
| **Gmail** | Official OAuth, initial/incremental sync, multiple accounts | Full message/thread content under the granted scope |
| **LINE personal** | Official text export + Windows notification listener | Export history; preview-only content for new visible notifications |
| **Messenger personal** | Accounts Center JSON/ZIP + Windows/browser notification listener | Export history; preview-only content for new visible notifications |
| **LINE Official Account** | Signed webhook connector | Full payload for the configured official account |
| **Messenger Page** | Signed Meta webhook connector | Full payload for the configured Page |

When only a preview is available, the UI preserves that limitation. Missing images, stickers, dismissed notifications, or thread context are never inferred as known facts.

## Architecture

SignalDesk separates the native Windows boundary from the local decision service. Communication uses an authenticated loopback API; OAuth tokens stay in Windows Credential Manager and private event state stays in local SQLite storage.

![SignalDesk local-first system architecture](docs/assets/architecture.svg)

| Boundary | Responsibility |
| :--- | :--- |
| **WinUI shell** | Inbox, Glance, tray, Focus controls, OAuth launch, file pickers, and `UserNotificationListener` |
| **Local agent service** | Connectors, normalization, grouping, evidence validation, attention policy, persistence, and trace |
| **Optional local inference** | On-device Qwen JSON assistance with schema validation and deterministic fallback |

The service binds to `127.0.0.1`, authenticates clients with an unguessable token, and exposes no arbitrary shell or auto-send endpoint. Read [`ARCHITECTURE.md`](ARCHITECTURE.md), [`SECURITY_PRIVACY.md`](SECURITY_PRIVACY.md), and the [code ownership map](docs/PROJECT_STRUCTURE.md).

## Quick start

### Native Windows build

**Prerequisites:** Windows 11, Python 3.12, .NET 8 SDK, and Visual Studio 2022 with the .NET desktop / Windows App SDK workload.

```powershell
git clone https://github.com/hanklin9188/Signal-Desk-Agent.git
cd Signal-Desk-Agent
powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows-prerequisites.ps1 -Install
.\scripts\build-windows.ps1 -Configuration Release
```

Gmail OAuth and development-signed packaging are documented in [`WINDOWS_GMAIL_SETUP.md`](WINDOWS_GMAIL_SETUP.md). Credentials, certificates, private databases, and real message captures are intentionally excluded.

### Service-only fictional demo

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e '.[dev,gmail]'
SIGNALDESK_DEMO=1 .venv/bin/signaldesk
```

`SIGNALDESK_DEMO=1` seeds only fictional content into an empty development database. The browser surface on `127.0.0.1:8765` is a diagnostic fallback; the portfolio product is the native desktop app.

## Verify locally

```bash
.venv/bin/ruff check signaldesk tests
.venv/bin/python -m pytest
.venv/bin/signaldesk-benchmark --output runs/verification
```

Public CI validates JSON/YAML, rejects common credential files, lints Python, runs tests and the fictional locked benchmark, and builds the WinUI shell on a Windows runner.

## Safety invariants

- Message text is untrusted data, never a tool instruction.
- OAuth tokens are not stored in SQLite or Git.
- Source URLs must match connector-specific HTTPS allowlists.
- Notification previews remain labelled incomplete.
- Draft creation requires explicit confirmation.
- There is no source-delete, automatic-send, or arbitrary-shell API route.
- Model failure must not discard the original event.

## Repository map

```text
native/SignalDesk.Shell/   native WinUI 3 application
signaldesk/                local agent service and decision pipeline
signaldesk/connectors/     Gmail, webhook, notification, and archive connectors
schemas/                   versioned event and agent-output contracts
tests/                     API, pipeline, archive, privacy, and safety tests
benchmarks/                locked fictional regression scenarios
scripts/                   setup, build, validation, and packaging tools
docs/                      architecture, UX, screenshots, and ownership maps
```

## Reviewer path

For a five-minute technical review:

1. Read [`PORTFOLIO.md`](PORTFOLIO.md).
2. Inspect the architecture and agent-loop diagrams.
3. Run the three verification commands above.
4. Read [`EVALUATION.md`](EVALUATION.md) to distinguish regression evidence from product evidence.
5. Inspect [`IMPLEMENTATION_STATUS.md`](IMPLEMENTATION_STATUS.md) and [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md).

## Documentation

| Document | Purpose |
| :--- | :--- |
| [`PORTFOLIO.md`](PORTFOLIO.md) | Interview-oriented engineering narrative and demo path |
| [`IMPLEMENTATION_STATUS.md`](IMPLEMENTATION_STATUS.md) | Verified features, deliberate boundaries, and remaining gates |
| [`EVALUATION.md`](EVALUATION.md) | Regression evidence, human-evaluation plan, and metric definitions |
| [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) | Preview and production release requirements |
| [`CONNECTORS.md`](CONNECTORS.md) | Integration setup and source-completeness boundaries |
| [`VALIDATION.md`](VALIDATION.md) | Test strategy, benchmark contracts, and safety validation |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Development workflow and privacy-safe contribution rules |

## License

Released under the [MIT License](LICENSE). © Hank Lin.
