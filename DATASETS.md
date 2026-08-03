# Dataset Plan

## 1. 原則

沒有任何單一公開資料集能完整覆蓋：

- Gmail 完整郵件；
- LINE／Messenger notification previews；
- 繁體中文；
- priority；
- requires reply；
- action item；
- deadline；
- false interruption；
-個人偏好。

所以資料策略必須是：

```text
公開資料
+ 合成資料
+ 人工審查
+ opt-in 使用者修正
```

## 2. 可參考的公開資料

| Dataset | 適用任務 | 注意事項 |
|---|---|---|
| EmailSum | email thread short/long summary | 使用前確認 summary data license |
| SAMSum | messenger-like dialogue summary | 常見版本具非商用限制，商用前需法律確認 |
| DialogSum | real-life dialogue summary | 適合對話摘要與主題 |
| MailEx | email event/argument extraction | 適合 event、參與者、時間、議題 |
| Smart To-Do | email-to-task generation | 確認 dataset 可取得性與授權 |
| EPA | email task assignee | 適合誰負責什麼 |
| Enron | email style/thread/raw corpus | 真實 PII 與倫理問題；需清理 |
| TempEval-3 | temporal expression | 主要是英文 news，需補中文 |
| BC3 / Email summarization corpora | email summary | 需確認取得與授權 |

## 3. SignalDesk 自建資料

### 3.1 類型

- Traditional Chinese Gmail。
- 中英混合工作信。
- LINE notification preview。
- Messenger notification preview。
- Group chat fragments。
- Promotion/OTP/system noise。
- Explicit deadline。
- Implicit request。
- Ambiguous preview。
- Image/sticker-only notification。
- Conflicting messages。
- Long thread delta。
- Traditional Chinese screenshots and chat captures with fictional identities。
- Event posters, receipts, tables and document pages。
- General photos/stickers where no exact text claim is possible。
- Image metadata-only, missing, blocked and corrupted hard negatives。

### 3.2 目標規模

#### Audit v0

300 examples。

#### SFT v1

5,000–10,000 reviewed examples。

#### SFT v2

20,000+ examples，包含 hard negatives。

#### Multimodal audit v0

300+ human-reviewed examples, balanced across screenshot, document, photo/sticker and unavailable
image slices. SFT image volume is not set until the zero-shot audit identifies real failure modes.

The repository now contains 300 deterministic fictional images and `manifest.jsonl` under
`benchmarks/multimodal/`. They are deliberately marked `unreviewed`; generation is not human
review. Use:

```bash
.venv/bin/signaldesk-multimodal-review status
.venv/bin/signaldesk-multimodal-review review --id mm-001 --decision approved \
  --reviewer "Reviewer name"
.venv/bin/signaldesk-multimodal-review lock --output data/multimodal-locked.jsonl
```

The `lock` command refuses to create a release audit until all 300 records have reviewer identity,
timestamp and decision. Review ledgers stay under `data/` and are excluded from Git by default.

### 3.3 來源比例建議

| 來源 | 比例 |
|---|---:|
| synthetic Traditional Chinese | 35% |
| adapted public email | 20% |
| adapted dialogue | 15% |
| notification preview synthetic | 20% |
| hard negative / ambiguity | 10% |

## 4. Split

必須按 thread、sender template、scenario family 切分。

```text
train 80%
validation 10%
locked test 10%
```

另有：

- Real-user shadow test；
- source OOD；
- bilingual OOD；
- unseen sender role；
- unseen deadline format。

## 5. PII

- public corpus 清理 email、phone、address；
- synthetic use fictional names；
- personal opt-in data 先 local redaction；
- dataset export 不含 raw private conversation；
- raw-to-label mapping 保存在使用者本機。

## 6. Dataset Record

每筆：

```json
{
  "input": {},
  "target": {},
  "source_type": "synthetic",
  "language": "zh-TW",
  "content_completeness": "notification_preview",
  "review_status": "human_verified",
  "license_tag": "project_generated",
  "split_group": "scenario_family_001"
}
```

Multimodal records additionally include asset hashes and evidence regions, never public local paths:

```json
{
  "asset_sha256": "<sha256>",
  "media_kind": "screenshot",
  "availability": "available",
  "ocr_blocks": [{"text": "截止 8 月 10 日", "region": [0.1, 0.4, 0.8, 0.5]}],
  "visual_target": {"summary": "活動報名海報", "deadline_span": "截止 8 月 10 日"},
  "review_status": "human_verified"
}
```

Private originals remain local. An export for annotation includes only explicit opt-in assets with
metadata stripped, or irreversible fictional/redacted derivatives. Image hashes are split-group
keys so resized copies of the same image cannot leak across train and test.
