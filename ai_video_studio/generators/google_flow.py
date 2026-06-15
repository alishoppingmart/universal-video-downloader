"""
Google Flow generator
======================
Drives the Google Flow website (https://labs.google/flow) with a headless
browser to turn a text prompt into a video, using your free daily credits.

IMPORTANT — how login works (and why it's done this way):
    Google blocks automated password logins, especially from data-center IPs,
    and storing your Google password would be unsafe. So instead you log in
    ONCE, by hand, in a real browser window that this module opens for you
    (`capture_session`). We save only the resulting *session cookies* to
    ~/.ai_video_studio/flow_session.json and reuse them. Your password is
    never seen or stored by this app.

    Because Google ties sessions loosely to your network, the most reliable
    place to run generation is YOUR OWN computer (home internet). Running this
    step on cloud servers will usually trip Google's "suspicious login"
    protection.

NOTE ON SELECTORS:
    Flow is a live product and its page can change. All the bits that depend
    on the exact page layout are grouped in the SELECTORS dict below, so they
    are easy to update in one place if Google moves things around.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from .base import VideoGenerator, GenerationError, LogFn
from ..config import FLOW_SESSION_FILE, FLOW_PROFILE_DIR, BROWSERS_DIR

# Flags that hide the "I'm an automated browser" signals Google looks for.
STEALTH_ARGS = ["--disable-blink-features=AutomationControlled"]
IGNORE_ARGS = ["--enable-automation"]

# Tell Playwright to keep its downloaded browser in our app folder (writable by
# a packaged .exe). MUST be set before Playwright is imported anywhere.
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(BROWSERS_DIR))

FLOW_URL = "https://labs.google/fx/tools/flow"

# Everything page-layout-specific lives here so it's easy to maintain.
SELECTORS = {
    "prompt_box": "textarea, [contenteditable='true']",
    "generate_button": "button:has-text('Generate'), button:has-text('Create')",
    "result_video": "video",
    "credits_exhausted": "text=/out of credits|no credits|daily limit/i",
}

GENERATION_TIMEOUT_S = 8 * 60  # Flow can take several minutes per clip.


class GoogleFlowGenerator(VideoGenerator):
    name = "Google Flow"

    def is_ready(self) -> tuple[bool, str]:
        if not FLOW_SESSION_FILE.exists():
            return False, (
                "Not logged in to Google Flow yet. Click 'Connect Google Flow' "
                "to sign in once in a browser window."
            )
        try:
            import playwright  # noqa: F401
        except ImportError:
            return False, "Playwright not installed. Run: pip install playwright && playwright install chromium"
        return True, "Ready"

    # -- make sure the browser engine is present (auto-download once) -------
    def _ensure_browser(self, log: LogFn = print) -> None:
        """Download Chromium on first use so the packaged .exe just works.

        Happens once (~150 MB, needs internet). Subsequent runs skip it.
        """
        BROWSERS_DIR.mkdir(parents=True, exist_ok=True)
        if any(BROWSERS_DIR.glob("chromium-*")):
            return  # already installed
        log("First-time setup: downloading the browser engine (~150 MB). One time only...")
        try:
            # Works both from source and inside a PyInstaller build that was
            # packaged with '--collect-all playwright'.
            from playwright.__main__ import main as pw_main
            saved_argv = sys.argv
            sys.argv = ["playwright", "install", "chromium"]
            try:
                pw_main()
            except SystemExit:
                pass
            finally:
                sys.argv = saved_argv
        except Exception:
            # Fallback for a normal Python install (not frozen).
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                check=False,
            )
        if not any(BROWSERS_DIR.glob("chromium-*")):
            raise GenerationError(
                "Could not download the browser engine. Check your internet "
                "connection and try 'Connect Google Flow' again."
            )
        log("Browser engine ready.")

    # -- shared browser launcher --------------------------------------------
    def _launch_context(self, p, headless: bool, log: LogFn):
        """Open a persistent browser profile that looks like a normal browser.

        Uses the real Google Chrome you already have installed when possible
        (Google trusts it far more than a bundled/automation browser), and
        reuses one profile folder so your login sticks.
        """
        FLOW_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        common = dict(
            user_data_dir=str(FLOW_PROFILE_DIR),
            headless=headless,
            args=STEALTH_ARGS,
            ignore_default_args=IGNORE_ARGS,
            viewport={"width": 1280, "height": 820},
        )
        # Prefer the user's installed Chrome; fall back to the bundled engine.
        try:
            return p.chromium.launch_persistent_context(channel="chrome", **common)
        except Exception as e:
            log(f"Couldn't use installed Chrome ({e}); using the bundled browser.")
            self._ensure_browser(log)
            return p.chromium.launch_persistent_context(**common)

    # -- one-time interactive login -----------------------------------------
    def capture_session(self, log: LogFn = print) -> None:
        """Open a real browser, let the user log in, then remember the session.

        Called by the GUI's 'Connect Google Flow' button. Blocks until you've
        signed in and Flow has loaded (up to 5 minutes).
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:  # pragma: no cover
            raise GenerationError(
                "Playwright is required. Run: pip install playwright && playwright install chromium"
            ) from e

        log("Opening Chrome. If you're already signed in to Google, Flow just opens.")
        log("If asked, sign in normally. (Using real Chrome avoids Google's security block.)")
        with sync_playwright() as p:
            context = self._launch_context(p, headless=False, log=log)
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(FLOW_URL, wait_until="domcontentloaded")
            log("Waiting for Flow to load (sign in if needed)...")
            try:
                page.wait_for_selector(SELECTORS["prompt_box"], timeout=5 * 60 * 1000)
            except Exception as e:
                context.close()
                raise GenerationError(
                    "Didn't reach the Flow page in time. If Google said 'browser may not "
                    "be secure', make sure Google Chrome is installed and you're signed "
                    "into your Google account in normal Chrome first."
                ) from e
            # Persist a storage-state marker (the profile folder holds the real login).
            context.storage_state(path=str(FLOW_SESSION_FILE))
            context.close()
        log("Connected to Google Flow. You won't need to sign in again unless it expires.")

    # -- the actual generation ----------------------------------------------
    def generate(self, prompt: str, out_path: Path, log: LogFn = print) -> Path:
        ready, reason = self.is_ready()
        if not ready:
            raise GenerationError(reason)

        from playwright.sync_api import sync_playwright

        log(f"Generating video for prompt: {prompt!r}")
        with sync_playwright() as p:
            # Reuse the same logged-in profile from 'Connect Google Flow'.
            context = self._launch_context(p, headless=True, log=log)
            page = context.pages[0] if context.pages else context.new_page()
            try:
                page.goto(FLOW_URL, wait_until="domcontentloaded")

                if page.locator(SELECTORS["credits_exhausted"]).count() > 0:
                    raise GenerationError("Google Flow reports your daily free credits are used up.")

                box = page.locator(SELECTORS["prompt_box"]).first
                box.wait_for(timeout=60_000)
                box.click()
                box.fill(prompt)
                log("Prompt entered, starting generation...")
                page.locator(SELECTORS["generate_button"]).first.click()

                # Wait for a finished video element with a real source URL.
                video_url = self._wait_for_result(page, log)
                log("Video ready, downloading...")
                self._download(context, video_url, out_path, log)
                return out_path
            except GenerationError:
                raise
            except Exception as e:  # pragma: no cover - live-site fragility
                raise GenerationError(
                    f"Flow automation failed: {e}. The site layout may have changed; "
                    f"update SELECTORS in generators/google_flow.py."
                ) from e
            finally:
                context.close()

    def _wait_for_result(self, page, log: LogFn) -> str:
        deadline = time.time() + GENERATION_TIMEOUT_S
        while time.time() < deadline:
            try:
                vid = page.locator(SELECTORS["result_video"]).first
                if vid.count() > 0:
                    src = vid.get_attribute("src")
                    if src and src.startswith("http"):
                        return src
            except Exception:
                pass
            log("...still rendering...")
            time.sleep(10)
        raise GenerationError("Timed out waiting for Flow to finish the video.")

    def _download(self, context, url: str, out_path: Path, log: LogFn) -> None:
        # Reuse the browser's authenticated context so the URL is fetchable.
        resp = context.request.get(url)
        if not resp.ok:
            raise GenerationError(f"Could not download finished video (HTTP {resp.status}).")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(resp.body())
        log(f"Saved {out_path.stat().st_size // 1024} KB to {out_path}")
