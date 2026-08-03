from __future__ import annotations

from datetime import UTC, datetime

from signaldesk.model_gateway import SYSTEM_CONTRACT, TransformersGateway, compile_prompt
from signaldesk.models import GroupedMessage, GroupedThread
from signaldesk.rules import RuleSignals


def _thread() -> GroupedThread:
    now = datetime.now(UTC)
    return GroupedThread(
        thread_id="thread-summary-contract",
        source="gmail",
        conversation_id="conversation-summary-contract",
        sender="教授 <professor@example.test>",
        event_ids=["event-summary-contract"],
        content_completeness="full",
        messages=[
            GroupedMessage(
                event_id="event-summary-contract",
                received_at=now,
                sender="教授 <professor@example.test>",
                content="請在週五前回覆是否參加會議。",
            )
        ],
        updated_at=now,
    )


def test_prompt_demands_clear_traditional_chinese_summary() -> None:
    prompt = compile_prompt(_thread(), RuleSignals())

    assert "Traditional Chinese (Taiwan)" in SYSTEM_CONTRACT
    assert "useful conclusion first" in prompt
    assert "notification boilerplate" in prompt
    assert "one clear zh-TW sentence" in prompt
    assert "deterministic evidence engine supplies those fields" in prompt


def test_repair_pass_preserves_context_and_demands_complete_json() -> None:
    messages = [
        {"role": "system", "content": SYSTEM_CONTRACT},
        {"role": "user", "content": "INPUT={}"},
    ]

    repaired = TransformersGateway._repair_messages(messages, '{"summary":"未完成')

    assert repaired[:2] == messages
    assert repaired[2]["role"] == "assistant"
    assert repaired[3]["role"] == "user"
    assert "one complete JSON object" in repaired[3]["content"]
    assert "Traditional Chinese" in repaired[3]["content"]
