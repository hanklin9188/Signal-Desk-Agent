# Connectors

## 1. Connector Interface

```python
class Connector:
    connector_id: str
    source: str

    async def authenticate(self) -> AuthResult: ...
    async def initial_sync(self) -> list[RawEvent]: ...
    async def incremental_sync(self, cursor: str | None) -> SyncBatch: ...
    async def health(self) -> ConnectorHealth: ...
    async def open_source(self, event: UnifiedEvent) -> OpenResult: ...
```

## 2. Gmail

### Authentication

- Google OAuth installed-app flow。
- 最小權限原則。
- Read-only MVP 使用 Gmail readonly scope。
- 建立 draft 為 optional capability，獨立 onboarding。
- refresh token 加密保存。
- sign-out 時撤銷與刪除 token。

### Incremental sync

- 保存 Gmail history ID。
- 使用 mailbox history 取得新增訊息。
- history ID 過期/404 時 full sync。
- 依 thread ID 分群。
- 取得 message body 時剝離 HTML、signature、quoted history。

### Draft

- 第一版只建立 draft，不 send。
- 顯示 recipients、subject、body preview。
- 使用者確認後才呼叫 Gmail drafts create。

## 3. Windows Notification Listener

- 初次使用顯示清楚的 permission rationale。
- 呼叫 RequestAccessAsync。
- 每次啟動檢查 access status。
- 使用 NotificationChanged 與定期 state reconciliation。
- 每個 notification 讀取 source AppInfo、timestamp、notification content。
- 權限撤銷時顯示 connector degraded，不靜默假裝正常。

## 4. Personal LINE

可用來源：

- LINE Desktop 產生的 Windows toast preview。

限制：

- 只有通知實際顯示內容。
- 關閉 preview 時可能只有「新訊息」。
- 圖片、貼圖、語音通常缺乏內容。
- 無完整歷史與已讀狀態。

標記：

```text
source=line_notification
content_completeness=notification_preview
```

## 5. Personal Messenger

可用來源：

- Messenger desktop 或瀏覽器產生的 Windows notification。

若 source app 是 Chrome/Edge：

- 解析 notification origin/title；
- 不可只靠 browser app ID 判定 sender；
- 低置信度標記 `source_resolution_uncertain`。

標記：

```text
source=messenger_notification
content_completeness=notification_preview
```

## 6. LINE Official Account

Optional connector：

- Messaging API webhook；
- 只收發使用者與 Official Account 的事件；
- 驗證 webhook signature；
- 非個人 LINE inbox。

## 7. Facebook Page Messenger

Optional connector：

- Meta Page webhook；
- 需要 Page 與 app permissions；
- 非個人 Messenger inbox；
- 驗證 webhook signature；
- webhook redelivery 必須去重。

## 8. Generic Windows Notification Connector

日後可支援：

- Teams；
- Slack；
- Discord；
- WhatsApp Desktop；
- Calendar；
- GitHub Desktop。

所有 source-specific parser 都要有 contract fixtures。
