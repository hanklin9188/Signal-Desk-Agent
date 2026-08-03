---
name: event-ingestion
description: Normalize connector payloads into privacy-aware UnifiedEvent records.
version: 1.0.0
---

# Event Ingestion Skill

## Trigger

A connector emits a new Gmail message, Windows notification, or official webhook.

## Inputs

- raw payload
- connector identity
- account identity
- cursor/idempotency metadata
- received timestamp

## Tools

- normalize_gmail
- normalize_windows_notification
- normalize_webhook
- compute_checksum
- persist_raw_event
- persist_normalized_event

## Workflow

1. Validate connector authentication and payload size.
2. Generate idempotency key.
3. Check whether the event already exists.
4. Normalize sender, title, content, timestamps and source.
5. Assign `content_completeness`.
6. Preserve raw checksum and source identifiers.
7. Persist event.
8. Emit `event_ingested`.

## Hard Rules

- Never call the LLM in ingestion.
- Never infer missing message content.
- Never mark notification preview as full content.
- Never discard a valid event because model service is offline.
- Never log credentials.
- Quarantine malformed payloads rather than crashing the connector.

## Completion

A stable `UnifiedEvent` exists or a structured quarantine record is created.
