from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .deadlines import extract_deadlines
from .models import ActionItem, GroupedThread, TriageResult


@dataclass(slots=True)
class RuleSignals:
    category: str = "other"
    priority: str = "normal"
    requires_reply: str = "no"
    reason_codes: list[str] = field(default_factory=list)
    is_noise: bool = False
    is_vip: bool = False
    image_only: bool = False
    muted: bool = False


NOISE_PATTERNS = [
    r"\bOTP\b|驗證碼|verification code|登入代碼",
    r"unsubscribe|取消訂閱|限時優惠|折扣碼|promotion|廣告",
    r"build (?:succeeded|passed)|部署成功|CI passed",
    r"新(?:的)?徽章|new badge|熱門動態|trending (?:feed|post)|engagement notice",
]
SECURITY_PATTERNS = [
    r"異常登入|可疑登入|陌生裝置.*登入|不是你.*保護帳戶|security alert|密碼已變更|"
    r"new sign-in"
]
MEETING_PATTERNS = [r"會議|meeting|appointment|議程|standup|sync|client call|\bcall at\b"]
RESEARCH_PATTERNS = [
    r"實驗|論文|研究|受試者|實驗室|指導教授|dataset|benchmark|reviewer|manuscript|"
    r"journal|thesis|reading list|lab material"
]
TRANSACTION_PATTERNS = [r"付款|發票|收據|payment|invoice|訂單"]
WORK_PATTERNS = [
    r"專案|客戶|辦公室|production|customer|client|project|upload|shared file|office"
]
SOCIAL_PATTERNS = [r"我已(?:經)?到|你慢慢來|有空再|一起去|週末愉快"]
URGENT_PATTERNS = [r"緊急|立即|asap|urgent|馬上"]
REQUEST_PATTERNS = [r"請(?:你|協助|幫忙|在|於|把|提供|回覆)?", r"麻煩", r"could you", r"please"]
LOW_PRIORITY_PATTERNS = [
    r"有空(?:再|時)|不急|沒有期限|無期限|週末愉快|optional|whenever you have time|"
    r"no deadline"
]
NO_REPLY_PATTERNS = [
    r"不用回覆|無需回覆|不必回覆|僅供通知|僅供參考|"
    r"no (?:response|reply) is (?:needed|required)"
]
IMAGE_ONLY_PATTERNS = [
    r"^(?:.*?)(?:傳送了?|sent)(?:\s+you)?\s*(?:\d+|一|one|an?)?\s*(?:張|個)?\s*"
    r"(?:相片|照片|圖片|photo|image|sticker|貼圖)[。.!]?$"
]


def combined_text(thread: GroupedThread) -> str:
    return "\n".join(message.content for message in thread.messages if message.content).strip()


def _match_any(patterns: list[str], content: str) -> bool:
    return any(re.search(pattern, content, re.IGNORECASE) for pattern in patterns)


def _trim_summary(content: str, limit: int = 96) -> str:
    cleaned = re.sub(r"\s+", " ", content).strip()
    if not cleaned:
        return "只有來源資訊，通知未提供可讀內容。"
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip("，。；; ") + "…"


def _action_span(content: str, reply: str) -> tuple[str, str] | None:
    question = re.search(r"[^。！？!?\n]{0,70}(?:可以嗎|能否|好嗎|是否|\?|？)", content, re.I)
    if question:
        span = question.group(0).strip()
        if re.search(r"參加|出席", span) and re.search(r"會議|meeting", content, re.I):
            return "回覆是否能參加會議", span
        return f"回覆對方的問題：{span.rstrip('？?')}", span
    request = re.search(
        r"(?:請|麻煩|please|could you)[^。！？!?\n]{2,100}[。！？!?]?", content, re.I
    )
    if request:
        span = request.group(0).strip()
        mailed_object = re.search(r"把(?:目前的)?(.{1,60}?)(?:寄給|寄出|傳給)", span)
        if mailed_object:
            return f"寄出{mailed_object.group(1).strip()}", span
        task = re.sub(r"^(?:請|麻煩|please|could you)\s*", "", span, flags=re.I)
        return task.rstrip("。！？!?"), span
    imperative = re.search(
        r"^(?:submit|upload|send|review|complete|confirm|reply)\s+[^.!?\n]{2,100}",
        content,
        re.I,
    )
    if imperative:
        span = imperative.group(0).strip()
        return span.rstrip("。！？!?"), span
    if reply == "yes":
        return "回覆此訊息", content[-min(len(content), 60) :]
    return None


