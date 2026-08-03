---
name: daily-digest
description: Build a concise digest of unresolved messages, actions and deadlines.
version: 1.0.0
---

# Daily Digest Skill

## Trigger

- scheduled time
- user asks for digest
- focus session ends

## Inputs

- unresolved cards
- action items
- deadlines
- waiting-for-reply state
- user priority policy

## Output sections

1. Urgent
2. Due today
3. Needs reply
4. Waiting on others
5. For information
6. Connector issues

## Rules

- Do not duplicate completed cards.
- Distinguish source facts from recommendations.
- Show counts and top items.
- Link every item to the original source.
