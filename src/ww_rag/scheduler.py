from __future__ import annotations

import threading
import time

from ww_rag.service import RagService


def interval_seconds(value: str) -> int:
    normalized = value.strip().lower()
    if normalized in {"daily", "day", "1d"}:
        return 24 * 60 * 60
    if normalized in {"hourly", "hour", "1h"}:
        return 60 * 60
    if normalized.endswith("m") and normalized[:-1].isdigit():
        return int(normalized[:-1]) * 60
    if normalized.endswith("s") and normalized[:-1].isdigit():
        return int(normalized[:-1])
    if normalized.isdigit():
        return int(normalized)
    return 24 * 60 * 60


class SyncScheduler:
    def __init__(self, service: RagService, interval: str):
        self.service = service
        self.interval = interval_seconds(interval)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="rag-sync-scheduler", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)

    def _loop(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                self.service.sync_local()
            except Exception:
                pass


