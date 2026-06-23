# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Universal Video Downloader is a single-file Windows desktop GUI app (`universal_downloader.py`) built with Python/tkinter. It wraps `yt-dlp` to download videos from TikTok, YouTube, Facebook, and Instagram — individually or in bulk — and deduplicates across runs using a per-folder archive file.

## Running the App

```bash
python universal_downloader.py
```

No dependencies beyond the Python standard library and tkinter (bundled with CPython). There is no `requirements.txt`, no virtual environment setup, and no package install step.

On non-Windows platforms the app runs but won't auto-download binaries; it falls back to system `yt-dlp` on `PATH`.

## Building the Windows Portable EXE

The CI workflow (`.github/workflows/build-windows.yml`) does the full build on `windows-latest`:

```powershell
pip install pyinstaller
pyinstaller --onefile --windowed --name UniversalVideoDownloader universal_downloader.py
```

It then assembles a portable kit folder containing the `.exe`, a downloaded `yt-dlp.exe`, and `ffmpeg.exe`/`ffprobe.exe` extracted from the FFmpeg GPL zip. There is no local build script; the build only runs in GitHub Actions (triggered by pushes to `universal_downloader.py` or the workflow file, or via `workflow_dispatch`).

## Architecture

The entire application lives in a single class, `DownloaderApp`, with one free function:

- **`stream_command(cmd, on_line, on_done, stop_event)`** — Runs a subprocess and streams stdout/stderr line-by-line to a callback in a daemon thread. All yt-dlp invocations go through this.

- **`DownloaderApp`** — Owns the tkinter root window and all state. Key subsystems:
  - **UI** (`_build_ui`): built imperatively with tkinter/ttk widgets; no layout files.
  - **Log queue**: `self.log_queue` (a `queue.Queue`) is the only thread-safe path from worker threads to the UI. `_drain_log_queue` polls it every 100 ms via `root.after(100, ...)` and also parses `[download] XX%` lines to drive the progress bar.
  - **Settings**: persisted as JSON to `~/.universal_downloader/settings.json` via `_load_settings` / `_save_settings`. Called on startup and on every download start.
  - **Download flow**: `_start_download` → `_run_all` (daemon thread) → `_run_one` per URL → `stream_command`. A `threading.Event` (`done_event`) inside `_run_one` blocks until each URL finishes before moving to the next, so downloads are sequential per batch.
  - **Stop**: `self.stop_event` (a `threading.Event`) is checked inside `stream_command`'s reader thread and kills the subprocess when set.

## Portable vs. Installed Mode

`app_base_dir()` returns the directory of the `.exe` when frozen by PyInstaller, or the script's directory otherwise. `_find_sibling()` looks for `yt-dlp.exe`/`ffmpeg.exe` next to the app first; if found, those win over the auto-downloaded copies in `~/.universal_downloader/`. Cookies files are similarly auto-detected next to the app via `_find_sibling_cookies()`.

## Key File Paths at Runtime

| Path | Purpose |
|------|---------|
| `~/.universal_downloader/settings.json` | Persisted UI settings |
| `~/.universal_downloader/yt-dlp.exe` | Auto-downloaded yt-dlp binary (Windows) |
| `~/.universal_downloader/ffmpeg/ffmpeg.exe` | Auto-downloaded ffmpeg binary (Windows) |
| `<output_dir>/_download_archive.txt` | yt-dlp archive for deduplication; one per output folder |

## yt-dlp Command Construction

`_build_command(url, output_dir)` assembles the full yt-dlp argument list. The output filename template is built by `_output_template()` from the naming/subfolder/numbering checkboxes. Format selection strings are in `_format_args()`. URL normalization (bare `@handle` → TikTok URL) is in `_normalize_input()`. Facebook URL heuristics for detecting un-downloadable profile/page links are in `_check_url()`.

## Branding Assets

`AJTECH_ICON_B64` and `AJTECH_LOGO_B64` are base64-encoded PNG images embedded directly in the source file for single-file distribution. They are decoded at startup in `_set_branding()`.
