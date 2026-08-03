from __future__ import annotations

import base64
from datetime import UTC, datetime

import pytest

from signaldesk.media_store import MediaStore
from signaldesk.models import GroupedThread, TriageResult, VisualAnalysis
from signaldesk.rules import RuleSignals
from signaldesk.validator import TriageValidator
from signaldesk.vision import PaddleOcrVlAnalyzer, parse_spotting_output

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def test_ocr_generation_budget_is_bounded(tmp_path):
    store = MediaStore(tmp_path)

    assert PaddleOcrVlAnalyzer("ocr", None, store, max_new_tokens=1024).max_new_tokens == 512
    assert PaddleOcrVlAnalyzer("ocr", None, store, max_new_tokens=1).max_new_tokens == 128


def _thread(media):
    now = datetime(2026, 8, 3, 9, 0, tzinfo=UTC)
    return GroupedThread(
        thread_id="thread-visual",
        source="gmail",
        sender="sender@example.com",
        event_ids=["event-visual"],
        content_completeness="full",
        messages=[
            {
                "event_id": "event-visual",
                "received_at": now,
                "content": "請查看附圖",
                "media": [media],
            }
        ],
        updated_at=now,
    )


def test_paddle_spotting_json_is_normalized_and_hash_stable(tmp_path):
    media = MediaStore(tmp_path).import_bytes(PNG_1X1, declared_mime="image/png")
    raw = '[{"text":"Please submit by Aug 8","bbox":[100,200,900,400],"score":0.97}]'

    first = parse_spotting_output(raw, asset_id=media.asset_id, width=1000, height=1000)
    second = parse_spotting_output(raw, asset_id=media.asset_id, width=1000, height=1000)

    assert len(first) == 1
    assert first[0].block_id == second[0].block_id
    assert first[0].region is not None
    assert first[0].region.x == pytest.approx(0.1)
    assert first[0].region.width == pytest.approx(0.8)


def test_real_paddle_loc_token_format_produces_localized_blocks(tmp_path):
    media = MediaStore(tmp_path).import_bytes(PNG_1X1, declared_mime="image/png")
    raw = (
        "Submit review by Aug 9， 2026"
        "<|LOC_90|><|LOC_465|><|LOC_563|><|LOC_465|>"
        "<|LOC_563|><|LOC_535|><|LOC_90|><|LOC_535|>\n"
    )

    blocks = parse_spotting_output(raw, asset_id=media.asset_id, width=960, height=540)

    assert len(blocks) == 1
    assert blocks[0].text == "Submit review by Aug 9， 2026"
    assert blocks[0].region is not None
    assert blocks[0].region.x == pytest.approx(0.09)
    assert blocks[0].region.y == pytest.approx(0.465)


def test_ocr_deadline_requires_asset_block_and_localized_region(tmp_path):
    media = MediaStore(tmp_path).import_bytes(PNG_1X1, declared_mime="image/png")
    thread = _thread(media)
    now = datetime(2026, 8, 3, 9, 0, tzinfo=UTC)
    blocks = parse_spotting_output(
        '[{"text":"Please submit by Aug 8","bbox":[0,0,1,1]}]',
        asset_id=media.asset_id,
        width=1,
        height=1,
    )
    analysis = VisualAnalysis(
        asset_id=media.asset_id,
        asset_sha256=media.sha256,
        status="completed",
        ocr_model_id="PaddlePaddle/PaddleOCR-VL-1.6",
        blocks=blocks,
        raw_text=blocks[0].text,
        started_at=now,
        completed_at=now,
    )
    candidate = TriageResult(
        summary="圖片包含交件期限",
        category="work",
        priority="high",
        requires_reply="no",
        deadlines=[
            {
                "original_text": "Aug 8",
                "normalized_at": "2026-08-08T00:00:00+08:00",
                "precision": "day",
                "timezone": "Asia/Taipei",
                "explicit": True,
                "supporting_span": "Please submit by Aug 8",
                "evidence_asset_id": media.asset_id,
                "evidence_block_ids": [blocks[0].block_id],
            }
        ],
        suggested_actions=["create_reminder"],
    )

    accepted, report = TriageValidator().validate(
        candidate, thread, RuleSignals(), [analysis]
    )
    rejected, rejected_report = TriageValidator().validate(
        candidate.model_copy(
            update={
                "deadlines": [
                    candidate.deadlines[0].model_copy(
                        update={"evidence_block_ids": ["ocr_000000000000"]}
                    )
                ]
            }
        ),
        thread,
        RuleSignals(),
        [analysis],
    )

    assert report.valid is True
    assert len(accepted.deadlines) == 1
    assert rejected_report.valid is False
    assert rejected.deadlines == []


def test_database_rejects_analysis_for_a_different_asset_hash(database, pipeline, tmp_path):
    store = MediaStore(tmp_path / "media")
    media = store.import_bytes(PNG_1X1, declared_mime="image/png")
    from signaldesk.models import UnifiedEvent

    pipeline.process(
        UnifiedEvent(
            event_id="event-visual-db",
            source="gmail",
            account_id="personal",
            sender="sender@example.com",
            content="請查看附圖",
            content_completeness="full",
            received_at=datetime(2026, 8, 3, 9, 0, tzinfo=UTC),
            media=[media],
        )
    )
    assert database.unanalyzed_media() == [media]
    analysis = VisualAnalysis(
        asset_id=media.asset_id,
        asset_sha256="0" * 64,
        status="failed",
        ocr_model_id="PaddlePaddle/PaddleOCR-VL-1.6",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )

    with pytest.raises(ValueError, match="hash mismatch"):
        database.save_visual_analysis(analysis)

    blocks = parse_spotting_output(
        '[{"text":"Deadline Aug 9","bbox":[0,0,1,1]}]',
        asset_id=media.asset_id,
        width=1,
        height=1,
    )
    completed = analysis.model_copy(
        update={
            "asset_sha256": media.sha256,
            "status": "completed",
            "blocks": blocks,
            "raw_text": blocks[0].text,
            "error_code": None,
        }
    )
    database.save_visual_analysis(completed)

    assert database.visual_analysis(media.asset_id) == completed
    assert database.unanalyzed_media() == []
    thread_id = database.thread_ids_for_media(media.asset_id)[0]
    assert database.visual_analyses_for_thread(thread_id) == [completed]
