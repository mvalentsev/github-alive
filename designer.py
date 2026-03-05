#!/usr/bin/env python3
"""
designer.py — Pattern visualizer for github-alive.

Shows an ASCII preview of the next 52 weeks of the contribution pattern,
with today's position marked. Uses the same deterministic mathematical
function as alive.py — no config or pattern.json needed.

Usage:
    python3 designer.py
"""

import datetime
import math
import sys

# ---------------------------------------------------------------------------
# Mathematical pattern (identical to alive.py)
# ---------------------------------------------------------------------------

ANCHOR_DATE = datetime.date(2012, 9, 9)


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

    w1 = math.sin(2 * math.pi * t / 26 + 0.0)         # 26-week primary cycle
    w2 = math.sin(2 * math.pi * t / 13 + 1.5)         # 13-week harmonic
    w3 = math.sin(2 * math.pi * t / 52 + 0.8)         # yearly drift
    w4 = math.sin(2 * math.pi * d / 7 + t * 0.4)      # day-of-week texture
    w5 = math.sin(2 * math.pi * (t * 1.3 + d) / 9)   # diagonal ripple

    combined = w1 * 0.35 + w2 * 0.25 + w3 * 0.15 + w4 * 0.15 + w5 * 0.10
    count = round(3 + (combined + 1) * 18.5)
    return max(1, min(40, count))


def commits_to_char(n: int) -> str:
    """
    Map a commit count to a density character.

    Ranges:
         1–5  →  · (empty/sparse)
        6–15  →  ░ (light)
       16–25  →  ▒ (medium)
       26–35  →  ▓ (heavy)
       36–40  →  █ (full)
    """
    if n <= 5:
        return '·'
    elif n <= 15:
        return '░'
    elif n <= 25:
        return '▒'
    elif n <= 35:
        return '▓'
    else:
        return '█'


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------

DISPLAY_WEEKS = 52
DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']


def get_week_start(today: datetime.date) -> datetime.date:
    """Return the Sunday that starts the current week."""
    dow = today.isoweekday() % 7  # Sun=0
    return today - datetime.timedelta(days=dow)


def render_pattern(today: datetime.date) -> None:
    """
    Render 52 weeks of the pattern starting from the current week.
    Marks today's column with an arrow indicator below.

    Args:
        today: reference date (normally datetime.date.today())
    """
    week_start = get_week_start(today)
    today_week = 0  # today is in the first displayed week

    # Find which column (week index) today falls in
    today_dow = today.isoweekday() % 7  # 0=Sun

    # Build grid: grid[day][week] → char
    grid = []
    for day in range(7):
        row = []
        for week in range(DISPLAY_WEEKS):
            date = week_start + datetime.timedelta(weeks=week, days=day)
            days = (date - ANCHOR_DATE).days
            n = base_commits(days, day)
            ch = commits_to_char(n)
            row.append(ch)
        grid.append(row)

    # Print header
    print()
    print("  github-alive — pattern preview (next 52 weeks)")
    print(f"  Anchor: {ANCHOR_DATE}  |  Today: {today.isoformat()}")
    print()

    # Legend
    print("  Legend:  · 1–5   ░ 6–15   ▒ 16–25   ▓ 26–35   █ 36–40  commits")
    print()

    # Grid (day rows × week columns)
    sep = '─' * (DISPLAY_WEEKS * 2 + 2)
    print(f"  {sep}")
    for day in range(7):
        row_str = ' '.join(grid[day])
        print(f"  {DAY_NAMES[day]}  {row_str}")
    print(f"  {sep}")

    # Today marker: arrow under today's column
    #   Each cell = 2 chars (char + space), offset = 6 chars for "  Sun  "
    col_offset = 6 + today_dow * 0  # day marker is not per-column but per-week
    # Actually mark the week column (today's week = column 0)
    # today_week=0, each week cell=2 chars wide
    arrow_pos = today_week * 2
    prefix = ' ' * (6 + arrow_pos)
    print(f"  {prefix}↑ today ({today.strftime('%a %b %d')})")
    print()

    # Stats
    total = sum(
        base_commits(
            (week_start + datetime.timedelta(weeks=w, days=d) - ANCHOR_DATE).days,
            d
        )
        for w in range(DISPLAY_WEEKS)
        for d in range(7)
    )
    avg = total / (DISPLAY_WEEKS * 7)
    print(f"  52-week window: {DISPLAY_WEEKS * 7} days  |  avg {avg:.1f} commits/day  |  est. {total} total")
    print()


def main():
    if '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        sys.exit(0)

    today = datetime.date.today()
    render_pattern(today)


if __name__ == '__main__':
    main()
