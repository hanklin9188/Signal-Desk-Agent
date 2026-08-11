# Evaluation and Evidence Policy

SignalDesk distinguishes four different kinds of evidence. They must not be collapsed into one accuracy claim.

## 1. Unit and integration tests

These validate deterministic code contracts such as API behavior, persistence, connector parsing, evidence spans, privacy controls, and safety boundaries.

They answer: **Does the implementation behave as specified on the tested cases?**

They do not answer: **Will the product prioritize real user messages correctly?**

## 2. Locked fictional benchmark

The repository's current benchmark contains 300 fictional scenarios and 1,800 policy checks. It is designed for repeatable regression detection, negative cases, and unauthorized-action prevention.

Current recorded evidence:

- 300 fictional scenarios;
- 1,800 policy checks;
- zero unauthorized actions;
- zero automatic-send actions.

Because the fixtures are fictional and repository-visible, this benchmark must not be described as a representative held-out human-message study.

## 3. Local-model calibration

Optional Qwen output is advisory and must pass schema/evidence validation. Calibration measurements, when recorded, should be reported separately for:

- priority classification;
- reply-needed classification;
- category classification;
- deadline extraction precision/recall;
- unsupported-claim rate;
- fallback and rejection rate;
- latency and peak VRAM.

A small calibration set is diagnostic evidence, not a generalization claim.

## 4. Real-world Shadow Mode evaluation

Before a production-quality claim, collect at least 300 anonymized, consented, human-reviewed events and run 7–14 elapsed days in Shadow Mode. SignalDesk should make recommendations without interrupting or acting automatically while reviewers record corrections.

### Required slices

- full Gmail messages;
- truncated notification previews;
- LINE and Messenger archive imports;
- direct questions and reply requests;
- explicit and relative deadlines;
- promotions and duplicate notifications;
- image/sticker-only or context-poor events;
- English and Traditional Chinese content.

### Required metrics

| Metric | Definition |
| :--- | :--- |
| Priority macro F1 | Macro-averaged classification across priority labels |
| Reply-needed F1 | Precision/recall for whether a response is required |
| Deadline precision/recall | Exact supported deadline detection under the stored timezone |
| Unsupported-claim rate | Fraction of outputs containing claims not supported by source evidence |
| User correction rate | Fraction of surfaced cards whose category/priority/action is corrected |
| Unwanted interruption rate | Fraction of surfaced-now decisions judged unnecessary |
| Missed urgent rate | Urgent events not surfaced under the configured policy |
| Model fallback rate | Fraction rejected or handled by deterministic rules |

Report confidence intervals and per-source/per-completeness slices, not only an overall average.

## Evidence hierarchy

```text
human-reviewed Shadow Mode evidence
> locked fictional regression benchmark
> unit/integration tests
> screenshots or anecdotes
```

A screenshot proves that a UI state can be displayed. It does not prove model quality, connector completeness, or user benefit.
