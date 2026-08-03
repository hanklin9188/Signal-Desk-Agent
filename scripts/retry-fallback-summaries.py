from __future__ import annotations

import argparse
import json
import re
from dataclasses import replace
from pathlib import Path

from signaldesk.config import load_settings
from signaldesk.database import Database
from signaldesk.media_store import MediaStore
from signaldesk.model_gateway import build_gateway
from signaldesk.pipeline import Pipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Retry recent rule fallbacks without printing private message text."
    )
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=1)
    args = parser.parse_args()
    limit = max(1, min(args.limit, 50))

    config = replace(load_settings(), database_path=args.database)
    database = Database(args.database)
    with database.connect() as connection:
        rows = connection.execute(
            """
            SELECT thread_id
            FROM triage_results
            WHERE model_backend LIKE '%fallback%'
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    gateway = build_gateway(
        "transformers",
        config.model_endpoint,
        config.model_id,
        media_store=MediaStore(config.data_dir / "media"),
        revision=config.model_revision,
        quantization=config.model_quantization,
    )
    pipeline = Pipeline(database, config, gateway)
    outcomes: list[dict[str, object]] = []
    try:
        for row in rows:
            result = pipeline.analyze_thread(row["thread_id"], use_model=True)
            detail = database.card_detail(result.card_id)
            summary = str(detail["summary"])
            backend = str(detail["model_backend"])
            outcomes.append(
                {
                    "success": "fallback" not in backend,
                    "backend": backend,
                    "summary_chars": len(summary),
                    "has_cjk": bool(re.search(r"[\u3400-\u9fff]", summary)),
                }
            )
    finally:
        gateway.release()

    print(
        json.dumps(
            {
                "retried": len(outcomes),
                "outcomes": outcomes,
                "private_data": False,
            },
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
