from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .models import (
    AgentDecision,
    GroupedThread,
    NotificationCard,
    TriageResult,
    UnifiedEvent,
)
from .normalizer import (
    MESSENGER_GENERIC_TITLES,
    line_identity_from_title,
    messenger_sender_from_preview,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime | None = None) -> str:
    return (value or utc_now()).isoformat()


def _json(value: Any) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


class Database:
    """Small SQLite repository with explicit transactions and no global connection."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._migration_lock = threading.Lock()
        self.migrate()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def migrate(self) -> None:
        with self._migration_lock, self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS raw_events (
                    event_id TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    source TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS normalized_events (
                    event_id TEXT PRIMARY KEY REFERENCES raw_events(event_id) ON DELETE CASCADE,
                    source TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    conversation_id TEXT,
                    title TEXT,
                    content TEXT NOT NULL,
                    content_completeness TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    source_url TEXT,
                    data_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_events_received
                    ON normalized_events(received_at DESC);

                CREATE TABLE IF NOT EXISTS threads (
                    thread_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    conversation_id TEXT,
                    sender TEXT,
                    title TEXT,
                    content_completeness TEXT NOT NULL,
                    verified_memory TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_threads_grouping
                    ON threads(source, account_id, sender, updated_at DESC);

                CREATE TABLE IF NOT EXISTS thread_events (
                    thread_id TEXT NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
                    event_id TEXT NOT NULL UNIQUE
                        REFERENCES normalized_events(event_id) ON DELETE CASCADE,
                    received_at TEXT NOT NULL,
                    PRIMARY KEY(thread_id, event_id)
                );

                CREATE TABLE IF NOT EXISTS triage_results (
                    thread_id TEXT PRIMARY KEY REFERENCES threads(thread_id) ON DELETE CASCADE,
                    result_json TEXT NOT NULL,
                    validation_json TEXT NOT NULL,
                    decision_json TEXT NOT NULL,
                    model_backend TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS notification_cards (
                    card_id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL UNIQUE REFERENCES threads(thread_id) ON DELETE CASCADE,
                    source TEXT NOT NULL,
                    sender TEXT,
                    title TEXT,
                    summary TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    category TEXT NOT NULL,
                    requires_reply TEXT NOT NULL,
                    deadline_text TEXT,
                    display_mode TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    snoozed_until TEXT,
                    card_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_cards_status_updated
                    ON notification_cards(status, updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_cards_priority
                    ON notification_cards(priority, updated_at DESC);

                CREATE TABLE IF NOT EXISTS action_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
                    item_index INTEGER NOT NULL,
                    data_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    UNIQUE(thread_id, item_index)
                );

                CREATE TABLE IF NOT EXISTS deadlines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
                    deadline_index INTEGER NOT NULL,
                    original_text TEXT NOT NULL,
                    normalized_at TEXT,
                    data_json TEXT NOT NULL,
                    UNIQUE(thread_id, deadline_index)
                );

                CREATE TABLE IF NOT EXISTS feedback_events (
                    feedback_id TEXT PRIMARY KEY,
                    card_id TEXT NOT NULL REFERENCES notification_cards(card_id) ON DELETE CASCADE,
                    action TEXT NOT NULL,
                    value_json TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS preference_observations (
                    observation_id TEXT PRIMARY KEY,
                    features_json TEXT NOT NULL,
                    label REAL NOT NULL,
                    action TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS preference_weights (
                    feature TEXT PRIMARY KEY,
                    weight REAL NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS reminders (
                    reminder_id TEXT PRIMARY KEY,
                    card_id TEXT NOT NULL REFERENCES notification_cards(card_id) ON DELETE CASCADE,
                    remind_at TEXT NOT NULL,
                    note TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS interruptions (
                    interruption_id TEXT PRIMARY KEY,
                    card_id TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_interruptions_created
                    ON interruptions(created_at DESC);

                CREATE TABLE IF NOT EXISTS reply_drafts (
                    draft_id TEXT PRIMARY KEY,
                    card_id TEXT NOT NULL REFERENCES notification_cards(card_id) ON DELETE CASCADE,
                    recipient TEXT,
                    subject TEXT,
                    body TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'local',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS traces (
                    trace_id TEXT PRIMARY KEY,
                    event_id TEXT,
                    thread_id TEXT,
                    stage TEXT NOT NULL,
                    status TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_traces_thread
                    ON traces(thread_id, created_at DESC);

                CREATE TABLE IF NOT EXISTS connector_health (
                    connector_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    status TEXT NOT NULL,
                    detail TEXT,
                    capabilities_json TEXT NOT NULL,
                    last_sync_at TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS connector_cursors (
                    connector_id TEXT PRIMARY KEY,
                    cursor TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS connector_accounts (
                    connector_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(source, account_id)
                );

                CREATE TABLE IF NOT EXISTS quarantine (
                    quarantine_id TEXT PRIMARY KEY,
                    connector_id TEXT,
                    reason TEXT NOT NULL,
                    payload_checksum TEXT NOT NULL,
                    safe_metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS user_rules (
                    rule_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    pattern TEXT NOT NULL,
                    value TEXT,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                INSERT OR IGNORE INTO schema_migrations(version, applied_at)
                VALUES(1, datetime('now'));
                """
            )

    def ensure_defaults(self, defaults: dict[str, Any]) -> None:
        with self.transaction() as connection:
            for key, value in defaults.items():
                connection.execute(
                    "INSERT OR IGNORE INTO settings(key, value_json, updated_at) VALUES(?, ?, ?)",
                    (key, _json(value), _iso()),
                )

    def settings(self) -> dict[str, Any]:
        with self.connect() as connection:
            rows = connection.execute("SELECT key, value_json FROM settings").fetchall()
        return {row["key"]: json.loads(row["value_json"]) for row in rows}

    def update_settings(self, values: dict[str, Any]) -> dict[str, Any]:
        with self.transaction() as connection:
            for key, value in values.items():
                connection.execute(
                    """
                    INSERT INTO settings(key, value_json, updated_at) VALUES(?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json,
                        updated_at=excluded.updated_at
                    """,
                    (key, _json(value), _iso()),
                )
        return self.settings()

    def insert_event(
        self, event: UnifiedEvent, *, idempotency_key: str, checksum: str, raw: dict[str, Any]
    ) -> bool:
        now = _iso()
        with self.transaction() as connection:
            existing = connection.execute(
                "SELECT event_id FROM raw_events WHERE idempotency_key=? OR event_id=?",
                (idempotency_key, event.event_id),
            ).fetchone()
            if existing:
                return False
            connection.execute(
                """
                INSERT INTO raw_events(
                    event_id, idempotency_key, source, account_id,
                    payload_json, checksum, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    idempotency_key,
                    event.source,
                    event.account_id,
                    _json(raw),
                    checksum,
                    now,
                ),
            )
            connection.execute(
                """
                INSERT INTO normalized_events(
                    event_id, source, account_id, sender, conversation_id, title, content,
                    content_completeness, received_at, source_url, data_json, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.source,
                    event.account_id,
                    event.sender,
                    event.conversation_id,
                    event.title,
                    event.content,
                    event.content_completeness,
                    event.received_at.isoformat(),
                    event.source_url,
                    _json(event),
                    now,
                ),
            )
        return True

    def existing_event_ids(self, event_ids: list[str]) -> set[str]:
        """Resolve deterministic archive duplicates in bounded SQLite batches."""
        if not event_ids:
            return set()
        existing: set[str] = set()
        with self.connect() as connection:
            for start in range(0, len(event_ids), 900):
                batch = event_ids[start : start + 900]
                placeholders = ",".join("?" for _ in batch)
                rows = connection.execute(
                    f"SELECT event_id FROM normalized_events WHERE event_id IN ({placeholders})",
                    batch,
                ).fetchall()
                existing.update(row["event_id"] for row in rows)
        return existing

    def event(self, event_id: str) -> UnifiedEvent | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT data_json FROM normalized_events WHERE event_id=?", (event_id,)
            ).fetchone()
        return UnifiedEvent.model_validate_json(row["data_json"]) if row else None

    def card_for_event(self, event_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT c.card_id, c.thread_id FROM notification_cards c
                JOIN thread_events te ON te.thread_id=c.thread_id
                WHERE te.event_id=?
                """,
                (event_id,),
            ).fetchone()
        return dict(row) if row else None

    def similar_chat_event(
        self, event: UnifiedEvent, *, window_seconds: int = 300
    ) -> dict[str, Any] | None:
        """Reconcile an archive row with its matching toast without merging normal repeats."""
        if event.source not in {"line_notification", "messenger_notification"}:
            return None
        if not event.conversation_id or not event.content:
            return None
        replay_capture = event.metadata.get("capture_reason") in {
            "startup_reconcile",
            "event_reconcile",
            "poll",
        }
        # LINE can republish the same notification-center item under several native
        # IDs. Its previews do not expose a durable message ID, so identical content
        # for the same visible user is treated as one item for twelve hours.
        line_snapshot = event.source == "line_notification"
        comparison_window = (
            86400 * 7 if replay_capture else 43200 if line_snapshot else window_seconds
        )
        cutoff = (event.received_at - timedelta(seconds=comparison_window)).isoformat()
        ceiling = (event.received_at + timedelta(seconds=comparison_window)).isoformat()
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT e.event_id, e.data_json, te.thread_id, c.card_id
                FROM normalized_events e
                JOIN thread_events te ON te.event_id=e.event_id
                LEFT JOIN notification_cards c ON c.thread_id=te.thread_id
                WHERE e.source=? AND e.account_id=? AND e.content=?
                  AND lower(COALESCE(e.conversation_id, e.title, ''))=lower(?)
                  AND e.received_at BETWEEN ? AND ?
                ORDER BY e.received_at DESC LIMIT 8
                """,
                (
                    event.source,
                    event.account_id,
                    event.content,
                    event.conversation_id,
                    cutoff,
                    ceiling,
                ),
            ).fetchall()
        incoming_archive = bool(event.metadata.get("archive_import"))
        for row in rows:
            existing = UnifiedEvent.model_validate_json(row["data_json"])
            if (replay_capture or line_snapshot) and (
                existing.metadata.get("native_app_id") == event.metadata.get("native_app_id")
            ):
                return {
                    "event_id": row["event_id"],
                    "thread_id": row["thread_id"],
                    "card_id": row["card_id"],
                }
            if bool(existing.metadata.get("archive_import")) != incoming_archive:
                return {
                    "event_id": row["event_id"],
                    "thread_id": row["thread_id"],
                    "card_id": row["card_id"],
                }
        return None

    def candidate_thread(self, event: UnifiedEvent, window_seconds: int) -> str | None:
        if event.source == "gmail" and event.conversation_id:
            thread_id = f"gmail:{event.account_id}:{event.conversation_id}"
            with self.connect() as connection:
                row = connection.execute(
                    "SELECT thread_id FROM threads WHERE thread_id=?", (thread_id,)
                ).fetchone()
            return thread_id if row else None

        if (
            event.source in {"line_notification", "messenger_notification"}
            and event.conversation_id
        ):
            with self.connect() as connection:
                row = connection.execute(
                    """
                    SELECT thread_id FROM threads
                    WHERE source=? AND account_id=?
                      AND lower(COALESCE(conversation_id, title, ''))=lower(?)
                    ORDER BY updated_at DESC LIMIT 1
                    """,
                    (event.source, event.account_id, event.conversation_id),
                ).fetchone()
            if row:
                return row["thread_id"]

        cutoff = (event.received_at - timedelta(seconds=window_seconds)).isoformat()
        ceiling = (event.received_at + timedelta(seconds=window_seconds)).isoformat()
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT t.thread_id
                FROM threads t
                WHERE t.source=? AND t.account_id=? AND lower(COALESCE(t.sender, ''))=lower(?)
                  AND t.updated_at BETWEEN ? AND ?
                  AND NOT EXISTS (
                    SELECT 1 FROM thread_events te
                    WHERE te.thread_id=t.thread_id
                    GROUP BY te.thread_id HAVING COUNT(*) >= 12
                  )
                ORDER BY t.updated_at DESC LIMIT 1
                """,
                (event.source, event.account_id, event.sender, cutoff, ceiling),
            ).fetchone()
        return row["thread_id"] if row else None

    def attach_event(self, thread_id: str, event: UnifiedEvent) -> None:
        now = _iso(event.received_at)
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT content_completeness, updated_at FROM threads WHERE thread_id=?",
                (thread_id,),
            ).fetchone()
            if row:
                completeness = row["content_completeness"]
                if completeness != event.content_completeness:
                    completeness = "mixed"
                updated_at = max(row["updated_at"], now)
                connection.execute(
                    """
                    UPDATE threads SET content_completeness=?, title=COALESCE(title, ?),
                        updated_at=? WHERE thread_id=?
                    """,
                    (completeness, event.title, updated_at, thread_id),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO threads(
                        thread_id, source, account_id, conversation_id, sender, title,
                        content_completeness, created_at, updated_at
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        thread_id,
                        event.source,
                        event.account_id,
                        event.conversation_id,
                        event.sender,
                        event.title,
                        event.content_completeness,
                        now,
                        now,
                    ),
                )
            connection.execute(
                "INSERT INTO thread_events(thread_id, event_id, received_at) VALUES(?, ?, ?)",
                (thread_id, event.event_id, event.received_at.isoformat()),
            )

    def grouped_thread(self, thread_id: str, *, limit: int | None = None) -> GroupedThread | None:
        with self.connect() as connection:
            thread = connection.execute(
                "SELECT * FROM threads WHERE thread_id=?", (thread_id,)
            ).fetchone()
            if not thread:
                return None
            if limit is None:
                events = connection.execute(
                    """
                    SELECT e.data_json FROM thread_events te
                    JOIN normalized_events e ON e.event_id=te.event_id
                    WHERE te.thread_id=? ORDER BY te.received_at ASC, te.event_id ASC
                    """,
                    (thread_id,),
                ).fetchall()
            else:
                events = connection.execute(
                    """
                    SELECT recent.data_json FROM (
                        SELECT e.data_json, te.received_at, te.event_id
                        FROM thread_events te
                        JOIN normalized_events e ON e.event_id=te.event_id
                        WHERE te.thread_id=?
                        ORDER BY te.received_at DESC, te.event_id DESC LIMIT ?
                    ) AS recent
                    ORDER BY recent.received_at ASC, recent.event_id ASC
                    """,
                    (thread_id, max(1, limit)),
                ).fetchall()
        parsed = [UnifiedEvent.model_validate_json(row["data_json"]) for row in events]
        return GroupedThread(
            thread_id=thread_id,
            source=thread["source"],
            conversation_id=thread["conversation_id"],
            sender=thread["sender"],
            event_ids=[event.event_id for event in parsed],
            content_completeness=thread["content_completeness"],
            messages=[
                {
                    "event_id": event.event_id,
                    "received_at": event.received_at,
                    "sender": event.sender,
                    "content": event.content,
                }
                for event in parsed
            ],
            verified_memory=thread["verified_memory"],
            updated_at=datetime.fromisoformat(thread["updated_at"]),
        )

    def save_analysis(
        self,
        *,
        thread: GroupedThread,
        triage: TriageResult,
        validation: dict[str, Any],
        decision: AgentDecision,
        card: NotificationCard,
        model_backend: str,
    ) -> None:
        now = _iso()
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO triage_results(
                    thread_id, result_json, validation_json, decision_json, model_backend,
                    created_at, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(thread_id) DO UPDATE SET result_json=excluded.result_json,
                    validation_json=excluded.validation_json,
                    decision_json=excluded.decision_json,
                    model_backend=excluded.model_backend, updated_at=excluded.updated_at
                """,
                (
                    thread.thread_id,
                    _json(triage),
                    _json(validation),
                    _json(decision),
                    model_backend,
                    now,
                    now,
                ),
            )
            connection.execute(
                """
                INSERT INTO notification_cards(
                    card_id, thread_id, source, sender, title, summary, priority, category,
                    requires_reply, deadline_text, display_mode, status, snoozed_until,
                    card_json, created_at, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(thread_id) DO UPDATE SET sender=excluded.sender,
                    title=excluded.title, summary=excluded.summary, priority=excluded.priority,
                    category=excluded.category, requires_reply=excluded.requires_reply,
                    deadline_text=excluded.deadline_text, display_mode=excluded.display_mode,
                    card_json=excluded.card_json, updated_at=excluded.updated_at
                """,
                (
                    card.card_id,
                    card.thread_id,
                    card.source,
                    card.sender,
                    card.title,
                    card.summary,
                    card.priority,
                    card.category,
                    card.requires_reply,
                    card.deadline_text,
                    card.display_mode,
                    card.status,
                    card.snoozed_until.isoformat() if card.snoozed_until else None,
                    _json(card),
                    card.created_at.isoformat(),
                    card.updated_at.isoformat(),
                ),
            )
            connection.execute("DELETE FROM action_items WHERE thread_id=?", (thread.thread_id,))
            for index, item in enumerate(triage.action_items):
                connection.execute(
                    """
                    INSERT INTO action_items(thread_id, item_index, data_json, status)
                    VALUES(?, ?, ?, ?)
                    """,
                    (thread.thread_id, index, _json(item), item.status),
                )
            connection.execute("DELETE FROM deadlines WHERE thread_id=?", (thread.thread_id,))
            for index, deadline in enumerate(triage.deadlines):
                connection.execute(
                    """
                    INSERT INTO deadlines(
                        thread_id, deadline_index, original_text, normalized_at, data_json
                    ) VALUES(?, ?, ?, ?, ?)
                    """,
                    (
                        thread.thread_id,
                        index,
                        deadline.original_text,
                        deadline.normalized_at.isoformat() if deadline.normalized_at else None,
                        _json(deadline),
                    ),
                )

    def list_cards(
        self,
        *,
        view: str = "now",
        search: str = "",
        source: str | None = None,
        priority: str | None = None,
        date_filter: str | None = None,
        timezone: str = "Asia/Taipei",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        conditions: list[str] = ["c.display_mode!='hidden'"]
        parameters: list[Any] = []
        now = _iso()
        local_start = datetime.now(ZoneInfo(timezone)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        local_end = local_start + timedelta(days=1)
        day_start = local_start.astimezone(UTC).isoformat()
        day_end = local_end.astimezone(UTC).isoformat()
        if view == "done":
            conditions.append("c.status='done'")
        elif view == "reply":
            conditions.extend(["c.status='open'", "c.requires_reply='yes'"])
        elif view == "digest":
            conditions.extend(["c.status='open'", "c.display_mode IN ('digest','inbox','review')"])
        elif view == "today":
            conditions.extend(
                [
                    "c.status='open'",
                    "((julianday(d.normalized_at)>=julianday(?) "
                    "AND julianday(d.normalized_at)<julianday(?)) "
                    "OR (julianday(c.updated_at)>=julianday(?) "
                    "AND julianday(c.updated_at)<julianday(?)))",
                ]
            )
            parameters.extend([day_start, day_end, day_start, day_end])
        else:
            conditions.append("c.status='open'")
            conditions.append("(c.snoozed_until IS NULL OR c.snoozed_until<=?)")
            parameters.append(now)
        if search:
            conditions.append(
                "(c.summary LIKE ? OR c.sender LIKE ? OR c.title LIKE ? OR EXISTS ("
                "SELECT 1 FROM thread_events search_te "
                "JOIN normalized_events search_e ON search_e.event_id=search_te.event_id "
                "WHERE search_te.thread_id=c.thread_id AND search_e.content LIKE ?))"
            )
            term = f"%{search}%"
            parameters.extend([term, term, term, term])
        if source:
            conditions.append("c.source=?")
            parameters.append(source)
        if priority:
            conditions.append("c.priority=?")
            parameters.append(priority)
        if date_filter == "today":
            conditions.append(
                "julianday(c.updated_at)>=julianday(?) "
                "AND julianday(c.updated_at)<julianday(?)"
            )
            parameters.extend([day_start, day_end])
        elif date_filter in {"7d", "30d"}:
            days = 7 if date_filter == "7d" else 30
            conditions.append("c.updated_at>=datetime('now', ?)")
            parameters.append(f"-{days} days")
        where = " AND ".join(conditions) if conditions else "1=1"
        parameters.append(min(limit, 500))
        order_by = (
            "c.updated_at DESC"
            if view == "latest"
            else """CASE c.priority
                    WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2
                    WHEN 'unknown' THEN 3 WHEN 'low' THEN 4 ELSE 5 END,
                    c.updated_at DESC"""
        )
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT c.*, d.normalized_at AS deadline_at,
                    (SELECT COUNT(*) FROM action_items ai WHERE ai.thread_id=c.thread_id
                        AND ai.status='open') AS action_count
                FROM notification_cards c
                LEFT JOIN deadlines d ON d.thread_id=c.thread_id AND d.deadline_index=0
                WHERE {where}
                ORDER BY {order_by}
                LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [self._card_row(row) for row in rows]

    @staticmethod
    def _card_row(row: sqlite3.Row) -> dict[str, Any]:
        card = json.loads(row["card_json"])
        card.update(
            {
                "status": row["status"],
                "snoozed_until": row["snoozed_until"],
                "updated_at": row["updated_at"],
            }
        )
        if "deadline_at" in row.keys():
            card["deadline_at"] = row["deadline_at"]
            card["action_count"] = row["action_count"]
        return card

    def card_detail(self, card_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            card = connection.execute(
                "SELECT * FROM notification_cards WHERE card_id=?", (card_id,)
            ).fetchone()
            if not card:
                return None
            thread_id = card["thread_id"]
            events = connection.execute(
                """
                SELECT e.data_json FROM thread_events te
                JOIN normalized_events e ON e.event_id=te.event_id
                WHERE te.thread_id=? ORDER BY te.received_at
                """,
                (thread_id,),
            ).fetchall()
            triage = connection.execute(
                "SELECT * FROM triage_results WHERE thread_id=?", (thread_id,)
            ).fetchone()
            action_items = connection.execute(
                "SELECT data_json FROM action_items WHERE thread_id=? ORDER BY item_index",
                (thread_id,),
            ).fetchall()
            deadlines = connection.execute(
                "SELECT data_json FROM deadlines WHERE thread_id=? ORDER BY deadline_index",
                (thread_id,),
            ).fetchall()
            reminders = connection.execute(
                "SELECT * FROM reminders WHERE card_id=? ORDER BY remind_at", (card_id,)
            ).fetchall()
            drafts = connection.execute(
                "SELECT * FROM reply_drafts WHERE card_id=? ORDER BY created_at DESC", (card_id,)
            ).fetchall()
            traces = connection.execute(
                "SELECT * FROM traces WHERE thread_id=? ORDER BY created_at DESC LIMIT 30",
                (thread_id,),
            ).fetchall()
        result = self._card_row(card)
        result["events"] = [json.loads(row["data_json"]) for row in events]
        result["triage"] = json.loads(triage["result_json"]) if triage else None
        result["validation"] = json.loads(triage["validation_json"]) if triage else None
        result["decision"] = json.loads(triage["decision_json"]) if triage else None
        result["model_backend"] = triage["model_backend"] if triage else None
        result["action_items"] = [json.loads(row["data_json"]) for row in action_items]
        result["deadlines"] = [json.loads(row["data_json"]) for row in deadlines]
        result["reminders"] = [dict(row) for row in reminders]
        result["drafts"] = [dict(row) for row in drafts]
        result["traces"] = [
            {**dict(row), "details": json.loads(row["details_json"])} for row in traces
        ]
        return result

    def update_card_status(
        self, card_id: str, status: str, *, snoozed_until: datetime | None = None
    ) -> bool:
        with self.transaction() as connection:
            result = connection.execute(
                """
                UPDATE notification_cards SET status=?, snoozed_until=?, updated_at=?
                WHERE card_id=?
                """,
                (status, snoozed_until.isoformat() if snoozed_until else None, _iso(), card_id),
            )
        return result.rowcount == 1

    def create_feedback(self, feedback_id: str, card_id: str, action: str, value: Any) -> None:
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO feedback_events(feedback_id, card_id, action, value_json, created_at)
                VALUES(?, ?, ?, ?, ?)
                """,
                (feedback_id, card_id, action, _json(value), _iso()),
            )

    def add_preference_observation(
        self,
        observation_id: str,
        features: dict[str, float],
        label: float,
        action: str,
    ) -> None:
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO preference_observations(
                    observation_id, features_json, label, action, created_at
                ) VALUES(?, ?, ?, ?, ?)
                """,
                (observation_id, _json(features), label, action, _iso()),
            )

    def preference_observations(self, limit: int = 500) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT features_json, label, action, created_at
                FROM preference_observations ORDER BY created_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "features": json.loads(row["features_json"]),
                "label": float(row["label"]),
                "action": row["action"],
                "created_at": row["created_at"],
            }
            for row in reversed(rows)
        ]

    def preference_weights(self) -> dict[str, float]:
        with self.connect() as connection:
            rows = connection.execute("SELECT feature, weight FROM preference_weights").fetchall()
        return {row["feature"]: float(row["weight"]) for row in rows}

    def save_preference_weights(self, weights: dict[str, float]) -> None:
        with self.transaction() as connection:
            connection.execute("DELETE FROM preference_weights")
            connection.executemany(
                "INSERT INTO preference_weights(feature, weight, updated_at) VALUES(?, ?, ?)",
                [(feature, weight, _iso()) for feature, weight in weights.items()],
            )

    def reset_preferences(self) -> None:
        with self.transaction() as connection:
            connection.execute("DELETE FROM preference_observations")
            connection.execute("DELETE FROM preference_weights")

    def create_reminder(
        self, reminder_id: str, card_id: str, remind_at: datetime, note: str | None
    ) -> None:
        now = _iso()
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO reminders(
                    reminder_id, card_id, remind_at, note, status, created_at, updated_at
                ) VALUES(?, ?, ?, ?, 'pending', ?, ?)
                """,
                (reminder_id, card_id, remind_at.isoformat(), note, now, now),
            )

    def create_draft(
        self,
        draft_id: str,
        card_id: str,
        recipient: str | None,
        subject: str | None,
        body: str,
    ) -> None:
        now = _iso()
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO reply_drafts(
                    draft_id, card_id, recipient, subject, body, status, created_at, updated_at
                ) VALUES(?, ?, ?, ?, ?, 'local', ?, ?)
                """,
                (draft_id, card_id, recipient, subject, body, now, now),
            )

    def draft_detail(self, draft_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT d.*, c.source, t.account_id, t.conversation_id
                FROM reply_drafts d
                JOIN notification_cards c ON c.card_id=d.card_id
                JOIN threads t ON t.thread_id=c.thread_id
                WHERE d.draft_id=?
                """,
                (draft_id,),
            ).fetchone()
        return dict(row) if row else None

    def update_draft_status(self, draft_id: str, status: str) -> bool:
        with self.transaction() as connection:
            result = connection.execute(
                "UPDATE reply_drafts SET status=?, updated_at=? WHERE draft_id=?",
                (status, _iso(), draft_id),
            )
        return result.rowcount == 1

    def fire_due_reminders(self) -> list[dict[str, Any]]:
        now = _iso()
        with self.transaction() as connection:
            rows = connection.execute(
                """
                SELECT r.reminder_id, r.card_id, r.remind_at, r.note,
                    c.summary, c.sender
                FROM reminders r
                JOIN notification_cards c ON c.card_id=r.card_id
                WHERE r.status='pending' AND r.remind_at<=?
                ORDER BY r.remind_at
                """,
                (now,),
            ).fetchall()
            if rows:
                connection.executemany(
                    "UPDATE reminders SET status='fired', updated_at=? WHERE reminder_id=?",
                    [(now, row["reminder_id"]) for row in rows],
                )
        return [dict(row) for row in rows]

    def interruption_count_since(self, since: datetime) -> int:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM interruptions WHERE created_at>=?",
                (since.isoformat(),),
            ).fetchone()
        return int(row["total"] or 0)

    def record_interruption(self, card_id: str) -> None:
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO interruptions(interruption_id, card_id, created_at)
                VALUES(?, ?, ?)
                """,
                (f"interrupt_{card_id}", card_id, _iso()),
            )

    def add_rule(self, rule_id: str, kind: str, pattern: str, value: str | None) -> None:
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO user_rules(rule_id, kind, pattern, value, created_at)
                VALUES(?, ?, ?, ?, ?)
                """,
                (rule_id, kind, pattern, value, _iso()),
            )

    def rules(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM user_rules ORDER BY created_at DESC"
            ).fetchall()
        return [{**dict(row), "enabled": bool(row["enabled"])} for row in rows]

    def delete_rule(self, rule_id: str) -> bool:
        with self.transaction() as connection:
            result = connection.execute("DELETE FROM user_rules WHERE rule_id=?", (rule_id,))
        return result.rowcount == 1

    def trace_start(
        self, trace_id: str, event_id: str | None, stage: str, details: dict[str, Any]
    ) -> None:
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO traces(trace_id, event_id, stage, status, details_json, created_at)
                VALUES(?, ?, ?, 'running', ?, ?)
                """,
                (trace_id, event_id, stage, _json(details), _iso()),
            )

    def trace_complete(
        self,
        trace_id: str,
        *,
        thread_id: str | None,
        status: str,
        stage: str,
        details: dict[str, Any],
    ) -> None:
        with self.transaction() as connection:
            connection.execute(
                """
                UPDATE traces SET thread_id=?, status=?, stage=?, details_json=?, completed_at=?
                WHERE trace_id=?
                """,
                (thread_id, status, stage, _json(details), _iso(), trace_id),
            )

    def set_connector_health(
        self,
        connector_id: str,
        source: str,
        status: str,
        detail: str,
        capabilities: list[str],
        *,
        synced: bool = False,
    ) -> None:
        now = _iso()
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO connector_health(
                    connector_id, source, status, detail,
                    capabilities_json, last_sync_at, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(connector_id) DO UPDATE SET status=excluded.status,
                    detail=excluded.detail, capabilities_json=excluded.capabilities_json,
                    last_sync_at=COALESCE(excluded.last_sync_at, connector_health.last_sync_at),
                    updated_at=excluded.updated_at
                """,
                (
                    connector_id,
                    source,
                    status,
                    detail,
                    _json(capabilities),
                    now if synced else None,
                    now,
                ),
            )

    def connectors(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM connector_health ORDER BY connector_id"
            ).fetchall()
        return [{**dict(row), "capabilities": json.loads(row["capabilities_json"])} for row in rows]

    def connector_cursor(self, connector_id: str) -> str | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT cursor FROM connector_cursors WHERE connector_id=?", (connector_id,)
            ).fetchone()
        return row["cursor"] if row else None

    def set_connector_cursor(self, connector_id: str, cursor: str | None) -> None:
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO connector_cursors(connector_id, cursor, updated_at) VALUES(?, ?, ?)
                ON CONFLICT(connector_id) DO UPDATE SET cursor=excluded.cursor,
                    updated_at=excluded.updated_at
                """,
                (connector_id, cursor, _iso()),
            )

    def upsert_connector_account(
        self, connector_id: str, source: str, account_id: str, config: dict[str, Any]
    ) -> None:
        now = _iso()
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO connector_accounts(
                    connector_id, source, account_id, config_json, created_at, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?)
                ON CONFLICT(connector_id) DO UPDATE SET config_json=excluded.config_json,
                    updated_at=excluded.updated_at
                """,
                (connector_id, source, account_id, _json(config), now, now),
            )

    def connector_accounts(self, source: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM connector_accounts"
        parameters: tuple[Any, ...] = ()
        if source:
            query += " WHERE source=?"
            parameters = (source,)
        query += " ORDER BY created_at"
        with self.connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [{**dict(row), "config": json.loads(row["config_json"])} for row in rows]

    def delete_connector_account(self, connector_id: str) -> bool:
        with self.transaction() as connection:
            connection.execute(
                "DELETE FROM connector_cursors WHERE connector_id=?", (connector_id,)
            )
            connection.execute("DELETE FROM connector_health WHERE connector_id=?", (connector_id,))
            result = connection.execute(
                "DELETE FROM connector_accounts WHERE connector_id=?", (connector_id,)
            )
        return result.rowcount == 1

    def delete_source_account_data(self, source: str, account_id: str) -> dict[str, int]:
        """Delete only data belonging to one explicitly selected connector account."""
        connector_id = f"{source}:{account_id}"
        with self.transaction() as connection:
            event_count = int(
                connection.execute(
                    "SELECT COUNT(*) AS count FROM normalized_events "
                    "WHERE source=? AND account_id=?",
                    (source, account_id),
                ).fetchone()["count"]
            )
            thread_count = int(
                connection.execute(
                    "SELECT COUNT(*) AS count FROM threads WHERE source=? AND account_id=?",
                    (source, account_id),
                ).fetchone()["count"]
            )
            connection.execute(
                """
                DELETE FROM interruptions
                WHERE card_id IN (
                    SELECT c.card_id FROM notification_cards c
                    JOIN threads t ON t.thread_id=c.thread_id
                    WHERE t.source=? AND t.account_id=?
                )
                """,
                (source, account_id),
            )
            connection.execute(
                """
                DELETE FROM traces
                WHERE event_id IN (
                    SELECT event_id FROM normalized_events WHERE source=? AND account_id=?
                ) OR thread_id IN (
                    SELECT thread_id FROM threads WHERE source=? AND account_id=?
                )
                """,
                (source, account_id, source, account_id),
            )
            connection.execute(
                "DELETE FROM threads WHERE source=? AND account_id=?",
                (source, account_id),
            )
            connection.execute(
                "DELETE FROM raw_events WHERE source=? AND account_id=?",
                (source, account_id),
            )
            connection.execute(
                "DELETE FROM connector_cursors WHERE connector_id=?",
                (connector_id,),
            )
        return {"events": event_count, "threads": thread_count}

    def _legacy_gmail_cleanup_plan(self) -> dict[str, Any]:
        """Identify orphan primary events and personal rows copied from nycu."""
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT event_id, account_id, data_json
                FROM normalized_events
                WHERE source='gmail' AND account_id IN ('primary', 'personal', 'nycu')
                """
            ).fetchall()

            by_account: dict[str, dict[str, str]] = {
                "primary": {},
                "personal": {},
                "nycu": {},
            }
            for row in rows:
                try:
                    message_id = str(
                        json.loads(row["data_json"]).get("metadata", {}).get("message_id", "")
                    )
                except (TypeError, ValueError, json.JSONDecodeError):
                    message_id = ""
                if message_id:
                    by_account[row["account_id"]][row["event_id"]] = message_id

            nycu_message_ids = set(by_account["nycu"].values())
            overlapping_personal = {
                event_id
                for event_id, message_id in by_account["personal"].items()
                if message_id in nycu_message_ids
            }
            primary_events = set(by_account["primary"])
            target_events = primary_events | overlapping_personal

            target_threads: set[str] = set()
            if target_events:
                placeholders = ",".join("?" for _ in target_events)
                target_threads = {
                    str(row["thread_id"])
                    for row in connection.execute(
                        f"SELECT DISTINCT thread_id FROM thread_events "
                        f"WHERE event_id IN ({placeholders})",
                        tuple(target_events),
                    ).fetchall()
                }

            mixed_threads: set[str] = set()
            if target_threads:
                placeholders = ",".join("?" for _ in target_threads)
                links = connection.execute(
                    f"SELECT thread_id, event_id FROM thread_events "
                    f"WHERE thread_id IN ({placeholders})",
                    tuple(target_threads),
                ).fetchall()
                mixed_threads = {
                    str(row["thread_id"]) for row in links if row["event_id"] not in target_events
                }

            card_count = 0
            if target_threads:
                placeholders = ",".join("?" for _ in target_threads)
                card_count = int(
                    connection.execute(
                        f"SELECT COUNT(*) AS count FROM notification_cards "
                        f"WHERE thread_id IN ({placeholders})",
                        tuple(target_threads),
                    ).fetchone()["count"]
                )

        return {
            "primary_event_ids": primary_events,
            "overlapping_personal_event_ids": overlapping_personal,
            "target_event_ids": target_events,
            "target_thread_ids": target_threads,
            "mixed_thread_ids": mixed_threads,
            "card_count": card_count,
        }

    def audit_legacy_gmail_data(self) -> dict[str, int]:
        """Return content-free counts for the explicitly supported Gmail cleanup."""
        plan = self._legacy_gmail_cleanup_plan()
        return {
            "primary_events": len(plan["primary_event_ids"]),
            "personal_events_overlapping_nycu": len(plan["overlapping_personal_event_ids"]),
            "affected_threads": len(plan["target_thread_ids"]),
            "affected_cards": int(plan["card_count"]),
            "mixed_threads": len(plan["mixed_thread_ids"]),
        }

    def cleanup_legacy_gmail_data(self) -> dict[str, int]:
        """Delete the audited legacy rows without touching current OAuth state."""
        plan = self._legacy_gmail_cleanup_plan()
        if plan["mixed_thread_ids"]:
            raise RuntimeError(
                "legacy Gmail cleanup stopped because an affected thread contains retained events"
            )

        event_ids = sorted(plan["target_event_ids"])
        thread_ids = sorted(plan["target_thread_ids"])
        with self.transaction() as connection:
            if thread_ids:
                placeholders = ",".join("?" for _ in thread_ids)
                connection.execute(
                    f"""
                    DELETE FROM interruptions
                    WHERE card_id IN (
                        SELECT card_id FROM notification_cards
                        WHERE thread_id IN ({placeholders})
                    )
                    """,
                    tuple(thread_ids),
                )
            if event_ids or thread_ids:
                clauses: list[str] = []
                parameters: list[str] = []
                if event_ids:
                    clauses.append(f"event_id IN ({','.join('?' for _ in event_ids)})")
                    parameters.extend(event_ids)
                if thread_ids:
                    clauses.append(f"thread_id IN ({','.join('?' for _ in thread_ids)})")
                    parameters.extend(thread_ids)
                connection.execute(
                    f"DELETE FROM traces WHERE {' OR '.join(clauses)}",
                    tuple(parameters),
                )
            if thread_ids:
                placeholders = ",".join("?" for _ in thread_ids)
                connection.execute(
                    f"DELETE FROM threads WHERE thread_id IN ({placeholders})",
                    tuple(thread_ids),
                )
            if event_ids:
                placeholders = ",".join("?" for _ in event_ids)
                connection.execute(
                    f"DELETE FROM raw_events WHERE event_id IN ({placeholders})",
                    tuple(event_ids),
                )
            connection.execute("DELETE FROM connector_cursors WHERE connector_id='gmail:primary'")
            connection.execute("DELETE FROM connector_health WHERE connector_id='gmail:primary'")
            connection.execute("DELETE FROM connector_accounts WHERE connector_id='gmail:primary'")

        return {
            "primary_events": len(plan["primary_event_ids"]),
            "personal_events_overlapping_nycu": len(plan["overlapping_personal_event_ids"]),
            "threads": len(thread_ids),
            "cards": int(plan["card_count"]),
        }

    def counts(self) -> dict[str, int]:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT
                  SUM(CASE WHEN status='open' AND display_mode!='hidden' THEN 1 ELSE 0 END) AS open,
                  SUM(CASE WHEN status='open' AND display_mode!='hidden'
                    AND priority IN ('urgent','high') THEN 1 ELSE 0 END)
                    AS important,
                  SUM(CASE WHEN status='open' AND display_mode!='hidden'
                    AND requires_reply='yes' THEN 1 ELSE 0 END)
                    AS reply,
                  SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) AS done
                FROM notification_cards
                """
            ).fetchone()
        return {key: int(row[key] or 0) for key in ("open", "important", "reply", "done")}

    def hide_browser_background_cards(self) -> int:
        """Hide browser lifecycle notices that contain no chat message content."""
        phrases = (
            "%此網站已在背景更新%",
            "%這個網站已在背景更新%",
            "%此网站已在后台更新%",
            "%该网站已在后台更新%",
            "%this website has been updated in the background%",
            "%this site has been updated in the background%",
            "%this website was updated in the background%",
            "%this site was updated in the background%",
        )
        checks = " OR ".join("lower(summary) LIKE ?" for _ in phrases)
        with self.transaction() as connection:
            result = connection.execute(
                f"""
                UPDATE notification_cards SET display_mode='hidden'
                WHERE display_mode!='hidden'
                  AND source IN ('messenger_notification','windows_notification')
                  AND ({checks})
                """,
                tuple(phrase.casefold() for phrase in phrases),
            )
        return result.rowcount

    def reclassify_messenger_browser_cards(self) -> int:
        """Repair browser Messenger notifications previously classified as Windows."""
        repaired = 0
        repaired_threads: dict[str, dict[str, Any]] = {}
        with self.transaction() as connection:
            rows = connection.execute(
                """
                SELECT e.event_id, e.data_json, te.thread_id
                FROM normalized_events e
                JOIN thread_events te ON te.event_id=e.event_id
                WHERE e.source='windows_notification'
                """
            ).fetchall()
            for row in rows:
                event = json.loads(row["data_json"])
                metadata = event.get("metadata", {})
                native_app = (
                    f"{metadata.get('native_app_id', '')} "
                    f"{metadata.get('native_app_name', '')}"
                ).casefold()
                title = str(event.get("title") or "").strip()
                if not any(browser in native_app for browser in ("chrome", "edge", "firefox")):
                    continue
                if title.casefold() not in MESSENGER_GENERIC_TITLES:
                    continue

                sender = messenger_sender_from_preview(str(event.get("content") or "")) or title
                event.update(
                    {
                        "source": "messenger_notification",
                        "sender": sender,
                        "conversation_id": sender,
                        "title": sender,
                        "source_url": "https://www.messenger.com/",
                    }
                )
                metadata["source_resolution_uncertain"] = False
                event["metadata"] = metadata
                connection.execute(
                    "UPDATE normalized_events SET source=?, sender=?, conversation_id=?, "
                    "title=?, source_url=?, data_json=? WHERE event_id=?",
                    (
                        "messenger_notification",
                        sender,
                        sender,
                        sender,
                        "https://www.messenger.com/",
                        _json(event),
                        row["event_id"],
                    ),
                )
                connection.execute(
                    "UPDATE raw_events SET source=? WHERE event_id=?",
                    ("messenger_notification", row["event_id"]),
                )
                repaired_threads[row["thread_id"]] = event
                repaired += 1

            for thread_id, event in repaired_threads.items():
                remaining = connection.execute(
                    """
                    SELECT COUNT(*) AS count FROM thread_events te
                    JOIN normalized_events e ON e.event_id=te.event_id
                    WHERE te.thread_id=? AND e.source!='messenger_notification'
                    """,
                    (thread_id,),
                ).fetchone()["count"]
                if remaining:
                    continue
                sender = event["sender"]
                connection.execute(
                    "UPDATE threads SET source=?, sender=?, conversation_id=?, title=? "
                    "WHERE thread_id=?",
                    ("messenger_notification", sender, sender, sender, thread_id),
                )
                card = connection.execute(
                    "SELECT card_json FROM notification_cards WHERE thread_id=?",
                    (thread_id,),
                ).fetchone()
                if card:
                    card_json = json.loads(card["card_json"])
                    card_json.update(
                        {"source": "messenger_notification", "sender": sender, "title": sender}
                    )
                    connection.execute(
                        "UPDATE notification_cards SET source=?, sender=?, title=?, card_json=? "
                        "WHERE thread_id=?",
                        ("messenger_notification", sender, sender, _json(card_json), thread_id),
                    )
        return repaired

    def merge_duplicate_messenger_threads(self) -> list[str]:
        """Merge duplicate browser cards that represent the same Messenger conversation."""
        merged: list[str] = []
        with self.transaction() as connection:
            groups = connection.execute(
                """
                SELECT account_id, lower(conversation_id) AS conversation_key
                FROM threads
                WHERE source='messenger_notification' AND conversation_id IS NOT NULL
                GROUP BY account_id, lower(conversation_id)
                HAVING COUNT(*) > 1
                """
            ).fetchall()
            for group in groups:
                rows = connection.execute(
                    """
                    SELECT t.thread_id, t.created_at, t.updated_at, c.card_id
                    FROM threads t
                    LEFT JOIN notification_cards c ON c.thread_id=t.thread_id
                    WHERE t.source='messenger_notification' AND t.account_id=?
                      AND lower(t.conversation_id)=?
                    ORDER BY t.updated_at DESC
                    """,
                    (group["account_id"], group["conversation_key"]),
                ).fetchall()
                if len(rows) < 2 or not rows[0]["card_id"]:
                    continue
                canonical = rows[0]
                canonical_thread = canonical["thread_id"]
                canonical_card = canonical["card_id"]
                created_at = min(row["created_at"] for row in rows)
                updated_at = max(row["updated_at"] for row in rows)

                for duplicate in rows[1:]:
                    duplicate_thread = duplicate["thread_id"]
                    duplicate_card = duplicate["card_id"]
                    if duplicate_card:
                        connection.execute(
                            "UPDATE feedback_events SET card_id=? WHERE card_id=?",
                            (canonical_card, duplicate_card),
                        )
                        connection.execute(
                            "UPDATE reminders SET card_id=? WHERE card_id=?",
                            (canonical_card, duplicate_card),
                        )
                        connection.execute(
                            "UPDATE reply_drafts SET card_id=? WHERE card_id=?",
                            (canonical_card, duplicate_card),
                        )
                        canonical_interruption = connection.execute(
                            "SELECT 1 FROM interruptions WHERE card_id=?",
                            (canonical_card,),
                        ).fetchone()
                        if canonical_interruption:
                            connection.execute(
                                "DELETE FROM interruptions WHERE card_id=?", (duplicate_card,)
                            )
                        else:
                            connection.execute(
                                "UPDATE interruptions SET card_id=? WHERE card_id=?",
                                (canonical_card, duplicate_card),
                            )
                    connection.execute(
                        "UPDATE traces SET thread_id=? WHERE thread_id=?",
                        (canonical_thread, duplicate_thread),
                    )
                    connection.execute(
                        "UPDATE thread_events SET thread_id=? WHERE thread_id=?",
                        (canonical_thread, duplicate_thread),
                    )
                    connection.execute(
                        "DELETE FROM threads WHERE thread_id=?", (duplicate_thread,)
                    )

                connection.execute(
                    "UPDATE threads SET created_at=?, updated_at=? WHERE thread_id=?",
                    (created_at, updated_at, canonical_thread),
                )
                connection.execute(
                    "UPDATE notification_cards SET updated_at=? WHERE card_id=?",
                    (updated_at, canonical_card),
                )
                merged.append(canonical_thread)
        return merged

    def collapse_duplicate_notification_replays(self) -> int:
        """Remove repeated notification-center snapshots while preserving live repeats."""
        removed = 0
        affected_threads: set[str] = set()
        with self.transaction() as connection:
            rows = connection.execute(
                """
                SELECT e.event_id, e.source, e.account_id, e.title, e.content,
                       e.received_at, e.data_json, te.thread_id
                FROM normalized_events e
                JOIN thread_events te ON te.event_id=e.event_id
                WHERE e.source IN ('line_notification','messenger_notification')
                ORDER BY e.received_at
                """
            ).fetchall()
            groups: dict[tuple[str, ...], list[sqlite3.Row]] = {}
            for row in rows:
                event = json.loads(row["data_json"])
                if event.get("metadata", {}).get("archive_import"):
                    continue
                native_app_id = str(
                    event.get("metadata", {}).get("native_app_id") or ""
                ).casefold()
                key = (
                    row["source"],
                    row["account_id"],
                    native_app_id,
                    str(row["title"] or "").casefold(),
                    row["content"],
                )
                groups.setdefault(key, []).append(row)

            for duplicates in groups.values():
                if len(duplicates) < 2:
                    continue
                force_line_snapshot = duplicates[0]["source"] == "line_notification"
                if not force_line_snapshot and len(duplicates) < 3:
                    continue
                cluster: list[sqlite3.Row] = []
                cluster_start: datetime | None = None
                for row in duplicates:
                    received_at = datetime.fromisoformat(row["received_at"])
                    cluster_window = timedelta(hours=12 if force_line_snapshot else 4)
                    if cluster_start is None or received_at - cluster_start <= cluster_window:
                        cluster.append(row)
                        cluster_start = cluster_start or received_at
                    else:
                        removed += self._remove_replay_cluster(
                            connection,
                            cluster,
                            affected_threads,
                            minimum_size=2 if force_line_snapshot else 3,
                        )
                        cluster = [row]
                        cluster_start = received_at
                removed += self._remove_replay_cluster(
                    connection,
                    cluster,
                    affected_threads,
                    minimum_size=2 if force_line_snapshot else 3,
                )

            for thread_id in affected_threads:
                bounds = connection.execute(
                    """
                    SELECT MIN(received_at) AS created_at, MAX(received_at) AS updated_at,
                           COUNT(*) AS count
                    FROM thread_events WHERE thread_id=?
                    """,
                    (thread_id,),
                ).fetchone()
                if not bounds["count"]:
                    connection.execute("DELETE FROM threads WHERE thread_id=?", (thread_id,))
                    continue
                connection.execute(
                    "UPDATE threads SET created_at=?, updated_at=? WHERE thread_id=?",
                    (bounds["created_at"], bounds["updated_at"], thread_id),
                )
                card = connection.execute(
                    "SELECT card_id, card_json FROM notification_cards WHERE thread_id=?",
                    (thread_id,),
                ).fetchone()
                if card:
                    card_json = json.loads(card["card_json"])
                    card_json["updated_at"] = bounds["updated_at"]
                    connection.execute(
                        "UPDATE notification_cards SET updated_at=?, card_json=? WHERE card_id=?",
                        (bounds["updated_at"], _json(card_json), card["card_id"]),
                    )
        return removed

    def normalize_line_notification_identities(self) -> list[str]:
        """Repair existing LINE cards to show one visible sender per card."""
        affected_threads: set[str] = set()
        latest_by_thread: dict[str, UnifiedEvent] = {}
        with self.transaction() as connection:
            rows = connection.execute(
                """
                SELECT e.event_id, e.data_json, te.thread_id
                FROM normalized_events e
                JOIN thread_events te ON te.event_id=e.event_id
                WHERE e.source='line_notification'
                ORDER BY e.received_at
                """
            ).fetchall()
            for row in rows:
                event = UnifiedEvent.model_validate_json(row["data_json"])
                if event.metadata.get("archive_import"):
                    continue
                sender, identity, title = line_identity_from_title(
                    event.conversation_id or event.title or event.sender
                )
                repaired = event.model_copy(
                    update={"sender": sender, "conversation_id": identity, "title": title}
                )
                if (
                    repaired.sender == event.sender
                    and repaired.conversation_id == event.conversation_id
                    and repaired.title == event.title
                ):
                    continue
                connection.execute(
                    """
                    UPDATE normalized_events
                    SET sender=?, conversation_id=?, title=?, data_json=?
                    WHERE event_id=?
                    """,
                    (sender, identity, title, _json(repaired), row["event_id"]),
                )
                affected_threads.add(row["thread_id"])
                latest_by_thread[row["thread_id"]] = repaired

            for thread_id, event in latest_by_thread.items():
                connection.execute(
                    """
                    UPDATE threads SET sender=?, conversation_id=?, title=?
                    WHERE thread_id=?
                    """,
                    (event.sender, event.conversation_id, event.title, thread_id),
                )
        return sorted(affected_threads)

    def sync_card_event_timestamps(self, thread_ids: list[str]) -> None:
        """Keep repair analysis from making old cards look newly received."""
        if not thread_ids:
            return
        with self.transaction() as connection:
            for thread_id in thread_ids:
                bounds = connection.execute(
                    """
                    SELECT MIN(received_at) AS created_at, MAX(received_at) AS updated_at
                    FROM thread_events WHERE thread_id=?
                    """,
                    (thread_id,),
                ).fetchone()
                if not bounds or not bounds["updated_at"]:
                    continue
                connection.execute(
                    "UPDATE threads SET created_at=?, updated_at=? WHERE thread_id=?",
                    (bounds["created_at"], bounds["updated_at"], thread_id),
                )
                card = connection.execute(
                    "SELECT card_id, card_json FROM notification_cards WHERE thread_id=?",
                    (thread_id,),
                ).fetchone()
                if not card:
                    continue
                card_json = json.loads(card["card_json"])
                card_json["created_at"] = bounds["created_at"]
                card_json["updated_at"] = bounds["updated_at"]
                connection.execute(
                    """
                    UPDATE notification_cards
                    SET created_at=?, updated_at=?, card_json=? WHERE card_id=?
                    """,
                    (
                        bounds["created_at"],
                        bounds["updated_at"],
                        _json(card_json),
                        card["card_id"],
                    ),
                )

    def thread_ids_for_source(self, source: str) -> list[str]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT thread_id FROM threads WHERE source=? ORDER BY thread_id",
                (source,),
            ).fetchall()
        return [row["thread_id"] for row in rows]

    @staticmethod
    def _remove_replay_cluster(
        connection: sqlite3.Connection,
        cluster: list[sqlite3.Row],
        affected_threads: set[str],
        *,
        minimum_size: int = 3,
    ) -> int:
        if len(cluster) < minimum_size:
            return 0
        for row in cluster[1:]:
            affected_threads.add(row["thread_id"])
            connection.execute("DELETE FROM traces WHERE event_id=?", (row["event_id"],))
            connection.execute("DELETE FROM raw_events WHERE event_id=?", (row["event_id"],))
        affected_threads.add(cluster[0]["thread_id"])
        return len(cluster) - 1

    def digest(self) -> dict[str, Any]:
        cards = self.list_cards(view="now", limit=300)
        now = utc_now()
        due_today = [
            card
            for card in cards
            if card.get("deadline_at")
            and datetime.fromisoformat(card["deadline_at"]).astimezone().date()
            == now.astimezone().date()
        ]
        return {
            "urgent": [c for c in cards if c["priority"] in {"urgent", "high"}][:5],
            "due_today": due_today[:5],
            "needs_reply": [c for c in cards if c["requires_reply"] == "yes"][:8],
            "for_information": [
                c for c in cards if c["requires_reply"] != "yes" and c["priority"] == "normal"
            ][:8],
            "connector_issues": [c for c in self.connectors() if c["status"] != "healthy"],
            "counts": {
                "urgent": sum(c["priority"] in {"urgent", "high"} for c in cards),
                "due_today": len(due_today),
                "needs_reply": sum(c["requires_reply"] == "yes" for c in cards),
                "for_information": sum(c["priority"] in {"normal", "low"} for c in cards),
            },
            "generated_at": _iso(),
        }

    def export_privacy_safe(self) -> dict[str, Any]:
        """Export settings and anonymized behavior only; raw message bodies are excluded."""
        with self.connect() as connection:
            feedback = connection.execute(
                "SELECT action, value_json, created_at FROM feedback_events ORDER BY created_at"
            ).fetchall()
        return {
            "export_version": "1.0",
            "created_at": _iso(),
            "settings": self.settings(),
            "rules": self.rules(),
            "feedback": [dict(row) for row in feedback],
            "preference_weights": self.preference_weights(),
            "raw_messages_included": False,
        }

    def delete_all_personal_data(self) -> None:
        with self.transaction() as connection:
            for table in (
                "feedback_events",
                "preference_observations",
                "preference_weights",
                "user_rules",
                "reminders",
                "interruptions",
                "reply_drafts",
                "action_items",
                "deadlines",
                "notification_cards",
                "triage_results",
                "traces",
                "thread_events",
                "threads",
                "normalized_events",
                "raw_events",
                "quarantine",
                "connector_cursors",
                "connector_accounts",
            ):
                connection.execute(f"DELETE FROM {table}")
            connection.execute("DELETE FROM connector_health WHERE source='gmail'")

    def cleanup_retention(
        self, raw_days: int, normalized_days: int, summary_days: int
    ) -> dict[str, int]:
        deleted: dict[str, int] = {}
        with self.transaction() as connection:
            result = connection.execute(
                """
                DELETE FROM raw_events WHERE created_at < datetime('now', ?)
                  AND event_id NOT IN (SELECT event_id FROM normalized_events)
                """,
                (f"-{raw_days} days",),
            )
            deleted["raw_events"] = result.rowcount
            result = connection.execute(
                """
                DELETE FROM normalized_events WHERE created_at < datetime('now', ?)
                  AND event_id NOT IN (SELECT event_id FROM thread_events)
                """,
                (f"-{normalized_days} days",),
            )
            deleted["normalized_events"] = result.rowcount
            result = connection.execute(
                """
                DELETE FROM notification_cards WHERE status IN ('done','dismissed')
                  AND updated_at < datetime('now', ?)
                """,
                (f"-{summary_days} days",),
            )
            deleted["cards"] = result.rowcount
        return deleted
