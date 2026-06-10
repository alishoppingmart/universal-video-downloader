#!/usr/bin/env python3
"""
Universal Video Downloader  -  AJ Tech
=====================================================
A standalone Windows desktop app that downloads videos from TikTok, YouTube,
Facebook and Instagram - either a single video link or a whole profile/channel.

Key feature: it remembers what it has already downloaded (an "archive").
So if you paste a TikTok profile today and get 100 videos, then paste the SAME
profile link in 3-4 days, it skips everything it already has and only downloads
the NEW uploads. No duplicates, ever.

It wraps yt-dlp (the open-source downloader) and manages yt-dlp.exe + ffmpeg.exe
automatically - downloading them on first run and keeping them updated.

Author: built with Claude for Ali (AJ Tech)
"""

import os
import sys
import re
import json
import queue
import shutil
import zipfile
import threading
import subprocess
import urllib.request
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, font as tkfont

# ----------------------------------------------------------------------------
# Constants & paths
# ----------------------------------------------------------------------------
APP_NAME = "Universal Video Downloader"
APP_VERSION = "1.0"

# Where we keep the yt-dlp / ffmpeg binaries and the saved settings.
# Using the user's home folder so it works no matter where the .exe lives.
APP_DIR = Path.home() / ".universal_downloader"
APP_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = APP_DIR / "settings.json"
ARCHIVE_NAME = "_download_archive.txt"  # lives inside each output folder

# Standalone binary download URLs (Windows)
YTDLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
FFMPEG_ZIP_URL = (
    "https://github.com/yt-dlp/FFmpeg-Builds/releases/latest/download/"
    "ffmpeg-master-latest-win64-gpl.zip"
)

YTDLP_BIN = APP_DIR / "yt-dlp.exe"
FFMPEG_DIR = APP_DIR / "ffmpeg"
FFMPEG_BIN = FFMPEG_DIR / "ffmpeg.exe"

IS_WINDOWS = os.name == "nt"


# --- Portable mode: use tools/cookies that sit NEXT TO the app ---------------
# This is what makes one build work on every PC: drop yt-dlp.exe / ffmpeg.exe /
# a cookies.txt into the same folder as the app, and it uses them automatically.
def app_base_dir():
    if getattr(sys, "frozen", False):          # running as a PyInstaller .exe
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent      # running as a .py script

APP_BASE_DIR = app_base_dir()

def _find_sibling(filename):
    """Look for a file next to the app, or in a 'bin' subfolder beside it."""
    for cand in (APP_BASE_DIR / filename, APP_BASE_DIR / "bin" / filename):
        if cand.exists():
            return cand
    return None

def _find_sibling_cookies():
    """Find any *cookies*.txt sitting next to the app (portable login)."""
    try:
        for p in sorted(APP_BASE_DIR.glob("*.txt")):
            if "cookie" in p.name.lower():
                return p
    except Exception:
        pass
    return None

# --- AJ Tech branding (base64 PNG, single-file distribution) ---
AJTECH_ICON_B64 = "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"
AJTECH_LOGO_B64 = "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"

# Hide the console window that subprocess would otherwise pop up on Windows
if IS_WINDOWS:
    CREATE_NO_WINDOW = 0x08000000
else:
    CREATE_NO_WINDOW = 0


# ----------------------------------------------------------------------------
# Helper: run a subprocess and stream its output line-by-line to a callback
# ----------------------------------------------------------------------------
def stream_command(cmd, on_line, on_done=None, stop_event=None):
    """Run cmd (list), call on_line(str) for every output line. Returns proc."""
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace",
        creationflags=CREATE_NO_WINDOW if IS_WINDOWS else 0,
    )

    def reader():
        try:
            for line in proc.stdout:
                if stop_event is not None and stop_event.is_set():
                    try:
                        proc.kill()
                    except Exception:
                        pass
                    break
                on_line(line.rstrip("\n"))
        finally:
            proc.stdout.close()
            proc.wait()
            if on_done:
                on_done(proc.returncode)

    threading.Thread(target=reader, daemon=True).start()
    return proc


