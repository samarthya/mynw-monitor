from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

from netwatch.shared.models import ConnectionEvent


class AbstractMonitor(ABC):
    def __init__(self, poll_interval_seconds: int = 5) -> None:
        self.poll_interval_seconds = poll_interval_seconds

    @abstractmethod
    async def run(self, queue: asyncio.Queue[ConnectionEvent]) -> None:
        """Continuously collect network events and enqueue them."""

    @abstractmethod
    async def collect_once(self) -> list[ConnectionEvent]:
        """Collect one snapshot of connection events."""
