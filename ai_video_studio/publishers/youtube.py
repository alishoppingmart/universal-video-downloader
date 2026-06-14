"""
YouTube publisher (official YouTube Data API v3)
================================================
Uploads the video as a public Short. A clip is treated as a Short by YouTube
automatically when it is vertical and <= 60s; adding #Shorts to the title/desc
also helps.

One-time setup you must do (documented in docs/SETUP.md):
  1. Create a Google Cloud project, enable "YouTube Data API v3".
  2. Create an OAuth client (Desktop app) -> get client_id + client_secret.
  3. Run the app's "Connect YouTube" button once to authorize -> this stores a
     refresh_token. After that, uploads run unattended (also in the cloud).
"""

from __future__ import annotations

from pathlib import Path

from .base import Publisher, PublishError, PublishResult, LogFn
from ..config import load_secrets, save_secrets

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


class YouTubePublisher(Publisher):
    name = "YouTube"

    def is_ready(self) -> tuple[bool, str]:
        s = load_secrets()
        if not s.get("youtube_client_id") or not s.get("youtube_client_secret"):
            return False, "Missing YouTube client id/secret. See docs/SETUP.md."
        if not s.get("youtube_refresh_token"):
            return False, "Not authorized yet. Click 'Connect YouTube' to sign in once."
        return True, "Ready"

    # -- one-time interactive authorization ---------------------------------
    def authorize(self, log: LogFn = print) -> None:
        """Run the OAuth consent flow once and store the refresh token."""
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ImportError as e:
            raise PublishError("Run: pip install google-auth-oauthlib") from e

        s = load_secrets()
        if not s.get("youtube_client_id") or not s.get("youtube_client_secret"):
            raise PublishError("Enter your YouTube client id and secret first.")

        client_config = {
            "installed": {
                "client_id": s["youtube_client_id"],
                "client_secret": s["youtube_client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        }
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        log("A browser window will open. Approve access to your YouTube channel...")
        creds = flow.run_local_server(port=0)
        s["youtube_refresh_token"] = creds.refresh_token
        save_secrets(s)
        log("YouTube connected. Refresh token saved.")

    # -- upload --------------------------------------------------------------
    def publish(self, video: Path, title: str, description: str, log: LogFn = print) -> PublishResult:
        ready, reason = self.is_ready()
        if not ready:
            raise PublishError(reason)
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
        except ImportError as e:
            raise PublishError("Run: pip install google-api-python-client google-auth") from e

        s = load_secrets()
        creds = Credentials(
            token=None,
            refresh_token=s["youtube_refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=s["youtube_client_id"],
            client_secret=s["youtube_client_secret"],
            scopes=SCOPES,
        )
        youtube = build("youtube", "v3", credentials=creds)

        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:4900],
                "categoryId": "22",
            },
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
        }
        media = MediaFileUpload(str(video), chunksize=-1, resumable=True, mimetype="video/mp4")
        log(f"Uploading '{title}' to YouTube...")
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                log(f"  ...{int(status.progress() * 100)}%")
        vid = response["id"]
        url = f"https://youtube.com/shorts/{vid}"
        log(f"Published to YouTube: {url}")
        return PublishResult(platform="youtube", id=vid, url=url)
