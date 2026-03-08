from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from soul.utils.decorator import catch_and_log
from soul.utils.logger import Logger
from soul.utils.type import HeartbeatSnapshot
from soul.utils.util import utc_now_iso

logger = Logger(__name__)


@dataclass
class HeartbeatState:
    started_at: float
    last_beat_at: str
    total_beats: int = 0


class Heartbeat:
    def __init__(self, interval_seconds: float, on_beat) -> None:
        self.interval_seconds = interval_seconds
        now = time.time()
        self.state = HeartbeatState(started_at=now, last_beat_at=utc_now_iso())
        self.on_beat = on_beat
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True, name="soul-heartbeat")
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self.interval_seconds + 0.5)

    def snapshot(self, arousal: float) -> HeartbeatSnapshot:
        with self._lock:
            bpm = int(68 + (arousal - 0.45) * 48)
            bpm = max(52, min(bpm, 130))
            return HeartbeatSnapshot(
                total_beats=self.state.total_beats,
                bpm=bpm,
                uptime_seconds=time.time() - self.state.started_at,
                last_beat_at=self.state.last_beat_at,
            )

    @catch_and_log(logger)
    def beat_once(self) -> None:
        with self._lock:
            self.state.total_beats += 1
            self.state.last_beat_at = utc_now_iso()
        self.on_beat()

    def _run(self) -> None:
        while not self._stop_event.wait(self.interval_seconds):
            self.beat_once()

