#!/usr/bin/env python3
"""
alive.py — Daily runner for github-alive.

Reads pattern.json, determines today's position in the rolling pattern,
counts real commits via GitHub API, and tops up as needed
by creating commits in the target repo.

Usage:
    python alive.py

Configuration (config.json or environment variables):
    GITHUB_TOKEN  — personal access token with repo + user scope
    GITHUB_USER   — your GitHub username
    GITHUB_REPO   — repo to commit into (default: "alive")
    PATTERN_FILE  — path to pattern.json (default: "pattern.json")

Rolling pattern logic:
    anchor_date and cycle_weeks are loaded from pattern.json.
    Today's position: (weeks_since_anchor) % cycle_weeks
"""

import json
import os
import sys
import base64
import datetime
import time
import logging
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
# Configuration
# ---------------------------------------------------------------------------

def load_config() -> dict:
    """
    Load config from config.json if present, then override with env vars.
    Required keys: github_token, github_user.
    Optional keys: alive_repo (default "alive"), pattern_file (default "pattern.json").
    """
    config = {
        'github_token': '',
        'github_user': '',
        'alive_repo': 'alive',
        'pattern_file': 'pattern.json',
    }

    # Load from config.json (same directory as this script)
    script_dir = Path(__file__).parent
    config_path = script_dir / 'config.json'
    if config_path.exists():
        with open(config_path) as f:
            file_config = json.load(f)
        config.update(file_config)
        log.debug(f"Loaded config from {config_path}")

    # Environment variables override file config
    env_map = {
        'GITHUB_TOKEN': 'github_token',
        'GITHUB_USER': 'github_user',
        'GITHUB_REPO': 'alive_repo',
        'PATTERN_FILE': 'pattern_file',
    }
    for env_key, cfg_key in env_map.items():
        if os.environ.get(env_key):
            config[cfg_key] = os.environ[env_key]

    # Validate required fields
    if not config['github_token']:
        log.error("Missing GITHUB_TOKEN. Set it in config.json or as an environment variable.")
        sys.exit(1)
    if not config['github_user']:
        log.error("Missing GITHUB_USER. Set it in config.json or as an environment variable.")
        sys.exit(1)

    return config


# ---------------------------------------------------------------------------
# Date helpers — rolling pattern
# ---------------------------------------------------------------------------

def get_today_info(anchor_date: str, cycle_weeks: int) -> tuple[int, int, str]:
    """
    Returns (pattern_week, day_index, date_str) for today using the rolling pattern.

    pattern_week: 0..(cycle_weeks-1)  — position in the tiling cycle
    day_index:    0=Sun, 1=Mon, ..., 6=Sat  (GitHub graph convention)
    date_str:     "YYYY-MM-DD"

    Rolling logic:
        anchor = datetime.date.fromisoformat(anchor_date)
        days_since_anchor = (today - anchor).days
        week_since_anchor = days_since_anchor // 7
        pattern_week = week_since_anchor % cycle_weeks
    """
    today = datetime.date.today()
    date_str = today.isoformat()

    anchor = datetime.date.fromisoformat(anchor_date)
    days_since_anchor = (today - anchor).days
    week_since_anchor = days_since_anchor // 7
    pattern_week = week_since_anchor % cycle_weeks

    # GitHub graph day convention: Sun=0, Mon=1, ..., Sat=6
    # Python isoweekday(): Mon=1..Sun=7  →  % 7 gives Sun=0, Mon=1, ..., Sat=6
    day_index = today.isoweekday() % 7

    return pattern_week, day_index, date_str


# ---------------------------------------------------------------------------
# Pattern
# ---------------------------------------------------------------------------

def load_pattern(pattern_file: str) -> dict:
    """Load pattern.json. Returns the parsed dict."""
    path = Path(pattern_file)
    if not path.is_absolute():
        # Resolve relative to script directory
        path = Path(__file__).parent / pattern_file
    if not path.exists():
        log.error(f"pattern.json not found at {path}. Run designer.py first.")
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def get_target_commits(pattern: dict, week: int, day: int) -> int:
    """Return the number of commits required for the given week/day."""
    grid = pattern['grid']
    levels = {int(k): v for k, v in pattern['levels'].items()}
    level = grid[week][day]
    return levels.get(level, 0)


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------

