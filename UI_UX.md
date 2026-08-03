# UI / UX Design

## 1. 設計原則

1. Glanceable：3 秒內知道重點。
2. Actionable：卡片直接提供下一步。
3. Quiet：不把 AI 本身變成新的干擾源。
4. Honest：顯示是完整郵件還是通知預覽。
5. Reversible：snooze、done、priority rule 可撤回。
6. Local-first：顯示資料處理位置。
7. Inspectable：可展開原文與處理 trace。

## 2. Navigation

```text
Tray Orb
├── Glance Panel
└── Open Inbox Center

Inbox Center
├── Now
├── Today
├── Needs Reply
├── Digest
├── Done
├── Sources
├── Rules
└── Settings
```

## 3. Floating Orb

### Default

- 40–48 px。
- 顯示 important count。
- drag reposition。
- 不搶 keyboard focus。
- 可設定自動隱藏。

### State

- idle；
- processing；
- important；
- connector error；
- focus mode。

## 4. Glance Panel

寬 360–420 px，高度動態。

卡片：

```text
[Priority] [Source] [Time]
Sender / conversation
One-line summary
Reply needed · Due today
[Open] [Snooze] [Draft] [...]
```

最多顯示 3 張，其餘顯示 count。

## 5. Expanded Card

- 原始內容（可收合）；
- summary；
- why shown；
- action items；
- deadlines；
- limitation；
- content completeness；
- model/validator status；
- trace（Developer Mode）。

## 6. Inbox Center

雙欄：

```text
Filter/List | Detail
```

支援：

- keyboard navigation；
- multi-select；
- search；
- source filter；
- priority filter；
- date filter；
- bulk mark done；
- bulk digest。

## 7. Fluent Design

- Main window：Mica。
- Floating transient panel：Acrylic。
- 不透明 fallback。
- 12–16 px corner radius。
- 8 px spacing grid。
- Source icon + label。
- Priority 不只用色彩。
- font：Segoe UI Variable。
- light/dark/system。

## 8. Onboarding

1. 說明產品不會自動傳送。
2. 選擇 local model。
3. 連接 Gmail。
4. 要求 Windows notification permission。
5. 選擇允許來源 App。
6. 設定 quiet hours。
7. 啟用 7 天 Shadow Mode。
8. 完成後再詢問是否開啟即時懸浮提醒。

## 9. Settings

- Source connectors。
- Notification allowlist。
- VIP senders。
- Quiet hours。
- Focus Mode。
- Retention。
- Model residency。
- GPU pause when gaming/training。
- Data export/delete。
- Personalization reset。

## 10. 圖片與 OCR

### Inbox / Glance

- 只有 `availability=available` 才顯示縮圖。
- 縮圖固定比例與高度，不讓圖片破壞卡片節奏。
- Glance 最多顯示一張 72–88 px 縮圖；其餘以 `+N` 表示。
- metadata-only 使用來源圖示與「來源未提供圖片」文字，不使用假的 placeholder 圖。
- 圖片卡仍依來源、conversation/sender 分組，不得集中到 LINE/Messenger/Windows 通用卡。

### Detail

```text
[原圖 / 安全縮圖]       [圖片摘要]
[放大] [開啟來源]       OCR 文字與可驗證區域
                        分析狀態 / 模型 / 限制
```

- 支援縮放、鍵盤操作、螢幕閱讀器名稱與高對比外框。
- OCR supporting span 可選取並在圖片上顯示對應區域。
- `分析中`、`分析失敗`、`圖片遺失`、`格式已封鎖` 是不同狀態。
- 任何未驗證圖片結論顯示黃色 limitation banner，不能偽裝成原文。
- 提供「重試分析」與「移除本機副本」；不提供來源刪除。

### Settings / Model

- 顯示 Qwen 與 OCR 模型狀態、GPU、residency、最近一次錯誤與 VRAM 峰值。
- 可暫停圖片分析但保留圖片顯示。
- Gaming/Training 模式可卸載模型，未處理項目留在安全佇列。
