# Annotation Guidelines

## 1. Priority

```text
urgent
high
normal
low
noise
unknown
```

### urgent

必須很快處理，否則有明確損失，例如：

- 幾小時內期限；
- 帳號安全；
- 緊急會議變更；
- 明確事故。

### high

需要今天處理或來自 VIP 的直接請求。

### normal

有資訊或一般回覆需求，但不應立即打斷。

### low

非必要資訊、可延後閱讀。

### noise

OTP 已過期、promotion、重複通知、無需行動系統訊息。

### unknown

通知預覽不足。

## 2. Requires Reply

```text
yes
no
unknown
```

`yes`：

- 直接問題；
- 要求確認；
- 要求提供資料；
- 對方明確等待回覆。

`no`：

- 單純告知；
- receipt；
- build success；
- newsletter。

`unknown`：

- preview 截斷；
- 只看到圖片/貼圖；
- 指涉不清。

## 3. Action Item

Action item 必須：

- 可由訊息支持；
- 是具體動作；
- 有 owner（如果可判斷）；
- 有 supporting span。

不要把一般資訊改寫成任務。

## 4. Deadline

標記：

```text
deadline_text
deadline_iso
timezone
precision
is_explicit
```

若只有「稍後」「有空」：

- 不產生 ISO deadline；
- precision=unknown；
- 保留文字。

相對時間以 received_at 為基準。

## 5. Summary

- 1–2 句；
- 不加入建議；
- 不加入未提及原因；
- 保留主要人物、要求與期限；
- preview 必須使用「可能／看起來」或 limitation。

## 6. Suggested Actions

只允許：

```text
open_source
draft_reply
create_reminder
snooze
mark_done
needs_review
```

## 7. Supporting Span

必須是原始 normalized content 的 exact substring。

## 8. 雙人審查

Locked benchmark：

- 兩位 annotator；
- disagreement adjudication；
- 記錄 rationale code；
- priority 需報 inter-annotator agreement。
