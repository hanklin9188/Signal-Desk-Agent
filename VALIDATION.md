# Validation Plan

## 1. 驗證層級

```text
L0 Schema
L1 Connector
L2 Normalization/Dedup
L3 Grouping
L4 Rule Engine
L5 Model Triage
L6 Validator/Policy
L7 End-to-End
L8 UI
L9 Performance
L10 Shadow Mode
```

## 2. L0 Schema

- valid fixtures accepted 100%；
- invalid fixtures rejected 100%；
- unknown fields rejected；
- version compatibility tests。

## 3. L1 Connector

### Gmail

- OAuth grant/deny/revoke；
- refresh token；
- initial sync；
- incremental history；
- 404 full sync；
- MIME plain/html；
- attachments metadata；
- draft create confirmation；
- no send。

### Windows

- permission allowed/denied/revoked；
- current toast sync；
- NotificationChanged；
- app identity；
- malformed notification；
- permission silent-empty behavior；
- duplicate notifications。

### LINE/Messenger

- preview on/off；
- truncated content；
- sticker/image-only；
- browser source ambiguity；
- same sender burst；
- group chat title。

## 4. L2 Dedup

- webhook redelivery；
- Gmail history replay；
- Windows same ID；
- same text different time；
- same text different sender；
- restart replay。

Metric：

```text
Duplicate suppression precision / recall
```

## 5. L3 Grouping

- Gmail thread ID exact；
- LINE/Messenger burst grouping；
- group boundary；
- sender change；
- out-of-order events；
- delayed event。

Metric：

```text
pairwise grouping F1
```

## 6. L4 Rule Engine

- OTP；
- promotion；
- build success/failure；
- calendar；
- VIP；
- quiet hours；
- focus mode；
- false positive。

## 7. L5 Model Audit

### Dataset

初版 300 events：

| 類型 | 數量 |
|---|---:|
| Gmail full | 80 |
| Gmail thread delta | 50 |
| LINE preview | 60 |
| Messenger preview | 60 |
| noise/system | 30 |
| ambiguous | 20 |

### Metrics

- Raw JSON validity。
- Summary faithfulness。
- Important-message recall。
- Priority macro F1。
- Requires-reply F1。
- Action-item span F1。
- Deadline exact/normalized accuracy。
- Hallucinated deadline rate。
- Preview overclaim rate。
- Suggested-action validity。

### 建議 release gate

| Metric | Gate |
|---|---:|
| Raw JSON validity | ≥ 0.98 |
| Important recall | ≥ 0.92 |
| Requires-reply F1 | ≥ 0.82 |
| Action-item F1 | ≥ 0.78 |
| Explicit deadline accuracy | ≥ 0.92 |
| Hallucinated deadline | ≤ 0.01 |
| Summary faithfulness | ≥ 0.92 |
| Preview overclaim | ≤ 0.03 |

這些是工程目標；未達必須如實報告。

## 8. L6 Validator / Policy

- invented span rejected；
- invented deadline removed；
- unknown action rejected；
- preview limitation added；
- low completeness cannot auto-surface urgent without rule support；
- auto-send impossible；
- user confirmation enforced。

## 9. L7 End-to-End

Scenario：

```text
events
→ grouping
→ triage
→ validation
→ interruption decision
→ card
→ user action
```

指標：

- task success；
- card correctness；
- wrong interruption；
- missed important；
- time to card；
- unauthorized action；
- trace completeness。

## 10. Baselines

1. Windows/Gmail raw notification。
2. Rule-only。
3. Fixed summarizer。
4. Qwen zero-shot。
5. Qwen + validator。
6. QLoRA SFT（若做）。
7. QLoRA + personal ranker。

## 11. False Interruption

\[
FIR =
\frac{\text{immediate cards judged unnecessary}}
{\text{all immediate cards}}.
\]

Important miss：

\[
IMR =
\frac{\text{important messages not surfaced within policy window}}
{\text{all important messages}}.
\]

兩者都必須報，不可只追求 accuracy。

## 12. Robustness

- prompt injection；
- mixed language；
- typo；
- emoji；
- sarcasm；
- truncated preview；
- adversarial dates；
- timezone；
- DST；
- very long Gmail；
- model timeout；
- OOM；
- DB lock；
- connector offline；
- clock skew；
- restart。

## 13. Performance

記錄：

- event-to-card p50/p95/p99；
- model load time；
- model inference latency；
- tokens/s；
- input/output tokens；
- GPU VRAM；
- CPU/RAM；
- queue size；
- model calls/event；
- batch size；
- idle GPU utilization；
- crash-free hours。

## 14. Shadow Mode

至少 7–14 天：

- 不立即浮出；
- 記錄 Agent 建議；
- 使用者回顧；
- 產生 confusion matrix；
- 個人 threshold；
- 只有達 gate 才開 live interruption。

## 15. Release Artifact

```text
runs/<id>/
├── config.yaml
├── environment.json
├── model_revision.json
├── dataset_manifest.json
├── raw_predictions.jsonl
├── traces.jsonl
├── per_example.csv
├── metrics.json
├── errors.csv
└── report.md
```
