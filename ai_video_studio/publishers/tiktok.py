"""
TikTok publisher (official Content Posting API)
===============================================
Uploads the video via TikTok's "direct post" endpoint.

IMPORTANT — real-world limits you should know:
  * You must register an app at developers.tiktok.com and request the
    "content.posting" scope. Until your app is approved for direct posting,
    TikTok only allows uploading to your *draft inbox* (you then tap "post"
    in the TikTok app). The code supports both modes via `direct_post`.
  * Access tokens expire; this module refreshes using the stored refresh
    token when possible. The one-time authorization is done with the
    'Connect TikTok' button (see docs/SETUP.md).

This uses the FILE_UPLOAD flow (we send the local .mp4 bytes to TikTok).
"""

from __future__ import annotations

import os
from pathlib import Path

from .base import Publisher, PublishError, PublishResult, LogFn
from ..config import load_secrets

API = "https://open.tiktokapis.com/v2"


class TikTokPublisher(Publisher):
    name = "TikTok"

    def is_ready(self) -> tuple[bool, str]:
        s = load_secrets()
        if not s.get("tiktok_access_token"):
            return False, "Not connected. Click 'Connect TikTok' (needs an approved developer app). See docs/SETUP.md."
        return True, "Ready"

    def publish(self, video: Path, title: str, description: str, log: LogFn = print,
                direct_post: bool = True) -> PublishResult:
        ready, reason = self.is_ready()
        if not ready:
            raise PublishError(reason)
        try:
            import requests
        except ImportError as e:
            raise PublishError("Run: pip install requests") from e

        s = load_secrets()
        token = s["tiktok_access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        size = os.path.getsize(video)

        # 1) Initialise an upload. direct_post publishes straight to the profile;
        #    otherwise it lands in the app's drafts/inbox.
        endpoint = "/post/publish/video/init/" if direct_post else "/post/publish/inbox/video/init/"
        init_body = {
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": size,
                "chunk_size": size,
                "total_chunk_count": 1,
            }
        }
        if direct_post:
            init_body["post_info"] = {
                "title": f"{title} {description}".strip()[:2200],
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_comment": False,
            }

        log("Initialising TikTok upload...")
        r = requests.post(API + endpoint, headers=headers, json=init_body, timeout=60)
        data = self._json_or_raise(r)
        upload_url = data["data"]["upload_url"]
        publish_id = data["data"]["publish_id"]

        # 2) Upload the bytes to the URL TikTok gave us.
        log("Uploading video bytes to TikTok...")
        with open(video, "rb") as f:
            up = requests.put(
                upload_url,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Range": f"bytes 0-{size - 1}/{size}",
                },
                data=f,
                timeout=600,
            )
        if up.status_code not in (200, 201):
            raise PublishError(f"TikTok byte upload failed: HTTP {up.status_code} {up.text[:300]}")

        where = "your TikTok profile" if direct_post else "your TikTok drafts (open the app to post)"
        log(f"TikTok upload accepted (publish_id={publish_id}); it will appear on {where}.")
        return PublishResult(platform="tiktok", id=publish_id)

    @staticmethod
    def _json_or_raise(resp) -> dict:
        try:
            data = resp.json()
        except Exception as e:
            raise PublishError(f"TikTok returned non-JSON (HTTP {resp.status_code}): {resp.text[:300]}") from e
        err = data.get("error", {})
        if err and err.get("code") not in (None, "ok"):
            raise PublishError(f"TikTok error: {err.get('code')} - {err.get('message')}")
        if not resp.ok:
            raise PublishError(f"TikTok HTTP {resp.status_code}: {resp.text[:300]}")
        return data