class GitHubAPI:
    BASE = 'https://api.github.com'

    def __init__(self, token: str, user: str):
        self.user = user
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
        })

    def _get(self, path: str, params: dict = None) -> dict | list:
        url = f'{self.BASE}{path}'
        resp = self.session.get(url, params=params, timeout=30)
        if resp.status_code == 404:
            return {}
        resp.raise_for_status()
        return resp.json()

    def _put(self, path: str, data: dict) -> dict:
        url = f'{self.BASE}{path}'
        resp = self.session.put(url, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def count_commits_today(self, date_str: str) -> int:
        """
        Count commits authored by self.user on the given date (YYYY-MM-DD).
        Uses the Search API: GET /search/commits
        """
        params = {
            'q': f'author:{self.user} committer-date:{date_str}',
            'per_page': 1,
        }
        try:
            data = self._get('/search/commits', params=params)
            return data.get('total_count', 0)
        except requests.HTTPError as e:
            # Search API requires special Accept header — fall back
            log.warning(f"Search API error ({e}), falling back to 0 existing commits.")
            return 0

    def get_file(self, repo: str, file_path: str) -> dict:
        """Get file metadata (including SHA) from a repo."""
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
        content: plain text (will be base64-encoded)
        sha: existing file SHA (required for updates, None for create)
        author_date: ISO 8601 timestamp for the commit
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
    Make `count` commits to the alive.md file in the target repo.
    Each commit gets a slightly different timestamp to avoid hash collisions.
    """
    log.info(f"Making {count} commit(s) to {api.user}/{repo} for {date_str}...")

    # Base timestamp: noon on the target date, spread commits across the day
    base_dt = datetime.datetime.strptime(date_str, '%Y-%m-%d').replace(hour=12, minute=0, second=0)

    # Fetch current file SHA (if it exists)
    existing = api.get_file(repo, 'alive.md')
    current_sha = existing.get('sha')  # None if file doesn't exist yet

    for i in range(count):
        # Spread commits: every ~30 minutes starting from noon
        commit_dt = base_dt + datetime.timedelta(minutes=30 * i)
        ts = commit_dt.strftime('%Y-%m-%dT%H:%M:%SZ')

        content = (
            f"# github-alive\n\n"
            f"Auto-commit #{i + 1} for {date_str} at {ts}\n\n"
            f"This file is maintained by [github-alive](https://github.com/your-username/github-alive).\n"
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

        # Update SHA for next iteration
        new_content = result.get('content', {})
        current_sha = new_content.get('sha', current_sha)

        log.info(f"  [{i + 1}/{count}] Committed: {message}")

        # Be polite to the API — small delay between commits
        if i < count - 1:
            time.sleep(0.5)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log.info("=== github-alive starting ===")

    # Load configuration
    config = load_config()
    token = config['github_token']
    user = config['github_user']
    repo = config['alive_repo']
    pattern_file = config['pattern_file']

    log.info(f"User: {user}  |  Repo: {repo}  |  Pattern: {pattern_file}")

    # Load pattern first — needed for anchor_date and cycle_weeks
    pattern = load_pattern(pattern_file)
    anchor_date = pattern.get("anchor_date", "2012-09-09")
    cycle_weeks = pattern.get("cycle_weeks", 26)

    log.info(f"Anchor: {anchor_date}  |  Cycle: {cycle_weeks} weeks")

    # Determine today's position in the rolling pattern
    week, day, date_str = get_today_info(anchor_date, cycle_weeks)
    log.info(f"Today: {date_str}  |  Pattern week: {week}  |  Day: {day}")

    # Find target commit count
    target = get_target_commits(pattern, week, day)
    log.info(f"Target commits for today (level {pattern['grid'][week][day]}): {target}")

    if target == 0:
        log.info("No commits needed today (background/empty cell). Done.")
        return

    # Count real commits already made today
    api = GitHubAPI(token=token, user=user)
    real = api.count_commits_today(date_str)
    log.info(f"Real commits today: {real}")

    needed = max(0, target - real)
    log.info(f"Commits needed: {needed}")

    if needed == 0:
        log.info("Already at or above target. Nothing to do.")
        return

    # Make the required commits
    make_commits(api, repo, needed, date_str)
    log.info(f"=== Done! Made {needed} commit(s). ===")


if __name__ == '__main__':
    main()