# ----------------------------------------------------------------------------
# Main application
# ----------------------------------------------------------------------------
class DownloaderApp:
    QUALITY_OPTIONS = [
        "Best (auto)",
        "1080p",
        "720p",
        "480p",
        "Audio only (mp3)",
    ]
    BROWSER_OPTIONS = ["chrome", "edge", "firefox", "brave", "opera", "vivaldi"]

    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION} - AJ Tech")
        self.root.geometry("1040x760")
        self.root.minsize(880, 640)
        # Start maximized on Windows so everything has plenty of room
        try:
            self.root.state("zoomed")
        except Exception:
            pass
        # Bump the app-wide text size so labels/buttons are easier to read
        try:
            for fname in ("TkDefaultFont", "TkTextFont", "TkMenuFont"):
                f = tkfont.nametofont(fname)
                f.configure(size=max(int(f.cget("size")), 10))
        except Exception:
            pass

        self.log_queue = queue.Queue()
        self.proc = None
        self.stop_event = threading.Event()
        self.is_running = False

        # Resolve which yt-dlp / ffmpeg to use: a copy next to the app wins,
        # otherwise the auto-downloaded copy in the home folder.
        self.ytdlp_bin = _find_sibling("yt-dlp.exe") or YTDLP_BIN
        sib_ff = _find_sibling("ffmpeg.exe")
        if sib_ff:
            self.ffmpeg_dir = sib_ff.parent
            self.ffmpeg_bin = sib_ff
        else:
            self.ffmpeg_dir = FFMPEG_DIR
            self.ffmpeg_bin = FFMPEG_BIN

        self._set_branding()
        self._build_ui()
        self._load_settings()
        self._autodetect_cookies()
        self.root.after(100, self._drain_log_queue)

        # Make sure the tools exist (download on first run, in background)
        threading.Thread(target=self._ensure_tools, daemon=True).start()

    def _autodetect_cookies(self):
        """If no valid cookies file is set, use any cookies.txt next to the app."""
        cur = self.cookies_var.get().strip()
        if cur and Path(cur).exists():
            return  # already have a working one
        sib = _find_sibling_cookies()
        if sib:
            self.cookies_var.set(str(sib))
            self.log(f"Using cookies file found next to the app: {sib.name}")

    # ------------------------------------------------------------- branding
    def _set_branding(self):
        """Load the AJ Tech icon (window) and logo (header) from embedded base64."""
        self._icon_img = None
        self._logo_img = None
        try:
            import base64
            self._icon_img = tk.PhotoImage(data=base64.b64decode(AJTECH_ICON_B64))
            self.root.iconphoto(True, self._icon_img)
        except Exception:
            pass
        try:
            import base64
            self._logo_img = tk.PhotoImage(data=base64.b64decode(AJTECH_LOGO_B64))
        except Exception:
            pass

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        # ---- header with logo ----
        if self._logo_img is not None:
            header = tk.Frame(self.root)
            header.pack(fill="x", padx=10, pady=(8, 0))
            tk.Label(header, image=self._logo_img).pack(side="left")

        # ---- URLs input ----
        tk.Label(self.root, text="Video / Profile links — one per line  "
                 "(TikTok, YouTube, Facebook, Instagram):",
                 anchor="w").pack(fill="x", padx=10, pady=(10, 0))
        self.urls_text = scrolledtext.ScrolledText(self.root, height=6, wrap="none",
                                                   font=("Consolas", 11))
        self.urls_text.pack(fill="x", padx=10, pady=(2, 2))

        url_btns = tk.Frame(self.root)
        url_btns.pack(fill="x", padx=10, pady=(0, 6))
        tk.Button(url_btns, text="📄 Load links from file…",
                  command=self._load_links_file).pack(side="left")
        tk.Button(url_btns, text="Clear",
                  command=self._clear_links).pack(side="left", padx=6)
        self.link_count_var = tk.StringVar(value="")
        tk.Label(url_btns, textvariable=self.link_count_var,
                 fg="#5b6570").pack(side="left", padx=8)
        self.urls_text.bind("<KeyRelease>", lambda e: self._update_link_count())

        # ---- Output folder ----
        out_frame = tk.Frame(self.root)
        out_frame.pack(fill="x", padx=10)
        tk.Label(out_frame, text="Output folder:").pack(side="left")
        self.output_var = tk.StringVar(value=str(Path.home() / "Downloads"))
        tk.Entry(out_frame, textvariable=self.output_var).pack(
            side="left", fill="x", expand=True, padx=6)
        tk.Button(out_frame, text="Choose…", command=self._choose_folder).pack(side="left")

        # ---- Naming ----
        name_frame = tk.LabelFrame(self.root, text="Naming")
        name_frame.pack(fill="x", padx=10, pady=6)
        self.naming_var = tk.StringVar(value="title_id")
        tk.Radiobutton(name_frame, text="Title only", variable=self.naming_var,
                       value="title").pack(side="left", **pad)
        tk.Radiobutton(name_frame, text="Title + ID (recommended)",
                       variable=self.naming_var, value="title_id").pack(side="left", **pad)
        self.number_var = tk.BooleanVar(value=True)
        tk.Checkbutton(name_frame, text="Add number prefix (001, 002, …)",
                       variable=self.number_var).pack(side="left", **pad)
        self.subfolder_var = tk.BooleanVar(value=True)
        tk.Checkbutton(name_frame, text="Subfolder per uploader",
                       variable=self.subfolder_var).pack(side="left", **pad)

        # ---- Options ----
        opt = tk.LabelFrame(self.root, text="Options")
        opt.pack(fill="x", padx=10, pady=6)

        row1 = tk.Frame(opt); row1.pack(fill="x")
        tk.Label(row1, text="Quality:", width=16, anchor="w").pack(side="left", **pad)
        self.quality_var = tk.StringVar(value=self.QUALITY_OPTIONS[0])
        ttk.Combobox(row1, textvariable=self.quality_var, values=self.QUALITY_OPTIONS,
                     state="readonly", width=18).pack(side="left", **pad)
        self.thumb_var = tk.BooleanVar(value=False)
        tk.Checkbutton(row1, text="Save thumbnails", variable=self.thumb_var).pack(side="left", **pad)
        self.archive_var = tk.BooleanVar(value=True)
        tk.Checkbutton(row1, text="Skip already-downloaded (archive) — only get NEW videos",
                       variable=self.archive_var).pack(side="right", **pad)

        row2 = tk.Frame(opt); row2.pack(fill="x")
        tk.Label(row2, text="Max items (0 = all):", width=16, anchor="w").pack(side="left", **pad)
        self.max_var = tk.StringVar(value="0")
        tk.Entry(row2, textvariable=self.max_var, width=8).pack(side="left", **pad)
        tk.Label(row2, text="(e.g. 100 to grab the latest 100 from a profile)",
                 fg="#666").pack(side="left", **pad)

        row3 = tk.Frame(opt); row3.pack(fill="x")
        tk.Label(row3, text="Proxy (optional):", width=16, anchor="w").pack(side="left", **pad)
        self.proxy_var = tk.StringVar(value="")
        tk.Entry(row3, textvariable=self.proxy_var).pack(side="left", fill="x", expand=True, **pad)

        row4 = tk.Frame(opt); row4.pack(fill="x")
        self.impersonate_var = tk.BooleanVar(value=True)
        tk.Checkbutton(row4, text="Enable impersonation (TikTok / Facebook fix)",
                       variable=self.impersonate_var).pack(side="left", **pad)
        self.browser_cookies_var = tk.BooleanVar(value=False)
        tk.Checkbutton(row4, text="Use browser cookies", variable=self.browser_cookies_var
                       ).pack(side="left", **pad)
        tk.Label(row4, text="Browser:").pack(side="left", **pad)
        self.browser_var = tk.StringVar(value="chrome")
        ttk.Combobox(row4, textvariable=self.browser_var, values=self.BROWSER_OPTIONS,
                     state="readonly", width=10).pack(side="left", **pad)

        row5 = tk.Frame(opt); row5.pack(fill="x")
        tk.Label(row5, text="Cookies file (.txt, optional — for private / age-restricted):",
                 anchor="w").pack(side="left", **pad)
        self.cookies_var = tk.StringVar(value="")
        tk.Entry(row5, textvariable=self.cookies_var).pack(side="left", fill="x", expand=True, **pad)
        tk.Button(row5, text="Browse…", command=self._choose_cookies).pack(side="left", **pad)

        # ---- Action buttons ----
        btns = tk.Frame(self.root); btns.pack(fill="x", padx=10, pady=8)
        self.start_btn = tk.Button(btns, text="▶ Start Download", width=16,
                                   command=self._start_download)
        self.start_btn.pack(side="left", padx=4)
        self.stop_btn = tk.Button(btns, text="■ Stop", width=10, state="disabled",
                                  command=self._stop_download)
        self.stop_btn.pack(side="left", padx=4)
        tk.Button(btns, text="⟳ Update yt-dlp", command=self._update_ytdlp).pack(side="left", padx=4)
        tk.Button(btns, text="🗑 Clear archive (re-download all)",
                  command=self._clear_archive).pack(side="left", padx=4)

        # ---- Progress + status ----
        self.progress = ttk.Progressbar(self.root, mode="determinate", maximum=100)
        self.progress.pack(fill="x", padx=10, pady=(4, 0))
        self.status_var = tk.StringVar(value="Idle")
        tk.Label(self.root, textvariable=self.status_var, anchor="w",
                 fg="#0a5").pack(fill="x", padx=10)

        # ---- Log ----
        tk.Label(self.root, text="Log  (scroll to see the full history):",
                 anchor="w", font=("Segoe UI", 10, "bold")).pack(
                     fill="x", padx=10, pady=(6, 0))
        self.log_text = scrolledtext.ScrolledText(
            self.root, height=16, wrap="word",
            bg="#111", fg="#e6e6e6", insertbackground="#e6e6e6",
            font=("Consolas", 11))
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(2, 10))

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------- settings
    def _load_settings(self):
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            except Exception:
                return
            self.output_var.set(data.get("output", self.output_var.get()))
            self.naming_var.set(data.get("naming", self.naming_var.get()))
            self.number_var.set(data.get("number", self.number_var.get()))
            self.subfolder_var.set(data.get("subfolder", self.subfolder_var.get()))
            self.quality_var.set(data.get("quality", self.quality_var.get()))
            self.thumb_var.set(data.get("thumb", self.thumb_var.get()))
            self.archive_var.set(data.get("archive", self.archive_var.get()))
            self.max_var.set(data.get("max", self.max_var.get()))
            self.proxy_var.set(data.get("proxy", self.proxy_var.get()))
            self.impersonate_var.set(data.get("impersonate", self.impersonate_var.get()))
            self.browser_cookies_var.set(data.get("browser_cookies", self.browser_cookies_var.get()))
            self.browser_var.set(data.get("browser", self.browser_var.get()))
            self.cookies_var.set(data.get("cookies", self.cookies_var.get()))

    def _save_settings(self):
        data = {
            "output": self.output_var.get(),
            "naming": self.naming_var.get(),
            "number": self.number_var.get(),
            "subfolder": self.subfolder_var.get(),
            "quality": self.quality_var.get(),
            "thumb": self.thumb_var.get(),
            "archive": self.archive_var.get(),
            "max": self.max_var.get(),
            "proxy": self.proxy_var.get(),
            "impersonate": self.impersonate_var.get(),
            "browser_cookies": self.browser_cookies_var.get(),
            "browser": self.browser_var.get(),
            "cookies": self.cookies_var.get(),
        }
        try:
            CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    # ---------------------------------------------------------------- log
    def log(self, msg):
        self.log_queue.put(msg)

    def _drain_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.insert("end", msg + "\n")
                self.log_text.see("end")
                # Try to update the progress bar from yt-dlp's [download] lines
                m = re.search(r"\[download\]\s+([\d.]+)%", msg)
                if m:
                    try:
                        self.progress["value"] = float(m.group(1))
                    except Exception:
                        pass
        except queue.Empty:
            pass
        self.root.after(100, self._drain_log_queue)

    def set_status(self, text, color="#0a5"):
        self.status_var.set(text)

    # ------------------------------------------------------- file pickers
    def _update_link_count(self):
        n = len([l for l in self.urls_text.get("1.0", "end").splitlines() if l.strip()])
        self.link_count_var.set(f"{n} link(s)" if n else "")

    def _clear_links(self):
        self.urls_text.delete("1.0", "end")
        self._update_link_count()

    def _load_links_file(self):
        f = filedialog.askopenfilename(
            title="Choose a links .txt file (e.g. fb_links.txt)",
            filetypes=[("Text file", "*.txt"), ("All files", "*.*")])
        if not f:
            return
        try:
            content = Path(f).read_text(encoding="utf-8", errors="replace").strip()
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Could not read file:\n{e}")
            return
        existing = self.urls_text.get("1.0", "end").strip()
        if existing:
            append = messagebox.askyesno(
                APP_NAME,
                "There are already links in the box.\n\n"
                "Yes  = ADD these to them\n"
                "No   = REPLACE them with the new file")
            if append:
                self.urls_text.insert("end", "\n" + content + "\n")
            else:
                self.urls_text.delete("1.0", "end")
                self.urls_text.insert("1.0", content + "\n")
        else:
            self.urls_text.delete("1.0", "end")
            self.urls_text.insert("1.0", content + "\n")
        self._update_link_count()
        self.log(f"Loaded links from: {f}")

    def _choose_folder(self):
        d = filedialog.askdirectory(initialdir=self.output_var.get() or str(Path.home()))
        if d:
            self.output_var.set(d)

    def _choose_cookies(self):
        f = filedialog.askopenfilename(
            filetypes=[("Cookies file", "*.txt"), ("All files", "*.*")])
        if f:
            self.cookies_var.set(f)

    # --------------------------------------------------- tool management
    def _ensure_tools(self):
        """Download yt-dlp.exe and ffmpeg on first run if missing."""
        if not IS_WINDOWS:
            # On non-Windows we just rely on system yt-dlp / ffmpeg if present.
            if shutil.which("yt-dlp"):
                self.log("Using system yt-dlp.")
            else:
                self.log("WARNING: yt-dlp not found on PATH. Install with: pip install yt-dlp")
            return
        try:
            if self.ytdlp_bin.exists():
                self.log(f"yt-dlp found ({self.ytdlp_bin}).")
            else:
                self.log("First run: downloading yt-dlp.exe …")
                self.set_status("Downloading yt-dlp…")
                YTDLP_BIN.parent.mkdir(parents=True, exist_ok=True)
                urllib.request.urlretrieve(YTDLP_URL, YTDLP_BIN)
                self.ytdlp_bin = YTDLP_BIN
                self.log("yt-dlp.exe ready.")

            if self.ffmpeg_bin.exists():
                self.log("ffmpeg found.")
            else:
                self.log("First run: downloading ffmpeg (needed for HD merging / mp3) …")
                self.set_status("Downloading ffmpeg…")
                self._download_ffmpeg()
                self.ffmpeg_dir = FFMPEG_DIR
                self.ffmpeg_bin = FFMPEG_BIN
                self.log("ffmpeg ready.")
            self.set_status("Idle")
        except Exception as e:
            self.log(f"ERROR setting up tools: {e}")
            self.log("You can still try downloading; some HD/audio features may not work.")
            self.set_status("Idle")

    def _download_ffmpeg(self):
        zip_path = APP_DIR / "ffmpeg.zip"
        urllib.request.urlretrieve(FFMPEG_ZIP_URL, zip_path)
        FFMPEG_DIR.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as z:
            for member in z.namelist():
                name = os.path.basename(member)
                if name.lower() in ("ffmpeg.exe", "ffprobe.exe"):
                    with z.open(member) as src, open(FFMPEG_DIR / name, "wb") as dst:
                        shutil.copyfileobj(src, dst)
        try:
            zip_path.unlink()
        except Exception:
            pass

    def _ytdlp_cmd_base(self):
        if IS_WINDOWS and self.ytdlp_bin.exists():
            return [str(self.ytdlp_bin)]
        # fall back to system yt-dlp
        return ["yt-dlp"]

    def _update_ytdlp(self):
        if self.is_running:
            messagebox.showinfo(APP_NAME, "Please wait for the current download to finish.")
            return
        def run():
            self.log("Updating yt-dlp…")
            self.set_status("Updating yt-dlp…")
            try:
                if IS_WINDOWS and self.ytdlp_bin.exists():
                    # standalone binary self-update
                    cmd = [str(self.ytdlp_bin), "-U"]
                else:
                    cmd = [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"]
                p = subprocess.run(cmd, capture_output=True, text=True,
                                   creationflags=CREATE_NO_WINDOW if IS_WINDOWS else 0)
                for line in (p.stdout + p.stderr).splitlines():
                    if line.strip():
                        self.log(line)
                self.log("yt-dlp update finished.")
            except Exception as e:
                self.log(f"Update failed: {e}")
            finally:
                self.set_status("Idle")
        threading.Thread(target=run, daemon=True).start()

    def _clear_archive(self):
        out = Path(self.output_var.get())
        archive = out / ARCHIVE_NAME
        if not archive.exists():
            messagebox.showinfo(APP_NAME, "No archive found for this output folder.")
            return
        if messagebox.askyesno(
                APP_NAME,
                "This will forget what has been downloaded in this folder.\n"
                "Next download will fetch ALL videos again (duplicates possible).\n\n"
                "Continue?"):
            try:
                archive.unlink()
                self.log(f"Archive cleared: {archive}")
            except Exception as e:
                self.log(f"Could not clear archive: {e}")

    # ----------------------------------------------------- build yt-dlp args
    def _output_template(self):
        parts = []
        if self.subfolder_var.get():
            parts.append("%(uploader,channel,id)s")
        prefix = "%(autonumber)03d - " if self.number_var.get() else ""
        if self.naming_var.get() == "title":
            name = f"{prefix}%(title).80s.%(ext)s"
        else:
            name = f"{prefix}%(title).80s [%(id)s].%(ext)s"
        parts.append(name)
        return os.path.join(*parts) if len(parts) > 1 else parts[0]

    def _format_args(self):
        q = self.quality_var.get()
        if q == "Audio only (mp3)":
            return ["-x", "--audio-format", "mp3"]
        if q == "1080p":
            return ["-f", "bv*[height<=1080]+ba/b[height<=1080]/b"]
        if q == "720p":
            return ["-f", "bv*[height<=720]+ba/b[height<=720]/b"]
        if q == "480p":
            return ["-f", "bv*[height<=480]+ba/b[height<=480]/b"]
        # Best (auto)
        return ["-f", "bv*+ba/b"]

    def _normalize_input(self, line):
        """Turn a bare @handle / username into a usable URL (defaults to TikTok)."""
        line = line.strip()
        if not line:
            return None
        if line.startswith("http://") or line.startswith("https://"):
            return line
        # bare handle -> TikTok profile (user's primary use case)
        handle = line.lstrip("@")
        return f"https://www.tiktok.com/@{handle}"

    def _check_url(self, url):
        """Return (ok, advice). ok=False means we warn but still let yt-dlp try.

        The big one: yt-dlp can download a SINGLE Facebook video/reel, but it
        cannot list every video on a Facebook page/profile. We detect that and
        tell the user plainly instead of letting a confusing error scroll by.
        """
        u = url.lower()

        # ---- Facebook ----
        if "facebook.com" in u or "fb.watch" in u or "fb.com" in u:
            single_markers = ["/videos/", "/reel/", "/watch", "/share/v/",
                              "story_fbid=", "/posts/", "v=", "fb.watch"]
            is_single = any(m in u for m in single_markers) and not u.rstrip("/").endswith("/videos")
            page_markers = ["profile.php", "/people/", "sk=reels_tab",
                           "/reels", "?sk=", "/videos"]
            looks_like_page = any(m in u for m in page_markers)
            if looks_like_page and not is_single:
                return (False,
                    "  ⚠ Facebook PROFILE/PAGE links cannot be bulk-downloaded.\n"
                    "    yt-dlp can only grab ONE Facebook video at a time.\n"
                    "    Open a specific video or reel on that page, copy its link\n"
                    "    (it will look like facebook.com/reel/123…  or  .../videos/123…)\n"
                    "    and paste those individual links here instead.")
            # single FB video usually needs cookies / impersonation
            return (True,
                "  ℹ Facebook video: if it fails, tick 'Use browser cookies' (Chrome\n"
                "    logged into Facebook) — FB blocks logged-out downloads.")

        # ---- YouTube ----
        if "youtube.com" in u or "youtu.be" in u:
            if not (self.browser_cookies_var.get() or self.cookies_var.get().strip()):
                return (True,
                    "  ℹ YouTube tip: if you see 'Sign in to confirm you're not a bot',\n"
                    "    tick 'Use browser cookies' (Chrome) and run again.")
            return (True, None)

        return (True, None)

    def _build_command(self, url, output_dir):
        cmd = self._ytdlp_cmd_base()
        cmd += ["--newline", "--no-warnings", "--ignore-errors"]
        cmd += ["-o", os.path.join(output_dir, self._output_template())]
        cmd += self._format_args()

        # ffmpeg location
        if IS_WINDOWS and self.ffmpeg_bin.exists():
            cmd += ["--ffmpeg-location", str(self.ffmpeg_dir)]

        # Archive (the "only new videos" feature)
        if self.archive_var.get():
            archive = os.path.join(output_dir, ARCHIVE_NAME)
            cmd += ["--download-archive", archive]

        # Max items
        try:
            mx = int(self.max_var.get().strip() or "0")
        except ValueError:
            mx = 0
        if mx > 0:
            cmd += ["--playlist-end", str(mx)]

        # Thumbnails
        if self.thumb_var.get():
            cmd += ["--write-thumbnail"]

        # Proxy
        if self.proxy_var.get().strip():
            cmd += ["--proxy", self.proxy_var.get().strip()]

        # Impersonation (TikTok / Facebook fix)
        if self.impersonate_var.get():
            cmd += ["--impersonate", "chrome"]

        # Cookies — prefer an explicit cookies.txt file (most reliable on Windows;
        # --cookies-from-browser fails when Chrome is open or uses new encryption)
        if self.cookies_var.get().strip():
            cmd += ["--cookies", self.cookies_var.get().strip()]
        elif self.browser_cookies_var.get():
            cmd += ["--cookies-from-browser", self.browser_var.get()]

        cmd.append(url)
        return cmd

    # --------------------------------------------------------- download flow
    def _start_download(self):
        if self.is_running:
            return
        raw = self.urls_text.get("1.0", "end").strip()
        if not raw:
            messagebox.showwarning(APP_NAME, "Please paste at least one link.")
            return
        output_dir = self.output_var.get().strip()
        if not output_dir:
            messagebox.showwarning(APP_NAME, "Please choose an output folder.")
            return
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        urls = [self._normalize_input(l) for l in raw.splitlines()]
        urls = [u for u in urls if u]

        # Cookies file path is machine-specific — warn early if it's missing here
        cpath = self.cookies_var.get().strip()
        if cpath and not Path(cpath).exists():
            self.log(f"⚠ Cookies file not found on this PC: {cpath}")
            self.log("  Export a fresh cookies.txt with the AJ Tech extension on THIS "
                     "computer and pick it in the 'Cookies file' box, or downloads may fail.")

        self._save_settings()
        self.is_running = True
        self.stop_event.clear()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.progress["value"] = 0
        self.log("=" * 60)
        self.log(f"Starting: {len(urls)} link(s)")

        threading.Thread(target=self._run_all, args=(urls, output_dir), daemon=True).start()

    def _run_all(self, urls, output_dir):
        total = len(urls)
        self._ok_count = 0
        self._fail_count = 0
        for idx, url in enumerate(urls, 1):
            if self.stop_event.is_set():
                break
            try:
                self._run_one(idx, total, url, output_dir)
            except Exception as e:
                # One bad link must never stop the whole batch
                self._fail_count += 1
                self.log(f"✖ Error on {url}: {e}")
        self._finish()

    def _run_one(self, idx, total, url, output_dir):
        ok, advice = self._check_url(url)
        if advice:
            self.log(advice)
        if not ok:
            self.log(f"⏭ Skipped (not a downloadable link): {url}\n")
            return

        self.set_status(f"Downloading {idx}/{total}: {url}")
        self.log(f"\n--- [{idx}/{total}] {url} ---")
        cmd = self._build_command(url, output_dir)

        done_event = threading.Event()
        saw_error = {"unsupported": False, "bot": False, "cookiedb": False}

        def on_line(line):
            low = line.lower()
            if "unsupported url" in low:
                saw_error["unsupported"] = True
            if "sign in to confirm" in low or "not a bot" in low:
                saw_error["bot"] = True
            if "could not copy chrome cookie" in low or "cookie database" in low:
                saw_error["cookiedb"] = True
            self.log(line)

        def on_done(code):
            if code == 0:
                self._ok_count += 1
                self.log(f"✔ Finished: {url}")
            else:
                self._fail_count += 1
                self.log(f"✖ Exit code {code} for: {url}")
                if saw_error["cookiedb"]:
                    self.log("   → Chrome's cookies are locked/encrypted. UNtick "
                             "'Use browser cookies', export a cookies.txt with the "
                             "AJ Tech extension, and load it in the 'Cookies file' box.")
                if saw_error["unsupported"]:
                    self.log("   → This link isn't a single downloadable video. "
                             "For Facebook, use an individual reel/video link.")
                if saw_error["bot"]:
                    self.log("   → Login needed. Load a cookies.txt file in the "
                             "'Cookies file' box and try again.")
            done_event.set()

        self.proc = stream_command(cmd, on_line, on_done, self.stop_event)
        done_event.wait()  # wait for this URL to finish before the next

    def _finish(self):
        self.is_running = False
        self.proc = None
        self.root.after(0, lambda: self.start_btn.config(state="normal"))
        self.root.after(0, lambda: self.stop_btn.config(state="disabled"))
        if self.stop_event.is_set():
            self.set_status("Stopped.")
            self.log("\nStopped by user.")
        else:
            self.set_status("All done. Idle.")
            ok = getattr(self, "_ok_count", 0)
            fail = getattr(self, "_fail_count", 0)
            self.log(f"\nAll downloads finished.  ✔ {ok} succeeded   ✖ {fail} failed.")
            if fail and ok == 0:
                self.log("Everything failed — this is almost always a cookies problem. "
                         "Export a fresh cookies.txt on THIS computer and load it in the "
                         "'Cookies file' box.")
            self.root.after(0, lambda: self.progress.config(value=100))

    def _stop_download(self):
        self.stop_event.set()
        if self.proc:
            try:
                self.proc.kill()
            except Exception:
                pass
        self.log("Stopping…")

    def _on_close(self):
        self._save_settings()
        self.stop_event.set()
        if self.proc:
            try:
                self.proc.kill()
            except Exception:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()
    DownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
