# How to Connect Your Accounts — Plain Guide

This explains, in simple steps, how to connect **Google Flow**, **YouTube**, and
**TikTok** to AI Video Studio on your laptop. Do each one once.

---

## A. Google Flow (makes the videos) — easiest

1. Open the app → **Accounts** tab.
2. Click **Connect Google Flow**.
3. **First time only:** the app downloads a small browser engine (~150 MB).
   This takes a few minutes and needs internet. You'll see "downloading the
   browser engine" in the log. *This happens just once.*
4. A browser window opens. **Log in to your Google account** and wait until you
   can see the Google Flow page.
5. The app saves your login and closes the window. ✅ Done.

> Your Google **password is never stored** — only a temporary "logged-in" token,
> the same way your browser stays logged in.

If it ever stops working, just click **Connect Google Flow** again.

---

## B. YouTube (auto-uploads your Shorts)

Google requires every app to have its own free "keys" before it can post to your
channel. It feels like a lot the first time, but you only do it once. **The app
has a wizard that does this with you:**

1. Open the app → **Accounts** tab → under YouTube, click **Setup wizard**.
2. The wizard has 4 numbered steps, each with an **Open** button:
   1. **Create a project** → press *Create* on Google's page.
   2. **Enable YouTube Data API** → press *Enable*.
   3. **Consent screen** → choose *External*, type an app name + your email,
      Save, and add yourself under *Test users*.
   4. **Create OAuth key** → *Create credentials → OAuth client ID →
      Desktop app → Create*.
3. Google shows you a **Client ID** and a **Client secret**. Copy both into the
   wizard's boxes → **Save keys**.
4. Click **Connect YouTube (login)** → a browser opens → approve access. ✅ Done.

> New projects are in "test mode" and may be limited to ~6 uploads/day — plenty
> for 1–2 videos a day.

---

## C. TikTok (auto-uploads to TikTok) — the strict one

TikTok does **not** allow a simple login for posting. They require a developer
app **they review and approve** first. Until approved, your videos go to your
TikTok **Drafts** and you tap *Post* yourself in the TikTok app.

1. Go to <https://developers.tiktok.com/> and log in with your TikTok account.
2. **Manage apps → Connect an app** → fill in the basic details.
3. Add the **Content Posting API** product. Request the **Direct Post** ability
   (this is the part TikTok reviews — it can take a few days).
4. From the app's settings, generate an **Access token**.
5. In AI Video Studio → **Accounts** tab → paste the token under TikTok →
   **Save token**. ✅ Connected (drafts mode until TikTok approves direct posting).

---

## Check it worked
In the app → **Run** tab → **Check setup**. It prints OK / NOT READY for each
account so you can see exactly what's still missing.

## Common issues
| Problem | Fix |
| --- | --- |
| "Playwright not installed" on Connect Flow | Use the latest `.exe` build; the new one auto-downloads the browser. |
| Flow login window never appears | Check internet; the first download is ~150 MB. |
| YouTube "access blocked / unverified" | Add your own email under *Test users* on the consent screen (step 3). |
| TikTok only saves to Drafts | Normal until TikTok approves Direct Post for your app. |
