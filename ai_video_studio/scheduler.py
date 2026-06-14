"""
A tiny scheduler for the desktop app.

Runs in a background thread and fires `run_job` at the local clock times in
Settings.schedule_times (e.g. ["09:00", "18:00"]). It keeps a record of the
last date each slot ran so it won't double-fire if the app stays open.

This is only for the "run on my PC" mode. The cloud mode uses GitHub Actions
cron instead (see .github/workflows/daily-publish.yml).
"""

from __future__ import annotations

import datetime as dt
import threading
import time
from typing import Callable

from .config import Settings
from .pipeline import run_job

LogFn = Callable[[str], None]


class Scheduler:
    def __init__(self, settings_provider: Callable[[], Settings], log: LogFn = print):
        self._get_settings = settings_provider
        self._log = log
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._last_run: dict[str, str] = {}  # "HH:MM" -> "YYYY-MM-DD"

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self._log("Scheduler started. Waiting for the next scheduled time...")

    def stop(self) -> None:
        self._stop.set()
        self._log("Scheduler stopped.")

    def _loop(self) -> None:
        while not self._stop.is_set():
            settings = self._get_settings()
            now = dt.datetime.now()
            today = now.strftime("%Y-%m-%d")
            hhmm = now.strftime("%H:%M")

            slots = settings.schedule_times[: max(1, settings.posts_per_day)]
            for i, slot in enumerate(slots):
                if slot == hhmm and self._last_run.get(slot) != today:
                    self._last_run[slot] = today
                    self._log(f"Scheduled time {slot} reached - running job #{i + 1}.")
                    try:
                        run_job(settings, topic_index=i, log=self._log)
                    except Exception as e:  # never let the loop die
                        self._log(f"!! Job error: {e}")

            # Check about twice a minute so we don't miss a slot.
            self._stop.wait(25)
