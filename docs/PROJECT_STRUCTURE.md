# Project Structure & Code Ownership

This document maps product responsibilities to concrete files so reviewers can navigate SignalDesk without reverse-engineering the repository.

## Runtime split

SignalDesk has two cooperating processes:

1. `SignalDesk.Shell.exe` — native WinUI 3 desktop interface and Windows integration.
2. `signaldesk.exe` — packaged Python/FastAPI agent service bound to authenticated loopback.

The split keeps Windows-only UI/notification code isolated from portable, heavily tested agent logic.

## Native desktop application

| Path | Responsibility |
|---|---|
| `native/SignalDesk.Shell/App.xaml.cs` | Application lifecycle, process wiring, tray/Orb/Glance creation, notification bridge startup |
| `MainWindow.xaml(.cs)` | Window chrome, navigation, global search, focus-mode control, service status, onboarding |
| `Controls/SourceBadge.xaml(.cs)` | Reusable Gmail/LINE/Messenger/Windows icon and brand-color treatment |
| `Views/InboxPage.xaml(.cs)` | Inbox filters, responsive list/detail layout, card actions, evidence and source preview |
| `Views/DigestPage.xaml(.cs)` | Daily attention summary and navigation into cards |
| `Views/SourcesPage.xaml(.cs)` | OAuth, notification permission, connector health, chat archive import |
| `Views/RulesPage.xaml(.cs)` | Explainable attention-policy rules and reversible personalization |
| `Views/SettingsPage.xaml(.cs)` | Focus/Shadow/quiet hours, theme, startup task, retention and privacy controls |
| `GlanceWindow.xaml(.cs)` | Always-on-top latest-items surface; 30-second data refresh and 60-second relative-time refresh |
| `OrbWindow.xaml(.cs)` | Draggable compact launcher with important-item count |
| `Services/LocalServiceManager.cs` | Starts the packaged local service and provisions the loopback token in Credential Manager |
| `Services/NotificationBridge.cs` | Windows `UserNotificationListener`, allowlist forwarding, replay reconciliation |
| `Services/LocalApiClient.cs` | Typed authenticated client for the local API and event stream |
| `Services/AppState.cs` | Shared desktop state, collections, preferences, live refresh events |
| `Models/ApiModels.cs` | Desktop view models and human-readable labels |
| `Styles.xaml` | Light/dark palette, card, chip, typography and reusable control styles |

## Agent service

| Path | Responsibility |
|---|---|
| `signaldesk/api.py` | Authenticated FastAPI surface, connector lifecycle, SSE events, background sync/retention workers |
| `signaldesk/models.py` | Strict Pydantic contracts for events, triage, actions, cards and settings |
| `signaldesk/normalizer.py` | Unicode/text cleanup, source classification, LINE/Messenger visible identity parsing |
| `signaldesk/grouping.py` | Stable Gmail threads and per-conversation chat grouping |
| `signaldesk/database.py` | SQLite schema, migrations, persistence, search, repairs and replay cleanup |
| `signaldesk/pipeline.py` | End-to-end agent orchestration and trace lifecycle |
| `signaldesk/rules.py` | Deterministic priority, reply, task and evidence extraction baseline |
| `signaldesk/deadlines.py` | Evidence-backed deadline normalization in the configured timezone |
| `signaldesk/validator.py` | Schema, action allowlist, evidence and preview-boundary validation |
| `signaldesk/policy.py` | Focus, quiet hours, Shadow Mode and interruption-budget decisions |
| `signaldesk/actions.py` | Bounded user actions; draft/reminder confirmation and no auto-send guarantee |
| `signaldesk/preference.py` | Privacy-minimized local ranking feedback |
| `signaldesk/model_gateway.py` | Optional Qwen/OpenAI-compatible inference with deterministic fallback |
| `signaldesk/connectors/gmail.py` | Gmail OAuth, MIME parsing, full/incremental synchronization and draft creation |
| `signaldesk/connectors/chat_archive.py` | LINE TXT and Messenger JSON/ZIP archive parsers |
| `signaldesk/benchmark.py` | Reproducible locked-scenario safety and quality gate |

## Contracts and test ownership

| Path | Responsibility |
|---|---|
| `schemas/` | Versioned JSON schemas shared by fixtures, tools and external integrations |
| `examples/` | Fictional contract examples; safe to use in public reports |
| `tests/test_api.py` | API auth, filtering, source classification and synchronization behavior |
| `tests/test_pipeline.py` | Grouping, deduplication, preview limitations and policy behavior |
| `tests/test_chat_archives.py` | LINE/Messenger parser compatibility and incremental import |
| `tests/test_new_capabilities.py` | Webhook validation, preferences, drafts, reminders and safety controls |
| `tests/test_gmail_legacy_cleanup.py` | Account migration and duplicate Gmail cleanup |
| `tests/test_schema_fixtures.py` | Machine-readable contract conformance |

## Scripts

| Script | Use |
|---|---|
| `scripts/setup-windows-prerequisites.ps1` | Detect/install Python, .NET, Visual Studio workloads and Windows SDK requirements |
| `scripts/build-windows.ps1` | Build Python service, WinUI shell, signed development MSIX and publish output |
| `scripts/install-windows-package.ps1` | Install the generated MSIX and launch SignalDesk |
| `scripts/new-development-certificate.ps1` | Create a local development signing certificate; certificate files stay untracked |
| `scripts/prepare-gmail-oauth.ps1` | Validate/copy a Google Desktop OAuth JSON into a protected local location |
| `scripts/capture-signaldesk-window.ps1` | Capture an actual native window for UI review without browser tooling |
| `scripts/cleanup_gmail_legacy.py` | Explicit migration utility for stale local Gmail aliases |
| `scripts/generate_locked_scenarios.py` | Rebuild fictional benchmark scenarios deterministically |
| `scripts/verify.sh` | Run lint, tests, schema checks and benchmark verification |
| `scripts/dev.sh` / `dev.ps1` | Start the service in local development/demo mode |

## Typical change paths

- New source: model/schema → connector → normalizer → grouping → API → desktop badge/filter → tests.
- New agent output: model/schema → rules/model gateway → validator → policy/card → desktop detail → benchmark.
- New desktop setting: API settings contract → `UserPreferences` → settings page/global chrome → policy test.
- New action: action allowlist → bounded implementation → confirmation UI → API and safety tests.

No module is allowed to bypass the validator/policy path for automatic external actions.
