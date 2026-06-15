"""
Talk to the cloud (GitHub Actions) from the phone.

The mobile app can't run Google Flow itself, so instead it asks your GitHub
repo to run the `daily-publish.yml` workflow now (a "workflow_dispatch"). That
cloud job does the generate/publish work.

You provide:
  * repo   - e.g. "alishoppingmart/universal-video-downloader"
  * token  - a GitHub Personal Access Token with the "actions" (workflow) scope
  * ref    - the branch the workflow file lives on (e.g. "main")
"""

from __future__ import annotations

WORKFLOW_FILE = "daily-publish.yml"


def trigger_cloud_run(repo: str, token: str, ref: str = "main", topic_index: int = 0) -> tuple[bool, str]:
    """Kick off one cloud publish run. Returns (ok, message)."""
    try:
        import requests
    except ImportError:
        return False, "requests not available"

    if not repo or "/" not in repo:
        return False, "Set your repo as 'owner/name' first."
    if not token:
        return False, "Paste a GitHub token first."

    url = f"https://api.github.com/repos/{repo}/actions/workflows/{WORKFLOW_FILE}/dispatches"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    body = {"ref": ref, "inputs": {"topic_index": str(topic_index)}}
    try:
        r = requests.post(url, headers=headers, json=body, timeout=30)
    except Exception as e:
        return False, f"Network error: {e}"

    if r.status_code == 204:
        return True, "Cloud run started! Check the Actions tab on GitHub."
    if r.status_code == 404:
        return False, ("Not found. Check repo name, that the token has 'workflow' "
                       f"scope, and that {WORKFLOW_FILE} exists on '{ref}'.")
    if r.status_code in (401, 403):
        return False, "Auth failed. Check the token and its permissions."
    return False, f"GitHub returned HTTP {r.status_code}: {r.text[:200]}"


def latest_run_status(repo: str, token: str) -> tuple[bool, str]:
    """Return (ok, human status) for the most recent daily-publish run."""
    try:
        import requests
    except ImportError:
        return False, "requests not available"
    if not repo or not token:
        return False, "Set repo and token first."
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{WORKFLOW_FILE}/runs?per_page=1"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    try:
        r = requests.get(url, headers=headers, timeout=30)
    except Exception as e:
        return False, f"Network error: {e}"
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}"
    runs = r.json().get("workflow_runs", [])
    if not runs:
        return True, "No runs yet."
    run = runs[0]
    return True, f"Last run: {run.get('status')} / {run.get('conclusion') or 'in progress'}"
