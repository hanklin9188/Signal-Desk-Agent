---
name: message-triage
description: Produce a faithful summary, priority, reply requirement and safe actions.
version: 1.0.0
---

# Message Triage Skill

## Trigger

A grouped thread passes rule filtering and needs semantic analysis.

## Model

- Qwen/Qwen3.5-4B
- non-thinking
- text-only
- 512 total tokens
- max input 384
- max output 128

## Inputs

- grouped thread
- content completeness
- compact verified memory
- source
- policy context
- allowed actions

## Output

Must validate as `TriageResult`.

## Workflow

1. Compile compact prompt.
2. Generate exactly one JSON object.
3. Validate schema.
4. Verify supporting spans.
5. Verify deadline/action evidence.
6. Add preview limitation where required.
7. Pass result to interruption policy.

## Hard Rules

- Do not invent deadlines.
- Do not infer image/sticker contents.
- Do not claim a preview is a full conversation.
- Summary must be descriptive, not a recommended reply.
- Do not select any action outside the allowlist.
- Do not auto-send.

## Failure

- one constrained retry for malformed JSON;
- then `needs_review`;
- preserve event for later reprocessing.
