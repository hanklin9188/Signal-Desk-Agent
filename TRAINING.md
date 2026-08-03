# Training Plan

## 1. 先不訓練

第一個模型 milestone 是 Qwen3.5-4B zero-shot audit。

先驗證：

- 512 context 是否足夠；
- JSON 是否穩；
- 中文摘要是否忠實；
- reply/action/deadline 指標；
- preview uncertainty。
- screenshot/photo understanding and OCR-grounded evidence faithfulness;
- image-unavailable refusal behavior;
- RTX 4080 SUPER latency, peak VRAM and OOM recovery.

## 2. 訓練觸發條件

### 做 SFT

- summary faithfulness 低於 gate；
- requires_reply F1 明顯不足；
- action-item F1 不足；
- preview 經常過度推論；
- zh-TW 結構化輸出系統性錯。

### 不做 SFT

- 只有 JSON parse 問題；
- 只有日期 normalization 問題；
- grouping 問題；
- connector 遺漏；
- UI 問題；
- priority 主要是個人偏好。

## 3. SFT Target

Prompt-completion 格式：

```json
{
  "prompt": [
    {"role": "system", "content": "compact triage contract"},
    {"role": "user", "content": "{UnifiedThread JSON}"}
  ],
  "completion": [
    {"role": "assistant", "content": "{TriageResult JSON}"}
  ]
}
```

只對 assistant/completion tokens 計算 loss。

## 4. QLoRA 建議

> 實際支援需先用當時最新版 Transformers/PEFT/TRL 對 Qwen3.5 architecture 做 smoke test。

```yaml
model: Qwen/Qwen3.5-4B
max_length: 512
quantization: 4bit_nf4
compute_dtype: bfloat16
lora_rank: 16
lora_alpha: 32
lora_dropout: 0.05
target_modules: all-linear-if-supported
micro_batch_size: 1
gradient_accumulation: 16
learning_rate: 1e-4
epochs: 2-3
warmup_ratio: 0.03
gradient_checkpointing: true
assistant_only_loss: true
eval_strategy: steps
save_best_metric: composite_validation_score
```

若 QLoRA backend 尚未支援：

1. BF16 LoRA；
2. 降低 batch；
3. activation offload；
4. 等待/升級框架；
5. 不更改 benchmark contract。

## 5. Composite Metric

\[
S =
0.25 F1_{\text{reply}}
+0.20 F1_{\text{action}}
+0.20 Acc_{\text{deadline}}
+0.20 Faithfulness
+0.15 JSONValidity
-\lambda HallucinationRate.
\]

## 6. Calibration

Generative output 不直接當機率。

建立 held-out outcome table：

```text
features
→ correct / incorrect
```

使用：

- logistic regression；
- isotonic regression；
- temperature scaling（適合分類 head 時）。

輸出：

- `validated_probability_important`
- `validated_probability_reply`

## 7. Preference Ranker

個人化不要先微調 LLM。

訓練資料：

- card surfaced；
- user opened；
- dismissed；
- snoozed；
- marked important；
- corrected label。

模型每個使用者獨立，本地更新。

## 8. Optional DPO

只針對：

- reply tone；
- summary brevity；
- card wording。

不得讓 DPO 直接取得 send permission。

## 9. 4080 SUPER

訓練前先跑：

- model load smoke；
- 512 batch 1 forward/backward；
- VRAM log；
- 20-step overfit test；
- checkpoint resume；
- output schema eval。

完整實驗保存：

```text
config
git commit
dataset manifest
model revision
tokenizer revision
raw predictions
metrics
VRAM
training time
```

## 10. Multimodal audit before training

Use `Qwen/Qwen3.5-4B` as the primary VLM and `PaddlePaddle/PaddleOCR-VL-1.6` as the
specialized OCR/document parser. Pin exact revisions before recording results.

Required evaluation slices:

| Slice | Minimum audit examples | Primary metric |
|---|---:|---|
| Traditional Chinese screenshots | 75 | OCR-grounded faithfulness |
| Documents/tables/posters | 75 | exact deadline/action evidence |
| General photos/stickers/charts | 75 | faithful short summary |
| Missing/blocked/metadata-only | 75 | refusal / no invention |

Training is allowed only after error attribution separates connector acquisition, OCR, VLM,
validator and UI failures. Do not train Qwen to compensate for missing pixels or broken grouping.

Multimodal QLoRA, if triggered, must preserve image-text pairs, apply loss only to assistant output,
and use a held-out family/thread split. Exact dates and action items remain validator-gated even if
the trained model improves.
