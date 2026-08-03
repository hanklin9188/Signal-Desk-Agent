from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from signaldesk.database import Database

CONFIRMATION = "CLEAN LEGACY GMAIL DATA"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit or clean orphan primary and personal/nycu duplicate Gmail rows."
    )
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirmation", default="")
    args = parser.parse_args()

    database = Database(args.database)
    audit = database.audit_legacy_gmail_data()
    if not args.apply:
        print(json.dumps({"mode": "audit", **audit}, ensure_ascii=False))
        return 0
    if args.confirmation != CONFIRMATION:
        raise SystemExit(f"--confirmation must equal: {CONFIRMATION}")
    if audit["mixed_threads"]:
        raise SystemExit("cleanup aborted: affected Gmail threads contain retained events")

    backup_dir = args.database.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    backup_path = backup_dir / f"signaldesk-before-gmail-cleanup-{timestamp}.db"
    with sqlite3.connect(args.database) as source, sqlite3.connect(backup_path) as target:
        source.backup(target)

    removed = database.cleanup_legacy_gmail_data()
    after = database.audit_legacy_gmail_data()
    print(
        json.dumps(
            {
                "mode": "applied",
                "backup": str(backup_path),
                "removed": removed,
                "remaining_legacy": after,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
