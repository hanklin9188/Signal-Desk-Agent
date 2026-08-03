---
name: reply-drafting
description: Draft a response only after the user explicitly requests it.
version: 1.0.0
---

# Reply Drafting Skill

## Trigger

User clicks Draft Reply or asks SignalDesk to draft a response.

## Inputs

- source message/thread
- verified summary
- user tone profile
- requested language
- allowed facts

## Output

- recipient preview
- subject
- body
- source references
- unsupported claim check

## Workflow

1. Confirm target message.
2. Build a fact-only context.
3. Generate a concise draft.
4. Validate no invented commitments.
5. Display editable preview.
6. Optionally create Gmail draft after confirmation.

## Hard Rules

- Never send.
- Never promise dates/tasks not authorized by the user.
- Never draft LINE/Messenger into an automated send path in v1.
- Preserve user review.
