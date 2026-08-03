---
name: deadline-normalization
description: Normalize explicit temporal expressions while preserving uncertainty.
version: 1.0.0
---

# Deadline Normalization Skill

## Trigger

An action or message contains a temporal expression.

## Inputs

- deadline_text
- received_at
- timezone
- locale
- source content

## Tools

- deterministic date parser
- timezone resolver
- calendar validator

## Output

- original_text
- normalized_at or null
- precision
- timezone
- explicit
- supporting_span

## Rules

- Original text must exist in source.
- 「今晚」may normalize to a configurable local cutoff, but must retain `precision=day_part`.
- 「有空時」must remain null.
- DST/timezone ambiguity must request review.
- Model cannot create an ISO timestamp without deterministic validation.
