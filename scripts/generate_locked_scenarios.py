from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "benchmarks" / "locked"


def event_base(event_id: str, source: str, sender: str, content: str) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "event_id": event_id,
        "source": source,
        "source_app_id": "gmail" if source == "gmail" else source,
        "account_id": "work" if source == "gmail" else "windows",
        "sender": sender,
        "conversation_id": None,
        "title": "實驗進度" if source == "gmail" else sender,
        "content": content,
        "content_completeness": (
            "full" if source == "gmail" else "notification_preview"
        ),
        "received_at": "2026-08-02T18:00:00+08:00",
        "source_url": None,
        "raw_notification_id": None,
        "privacy_class": "sensitive" if source == "gmail" else "private",
        "metadata": {},
        "checksum": None,
    }


def write(name: str, scenario: dict[str, object]) -> None:
    (OUTPUT / f"{name}.yaml").write_text(
        yaml.safe_dump(scenario, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for existing in OUTPUT.glob("*.yaml"):
        existing.unlink()
    for index in range(100):
        gmail = event_base(
            f"locked-gmail-{index}",
            "gmail",
            f"professor{index}@example.edu",
            "請在今晚前把目前的實驗結果寄給我。",
        )
        gmail["conversation_id"] = f"locked-gmail-thread-{index}"
        write(
            f"gmail_{index:03}",
            {
                "scenario_id": f"locked-gmail-{index:03}",
                "events": [gmail],
                "expected": {
                    "priority": "high",
                    "requires_reply": "yes",
                    "display_mode": "surface_now",
                    "action_items": ["寄出實驗結果"],
                    "deadline_texts": ["今晚前"],
                    "must_include_limitations": [],
                },
                "tags": ["synthetic", "gmail", "deadline", "reply"],
            },
        )

        sender = f"實驗室群組 {index}"
        line_first = event_base(
            f"locked-line-{index}-1", "line_notification", sender, "明天會議改到三點"
        )
        line_first["raw_notification_id"] = f"locked-win-line-{index}-1"
        line_second = event_base(
            f"locked-line-{index}-2",
            "line_notification",
            sender,
            "教授也會參加，你可以嗎",
        )
        line_second["raw_notification_id"] = f"locked-win-line-{index}-2"
        line_second["received_at"] = "2026-08-02T18:00:10+08:00"
        write(
            f"line_{index:03}",
            {
                "scenario_id": f"locked-line-{index:03}",
                "events": [line_first, line_second],
                "expected": {
                    "priority": "high",
                    "requires_reply": "yes",
                    "display_mode": "surface_now",
                    "action_items": ["回覆是否能參加會議"],
                    "deadline_texts": ["明天"],
                    "must_include_limitations": ["incomplete_preview"],
                },
                "tags": ["synthetic", "line", "grouping", "reply"],
            },
        )

        messenger = event_base(
            f"locked-messenger-{index}",
            "messenger_notification",
            f"Messenger user {index}",
            "傳送了一張相片",
        )
        messenger["source_app_id"] = "Microsoft Edge"
        messenger["raw_notification_id"] = f"locked-win-messenger-{index}"
        messenger["metadata"] = {"origin": "messenger.com"}
        write(
            f"messenger_{index:03}",
            {
                "scenario_id": f"locked-messenger-{index:03}",
                "events": [messenger],
                "expected": {
                    "priority": "unknown",
                    "requires_reply": "unknown",
                    "display_mode": "store_in_inbox",
                    "action_items": [],
                    "deadline_texts": [],
                    "must_include_limitations": ["incomplete_preview"],
                },
                "tags": ["synthetic", "messenger", "preview", "image_only"],
            },
        )
    print(f"generated {len(list(OUTPUT.glob('*.yaml')))} locked scenarios in {OUTPUT}")


if __name__ == "__main__":
    main()
