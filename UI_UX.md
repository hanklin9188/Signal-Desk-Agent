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
