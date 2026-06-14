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

import time
from pathlib import Path

from .base import VideoGenerator, GenerationError, LogFn
from ..config import FLOW_SESSION_FILE

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

    # -- one-time interactive login -----------------------------------------
    def capture_session(self, log: LogFn = print) -> None:
        """Open a real browser, let the user log in, then save the session.

        Call this from the GUI's 'Connect Google Flow' button. It blocks until
        the user has signed in and pressed Enter / closed the helper.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:  # pragma: no cover
            raise GenerationError(
                "Playwright is required. Run: pip install playwright && playwright install chromium"
            ) from e

        log("Opening a browser window. Please sign in to Google Flow...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            page.goto(FLOW_URL, wait_until="domcontentloaded")
            log("Waiting for you to finish signing in (up to 5 minutes)...")
            # Wait until the prompt box appears, which means we're inside Flow.
            try:
                page.wait_for_selector(SELECTORS["prompt_box"], timeout=5 * 60 * 1000)
            except Exception as e:
                browser.close()
                raise GenerationError("Did not detect a signed-in Flow session in time.") from e
            context.storage_state(path=str(FLOW_SESSION_FILE))
            browser.close()
        log("Google Flow session saved. You won't need to sign in again unless it expires.")

    # -- the actual generation ----------------------------------------------
    def generate(self, prompt: str, out_path: Path, log: LogFn = print) -> Path:
        ready, reason = self.is_ready()
        if not ready:
            raise GenerationError(reason)

        from playwright.sync_api import sync_playwright

        log(f"Generating video for prompt: {prompt!r}")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state=str(FLOW_SESSION_FILE))
            page = context.new_page()
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
                browser.close()

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
