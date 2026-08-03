from __future__ import annotations

import argparse

from .config import load_settings
from .database import Database
from .media_store import MediaStore
from .model_gateway import build_gateway
from .pipeline import Pipeline
from .preference import PreferenceRanker
from .vision import build_vision_analyzer


def run_vision(asset_id: str) -> None:
    config = load_settings()
    database = Database(config.database_path)
    media = database.media_asset(asset_id)
    if media is None:
        raise RuntimeError("media asset does not exist")
    store = MediaStore(config.data_dir / "media")
    analyzer = build_vision_analyzer(
        config.vision_backend,
        config.ocr_model_id,
        config.ocr_model_revision,
        store,
        max_new_tokens=config.ocr_max_new_tokens,
    )
    try:
        database.save_visual_analysis(analyzer.analyze(media))
    finally:
        analyzer.release()


def run_triage(thread_ids: list[str]) -> None:
    config = load_settings()
    database = Database(config.database_path)
    store = MediaStore(config.data_dir / "media")
    gateway = build_gateway(
        config.model_backend,
        config.model_endpoint,
        config.model_id,
        media_store=store,
        revision=config.model_revision,
        quantization=config.model_quantization,
    )
    pipeline = Pipeline(
        database,
        config,
        gateway,
        preference_ranker=PreferenceRanker(database),
    )
    try:
        for thread_id in thread_ids:
            pipeline.analyze_thread(thread_id, use_model=True)
    finally:
        gateway.release()


def main() -> None:
    parser = argparse.ArgumentParser(description="Disposable local CUDA inference worker")
    subparsers = parser.add_subparsers(dest="kind", required=True)
    vision = subparsers.add_parser("vision")
    vision.add_argument("asset_id")
    triage = subparsers.add_parser("triage")
    triage.add_argument("thread_ids", nargs="+")
    args = parser.parse_args()
    if args.kind == "vision":
        run_vision(args.asset_id)
    else:
        run_triage(args.thread_ids)


if __name__ == "__main__":
    main()
