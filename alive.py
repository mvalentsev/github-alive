#!/usr/bin/env python3
"""
alive.py — Daily runner for github-alive.

Computes today's target commit count from a deterministic mathematical pattern,
counts real commits already made today via GitHub Search API, and tops up as
needed by creating commits in the target repo.

Usage:
    python alive.py

Configuration (config.json or environment variables):
    GITHUB_TOKEN  — personal access token with repo + user scope
    GITHUB_USER   — your GitHub username
    GITHUB_REPO   — repo to commit into (default: "alive")

No pattern.json needed — the pattern is computed on the fly from a
mathematical function anchored to 2012-09-09.
"""

import base64
import datetime
import json
import logging
import math
import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: 'requests' is not installed. Run: pip install requests")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
log = logging.getLogger('alive')


# ---------------------------------------------------------------------------
# Mathematical pattern
# ---------------------------------------------------------------------------

ANCHOR_DATE = datetime.date(2012, 9, 9)  # Sunday; GitHub contribution graph epoch


def base_commits(days_since_anchor: int, day_of_week: int) -> int:
    """
    Return the base commit count for a given day.

    Produces an organic, multi-scale wave pattern with values in [1, 40].
    The pattern is fully deterministic — same date always gives the same result.

    Args:
        days_since_anchor: days elapsed since ANCHOR_DATE (2012-09-09)
        day_of_week: 0=Sun, 1=Mon, ..., 6=Sat  (GitHub graph convention)

    Returns:
        Integer commit count in [1, 40]
    """
    t = days_since_anchor / 7.0   # time in weeks
    d = day_of_week

    # Multiple overlapping sine waves create organic, multi-scale texture
    w1 = math.sin(2 * math.pi * t / 26 + 0.0)         # 26-week primary cycle
    w2 = math.sin(2 * math.pi * t / 13 + 1.5)         # 13-week harmonic
    w3 = math.sin(2 * math.pi * t / 52 + 0.8)         # yearly drift
    w4 = math.sin(2 * math.pi * d / 7 + t * 0.4)      # day-of-week texture
    w5 = math.sin(2 * math.pi * (t * 1.3 + d) / 9)   # diagonal ripple

    combined = w1 * 0.35 + w2 * 0.25 + w3 * 0.15 + w4 * 0.15 + w5 * 0.10
    # combined ≈ [-1, 1] → normalize to [3, 40]
    count = round(3 + (combined + 1) * 18.5)
    return max(1, min(40, count))


def get_base_commits(today: datetime.date) -> int:
    """
    Return the base commit count for the given date.

    Args:
        today: the date to compute for

    Returns:
        Integer commit count in [1, 40]
    """
    days = (today - ANCHOR_DATE).days
    dow = today.isoweekday() % 7  # isoweekday Mon=1..Sun=7 → Sun=0, Mon=1, ..., Sat=6
    return base_commits(days, dow)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def load_config() -> dict:
    """
    Load config from config.json (if present), then override with env vars.

    Required keys: github_token, github_user.
    Optional keys: alive_repo (default "alive").

    Returns:
        Config dict with all keys populated.
    """
    config = {
        'github_token': '',
        'github_user': '',
        'alive_repo': 'alive',
    }

    script_dir = Path(__file__).parent
    config_path = script_dir / 'config.json'
    if config_path.exists():
        with open(config_path) as f:
            file_config = json.load(f)
        config.update(file_config)
        log.debug(f"Loaded config from {config_path}")

    env_map = {
        'ALIVE_GH_TOKEN': 'github_token',  # Used in GitHub Actions (avoids clash with built-in GITHUB_TOKEN)
        'GITHUB_TOKEN': 'github_token',    # Fallback for local use
        'GITHUB_USER': 'github_user',
        'GITHUB_REPO': 'alive_repo',
    }
    for env_key, cfg_key in env_map.items():
        if os.environ.get(env_key):
            config[cfg_key] = os.environ[env_key]

    if not config['github_token']:
        log.error("Missing GITHUB_TOKEN. Set it in config.json or as an environment variable.")
        sys.exit(1)
    if not config['github_user']:
        log.error("Missing GITHUB_USER. Set it in config.json or as an environment variable.")
        sys.exit(1)

    return config


# ---------------------------------------------------------------------------
# GitHub API
# ---------------------------------------------------------------------------

