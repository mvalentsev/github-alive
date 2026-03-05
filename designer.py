#!/usr/bin/env python3
"""
designer.py — Generate pattern.json for github-alive.

Usage:
    python designer.py            # generates pattern for "ALIVE"
    python designer.py "HELLO"   # generates pattern for custom text
    python designer.py --help

The script renders the given text using a 7-row pixel font, places it
at the start of a 26-week cycle (CYCLE_WEEKS), and saves pattern.json.
It also prints an ASCII preview × 2 cycles (simulating the 52-week graph).

Rolling/tiling logic:
    ALIVE fits in 25 columns. Column 25 is a blank gap.
    Total cycle = 26 weeks. In any 52-week window, ALIVE appears exactly twice.
    Position in cycle: (weeks_since_anchor) % 26
"""

import json
import sys
import os

# ---------------------------------------------------------------------------
# Pixel font — 7 rows tall, variable width
# Each letter is a list of 7 strings. 'X' = lit, '.' = dark.
# ---------------------------------------------------------------------------
FONT = {
    'A': [
        '.XXX.',
        'X...X',
        'X...X',
        'XXXXX',
        'X...X',
        'X...X',
        'X...X',
    ],
    'L': [
        'X...',
        'X...',
        'X...',
        'X...',
        'X...',
        'X...',
        'XXXX',
    ],
    'I': [
        'XXX',
        '.X.',
        '.X.',
        '.X.',
        '.X.',
        '.X.',
        'XXX',
    ],
    'V': [
        'X...X',
        'X...X',
        '.X.X.',
        '.X.X.',
        '..X..',
        '..X..',
        '..X..',
    ],
    'E': [
        'XXXX.',
        'X....',
        'X....',
        'XXXX.',
        'X....',
        'X....',
        'XXXXX',
    ],
    'H': [
        'X...X',
        'X...X',
        'X...X',
        'XXXXX',
        'X...X',
        'X...X',
        'X...X',
    ],
    'O': [
        '.XXX.',
        'X...X',
        'X...X',
        'X...X',
        'X...X',
        'X...X',
        '.XXX.',
    ],
    'P': [
        'XXXX.',
        'X...X',
        'X...X',
        'XXXX.',
        'X....',
        'X....',
        'X....',
    ],
    'Y': [
        'X...X',
        'X...X',
        '.X.X.',
        '..X..',
        '..X..',
        '..X..',
        '..X..',
    ],
    'N': [
        'X...X',
        'XX..X',
        'X.X.X',
        'X..XX',
        'X...X',
        'X...X',
        'X...X',
    ],
    'G': [
        '.XXX.',
        'X....',
        'X....',
        'X.XXX',
        'X...X',
        'X...X',
        '.XXX.',
    ],
    'B': [
        'XXXX.',
        'X...X',
        'X...X',
        'XXXX.',
        'X...X',
        'X...X',
        'XXXX.',
    ],
    'T': [
        'XXXXX',
        '..X..',
        '..X..',
        '..X..',
        '..X..',
        '..X..',
        '..X..',
    ],
    'S': [
        '.XXXX',
        'X....',
        'X....',
        '.XXX.',
        '....X',
        '....X',
        'XXXX.',
    ],
    'R': [
        'XXXX.',
        'X...X',
        'X...X',
        'XXXX.',
        'X.X..',
        'X..X.',
        'X...X',
    ],
    'C': [
        '.XXXX',
        'X....',
        'X....',
        'X....',
        'X....',
        'X....',
        '.XXXX',
    ],
    'D': [
        'XXXX.',
        'X...X',
        'X...X',
        'X...X',
        'X...X',
        'X...X',
        'XXXX.',
    ],
    'F': [
        'XXXXX',
        'X....',
        'X....',
        'XXXX.',
        'X....',
        'X....',
        'X....',
    ],
    'J': [
        '..XXX',
        '...X.',
        '...X.',
        '...X.',
        '...X.',
        'X..X.',
        '.XX..',
    ],
    'K': [
        'X...X',
        'X..X.',
        'X.X..',
        'XX...',
        'X.X..',
        'X..X.',
        'X...X',
    ],
    'M': [
        'X...X',
        'XX.XX',
        'X.X.X',
        'X...X',
        'X...X',
        'X...X',
        'X...X',
    ],
    'Q': [
        '.XXX.',
        'X...X',
        'X...X',
        'X...X',
        'X.X.X',
        'X..XX',
        '.XXXX',
    ],
    'U': [
        'X...X',
        'X...X',
        'X...X',
        'X...X',
        'X...X',
        'X...X',
        '.XXX.',
    ],
    'W': [
        'X...X',
        'X...X',
        'X...X',
        'X.X.X',
        'X.X.X',
        'XX.XX',
        'X...X',
    ],
    'X': [
        'X...X',
        'X...X',
        '.X.X.',
        '..X..',
        '.X.X.',
        'X...X',
        'X...X',
    ],
    'Z': [
        'XXXXX',
        '....X',
        '...X.',
        '..X..',
        '.X...',
        'X....',
        'XXXXX',
    ],
    ' ': [
        '...',
        '...',
        '...',
        '...',
        '...',
        '...',
        '...',
    ],
}

