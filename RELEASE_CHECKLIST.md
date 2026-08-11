# Release Checklist

## Repository gate

- [ ] CI passes on Linux and Windows runners.
- [ ] README commands match the current package and repository name.
- [ ] No credentials, tokens, private databases, certificates, real messages, or private screenshots are tracked.
- [ ] Dependency and package versions are internally consistent.
- [ ] `IMPLEMENTATION_STATUS.md` matches the release commit.
- [ ] Known limitations and source-completeness boundaries are visible.

## Functional gate

- [ ] Gmail OAuth onboarding, initial sync, incremental sync, logout, and token failure are exercised.
- [ ] Windows notification permission denial/revocation is handled.
- [ ] LINE and Messenger archive imports are tested against supported variants.
- [ ] Duplicate and replay suppression survives restart.
- [ ] Focus mode, quiet hours, VIP/mute rules, and interruption budget persist correctly.
- [ ] Draft creation remains confirmation-gated.
- [ ] No auto-send, source-delete, or arbitrary-shell route exists.

## Privacy and security gate

- [ ] API binds only to loopback and requires an unguessable token.
- [ ] Host, Origin, request-size, URL allowlist, and path validation tests pass.
- [ ] OAuth tokens remain in the OS credential store.
- [ ] Export, retention, reset, and confirmed deletion are exercised.
- [ ] Prompt-injection and malformed-model-output negative tests pass.
- [ ] Logs and diagnostics exclude message bodies, tokens, and local secret paths.

## Evaluation gate

- [ ] Locked fictional benchmark passes without unauthorized actions.
- [ ] Optional model is compared with the deterministic baseline.
- [ ] At least 300 anonymized events receive human review.
- [ ] A 7–14 day Shadow Mode study is completed.
- [ ] Correction, interruption, unsupported-claim, and missed-urgent metrics are reported.
- [ ] Evaluation limitations and dataset provenance are documented.

## Windows distribution gate

- [ ] Release build completes on a clean Windows machine.
- [ ] Production publisher certificate replaces the development certificate.
- [ ] MSIX install, first launch, upgrade, rollback, repair, and uninstall are tested.
- [ ] Packaged service and shell versions match.
- [ ] No private configuration or model cache is bundled.
- [ ] Checksums and release notes are published.

## Release labels

- **Development build:** local developer use; no public install guarantee.
- **Preview release:** installable, but human evaluation or production signing remains incomplete.
- **Production release:** every mandatory gate above is complete and evidenced.
