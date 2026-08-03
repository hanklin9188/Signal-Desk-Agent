# Contributing

Thanks for helping improve SignalDesk. Contributions should preserve its local-first, evidence-backed, no-auto-send guarantees.

## Before opening a pull request

- Link a focused issue or explain the user problem clearly.
- Add fictional regression fixtures and tests.
- Run Ruff, Pytest, and the relevant benchmark.
- Build the native project when changing XAML or C#.
- Include a privacy-safe screenshot for UI changes.
- Document schema migrations and connector/security impact.
- Update the architecture/status docs when ownership or product boundaries change.

## Commit style

Use a concise conventional prefix: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `perf:`, or `security:`.

## Sensitive data

Never upload real Gmail, LINE, Messenger, or Windows notification contents. Do not commit OAuth JSON, tokens, local databases, certificates, private screenshots, or machine-specific output reports. Use the fictional fixtures in `examples/` and `benchmarks/`.

## Security-sensitive changes

Changes to authentication, connectors, external actions, source URL handling, retention, or model tool permissions require an explicit security review and negative tests.
