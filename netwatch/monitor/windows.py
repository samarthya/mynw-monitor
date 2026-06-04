from __future__ import annotations

import asyncio

from netwatch.monitor.base import AbstractMonitor
from netwatch.shared.models import ConnectionEvent


class WindowsMonitor(AbstractMonitor):
    # TODO: Phase 2
    async def run(self, queue: asyncio.Queue[ConnectionEvent]) -> None:
        raise NotImplementedError("Windows monitor adapter is planned for Phase 2")

    # TODO: Phase 2
    async def collect_once(self) -> list[ConnectionEvent]:
        raise NotImplementedError("Windows monitor adapter is planned for Phase 2")
