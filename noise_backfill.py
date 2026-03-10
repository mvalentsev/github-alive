#!/usr/bin/env python3
"""
noise_backfill.py — DEPRECATED. Do not use.

This script was written when backfill.py only covered Mon/Wed/Fri. It added
1–3 commits to the empty Tue/Thu/Sat/Sun days. backfill.py now covers all days
of the week using the full mathematical pattern, so this script is no longer
needed and would create duplicate commits if run against an up-to-date repo.

Kept for historical reference only.

Usage (historical):
    python3 noise_backfill.py

Config: reads config.json (same format as alive.py).
Env vars: GITHUB_TOKEN, GITHUB_USER, GITHUB_REPO also accepted.
"""

import base64
import datetime
import json
import logging
import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: 'requests' is not installed. Run: pip install requests")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
log = logging.getLogger('noise_backfill')

# Days to add noise to (these were empty in the initial backfill)
# isoweekday(): Mon=1, Tue=2, Wed=3, Thu=4, Fri=5, Sat=6, Sun=7
NOISE_DAYS = {2, 4, 6, 7}  # Tue, Thu, Sat, Sun

# Date range — same as initial backfill
START_DATE = datetime.date(2025, 3, 6)
END_DATE = datetime.date(2026, 3, 4)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def noise_count(d: datetime.date) -> int:
    """
    Return 1–3 noise commits for a date, deterministically.
    Uses a Knuth multiplicative hash on the date ordinal.
    """
    h = (d.toordinal() * 2654435761 + 1234567) & 0xFFFFFFFF
    return 1 + (h % 3)


def load_config() -> dict:
    config = {'github_token': '', 'github_user': '', 'alive_repo': 'alive'}
    cfg_path = Path(__file__).parent / 'config.json'
    if cfg_path.exists():
        with open(cfg_path) as f:
            config.update(json.load(f))
    token = os.environ.get('ALIVE_GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if token:
        config['github_token'] = token
    for env_key, cfg_key in [('GITHUB_USER', 'github_user'), ('GITHUB_REPO', 'alive_repo')]:
        if os.environ.get(env_key):
            config[cfg_key] = os.environ[env_key]
    if not config['github_token']:
        log.error("Missing GITHUB_TOKEN. Set it in config.json or as an env var.")
        sys.exit(1)
    if not config['github_user']:
        log.error("Missing GITHUB_USER. Set it in config.json or as an env var.")
        sys.exit(1)
    return config


# ---------------------------------------------------------------------------
# GitHub API
# ---------------------------------------------------------------------------

class GitHubAPI:
    BASE = 'https://api.github.com'

    def __init__(self, token: str, user: str):
        self.user = user
        self._user_id: int | None = None
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
        })

    def get_user_id(self) -> int:
        if self._user_id:
            return self._user_id
        resp = self.session.get(f'{self.BASE}/user', timeout=30)
        resp.raise_for_status()
        self._user_id = resp.json()['id']
        return self._user_id

    def get_noreply_email(self) -> str:
        return f'{self.get_user_id()}+{self.user}@users.noreply.github.com'

    def get_file(self, repo: str, path: str) -> dict:
        resp = self.session.get(
            f'{self.BASE}/repos/{self.user}/{repo}/contents/{path}', timeout=30
        )
        resp.raise_for_status()
        return resp.json()

    def put_file(self, repo: str, path: str, data: dict) -> dict:
        resp = self.session.put(
            f'{self.BASE}/repos/{self.user}/{repo}/contents/{path}',
            json=data, timeout=30,
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    config = load_config()
    api = GitHubAPI(config['github_token'], config['github_user'])
    repo = config['alive_repo']
    user = config['github_user']

    log.warning("noise_backfill is DEPRECATED — backfill.py now covers all days. Aborting.")
    log.warning("Remove this guard and update START_DATE/END_DATE only if you know what you're doing.")
    import sys; sys.exit(1)

    log.info(f"=== noise_backfill starting ===")
    log.info(f"User: {user}  |  Repo: {repo}")
    log.info(f"Range: {START_DATE} → {END_DATE}  |  Noise days: Tue/Thu/Sat/Sun")
    noreply = api.get_noreply_email()
    log.info(f"Email: {noreply}")

    # Get starting SHA
    file_info = api.get_file(repo, 'alive.md')
    current_sha = file_info['sha']
    log.info(f"Starting SHA: {current_sha}")

    total_days = 0
    total_commits = 0
    d = START_DATE

    while d <= END_DATE:
        if d.isoweekday() in NOISE_DAYS:
            count = noise_count(d)
            date_str = d.isoformat()
            log.info(f"  {date_str} ({d.strftime('%a')}) → {count} commit(s)")

            # Spread commits across morning hours to look natural
            base_dt = datetime.datetime.strptime(date_str, '%Y-%m-%d').replace(
                hour=9, minute=0, second=0
            )

            for i in range(count):
                commit_dt = base_dt + datetime.timedelta(hours=i * 3)
                ts = commit_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                content = f"alive: {date_str} #{i + 1}\n"
                encoded = base64.b64encode(content.encode()).decode()

                data = {
                    'message': f'alive: {date_str} #{i + 1}',
                    'content': encoded,
                    'sha': current_sha,
                    'author': {
                        'name': user,
                        'email': noreply,
                        'date': ts,
                    },
                    'committer': {
                        'name': user,
                        'email': noreply,
                        'date': ts,
                    },
                }

                try:
                    result = api.put_file(repo, 'alive.md', data)
                    current_sha = result['content']['sha']
                    total_commits += 1
                    time.sleep(0.5)
                except Exception as e:
                    log.error(f"    ERROR on {date_str} #{i + 1}: {e}")
                    # Refresh SHA and continue
                    try:
                        time.sleep(2)
                        current_sha = api.get_file(repo, 'alive.md')['sha']
                        log.info(f"    Refreshed SHA: {current_sha}")
                    except Exception as e2:
                        log.error(f"    Failed to refresh SHA: {e2}")

            total_days += 1

        d += datetime.timedelta(days=1)

    log.info(f"=== Done! {total_days} days, {total_commits} commits total. ===")


if __name__ == '__main__':
    main()
