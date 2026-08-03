---
name: user-preference-learning
description: Learn interruption preferences from explicit and implicit feedback without retraining the LLM first.
version: 1.0.0
---

# User Preference Learning Skill

## Trigger

User opens, dismisses, snoozes, corrects or marks a card.

## Inputs

- feedback event
- card features
- source metadata
- prior preference state

## Workflow

1. Store privacy-minimized feature record.
2. Update sender/category rules immediately for explicit choices.
3. Periodically retrain local ranker.
4. Validate on recent held-out feedback.
5. Apply only if calibration improves.
6. Allow reset/export.

## Hard Rules

- Do not silently create permanent sender rules from one implicit event.
- Do not upload raw content.
- Do not modify semantic extraction labels without explicit correction.
