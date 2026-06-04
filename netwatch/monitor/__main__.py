from __future__ import annotations

import asyncio
import platform
from collections import deque

from rich.console import Console
from rich.live import Live
from rich.table import Table

from netwatch.aggregator.classifier import DomainClassifier
from netwatch.aggregator.enricher import enrich_event
from netwatch.aggregator.storage import init_db, insert_connection_event
from netwatch.monitor.base import AbstractMonitor
from netwatch.monitor.macos import MacOSMonitor
from netwatch.shared.config import Settings
from netwatch.shared.logger import get_logger
from netwatch.shared.models import ConnectionEvent

logger = get_logger("monitor.cli")



def _build_monitor(settings: Settings) -> AbstractMonitor:
    system = platform.system().lower()
    if system == "darwin":
        return MacOSMonitor(settings.poll_interval_seconds)
    if system == "linux":
        from netwatch.monitor.linux import LinuxMonitor

        return LinuxMonitor(settings.poll_interval_seconds)
    if system == "windows":
        from netwatch.monitor.windows import WindowsMonitor

        return WindowsMonitor(settings.poll_interval_seconds)
    raise RuntimeError(f"Unsupported platform: {system}")


async def _consume_events(queue: asyncio.Queue[ConnectionEvent], settings: Settings) -> None:
    classifier = DomainClassifier(settings=settings, db_path=settings.resolved_db_path())
    recent: deque[ConnectionEvent] = deque(maxlen=20)
    console = Console()

    with Live(console=console, refresh_per_second=2) as live:
        while True:
            event = await queue.get()
            enriched = enrich_event(event)
            hostname = enriched.hostname or enriched.remote_addr
            enriched.category = classifier.classify(hostname)
            insert_connection_event(enriched, settings.resolved_db_path())
            recent.appendleft(enriched)
            live.update(_render_table(recent))
            queue.task_done()



def _render_table(events: deque[ConnectionEvent]) -> Table:
    table = Table(title="NetWatch Monitor")
    table.add_column("Time")
    table.add_column("Process")
    table.add_column("Remote")
    table.add_column("Hostname")
    table.add_column("Category")

    for event in events:
        table.add_row(
            event.timestamp.strftime("%H:%M:%S"),
            f"{event.process_name} ({event.pid})",
            f"{event.remote_addr}:{event.remote_port}",
            event.hostname or "-",
            event.category,
        )

    return table


async def _run() -> None:
    settings = Settings.load()
    init_db(settings.resolved_db_path())

    queue: asyncio.Queue[ConnectionEvent] = asyncio.Queue(maxsize=5000)
    monitor = _build_monitor(settings)

    producer = asyncio.create_task(monitor.run(queue))
    consumer = asyncio.create_task(_consume_events(queue, settings))
    await asyncio.gather(producer, consumer)



def main() -> None:
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user")


if __name__ == "__main__":
    main()
