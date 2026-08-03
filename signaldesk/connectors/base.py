from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..models import UnifiedEvent


@dataclass(slots=True)
class ConnectorHealth:
    connector_id: str
    source: str
    status: str
    detail: str = ""
    capabilities: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SyncBatch:
    events: list[UnifiedEvent]
    cursor: str | None
    full_sync_required: bool = False


class Connector(ABC):
    connector_id: str
    source: str

    @abstractmethod
    def authenticate(self) -> bool: ...

    @abstractmethod
    def initial_sync(self) -> SyncBatch: ...

    @abstractmethod
    def incremental_sync(self, cursor: str | None) -> SyncBatch: ...

    @abstractmethod
    def health(self) -> ConnectorHealth: ...
