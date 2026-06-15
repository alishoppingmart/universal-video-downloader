"""
AI Video Studio - mobile control panel (Kivy)

A phone can't run the Google Flow browser, so this app:
  * lets you manage your topics / schedule / platforms (same settings format
    as the desktop app), and
  * triggers the CLOUD (GitHub Actions) to generate + publish on demand,
    and shows the last run's status.

Storage: on Android we point HOME at the app's private folder so the shared
`ai_video_studio.config` writes somewhere we're allowed to.
"""

from __future__ import annotations

import os
import threading

# --- make the shared config write to a phone-writable folder ----------------
_android_home = os.environ.get("ANDROID_PRIVATE")
if _android_home:
    os.environ["HOME"] = _android_home

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.switch import Switch
from kivy.clock import Clock
from kivy.metrics import dp

from ai_video_studio.config import Settings, load_secrets, save_secrets
from .cloud import trigger_cloud_run, latest_run_status


def _row(label_text: str, widget) -> BoxLayout:
    row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(48), spacing=dp(8))
    row.add_widget(Label(text=label_text, size_hint_x=0.45, halign="left", valign="middle"))
    row.add_widget(widget)
    return row


def _heading(text: str) -> Label:
    return Label(text=f"[b]{text}[/b]", markup=True, size_hint_y=None, height=dp(40),
                 color=(0.2, 0.6, 1, 1))


class StudioMobile(App):
    title = "AI Video Studio"

    def build(self):
        self.settings = Settings.load()
        self.secrets = load_secrets()

        root = ScrollView()
        col = BoxLayout(orientation="vertical", size_hint_y=None, padding=dp(12), spacing=dp(8))
        col.bind(minimum_height=col.setter("height"))

        col.add_widget(Label(text="[b]AI Video Studio[/b]", markup=True,
                             size_hint_y=None, height=dp(48), font_size="22sp"))

        # --- Topics ---
        col.add_widget(_heading("Your video ideas (one per line)"))
        self.topics_in = TextInput(text="\n".join(self.settings.topics),
                                   size_hint_y=None, height=dp(140), multiline=True)
        col.add_widget(self.topics_in)

        # --- Schedule ---
        col.add_widget(_heading("Schedule"))
        self.posts_in = TextInput(text=str(self.settings.posts_per_day),
                                  multiline=False, input_filter="int")
        col.add_widget(_row("Videos / day:", self.posts_in))
        self.times_in = TextInput(text=", ".join(self.settings.schedule_times), multiline=False)
        col.add_widget(_row("Times (24h):", self.times_in))
        self.tags_in = TextInput(text=self.settings.hashtags, multiline=False)
        col.add_widget(_row("Hashtags:", self.tags_in))

        # --- Platforms ---
        col.add_widget(_heading("Publish to"))
        self.yt_sw = Switch(active=self.settings.publish_youtube)
        col.add_widget(_row("YouTube Shorts:", self.yt_sw))
        self.tt_sw = Switch(active=self.settings.publish_tiktok)
        col.add_widget(_row("TikTok:", self.tt_sw))

        col.add_widget(Button(text="Save settings", size_hint_y=None, height=dp(48),
                              on_release=lambda *_: self.save_settings()))

        # --- Cloud control ---
        col.add_widget(_heading("Cloud (GitHub Actions)"))
        self.repo_in = TextInput(text=self.secrets.get("github_repo", ""), multiline=False)
        col.add_widget(_row("Repo (owner/name):", self.repo_in))
        self.ref_in = TextInput(text=self.secrets.get("github_ref", "main"), multiline=False)
        col.add_widget(_row("Branch:", self.ref_in))
        self.token_in = TextInput(text=self.secrets.get("github_token", ""),
                                  multiline=False, password=True)
        col.add_widget(_row("GitHub token:", self.token_in))

        btns = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(48), spacing=dp(8))
        btns.add_widget(Button(text="Save cloud keys", on_release=lambda *_: self.save_cloud()))
        btns.add_widget(Button(text="Run now in cloud", on_release=lambda *_: self.run_cloud()))
        btns.add_widget(Button(text="Check status", on_release=lambda *_: self.check_status()))
        col.add_widget(btns)

        self.status = Label(text="Ready.", size_hint_y=None, height=dp(60),
                            halign="left", valign="top", text_size=(None, None))
        col.add_widget(self.status)

        root.add_widget(col)
        return root

    # -- helpers -------------------------------------------------------------
    def _set_status(self, msg: str) -> None:
        Clock.schedule_once(lambda *_: setattr(self.status, "text", msg))

    def _bg(self, fn):
        threading.Thread(target=fn, daemon=True).start()

    def _collect(self) -> Settings:
        s = self.settings
        s.topics = [t.strip() for t in self.topics_in.text.splitlines() if t.strip()]
        try:
            s.posts_per_day = max(1, int(self.posts_in.text or "1"))
        except ValueError:
            s.posts_per_day = 1
        s.schedule_times = [t.strip() for t in self.times_in.text.split(",") if t.strip()]
        s.hashtags = self.tags_in.text.strip()
        s.publish_youtube = self.yt_sw.active
        s.publish_tiktok = self.tt_sw.active
        return s

    # -- actions -------------------------------------------------------------
    def save_settings(self) -> None:
        self._collect().save()
        self._set_status("Settings saved on this device.")

    def save_cloud(self) -> None:
        self.secrets["github_repo"] = self.repo_in.text.strip()
        self.secrets["github_ref"] = self.ref_in.text.strip() or "main"
        self.secrets["github_token"] = self.token_in.text.strip()
        save_secrets(self.secrets)
        self._set_status("Cloud keys saved.")

    def run_cloud(self) -> None:
        self.save_cloud()
        self._set_status("Starting cloud run...")

        def work():
            ok, msg = trigger_cloud_run(
                self.secrets.get("github_repo", ""),
                self.secrets.get("github_token", ""),
                self.secrets.get("github_ref", "main"),
            )
            self._set_status(("OK: " if ok else "Error: ") + msg)

        self._bg(work)

    def check_status(self) -> None:
        self.save_cloud()

        def work():
            ok, msg = latest_run_status(
                self.secrets.get("github_repo", ""),
                self.secrets.get("github_token", ""),
            )
            self._set_status(msg if ok else "Error: " + msg)

        self._bg(work)


def run() -> None:
    StudioMobile().run()
