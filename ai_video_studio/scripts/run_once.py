"""
One-shot runner: generate + publish a single video, then exit.

This is what the cloud (GitHub Actions cron) calls on schedule. It reads
settings from the repo/environment and credentials from AVS_* env vars
(see config.load_secrets), so no interactive login happens here.

Usage:
    python -m ai_video_studio.scripts.run_once [--topic-index N]
"""

from __future__ import annotations

import argparse
import sys

from ..config import Settings
from ..pipeline import run_job


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate and publish one video.")
    parser.add_argument("--topic-index", type=int, default=0,
                        help="Which topic in the list to use (round-robin).")
    args = parser.parse_args(argv)

    settings = Settings.load()
    result = run_job(settings, topic_index=args.topic_index, log=print)

    if result.errors:
        for e in result.errors:
            print(f"ERROR: {e}", file=sys.stderr)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