class RuleEngine:
    """High-precision offline baseline and pre-model signals."""

    def __init__(self, timezone: str):
        self.timezone = timezone

    def signals(self, thread: GroupedThread, rules: list[dict[str, Any]]) -> RuleSignals:
        content = combined_text(thread)
        sender = (thread.sender or "").casefold()
        signal = RuleSignals()
        for rule in rules:
            if not rule.get("enabled", True):
                continue
            pattern = str(rule["pattern"]).casefold()
            if pattern and pattern in sender:
                if rule["kind"] in {"vip_sender", "priority_sender"}:
                    signal.is_vip = True
                    signal.reason_codes.append("vip_sender")
                elif rule["kind"] == "mute_sender":
                    signal.muted = True
                    signal.reason_codes.append("muted_sender")

        signal.image_only = _match_any(IMAGE_ONLY_PATTERNS, content.strip())
        if signal.image_only:
            signal.category = "unknown"
            signal.priority = "unknown"
            signal.requires_reply = "unknown"
            signal.reason_codes.extend(["content_missing", "preview_only"])
            return signal
        if not content.strip() and str(thread.content_completeness) == "metadata_only":
            signal.category = "unknown"
            signal.priority = "unknown"
            signal.requires_reply = "unknown"
            signal.reason_codes.extend(["content_missing", "metadata_only"])
            return signal

        if _match_any(NOISE_PATTERNS, content):
            signal.category = (
                "promotion"
                if re.search(r"優惠|折扣|promotion|徽章|badge|熱門動態|trending", content, re.I)
                else "system"
            )
            signal.priority = "noise"
            signal.requires_reply = "no"
            signal.is_noise = True
            signal.reason_codes.append("high_precision_noise_rule")
            return signal
        elif _match_any(SECURITY_PATTERNS, content):
            signal.category = "security"
            signal.priority = "urgent"
            signal.reason_codes.extend(["security_alert", "explicit_risk"])
        if signal.category != "security":
            category_context = f"{thread.sender or ''}\n{content}"
            if _match_any(RESEARCH_PATTERNS, category_context):
                signal.category = "research"
                signal.reason_codes.append("research_topic")
            elif _match_any(SOCIAL_PATTERNS, content):
                signal.category = "social"
                signal.reason_codes.append("social_topic")
            elif _match_any(MEETING_PATTERNS, category_context):
                signal.category = "meeting"
                signal.reason_codes.append("meeting_topic")
            elif _match_any(TRANSACTION_PATTERNS, content):
                signal.category = "transaction"
                signal.reason_codes.append("transaction_topic")
            elif _match_any(WORK_PATTERNS, category_context):
                signal.category = "work"
                signal.reason_codes.append("work_topic")
            elif thread.source in {"line_notification", "messenger_notification"}:
                signal.category = "social"
            elif thread.source == "gmail":
                signal.category = "work"

        question = bool(re.search(r"[?？]|可以嗎|能否|請回覆|回覆我|let me know", content, re.I))
        request = _match_any(REQUEST_PATTERNS, content)
        if question or request:
            signal.requires_reply = "yes"
            signal.reason_codes.append("direct_question" if question else "explicit_request")
        if _match_any(NO_REPLY_PATTERNS, content):
            signal.requires_reply = "no"
            signal.reason_codes.append("explicit_no_reply")
        if signal.category == "security" and not question:
            # Security alerts often ask the user to act, but a no-reply sender does not
            # expect a reply.
            signal.requires_reply = "no"
        if _match_any(URGENT_PATTERNS, content):
            signal.priority = "urgent"
            signal.reason_codes.append("explicit_urgency")
        elif signal.requires_reply == "yes" or signal.is_vip:
            signal.priority = "high"
        elif _match_any(LOW_PRIORITY_PATTERNS, content):
            signal.priority = "low"
            signal.reason_codes.append("explicitly_optional")

        deadlines = extract_deadlines(content, thread.updated_at, self.timezone)
        if deadlines:
            signal.reason_codes.append("explicit_deadline")
            if (
                signal.priority in {"normal", "low"}
                and "explicit_no_reply" not in signal.reason_codes
            ):
                signal.priority = "high"
        if signal.muted:
            signal.priority = "low"
        for rule in rules:
            if rule.get("kind") == "mute_category" and rule.get("pattern") == signal.category:
                signal.muted = True
                signal.priority = "low"
                signal.reason_codes.append("muted_category")
        return signal

    def triage(self, thread: GroupedThread, signals: RuleSignals) -> TriageResult:
        content = combined_text(thread)
        deadlines = extract_deadlines(content, thread.updated_at, self.timezone)
        preview = thread.content_completeness in {"notification_preview", "metadata_only", "mixed"}
        uncertainty: list[str] = []
        if preview:
            uncertainty.append("incomplete_preview")
        if signals.image_only or not content:
            uncertainty.append("missing_context")
        if any("source_resolution_uncertain" in message.content for message in thread.messages):
            uncertainty.append("source_resolution_uncertain")

        action_items: list[ActionItem] = []
        action = None if signals.image_only else _action_span(content, signals.requires_reply)
        if action:
            action_items.append(
                ActionItem(
                    text=action[0],
                    owner=None,
                    supporting_span=action[1],
                    source_event_ids=thread.event_ids,
                    deadline_ref=0 if deadlines else None,
                )
            )

        actions = ["open_source", "snooze", "mark_done"]
        if signals.requires_reply == "yes" and thread.source == "gmail":
            actions.insert(1, "draft_reply")
        if deadlines or action_items:
            actions.insert(-1, "create_reminder")
        if preview:
            actions.append("needs_review")

        summary = _trim_summary(content)
        if signals.image_only:
            summary = "收到一則圖片／貼圖通知；預覽沒有提供內容，請開啟來源查看。"
        elif len(thread.messages) > 1:
            summary = f"{len(thread.messages)} 則同一對話訊息：{summary}"

        spans: list[str] = []
        spans.extend(item.supporting_span for item in action_items)
        spans.extend(deadline.supporting_span for deadline in deadlines)
        if not spans and content:
            spans.append(content[: min(80, len(content))])
        return TriageResult(
            summary=summary,
            category=signals.category,
            priority=signals.priority,
            requires_reply=signals.requires_reply,
            action_items=action_items,
            deadlines=deadlines,
            suggested_actions=list(dict.fromkeys(actions)),
            supporting_spans=list(dict.fromkeys(spans)),
            uncertainty_flags=list(dict.fromkeys(uncertainty)),
        )
