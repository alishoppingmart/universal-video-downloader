# AI Video Studio

Turn a **topic idea** into a short video and **auto-publish** it to **YouTube
Shorts** and **TikTok** — on a daily schedule.

You give it your ideas and a posting schedule; it generates the video with
**Google Flow**, then uploads it for you.

```
topic  →  generate (Google Flow)  →  download  →  publish (YouTube + TikTok)
```

## Apps in this repo
| App | What it is | Build |
| --- | --- | --- |
| **AI Video Studio — desktop** (`ai_video_studio/`, `studio_app.py`) | Full create-and-publish system | `build-studio.yml` → Windows `.exe` |
| **AI Video Studio — mobile** (`mobile/`, `main.py`) | Android control panel that drives the cloud | `build-android.yml` → Android `.apk` |
| **Universal Video Downloader** (`universal_downloader.py`) | The original downloader (TikTok/YouTube/FB/IG) | `build-windows.yml` |

## Quick start
```bash
pip install -r requirements.txt
playwright install chromium
python studio_app.py
```
Then follow **[docs/SETUP.md](docs/SETUP.md)** to connect your accounts.

## Status
**v0.1 — desktop + mobile foundation.** Pipeline, desktop GUI, scheduler, Google
Flow generator, YouTube + TikTok publishers, Windows `.exe` build, and an Android
`.apk` control-panel app are all in place. You connect your own accounts (one-time,
required by each platform). See the roadmap in SETUP.md.

## Honest notes
- **Google Flow** has no public API; the app drives the Flow website using a
  login session **you** capture once (your password is never stored). This step
  works best on your own PC — Google blocks logins from cloud servers.
- **Cloud 24/7** scheduling (GitHub Actions) is wired for *publishing*; Flow
  *generation* realistically runs on your machine.