class GitHubAPI:
    """Thin wrapper around the GitHub REST API."""

    BASE = 'https://api.github.com'

    def __init__(self, token: str, user: str):
        self.user = user
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
        })

    def _get(self, path: str, params: dict = None, extra_headers: dict = None) -> dict | list:
        url = f'{self.BASE}{path}'
        headers = {}
        if extra_headers:
            headers.update(extra_headers)
        resp = self.session.get(url, params=params, headers=headers, timeout=30)
        if resp.status_code == 404:
            return {}
        resp.raise_for_status()
        return resp.json()

    def _put(self, path: str, data: dict) -> dict:
        url = f'{self.BASE}{path}'
        resp = self.session.put(url, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def count_real_commits(self, date_str: str, alive_repo: str) -> int:
        """
        Count commits authored by self.user on date_str, excluding the alive repo itself.

        Uses GitHub Search API with committer-date filter. Returns 0 on error.

        Args:
            date_str: date in "YYYY-MM-DD" format
            alive_repo: name of the alive repo to exclude from count

        Returns:
            Number of commits found
        """
        # Exclude the alive repo to avoid counting our own synthetic commits
        query = f'author:{self.user} committer-date:{date_str} -repo:{self.user}/{alive_repo}'
        params = {'q': query, 'per_page': 1}
        extra_headers = {'Accept': 'application/vnd.github.cloak-preview+json'}
        try:
            data = self._get('/search/commits', params=params, extra_headers=extra_headers)
            return data.get('total_count', 0)
        except requests.HTTPError as e:
            log.warning(f"Search API error ({e}), assuming 0 real commits today.")
            return 0

    def get_file(self, repo: str, file_path: str) -> dict:
        """Fetch file metadata (including SHA) from a repo."""
        return self._get(f'/repos/{self.user}/{repo}/contents/{file_path}')

    def create_or_update_file(
        self,
        repo: str,
        file_path: str,
        content: str,
        message: str,
        sha: str | None,
        author_date: str,
    ) -> dict:
        """
        Create or update a file in the repo via the Contents API.

        Args:
            repo: repository name
            file_path: path inside the repo
            content: plain text content (will be base64-encoded)
            message: commit message
            sha: existing file SHA (required for updates, None for first create)
            author_date: ISO 8601 timestamp, e.g. "2024-01-15T12:00:00Z"

        Returns:
            API response dict
        """
        encoded = base64.b64encode(content.encode()).decode()
        data = {
            'message': message,
            'content': encoded,
            'committer': {
                'name': 'github-alive',
                'email': 'github-alive@users.noreply.github.com',
                'date': author_date,
            },
            'author': {
                'name': 'github-alive',
                'email': 'github-alive@users.noreply.github.com',
                'date': author_date,
            },
        }
        if sha:
            data['sha'] = sha
        return self._put(f'/repos/{self.user}/{repo}/contents/{file_path}', data)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def make_commits(api: GitHubAPI, repo: str, count: int, date_str: str) -> None:
    """
    Create `count` commits to alive.md in the target repo.

    Commits are spread across the day (every ~30 minutes from noon) to look
    natural in the contribution graph timeline.

    Args:
        api: GitHubAPI instance
        repo: repository name to commit into
        count: number of commits to make
        date_str: date string "YYYY-MM-DD"
    """
    log.info(f"Making {count} commit(s) to {api.user}/{repo} for {date_str}...")

    base_dt = datetime.datetime.strptime(date_str, '%Y-%m-%d').replace(
        hour=12, minute=0, second=0
    )

    existing = api.get_file(repo, 'alive.md')
    current_sha = existing.get('sha')

    for i in range(count):
        commit_dt = base_dt + datetime.timedelta(minutes=30 * i)
        ts = commit_dt.strftime('%Y-%m-%dT%H:%M:%SZ')

        content = (
            f"# github-alive\n\n"
            f"Auto-commit #{i + 1} for {date_str} at {ts}\n\n"
            f"This file is maintained by "
            f"[github-alive](https://github.com/{api.user}/{repo}).\n"
        )
        message = f"alive: {date_str} #{i + 1}"

        result = api.create_or_update_file(
            repo=repo,
            file_path='alive.md',
            content=content,
            message=message,
            sha=current_sha,
            author_date=ts,
        )

        new_content = result.get('content', {})
        current_sha = new_content.get('sha', current_sha)

        log.info(f"  [{i + 1}/{count}] {message}")

        if i < count - 1:
            time.sleep(0.5)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log.info("=== github-alive starting ===")

    config = load_config()
    token = config['github_token']
    user = config['github_user']
    repo = config['alive_repo']

    log.info(f"User: {user}  |  Repo: {repo}")

    today = datetime.date.today()
    date_str = today.isoformat()

    # Compute target from mathematical pattern
    base = get_base_commits(today)
    log.info(f"Today: {date_str}  |  Pattern target: {base} commits")

    api = GitHubAPI(token=token, user=user)

    # Count real commits (excluding alive repo)
    real = api.count_real_commits(date_str, repo)
    log.info(f"Real commits today (excl. {repo}): {real}")

    # Only fill the gap; real activity never breaks the pattern
    delta = max(0, base - real)
    log.info(f"Commits to make: {delta}")

    if delta == 0:
        log.info("Already at or above pattern target. Nothing to do.")
        return

    make_commits(api, repo, delta, date_str)
    log.info(f"=== Done! Made {delta} commit(s). ===")


if __name__ == '__main__':
    main()
