from __future__ import annotations

import re
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from .models import Deadline

CHINESE_HOUR = {
    "一": 1,
    "二": 2,
    "兩": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
    "十一": 11,
    "十二": 12,
}

PATTERNS = [
    re.compile(r"(今天|今日|今晚)(?:前|以前|之內)?"),
    re.compile(
        r"(明天|明日)(?:上午|早上|下午|晚上)?(?:[一二兩三四五六七八九十]{1,3}|\d{1,2})?[點時](?:半|\d{1,2}分)?(?:前)?"
    ),
    re.compile(r"(明天|明日)(?:前|以前|之內)?"),
    re.compile(r"(下週|下周)(?:一|二|三|四|五|六|日|天)?(?:前)?"),
    re.compile(r"\d{4}[/-]\d{1,2}[/-]\d{1,2}(?:\s+\d{1,2}:\d{2})?"),
    re.compile(r"\d{1,2}[/-]\d{1,2}(?:\s+\d{1,2}:\d{2})?(?:前)?"),
    re.compile(r"(?:before|by)\s+(?:tonight|tomorrow|\d{4}-\d{1,2}-\d{1,2})", re.I),
]


def _hour_from_text(text_value: str) -> tuple[int | None, int]:
    match = re.search(r"([一二兩三四五六七八九十]{1,3}|\d{1,2})[點時]", text_value)
    if not match:
        return None, 0
    raw = match.group(1)
    hour = int(raw) if raw.isdigit() else CHINESE_HOUR.get(raw)
    if hour is None:
        return None, 0
    if any(word in text_value for word in ("下午", "晚上")) and hour < 12:
        hour += 12
    minute = 30 if "半" in text_value else 0
    minute_match = re.search(r"[點時](\d{1,2})分", text_value)
    if minute_match:
        minute = int(minute_match.group(1))
    return hour, minute


def _normalize_deadline(text_value: str, received_at: datetime, timezone: str) -> Deadline:
    zone = ZoneInfo(timezone)
    base = received_at.astimezone(zone)
    normalized: datetime | None = None
    precision = "unknown"

    if re.search(r"今天|今日", text_value):
        normalized = datetime.combine(base.date(), time(18, 0), zone)
        precision = "day"
    elif "今晚" in text_value or re.search(r"by\s+tonight", text_value, re.I):
        normalized = datetime.combine(base.date(), time(23, 59), zone)
        precision = "day_part"
    elif re.search(r"明天|明日|tomorrow", text_value, re.I):
        target = base.date() + timedelta(days=1)
        hour, minute = _hour_from_text(text_value)
        if hour is None:
            normalized = datetime.combine(target, time(18, 0), zone)
            precision = "day"
        else:
            normalized = datetime.combine(target, time(hour, minute), zone)
            precision = "exact"
    elif re.search(r"下週|下周", text_value):
        days_until_monday = (7 - base.weekday()) or 7
        target = base.date() + timedelta(days=days_until_monday)
        day_char = re.search(r"下[週周]([一二三四五六日天])", text_value)
        if day_char:
            target += timedelta(days="一二三四五六日天".index(day_char.group(1)))
        normalized = datetime.combine(target, time(18, 0), zone)
        precision = "week"
    else:
        numeric = re.search(
            r"(?:(\d{4})[/-])?(\d{1,2})[/-](\d{1,2})(?:\s+(\d{1,2}):(\d{2}))?",
            text_value,
        )
        if numeric:
            year = int(numeric.group(1) or base.year)
            month, day = int(numeric.group(2)), int(numeric.group(3))
            hour, minute = int(numeric.group(4) or 18), int(numeric.group(5) or 0)
            try:
                normalized = datetime(year, month, day, hour, minute, tzinfo=zone)
                precision = "minute" if numeric.group(4) else "day"
            except ValueError:
                normalized = None
                precision = "unknown"

    return Deadline(
        original_text=text_value,
        normalized_at=normalized,
        precision=precision,
        timezone=timezone,
        explicit=True,
        supporting_span=text_value,
    )


def extract_deadlines(content: str, received_at: datetime, timezone: str) -> list[Deadline]:
    found: list[tuple[int, str]] = []
    for pattern in PATTERNS:
        for match in pattern.finditer(content):
            value = match.group(0).strip()
            if value and all(value not in prior for _, prior in found):
                found.append((match.start(), value))
    found.sort(key=lambda item: item[0])
    return [_normalize_deadline(value, received_at, timezone) for _, value in found[:3]]
