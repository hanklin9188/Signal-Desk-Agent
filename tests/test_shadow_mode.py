from __future__ import annotations

from datetime import UTC, datetime

from signaldesk.shadow_mode import report, start


def test_shadow_mode_cannot_pass_without_real_elapsed_time_and_samples(database):
    started = start(database)
    result = report(database, now=datetime.now(UTC))

    assert started == database.settings()["shadow_evaluation_started_at"]
    assert database.settings()["shadow_mode"] is True
    assert result["release_eligible"] is False
    assert result["gates"]["minimum_elapsed_days"] is False
    assert result["total_decisions"] == 0
    assert result["contains_message_content"] is False
