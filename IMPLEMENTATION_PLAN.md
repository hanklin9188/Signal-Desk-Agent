# Implementation Plan

## Epic 0 — Repository

- [ ] clean independent repo
- [ ] license decision
- [ ] CI
- [ ] schema validation
- [ ] issue templates
- [ ] release artifact verifier

## Epic 1 — Core Event Model

- [ ] UnifiedEvent
- [ ] connector cursor
- [ ] idempotency
- [ ] raw/normalized event store
- [ ] migration system

## Epic 2 — Windows Shell

- [ ] WinUI 3 app
- [ ] package identity
- [ ] notification permission onboarding
- [ ] UserNotificationListener
- [ ] tray
- [ ] compact overlay
- [ ] local IPC auth
- [ ] deep link open

## Epic 3 — Gmail

- [ ] Google Cloud project
- [ ] OAuth
- [ ] readonly sync
- [ ] history cursor
- [ ] MIME parser
- [ ] thread delta
- [ ] draft optional scope
- [ ] connector health

## Epic 4 — Message Pipeline

- [ ] normalize
- [ ] dedup
- [ ] grouping
- [ ] noise rules
- [ ] quiet hours
- [ ] event queue
- [ ] retry/quarantine

## Epic 5 — Model

- [ ] Qwen model smoke
- [ ] 512 prompt compiler
- [ ] non-thinking
- [ ] schema output
- [ ] model service
- [ ] batch queue
- [ ] GPU modes
- [ ] metrics

## Epic 6 — Validation

- [ ] span validator
- [ ] deadline validator
- [ ] preview limitation
- [ ] action allowlist
- [ ] calibration
- [ ] end-to-end scenario runner

## Epic 7 — UI

- [ ] orb
- [ ] glance panel
- [ ] inbox center
- [ ] detail
- [ ] why shown
- [ ] snooze/done
- [ ] reminders
- [ ] reply draft preview
- [ ] connector settings
- [ ] privacy settings
- [ ] developer trace

## Epic 8 — Dataset / Training

- [ ] annotation tool
- [ ] synthetic generator
- [ ] public dataset adapters
- [ ] human review
- [ ] QLoRA smoke
- [ ] SFT
- [ ] model card

## Epic 9 — Release

- [ ] shadow mode
- [ ] performance report
- [ ] privacy report
- [ ] installer
- [ ] demo video
- [ ] GitHub release
- [ ] issue triage

## First 4 Weeks

### Week 1

Schemas, DB, notification recorder, fixtures。

### Week 2

Gmail OAuth/sync, normalization, event list UI。

### Week 3

dedup/group/rules, floating panel。

### Week 4

Qwen audit runner, validator, first benchmark report。

## Definition of Done v1

- source connectors work；
- no duplicate cards；
- locked benchmark；
- shadow mode；
- no auto-send；
- local privacy controls；
- polished UI；
- release package；
- full docs。
