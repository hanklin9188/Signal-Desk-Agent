from __future__ import annotations

import hashlib

from .database import Database
from .models import Source, UnifiedEvent


class ThreadGrouper:
    def __init__(self, database: Database, window_seconds: int = 30):
        self.database = database
        self.window_seconds = window_seconds

    def group(self, event: UnifiedEvent) -> str:
        candidate = self.database.candidate_thread(event, self.window_seconds)
        if candidate:
            thread_id = candidate
        elif event.source == Source.GMAIL and event.conversation_id:
            thread_id = f"gmail:{event.account_id}:{event.conversation_id}"
        elif event.source in {Source.LINE, Source.MESSENGER} and event.conversation_id:
            seed = f"{event.source}|{event.account_id}|{event.conversation_id.casefold()}"
            thread_id = f"conversation_{hashlib.sha256(seed.encode()).hexdigest()[:20]}"
        else:
            # Stable but opaque: message contents and sender are not exposed in IDs.
            seed = (
                f"{event.source}|{event.account_id}|{event.sender.casefold()}|"
                f"{event.received_at.timestamp()}|{event.event_id}"
            )
            thread_id = f"thread_{hashlib.sha256(seed.encode()).hexdigest()[:20]}"
        self.database.attach_event(thread_id, event)
        return thread_id
