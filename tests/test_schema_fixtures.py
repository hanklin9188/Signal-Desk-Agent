from __future__ import annotations

import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).parents[1]


def test_json_examples_match_schemas():
    mapping = {
        "gmail_event.json": "unified_event.schema.json",
        "gmail_image_event.json": "unified_event.schema.json",
        "line_notification_event.json": "unified_event.schema.json",
        "messenger_notification_event.json": "unified_event.schema.json",
        "grouped_thread.json": "grouped_thread.schema.json",
        "triage_result.json": "triage_result.schema.json",
        "notification_card.json": "notification_card.schema.json",
    }
    store = {}
    for path in (ROOT / "schemas").glob("*.json"):
        schema = json.loads(path.read_text(encoding="utf-8"))
        store[path.name] = schema
    for fixture, schema_name in mapping.items():
        instance = json.loads((ROOT / "examples" / fixture).read_text(encoding="utf-8"))
        resolver = jsonschema.RefResolver.from_schema(store[schema_name], store=store)
        jsonschema.Draft202012Validator(store[schema_name], resolver=resolver).validate(instance)
