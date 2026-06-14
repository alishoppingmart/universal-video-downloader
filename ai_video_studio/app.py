#!/usr/bin/env python3
"""
AI Video Studio - desktop control panel (Tkinter GUI)
=====================================================
Set your topics + schedule, connect your accounts, and let it run.

The window has four parts:
  1. Topics        - your video ideas (one per line)
  2. Schedule      - how many per day and at what times
  3. Accounts      - connect Google Flow / YouTube / TikTok
  4. Run + Log     - start the scheduler, or run one now; watch the output
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

from . import APP_NAME, __version__
from .config import Settings, load_secrets, save_secrets
from .scheduler import Scheduler
from .pipeline import run_job
from .generators import get_generator
from .publishers import get_publisher


class StudioApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.settings = Settings.load()
        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self.scheduler = Scheduler(self._current_settings, log=self.log)

        root.title(f"{APP_NAME} v{__version__}")
        root.geometry("760x720")
        root.minsize(680, 600)

        self._build_ui()
        self._load_into_ui()
        self.root.after(150, self._drain_log)

    # -- helpers -------------------------------------------------------------
    def log(self, msg: str) -> None:
        self.log_queue.put(str(msg))

    def _drain_log(self) -> None:
        while not self.log_queue.empty():
            line = self.log_queue.get_nowait()
            self.log_box.configure(state="normal")
            self.log_box.insert("end", line + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.root.after(150, self._drain_log)

    def _run_bg(self, fn, *args):
        threading.Thread(target=fn, args=args, daemon=True).start()

    def _current_settings(self) -> Settings:
        """Snapshot the UI into a Settings object."""
        self.settings.topics = [t.strip() for t in self.topics_box.get("1.0", "end").splitlines() if t.strip()]
        try:
            self.settings.posts_per_day = max(1, int(self.posts_var.get()))
        except ValueError:
            self.settings.posts_per_day = 1
        self.settings.schedule_times = [t.strip() for t in self.times_var.get().split(",") if t.strip()]
        self.settings.publish_youtube = bool(self.yt_var.get())
        self.settings.publish_tiktok = bool(self.tt_var.get())
        self.settings.hashtags = self.hashtags_var.get().strip()
        return self.settings

    # -- UI construction -----------------------------------------------------
    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 6}
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True)

        # ----- Tab 1: Topics & schedule -----
        tab1 = ttk.Frame(nb)
        nb.add(tab1, text="Topics & Schedule")

        ttk.Label(tab1, text="Your video ideas (one topic per line):").pack(anchor="w", **pad)
        self.topics_box = scrolledtext.ScrolledText(tab1, height=8, wrap="word")
        self.topics_box.pack(fill="both", expand=True, padx=10)

        row = ttk.Frame(tab1)
        row.pack(fill="x", **pad)
        ttk.Label(row, text="Videos per day:").pack(side="left")
        self.posts_var = tk.StringVar(value="1")
        ttk.Spinbox(row, from_=1, to=12, width=5, textvariable=self.posts_var).pack(side="left", padx=6)
        ttk.Label(row, text="   Times (24h, comma-separated):").pack(side="left")
        self.times_var = tk.StringVar(value="18:00")
        ttk.Entry(row, textvariable=self.times_var, width=24).pack(side="left", padx=6)

        row2 = ttk.Frame(tab1)
        row2.pack(fill="x", **pad)
        ttk.Label(row2, text="Hashtags / caption tail:").pack(side="left")
        self.hashtags_var = tk.StringVar(value="#shorts #ai")
        ttk.Entry(row2, textvariable=self.hashtags_var, width=40).pack(side="left", padx=6)

        row3 = ttk.Frame(tab1)
        row3.pack(fill="x", **pad)
        self.yt_var = tk.IntVar(value=1)
        self.tt_var = tk.IntVar(value=1)
        ttk.Checkbutton(row3, text="Publish to YouTube Shorts", variable=self.yt_var).pack(side="left")
        ttk.Checkbutton(row3, text="Publish to TikTok", variable=self.tt_var).pack(side="left", padx=20)

        ttk.Button(tab1, text="Save settings", command=self._save).pack(anchor="e", **pad)

        # ----- Tab 2: Accounts -----
        tab2 = ttk.Frame(nb)
        nb.add(tab2, text="Accounts")
        self._build_accounts_tab(tab2, pad)

        # ----- Tab 3: Run -----
        tab3 = ttk.Frame(nb)
        nb.add(tab3, text="Run")
        runbar = ttk.Frame(tab3)
        runbar.pack(fill="x", **pad)
        self.start_btn = ttk.Button(runbar, text="Start scheduler", command=self._toggle_scheduler)
        self.start_btn.pack(side="left")
        ttk.Button(runbar, text="Run one now", command=self._run_now).pack(side="left", padx=10)
        ttk.Button(runbar, text="Check setup", command=self._check_setup).pack(side="left")

        self.log_box = scrolledtext.ScrolledText(tab3, height=20, state="disabled", wrap="word")
        self.log_box.pack(fill="both", expand=True, padx=10, pady=10)

    def _build_accounts_tab(self, parent, pad) -> None:
        # Google Flow
        f1 = ttk.LabelFrame(parent, text="Google Flow (video generator)")
        f1.pack(fill="x", **pad)
        ttk.Label(f1, text="Sign in once in a browser; your password is never stored.").pack(anchor="w", padx=10, pady=4)
        ttk.Button(f1, text="Connect Google Flow", command=self._connect_flow).pack(anchor="w", padx=10, pady=6)

        # YouTube
        f2 = ttk.LabelFrame(parent, text="YouTube")
        f2.pack(fill="x", **pad)
        self.yt_id = tk.StringVar()
        self.yt_secret = tk.StringVar()
        self._labeled_entry(f2, "Client ID:", self.yt_id)
        self._labeled_entry(f2, "Client secret:", self.yt_secret, show="*")
        btns = ttk.Frame(f2)
        btns.pack(fill="x", padx=10, pady=6)
        ttk.Button(btns, text="Save keys", command=self._save_yt_keys).pack(side="left")
        ttk.Button(btns, text="Connect YouTube", command=self._connect_youtube).pack(side="left", padx=8)

        # TikTok
        f3 = ttk.LabelFrame(parent, text="TikTok")
        f3.pack(fill="x", **pad)
        self.tt_token = tk.StringVar()
        self._labeled_entry(f3, "Access token:", self.tt_token, show="*")
        ttk.Button(f3, text="Save token", command=self._save_tt_token).pack(anchor="w", padx=10, pady=6)
        ttk.Label(f3, text="See docs/SETUP.md for how to obtain these.").pack(anchor="w", padx=10, pady=2)

    def _labeled_entry(self, parent, label, var, show=None):
        row = ttk.Frame(parent)
        row.pack(fill="x", padx=10, pady=3)
        ttk.Label(row, text=label, width=14).pack(side="left")
        ttk.Entry(row, textvariable=var, show=show, width=52).pack(side="left", fill="x", expand=True)

    # -- load / save ---------------------------------------------------------
    def _load_into_ui(self) -> None:
        s = self.settings
        self.topics_box.insert("1.0", "\n".join(s.topics))
        self.posts_var.set(str(s.posts_per_day))
        self.times_var.set(", ".join(s.schedule_times))
        self.hashtags_var.set(s.hashtags)
        self.yt_var.set(1 if s.publish_youtube else 0)
        self.tt_var.set(1 if s.publish_tiktok else 0)
        secrets = load_secrets()
        self.yt_id.set(secrets.get("youtube_client_id", ""))
        self.yt_secret.set(secrets.get("youtube_client_secret", ""))

    def _save(self) -> None:
        self._current_settings().save()
        self.log("Settings saved.")
        messagebox.showinfo(APP_NAME, "Settings saved.")

    def _save_yt_keys(self) -> None:
        s = load_secrets()
        s["youtube_client_id"] = self.yt_id.get().strip()
        s["youtube_client_secret"] = self.yt_secret.get().strip()
        save_secrets(s)
        self.log("YouTube client keys saved.")

    def _save_tt_token(self) -> None:
        s = load_secrets()
        s["tiktok_access_token"] = self.tt_token.get().strip()
        save_secrets(s)
        self.log("TikTok access token saved.")

    # -- account connect actions (run in background threads) -----------------
    def _connect_flow(self) -> None:
        self.log("Opening Google Flow login...")
        self._run_bg(lambda: self._safe(lambda: get_generator("google_flow").capture_session(self.log)))

    def _connect_youtube(self) -> None:
        self.log("Starting YouTube authorization...")
        self._run_bg(lambda: self._safe(lambda: get_publisher("youtube").authorize(self.log)))

    def _safe(self, fn) -> None:
        try:
            fn()
        except Exception as e:
            self.log(f"!! {e}")

    # -- run -----------------------------------------------------------------
    def _toggle_scheduler(self) -> None:
        if self.scheduler.running:
            self.scheduler.stop()
            self.start_btn.config(text="Start scheduler")
        else:
            self._current_settings().save()
            self.scheduler.start()
            self.start_btn.config(text="Stop scheduler")

    def _run_now(self) -> None:
        settings = self._current_settings()
        settings.save()
        self.log("Running one job now...")
        self._run_bg(lambda: self._safe(lambda: run_job(settings, 0, self.log)))

    def _check_setup(self) -> None:
        s = self._current_settings()
        self.log("--- Setup check ---")
        try:
            g = get_generator(s.generator)
            ok, why = g.is_ready()
            self.log(f"Generator ({g.name}): {'OK' if ok else 'NOT READY - ' + why}")
        except Exception as e:
            self.log(f"Generator: error {e}")
        for plat in (["youtube"] if s.publish_youtube else []) + (["tiktok"] if s.publish_tiktok else []):
            try:
                p = get_publisher(plat)
                ok, why = p.is_ready()
                self.log(f"{p.name}: {'OK' if ok else 'NOT READY - ' + why}")
            except Exception as e:
                self.log(f"{plat}: error {e}")
        self.log("--- End check ---")


def main() -> None:
    root = tk.Tk()
    StudioApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
