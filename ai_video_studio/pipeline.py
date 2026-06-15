"""
The orchestrator: run ONE full job end to end.

    pick a topic  ->  build a video prompt + caption
                  ->  generate the video (Google Flow)
                  ->  publish to each enabled platform

This same function is called both by the desktop scheduler and by the cloud
one-shot runner (scripts/run_once.py).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .config import Settings, VIDEOS_DIR
from .generators import get_generator, GenerationError
from .publishers import get_publisher, PublishError, PublishResult

LogFn = Callable[[str], None]


@dataclass
class JobResult:
    topic: str
    video_path: Path | None = None
    published: list[PublishResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.published) and not self.errors


# ---------------------------------------------------------------------------
# Turning a short topic into a real video prompt + caption.
# (Kept simple & offline for now; can later call an LLM for richer scripts.)
# ---------------------------------------------------------------------------
def build_prompt(topic: str) -> str:
    return (
        f"A short, vertical (9:16) cinematic video about: {topic}. "
        f"Eye-catching, high quality, smooth camera motion, vibrant colors, "
        f"suitable for a 15-30 second social media Short."
    )


def build_caption(topic: str, hashtags: str) -> tuple[str, str]:
    title = topic.strip().capitalize()
    if len(title) > 80:
        title = title[:77] + "..."
    description = f"{topic.strip()}\n\n{hashtags}".strip()
    return title, description


def pick_topic(settings: Settings, index: int) -> str:
    if not settings.topics:
        raise ValueError("No topics configured. Add at least one idea first.")
    return settings.topics[index % len(settings.topics)]


# ---------------------------------------------------------------------------
def run_job(settings: Settings, topic_index: int = 0, log: LogFn = print) -> JobResult:
    """Generate one video and publish it to all enabled platforms."""
    topic = pick_topic(settings, topic_index)
    result = JobResult(topic=topic)
    log(f"=== Job started for topic: {topic!r} ===")

    # 1) Generate -----------------------------------------------------------
    try:
        gen = get_generator(settings.generator)
        ready, reason = gen.is_ready()
        if not ready:
            raise GenerationError(reason)
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = VIDEOS_DIR / f"{stamp}.mp4"
        prompt = build_prompt(topic)
        result.video_path = gen.generate(prompt, out_path, log=log)
    except (GenerationError, Exception) as e:
        result.errors.append(f"generation: {e}")
        log(f"!! Generation failed: {e}")
        return result  # nothing to publish

    # 2) Publish ------------------------------------------------------------
    title, description = build_caption(topic, settings.hashtags)
    targets = []
    if settings.publish_youtube:
        targets.append("youtube")
    if settings.publish_tiktok:
        targets.append("tiktok")

    for platform in targets:
        try:
            pub = get_publisher(platform)
            ready, reason = pub.is_ready()
            if not ready:
                raise PublishError(reason)
            res = pub.publish(result.video_path, title, description, log=log)
            result.published.append(res)
        except (PublishError, Exception) as e:
            result.errors.append(f"{platform}: {e}")
            log(f"!! Publish to {platform} failed: {e}")

    log(f"=== Job done. Published: {len(result.published)}, errors: {len(result.errors)} ===")
    return result
