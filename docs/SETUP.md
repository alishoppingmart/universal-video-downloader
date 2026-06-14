# AI Video Studio — Setup Guide

This app turns your **topic ideas** into short videos with **Google Flow**, then
auto-publishes them to **YouTube Shorts** and **TikTok** on a schedule.

> **Status:** v0.1 — desktop foundation. The pieces below are wired up; you
> provide the account connections (these are one-time and unavoidable, because
> Google/YouTube/TikTok require *you* to authorize access to your own accounts).

---

## 1. Install / run

**Easiest (Windows):** download the `AIVideoStudio-Portable` build from the
GitHub Actions "Build AI Video Studio" run, unzip, double-click `AIVideoStudio.exe`.

**From source (any OS):**
```bash
pip install -r requirements.txt
playwright install chromium      # one-time, for Google Flow generation
python studio_app.py
```

---

## 2. Connect Google Flow (video generation)

1. In the app, open the **Accounts** tab → **Connect Google Flow**.
2. A browser window opens. Sign in to your Google account and open Flow.
3. Once you can see the Flow prompt box, the app saves your **session** (cookies
   only — *your password is never stored*).

⚠️ Run generation on **your own PC**. Google blocks logins from cloud servers,
so the cloud scheduler can't generate Flow videos (it can still publish).

---

## 3. Connect YouTube (one-time)

1. Go to <https://console.cloud.google.com/> → create a project.
2. **APIs & Services → Library** → enable **YouTube Data API v3**.
3. **APIs & Services → Credentials** → **Create credentials → OAuth client ID**
   → application type **Desktop app**. Copy the **Client ID** and **Client secret**.
4. In the app's **Accounts** tab, paste them and click **Save keys**, then
   **Connect YouTube** and approve access. Done — uploads now run unattended.

> Heads-up: brand-new Google Cloud projects are "unverified" and may cap you at
> ~6 uploads/day until you complete Google's verification. Fine for 1–2/day.

---

## 4. Connect TikTok (one-time)

1. Go to <https://developers.tiktok.com/> → create an app.
2. Add the **Content Posting API** product and request the `video.publish`
   (direct post) scope. *Until TikTok approves direct posting, uploads land in
   your TikTok **drafts** — you tap "Post" in the app.*
3. Complete the OAuth flow to get an **access token**, paste it in the
   **Accounts** tab → **Save token**.

---

## 5. Set topics & schedule

In the **Topics & Schedule** tab:
- Add one idea per line (e.g. `relaxing ocean waves at sunset`).
- Choose **videos per day** and the **times** (24-hour, comma-separated).
- Tick the platforms and set your hashtags → **Save settings**.

---

## 6. Run

- **Run tab → "Run one now"** to test the whole pipeline once.
- **"Start scheduler"** to keep posting on your times (while the app/PC is on).
- **"Check setup"** tells you exactly what's still not connected.

### Cloud 24/7 (optional, for publishing)
The repo includes `.github/workflows/daily-publish.yml`. Add your credentials as
GitHub **Actions secrets** (`AVS_YT_CLIENT_ID`, `AVS_YT_CLIENT_SECRET`,
`AVS_YT_REFRESH_TOKEN`, `AVS_TIKTOK_ACCESS_TOKEN`, …) and it will run on the cron
schedule even when your PC is off. (Generation still needs your PC — see §2.)

---

---

## 7. Mobile app (Android APK)

The phone app is a **control panel**: it manages your topics/schedule/accounts
and **triggers the cloud** to generate + publish (a phone can't run the Google
Flow browser itself).

**Get the APK:** open the GitHub **Actions** tab → run **"Build AI Video Studio
(Android .apk)"** → download the `AIVideoStudio-APK` artifact → copy it to your
phone and install (allow "install from unknown sources").

**Using it:**
1. Fill in topics, schedule, hashtags, platform toggles → **Save settings**.
2. Under **Cloud (GitHub Actions)** enter:
   - **Repo**: `alishoppingmart/universal-video-downloader`
   - **Branch**: the branch that has `daily-publish.yml` (must be on **main** for
     "Run now" to work — see note)
   - **GitHub token**: a Personal Access Token with the **workflow** scope
     (github.com → Settings → Developer settings → Tokens)
3. **Run now in cloud** kicks off one publish job; **Check status** shows the
   last run's result.

> ⚠️ GitHub only lets you trigger a workflow that exists on the **default
> branch**. So merge `daily-publish.yml` into `main` before using "Run now".

---

## Roadmap / not done yet
- iPhone (iOS) app — Buildozer is Android-only; iOS needs a Mac/Xcode build.
- On-device direct posting from the phone (currently it routes through the cloud).
- Smarter AI scripts/voiceover and a 100%-free generation fallback.
- Auto-refresh of TikTok access tokens.
- Storing/queuing pre-generated videos for the cloud publisher.
