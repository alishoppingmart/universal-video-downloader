"""
AI Video Studio
===============
Turn a topic idea into a short video, then auto-publish it to YouTube Shorts
and TikTok on a schedule.

Pipeline:   topic  ->  generate (Google Flow)  ->  download  ->  publish.

This package is split into small, swappable pieces so the hard parts
(generation, each publisher) can be developed and tested on their own:

    config.py            paths, settings, secrets
    pipeline.py          the orchestrator that runs one full job
    generators/          text -> video back-ends (Google Flow today)
    publishers/          upload to YouTube / TikTok
    scheduler.py         "run N times a day" loop for the desktop app
    scripts/run_once.py  one-shot entry used by the cloud (GitHub Actions)
"""

__version__ = "0.1.0"
APP_NAME = "AI Video Studio"
