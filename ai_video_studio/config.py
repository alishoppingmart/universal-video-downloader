"""
Configuration, paths and persisted settings for AI Video Studio.

Everything the app needs to remember lives under one folder in the user's
home directory, so it works no matter where the .exe is launched from:

    ~/.ai_video_studio/
        settings.json          <- topics, schedule, which platforms are on
        secrets.json           <- API keys / tokens (never committed to git)
        flow_session.json       <- saved Google Flow browser login (cookies)
        videos/                <- generated .mp4 files
        logs/                  <- run logs
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

APP_DIR = Path.home() / ".ai_video_studio"
VIDEOS_DIR = APP_DIR / "videos"
LOGS_DIR = APP_DIR / "logs"

SETTINGS_FILE = APP_DIR / "settings.json"
SECRETS_FILE = APP_DIR / "secrets.json"
FLOW_SESSION_FILE = APP_DIR / "flow_session.json"

for _d in (APP_DIR, VIDEOS_DIR, LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Settings  (safe to read on any machine; no secrets here)
# ---------------------------------------------------------------------------
@dataclass
class Settings:
    """User-facing choices, edited from the desktop GUI."""

    # What the videos are about. One job picks the next topic in the list,
    # round-robin, so you can queue several ideas.
    topics: list[str] = field(default_factory=list)

    # How many videos to publish per day: 1, 2, ...
    posts_per_day: int = 1

    # Local clock times (24h "HH:MM") to publish at. Length should match
    # posts_per_day; extra/missing entries are handled gracefully.
    schedule_times: list[str] = field(default_factory=lambda: ["18:00"])

    # Which platforms to publish to.
    publish_youtube: bool = True
    publish_tiktok: bool = True

    # Extra text appended to every caption/description.
    hashtags: str = "#shorts #ai"

    # Generation back-end id (only "google_flow" today).
    generator: str = "google_flow"

    def save(self) -> None:
        SETTINGS_FILE.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls) -> "Settings":
        if SETTINGS_FILE.exists():
            try:
                data = json.loads(SETTINGS_FILE.read_text())
                known = {k: data[k] for k in cls.__dataclass_fields__ if k in data}
                return cls(**known)
            except Exception:
                pass
        return cls()


# ---------------------------------------------------------------------------
# Secrets  (API keys / tokens; this file is git-ignored)
# ---------------------------------------------------------------------------
def load_secrets() -> dict[str, Any]:
    """Read secrets from the file, falling back to environment variables.

    Environment variables win, which is what lets the SAME code run in the
    cloud (GitHub Actions) where secrets are injected as env vars.
    """
    data: dict[str, Any] = {}
    if SECRETS_FILE.exists():
        try:
            data = json.loads(SECRETS_FILE.read_text())
        except Exception:
            data = {}

    # Cloud / CI override: any AVS_* environment variable.
    for key, env in {
        "youtube_client_id": "AVS_YT_CLIENT_ID",
        "youtube_client_secret": "AVS_YT_CLIENT_SECRET",
        "youtube_refresh_token": "AVS_YT_REFRESH_TOKEN",
        "tiktok_client_key": "AVS_TIKTOK_CLIENT_KEY",
        "tiktok_client_secret": "AVS_TIKTOK_CLIENT_SECRET",
        "tiktok_access_token": "AVS_TIKTOK_ACCESS_TOKEN",
    }.items():
        if os.environ.get(env):
            data[key] = os.environ[env]
    return data


def save_secrets(data: dict[str, Any]) -> None:
    SECRETS_FILE.write_text(json.dumps(data, indent=2))
    # Best-effort lock-down of the secrets file on POSIX systems.
    try:
        os.chmod(SECRETS_FILE, 0o600)
    except Exception:
        pass
