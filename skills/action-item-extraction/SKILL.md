---
name: action-item-extraction
description: Extract concrete tasks and commitments supported by exact message spans.
version: 1.0.0
---

# Action Item Extraction Skill

## Trigger

Triage indicates a request, commitment, assignment or pending response.

## Output fields

- text
- owner
- status
- supporting_span
- source_event_ids
- deadline reference
- confidence class from validator

## Rules

An action item must be executable and supported.

Valid:

- 「今晚前請把報告寄給我」→ 寄出報告。
- 「你可以參加嗎？」→ 回覆是否參加。

Invalid:

- 「報告很重要」→ 不自動產生「完成報告」。
- 「傳送一張相片」→ 不猜待辦。

## Validation

- supporting span exact match;
- owner not invented;
- preview ambiguity produces `owner=unknown` where appropriate;
- duplicate action items merged only when semantically identical.
