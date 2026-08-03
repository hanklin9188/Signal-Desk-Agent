# Product Requirements Document

## 1. 產品目標

SignalDesk 必須讓使用者在不頻繁切換 Gmail、LINE、Messenger 的情況下，快速知道：

1. 哪些訊息重要。
2. 哪些需要回覆。
3. 對方要求了什麼。
4. 有沒有期限。
5. 下一步可以做什麼。
6. 哪些資訊只是通知預覽、不能過度推論。

## 2. MVP 功能

### P0

- Gmail OAuth 與新郵件同步。
- Windows 通知權限與 listener。
- LINE／Messenger notification preview normalization。
- Event deduplication。
- Same-conversation grouping。
- Rule-based noise filter。
- Qwen3.5-4B 512-token triage。
- Schema validator。
- System tray。
- Floating glance panel。
- Inbox Center。
- Open source、snooze、mark done、create reminder。
- Gmail reply draft preview。
- Local SQLite。
- Trace 與 benchmark。
- Supported connector 圖片安全儲存、縮圖與詳細檢視。
- Qwen3.5-4B 圖片理解與 PaddleOCR-VL 文字證據路由。
- 圖片不可用、分析失敗與未驗證證據的明確狀態。

### P1

- Daily digest。
- Focus mode。
- VIP sender。
- Personal preference ranker。
- Search/filter。
- Export anonymized benchmark。
- Page/Official Account webhooks。
- 多圖片批次、OCR 區域高亮與分析重試。

### 非 MVP

- 自動傳送回覆。
- 讀取完整個人 LINE/Messenger inbox。
- 任意操作桌面。
- 任意 shell。
- 多 Agent。
- 雲端同步。
- FAD / Adaptive Exit。

## 3. 使用者故事

### US-01

當教授寄信要求今晚前回覆，我希望收到一張高優先卡，顯示期限與建立草稿操作。

### US-02

當 LINE 群組連續傳 5 則短訊息，我希望它們先合併成一張摘要，而不是彈 5 次。

### US-03

當 Messenger 只通知「傳送一張相片」，我希望 Agent 顯示上下文不足，而不是猜圖片內容。

### US-04

在 Focus Mode，我只希望明確重要且需回覆的訊息打斷我。

### US-05

我希望告訴系統某個寄件者永遠重要，或某類通知永遠不要打斷。

### US-06

我希望所有私人訊息預設留在本機，且可以刪除歷史。

### US-07

當 Gmail 或匯入的 Messenger 對話真的包含圖片，我希望在訊息卡詳細頁看到圖片、OCR
文字及圖片摘要，不必跳回來源才能知道內容。

### US-08

當 LINE/Messenger 通知只說「傳送一張圖片」卻沒有提供圖片內容，我希望 SignalDesk
清楚顯示無法讀取，不得產生假的圖片摘要、期限或待辦。

### US-09

當活動海報包含截止日期，我希望截止日期只有在 OCR 證據能對應同一張圖片時才進入待辦。

## 4. 非功能需求

- Windows 11。
- 服務只綁 localhost。
- Gmail OAuth token 加密保存。
- 在 model unavailable 時，事件不可遺失。
- 同一 event 不可重複建立卡片。
- UI restart 後恢復未處理狀態。
- 任何 auto-send rate 必須為 0。
- 任何 hallucinated source action 必須被 policy 阻擋。
- Accessibility：keyboard、screen reader、contrast。
- 重要事件到卡片 p95 目標 < 10 秒（模型已常駐時）。
- 規則可直接處理的事件 p95 目標 < 1 秒。
- 原始圖片只接受允許格式、檔案簽章必須符合 MIME，單檔上限 20 MB。
- 本機路徑不得出現在 API、trace、export 或模型輸出。
- 圖片衍生檔、OCR 與分析結果必須受 retention/full-delete 管理。
- 圖片即時路由 p95 目標 < 15 秒（模型已常駐且圖片已在本機時）。

## 5. MVP 驗收

- 兩個 Gmail 帳號可選擇性連接。
- Windows notification permission onboarding 正常。
- 來源辨識與 content completeness 正確。
- 300+ locked events 完成 benchmark。
- fabricated deadline rate 低於 release gate。
- no unauthorized action。
- shadow mode 完成。
- 產品 UI 可連續運作一個工作日。
- 300+ 人工審查圖片案例完成 locked audit，精確期限虛構率為 0。
- 可用圖片、metadata-only、missing、blocked 與分析失敗皆有可測試 WinUI 狀態。
