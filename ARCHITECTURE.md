# Architecture

## 1. Process Topology

```text
SignalDesk.Shell.exe
├── WinUI 3
├── UserNotificationListener
├── tray / AppWindow
├── OAuth launch
└── local IPC client

signaldesk-agent-service.exe / python
├── Gmail connector
├── event normalizer
├── SQLite
├── rule engine
├── skill registry
├── policy
├── validation
├── trace
└── FastAPI localhost

signaldesk-model-service
├── Qwen3.5-4B
├── 512 context
├── non-thinking
├── JSON output
└── health / metrics
```

## 2. Component Contracts

### Native Shell → Agent Service

```json
{
  "type": "notification_event",
  "payload": {},
  "shell_version": "0.1.0"
}
```

### Agent Service → Model Service

```json
{
  "request_id": "req_x",
  "task": "message_triage",
  "prompt_version": "triage-v1",
  "input": {},
  "max_context": 512,
  "max_output": 128
}
```

### Agent Service → UI

SSE/WebSocket event：

```text
event_ingested
thread_grouped
triage_started
triage_completed
card_created
card_updated
connector_health
```

## 3. Database

### tables

- accounts
- connectors
- raw_events
- normalized_events
- threads
- thread_events
- triage_results
- action_items
- deadlines
- notification_cards
- user_feedback
- reminders
- reply_drafts
- traces
- model_runs
- connector_cursors

### Data lifecycle

```text
raw event
→ normalized event
→ grouped thread
→ triage
→ card
→ feedback
→ retention cleanup
```

## 4. Idempotency

Every ingestion path MUST produce an idempotency key.

Gmail：

```text
gmail:{account}:{message_id}:{history_id}
```

Windows notification：

```text
windows:{app_id}:{notification_id}:{content_hash}
```

Webhooks：

```text
provider:{webhook_event_id}
```

## 5. Failure Isolation

- Connector failure 不停止其他 connector。
- Model OOM 不刪除 event。
- UI crash 不停止 ingestion。
- DB lock 使用 bounded retry。
- malformed event 放 quarantine。
- failed model request 可重跑。
- Gmail history 404 觸發 full sync。
