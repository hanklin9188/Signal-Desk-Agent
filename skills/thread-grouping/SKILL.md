---
name: thread-grouping
description: Deduplicate and combine related message events into a stable thread.
version: 1.0.0
---

# Thread Grouping Skill

## Trigger

One or more ungrouped UnifiedEvents exist.

## Inputs

- normalized events
- source
- conversation/thread metadata
- grouping windows
- prior threads

## Tools

- lookup_thread
- create_thread
- attach_event
- merge_thread
- sort_events
- compute_group_features

## Workflow

1. Gmail: prefer provider thread ID.
2. Notification previews: use source, sender/group title and time window.
3. Preserve event order using timestamps.
4. Do not merge across different sources unless a user explicitly links identities.
5. Update thread delta.
6. Emit `thread_updated`.

## Hard Rules

- Same text from different senders is not a duplicate.
- Out-of-order events must be sorted.
- Browser notifications with uncertain origin must not be merged aggressively.
- Never combine unrelated personal conversations to save model calls.

## Validation

- pairwise grouping fixture
- duplicate replay
- delayed event
- sender change
- group-title collision
