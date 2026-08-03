from __future__ import annotations

from dataclasses import replace

import pytest

from signaldesk.config import load_settings
from signaldesk.database import Database
from signaldesk.model_gateway import build_gateway
from signaldesk.pipeline import Pipeline


@pytest.fixture
def test_config(tmp_path):
    return replace(
        load_settings(),
        database_path=tmp_path / "signaldesk-test.db",
        model_backend="rule",
        quiet_start="00:00",
        quiet_end="00:00",
    )


@pytest.fixture
def database(test_config):
    db = Database(test_config.database_path)
    db.ensure_defaults(
        {
            "shadow_mode": False,
            "focus_mode": False,
            "quiet_start": "00:00",
            "quiet_end": "00:00",
            "notification_allowlist": ["LINE", "Messenger", "Edge"],
        }
    )
    return db


@pytest.fixture
def pipeline(database, test_config):
    return Pipeline(
        database,
        test_config,
        build_gateway("rule", test_config.model_endpoint, test_config.model_id),
    )
