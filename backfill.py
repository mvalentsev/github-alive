#!/usr/bin/env python3
"""
GitHub contribution graph backfill script.
Makes backdated commits to create a pattern in the contribution graph.
"""

import json
import time
import base64
import urllib.request
import urllib.error
from datetime import date, timedelta

# Config
TOKEN = "YOUR_TOKEN_HERE"
USER = "mvalentsev"
REPO = "alive"
FILE_PATH = "alive.md"
AUTHOR_NAME = "Mikhail Valentsev"
AUTHOR_EMAIL = "mvalentsev@users.noreply.github.com"

# Date range
START_DATE = date(2025, 3, 6)
END_DATE = date(2026, 3, 4)

# Load pattern
with open("/home/openclaw/.openclaw/workspace/projects/github-alive/pattern.json") as f:
    pattern = json.load(f)

GRID = pattern["grid"]
LEVELS = pattern["levels"]
ANCHOR = date.fromisoformat(pattern["anchor_date"])
CYCLE_WEEKS = pattern["cycle_weeks"]


def api_request(method, path, body=None):
    url = f"https://api.github.com{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "backfill-script/1.0",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body_text}")


def get_file_sha():
    """Get current SHA of alive.md."""
    result = api_request("GET", f"/repos/{USER}/{REPO}/contents/{FILE_PATH}")
    return result["sha"]


def make_commit(date_str, commit_num, sha, minutes_offset=0):
    """Make a single backdated commit. Returns new SHA."""
    hour = 12 + (minutes_offset * 30) // 60
    minute = (minutes_offset * 30) % 60
    timestamp = f"{date_str}T{hour:02d}:{minute:02d}:00Z"
    
    content_text = f"alive: {date_str} #{commit_num}\n"
    content_b64 = base64.b64encode(content_text.encode("utf-8")).decode("ascii")
    
    body = {
        "message": f"alive: {date_str} #{commit_num}",
        "content": content_b64,
        "sha": sha,
        "author": {"name": AUTHOR_NAME, "email": AUTHOR_EMAIL, "date": timestamp},
        "committer": {"name": AUTHOR_NAME, "email": AUTHOR_EMAIL, "date": timestamp},
    }
    
    result = api_request("PUT", f"/repos/{USER}/{REPO}/contents/{FILE_PATH}", body)
    return result["content"]["sha"]


def main():
    print(f"Starting backfill: {START_DATE} → {END_DATE}")
    print(f"Anchor: {ANCHOR}, cycle: {CYCLE_WEEKS} weeks")
    
    # Get initial SHA
    print("Getting initial file SHA...")
    current_sha = get_file_sha()
    print(f"Initial SHA: {current_sha}")
    
    total_days = 0
    total_commits = 0
    days_processed = 0
    
    current_date = START_DATE
    while current_date <= END_DATE:
        days_since_anchor = (current_date - ANCHOR).days
        pattern_week = (days_since_anchor // 7) % CYCLE_WEEKS
        # isoweekday: Mon=1..Sun=7; we want Sun=0, Mon=1..Sat=6
        day_of_week = current_date.isoweekday() % 7
        
        level = GRID[pattern_week][day_of_week]
        num_commits = LEVELS.get(str(level), 0)
        
        date_str = current_date.isoformat()
        
        if num_commits > 0:
            total_days += 1
            day_commits = 0
            for i in range(num_commits):
                try:
                    current_sha = make_commit(date_str, i + 1, current_sha, minutes_offset=i)
                    day_commits += 1
                    total_commits += 1
                    time.sleep(0.5)
                except Exception as e:
                    print(f"ERROR on {date_str} commit #{i+1}: {e}")
                    # Try to refresh SHA on error
                    try:
                        time.sleep(2)
                        current_sha = get_file_sha()
                        print(f"  Refreshed SHA: {current_sha}")
                    except Exception as e2:
                        print(f"  Failed to refresh SHA: {e2}")
            
            days_processed += 1
        
        # Log every 10 days
        if (current_date - START_DATE).days % 10 == 9:
            print(f"Done: {date_str} (week {pattern_week}, level {level}, total {total_commits} commits so far)")
        
        current_date += timedelta(days=1)
    
    print(f"\n{'='*50}")
    print(f"BACKFILL COMPLETE")
    print(f"Days with commits: {total_days}")
    print(f"Total commits made: {total_commits}")
    print(f"{'='*50}")
    return total_days, total_commits


if __name__ == "__main__":
    days, commits = main()
    print(f"\nBACKFILL DONE: {days} дней, {commits} коммитов")