# ---------------------------------------------------------------------------
# Rolling pattern constants
# ---------------------------------------------------------------------------
CYCLE_WEEKS = 26          # 25 text cols + 1 gap col = 26-week cycle
GRAPH_DAYS = 7
LETTER_SPACING = 1        # blank columns between letters
ANCHOR_DATE = "2012-09-09"  # Sunday closest to GitHub account creation (2012-09-08)


def letter_to_pixels(char: str) -> list[list[int]]:
    """Convert a character to a 2D pixel array [row][col] of 0/1."""
    rows = FONT.get(char.upper(), FONT[' '])
    return [[1 if c == 'X' else 0 for c in row] for row in rows]


def text_to_columns(text: str) -> list[list[int]]:
    """
    Render text as a list of columns.
    Each column is a list of 7 ints (one per day/row).
    Returns list of columns (to be placed in graph weeks).
    """
    columns = []
    for i, ch in enumerate(text.upper()):
        pixels = letter_to_pixels(ch)  # pixels[row][col]
        width = len(pixels[0])
        # Convert row-major to column-major
        for col_i in range(width):
            col_data = [pixels[row][col_i] for row in range(GRAPH_DAYS)]
            columns.append(col_data)
        # Add spacing between letters (not after the last)
        if i < len(text) - 1:
            for _ in range(LETTER_SPACING):
                columns.append([0] * GRAPH_DAYS)
    return columns


def build_grid(text: str, level: int = 4) -> list[list[int]]:
    """
    Build the CYCLE_WEEKS×7 grid for the given text.
    Text starts at column 0, truncated to CYCLE_WEEKS-1 (leaving 1 gap col at the end).
    Lit pixels get the given level (1-4).
    Returns grid[week][day].
    """
    grid = [[0] * GRAPH_DAYS for _ in range(CYCLE_WEEKS)]

    columns = text_to_columns(text)
    text_width = len(columns)

    # Leave 1 trailing column as gap — text occupies at most CYCLE_WEEKS-1 cols
    max_text_cols = CYCLE_WEEKS - 1
    if text_width > max_text_cols:
        print(f"Warning: text is {text_width} columns wide, truncating to {max_text_cols}.")
        columns = columns[:max_text_cols]
        text_width = max_text_cols

    # Place text starting at column 0
    for col_i, col_data in enumerate(columns):
        week = col_i
        for day in range(GRAPH_DAYS):
            if col_data[day]:
                grid[week][day] = level

    # Column CYCLE_WEEKS-1 stays all zeros (the gap)
    return grid


def print_ascii_preview(grid: list[list[int]], text: str) -> None:
    """
    Print a visual ASCII preview of the contribution graph pattern.
    Shows 2 cycles side by side (= 52 weeks) to simulate the real GitHub graph.
    """
    level_chars = {0: '·', 1: '░', 2: '▒', 3: '▓', 4: '█'}
    display_weeks = CYCLE_WEEKS * 2   # show 2 full cycles = 52 weeks

    print()
    print(f"  Pattern preview for: \"{text}\"  (2× {CYCLE_WEEKS}-week cycle = {display_weeks} weeks)")
    print(f"  {'─' * (display_weeks * 2)}")

    day_names = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    for day in range(GRAPH_DAYS):
        row_chars = []
        for week_i in range(display_weeks):
            week = week_i % CYCLE_WEEKS   # tile the pattern
            level = grid[week][day]
            row_chars.append(level_chars[level])
        print(f"  {day_names[day]}  {''.join(c + ' ' for c in row_chars)}")

    print(f"  {'─' * (display_weeks * 2)}")
    print()

    lit_count = sum(1 for w in range(CYCLE_WEEKS) for d in range(GRAPH_DAYS) if grid[w][d] > 0)
    print(f"  Cycle: {CYCLE_WEEKS} weeks  |  Lit cells per cycle: {lit_count} / {CYCLE_WEEKS * GRAPH_DAYS}")
    print(f"  Anchor: {ANCHOR_DATE}  |  pattern_week = (weeks_since_anchor) % {CYCLE_WEEKS}")
    print()


def generate_pattern(text: str, output_file: str = 'pattern.json', level: int = 4) -> dict:
    """Generate pattern.json for the given text (rolling/tiling mode)."""
    grid = build_grid(text, level=level)

    pattern = {
        "text": text.upper(),
        "cycle_weeks": CYCLE_WEEKS,
        "grid": grid,
        "levels": {
            "0": 0,   # no commits
            "1": 1,   # 1 commit  → lightest green
            "2": 3,   # 3 commits
            "3": 6,   # 6 commits
            "4": 10   # 10 commits → darkest green
        },
        "anchor_date": ANCHOR_DATE,
    }

    print_ascii_preview(grid, text)

    with open(output_file, 'w') as f:
        json.dump(pattern, f, indent=2)

    print(f"  ✓ Saved to {output_file}")
    return pattern


def main():
    if '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        sys.exit(0)

    text = sys.argv[1] if len(sys.argv) > 1 else 'ALIVE'
    output = sys.argv[2] if len(sys.argv) > 2 else 'pattern.json'

    print(f"\n  github-alive pattern designer")
    print(f"  Text: \"{text.upper()}\"  |  Cycle: {CYCLE_WEEKS} weeks  |  Output: {output}")

    generate_pattern(text, output_file=output)


if __name__ == '__main__':
    main()
