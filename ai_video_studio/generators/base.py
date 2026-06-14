"""Common interface every video generator must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable


class GenerationError(Exception):
    """Raised when a video could not be generated."""


# A simple progress/log sink: gen.generate(..., log=print)
LogFn = Callable[[str], None]


class VideoGenerator(ABC):
    """Turn a text prompt into a local .mp4 file."""

    #: human-readable name shown in the UI
    name: str = "generator"

    @abstractmethod
    def is_ready(self) -> tuple[bool, str]:
        """Return (ready?, reason). Used by the UI to show a setup hint."""

    @abstractmethod
    def generate(self, prompt: str, out_path: Path, log: LogFn = print) -> Path:
        """Generate a video for `prompt`, save it to `out_path`, return it.

        Must raise GenerationError on any failure.
        """
