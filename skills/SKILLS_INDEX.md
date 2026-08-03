# Skills Index

| Skill | Trigger | Main output |
|---|---|---|
| event-ingestion | connector receives new data | UnifiedEvent |
| thread-grouping | one or more normalized events | GroupedThread |
| message-triage | grouped thread needs semantic analysis | TriageResult |
| action-item-extraction | message contains request/commitment | ActionItems |
| deadline-normalization | time expression exists | Deadline |
| reply-drafting | user requests a reply draft | Draft |
| reminder-management | action/deadline needs reminder | Reminder |
| daily-digest | scheduled/user-requested digest | Digest |
| user-preference-learning | user gives feedback | preference update |
| research-evidence | user asks research-document task | evidence workflow |
