---
name: reminder-management
description: Create, snooze, update and complete local reminders with confirmation.
version: 1.0.0
---

# Reminder Management Skill

## Trigger

User clicks Create Reminder or confirms a suggested reminder.

## Inputs

- action item
- deadline
- source link
- reminder time
- recurrence

## Rules

- Local reminder creation may be confirmed in one click.
- External calendar mutation is a separate permission.
- Reminder must link back to source card.
- Unknown deadline requires user selection.
- Deleting or changing reminder is reversible.
