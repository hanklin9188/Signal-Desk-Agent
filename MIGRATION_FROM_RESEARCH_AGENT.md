# Migration from Existing Research Evidence Agent

## 可直接重用

| Existing | SignalDesk |
|---|---|
| Stateful orchestrator | event processing coordinator |
| Typed tools | connector/action tools |
| Pydantic schemas | UnifiedEvent/Triage schemas |
| SQLite session | local event/thread store |
| Trace JSONL | model/agent execution trace |
| Policy | action/confirmation policy |
| Scenario runner | message benchmark |
| FastAPI | local agent service |
| Model gateway | Qwen gateway |
| Rule gateway | rule-only baseline |

## 需要改寫

### 文件導向 state

改為：

```text
event/thread/card state
```

### search_documents tools

保留為 optional Research Evidence Skill，不放主 message pipeline。

### Web UI

保留作 developer dashboard；產品 UI 改 WinUI 3。

### Completion

原本是 task completed；新 Agent 是：

```text
event processed
card routed
feedback pending/received
```

## 建議 branch

```text
main
feature/signaldesk-core
```

但若原 repo 已有大量 unrelated history，建議建立獨立 `signaldesk-agent` repo，透過 package/submodule 重用共用 Python 元件。
