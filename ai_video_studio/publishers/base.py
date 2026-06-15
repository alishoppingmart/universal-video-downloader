"""Common interface for every publisher."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

LogFn = Callable[[str], None]


class PublishError(Exception):
    """Raised when an upload fails."""


@dataclass
class PublishResult:
    platform: str
    url: str | None = None
    id: str | None = None


class Publisher(ABC):
    name: str = "publisher"

    @abstractmethod
    def is_ready(self) -> tuple[bool, str]:
        """Return (ready?, reason) based on whether credentials are present."""

    @abstractmethod
    def publish(self, video: Path, title: str, description: str, log: LogFn = print) -> PublishResult:
        """Upload `video` with the given title/description. Raise PublishError on failure."""
