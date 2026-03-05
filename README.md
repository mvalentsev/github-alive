# github-alive

[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Paints the word ALIVE in your GitHub contribution graph** — automatically topping up commits every day, taking your real activity into account.

```
  Sun  · · · · · · · · · · · · · · █ █ █ · · █ · · · · █ █ █ · █ · · · █ · █ █ █ █ · · · · · · · · ·
  Mon  · · · · · · · · · · · · · █ · · · █ · █ · · · · · █ · · █ · · · █ · █ · · · · · · · · · · · ·
  Tue  · · · · · · · · · · · · · █ · · · █ · █ · · · · · █ · · · █ · █ · · █ · · · · · · · · · · · ·
  Wed  · · · · · · · · · · · · · █ █ █ █ █ · █ · · · · · █ · · · █ · █ · · █ █ █ █ · · · · · · · · ·
  Thu  · · · · · · · · · · · · · █ · · · █ · █ · · · · · █ · · · · █ · · · █ · · · · · · · · · · · ·
  Fri  · · · · · · · · · · · · · █ · · · █ · █ · · · · · █ · · · · █ · · · █ · · · · · · · · · · · ·
  Sat  · · · · · · · · · · · · · █ · · · █ · █ █ █ █ · █ █ █ · · · █ · · · █ █ █ █ █ · · · · · · · ·
```

> `█` = dark green squares on your contribution graph.  
> Your graph wraps around every year — the pattern repeats automatically.

---

## How it works

GitHub renders a 52 × 7 contribution graph (52 weeks × 7 days).  
`github-alive` maps the letters **A · L · I · V · E** onto that grid using a 7-row pixel font.

Each day, a small script checks:
1. **What level** (0–4) the current cell requires.
2. **How many commits** you've already made today (via GitHub API).
3. **How many more** are needed to hit the target, and creates them.

| Level | Commits needed | Shade |
|-------|---------------|-------|
| 0     | 0             | none  |
| 1     | 1             | light green |
| 2     | 3             | medium green |
| 3     | 6             | dark green |
| 4     | 10            | darkest green |

The project uses only a lightweight `alive.md` file inside a dedicated repo as the commit target — your actual code repos stay untouched.

---

## Installation

### 1. Create the target repo

Create a **public** repo called `alive` on GitHub (or any name you prefer — set it in config).  
You can leave it completely empty; `alive.py` will create `alive.md` automatically.

### 2. Clone github-alive

```bash
git clone https://github.com/your-username/github-alive.git
cd github-alive
pip install requests
```

### 3. Configure

```bash
cp config.example.json config.json
```

Edit `config.json`:

```json
{
  "github_token": "ghp_...",
  "github_user": "your-username",
  "alive_repo": "alive",
  "pattern_file": "pattern.json"
}
```

**Token scopes needed:** `repo` (to create commits via the Contents API).

### 4. Generate the pattern

```bash
python designer.py           # generates pattern.json for "ALIVE"
python designer.py "HELLO"   # or any custom word (A-Z supported)
```

The designer prints an ASCII preview and saves `pattern.json`.

### 5. Run manually

```bash
python alive.py
```

The script will log what it's doing:

```
2024-01-15 12:00:00  INFO      === github-alive starting ===
2024-01-15 12:00:00  INFO      User: yourname  |  Repo: alive  |  Pattern: pattern.json
2024-01-15 12:00:00  INFO      Today: 2024-01-15  |  Week: 2  |  Day: 1
2024-01-15 12:00:00  INFO      Target commits for today (level 4): 10
2024-01-15 12:00:01  INFO      Real commits today: 3
2024-01-15 12:00:01  INFO      Commits needed: 7
2024-01-15 12:00:01  INFO      Making 7 commit(s) to yourname/alive for 2024-01-15...
2024-01-15 12:00:05  INFO      === Done! Made 7 commit(s). ===
```

---

## GitHub Actions setup

To run automatically every day, push this repo to GitHub and configure Actions:

### 1. Add repository secrets

Go to your **github-alive** repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret name   | Value |
|---------------|-------|
| `ALIVE_TOKEN` | Your personal access token (with `repo` scope) |
| `GITHUB_USER` | Your GitHub username |

> Note: The built-in `GITHUB_TOKEN` in Actions cannot create commits that count in the contribution graph — you **must** use a personal access token stored as `ALIVE_TOKEN`.

### 2. Push the workflow

The workflow file is already at `.github/workflows/alive.yml`. Push it:

```bash
git add .
git commit -m "feat: initial github-alive setup"
git push
```

The workflow runs at **08:00, 13:00, and 19:00 UTC** every day. You can also trigger it manually from the Actions tab.

---

## Custom text

```bash
python designer.py "HELLO"
python designer.py "CODE"
python designer.py "OPEN"
```

Supported characters: A–Z and space. The text is automatically centered in the 52-week graph. If it's too long to fit, it's truncated.

After generating a new `pattern.json`, commit and push it — the Actions workflow will pick it up on the next run.

---

## File structure

```
github-alive/
├── README.md               ← you are here
├── config.example.json     ← copy to config.json and fill in your token
├── config.json             ← (git-ignored) your real config
├── pattern.json            ← 52×7 grid generated by designer.py
├── designer.py             ← pixel-font renderer, generates pattern.json
├── alive.py                ← daily runner: count commits, top up as needed
└── .github/
    └── workflows/
        └── alive.yml       ← GitHub Actions cron job
```

---

## How the pattern tiles

`github-alive` uses a **rolling / tiling** pattern rather than a fixed calendar-year layout.

### Concept

```
|<-- 26 weeks (1 cycle) -->|<-- 26 weeks (1 cycle) -->|
| A L I V E · · · · · · · | A L I V E · · · · · · · |
```

- The word **ALIVE** occupies **25 columns** of the pixel font.
- Column 26 is a blank gap — creating visual separation between repetitions.
- Total **cycle length = 26 weeks**.
- In any **52-week window** (GitHub's full contribution graph), ALIVE appears **exactly twice**.

### Why it's better than year-anchored patterns

| Year-anchored | Rolling |
|---|---|
| Must backfill when you start mid-year | No backfill needed — tiling works from any date |
| Pattern breaks at year boundaries | Seamless, infinite repetition |
| Need to regenerate every year | Set it and forget it |

### How position is calculated

```python
anchor = datetime.date.fromisoformat(cfg["anchor_date"])  # 2012-09-09 (Sunday)
days_since_anchor = (today - anchor).days
week_since_anchor = days_since_anchor // 7
pattern_week = week_since_anchor % cycle_weeks            # 0..25
day_index    = today.isoweekday() % 7                     # Sun=0 .. Sat=6
```

`anchor_date` is the Sunday closest to the GitHub account creation date (2012-09-08 → 2012-09-09). It can be any Sunday — it just determines where ALIVE "phases" in the graph.

---

## FAQ

**Will this overwrite my real commits?**  
No. The script counts your real commits first and only adds what's missing to reach the target.

**Does it mess with my existing repos?**  
No. All synthetic commits go into the dedicated `alive` repo (or whatever you configure in `alive_repo`).

**What if I have more commits than the target?**  
Nothing happens — the script never removes commits.

**Can I change the pattern mid-year?**  
Yes. Run `designer.py` with new text, commit `pattern.json`, and the next run picks up the new pattern. Historical cells in the graph won't change, but future ones will.

**The graph starts on a different week for me.**  
GitHub's graph always shows the last 52 weeks starting from "today minus 52 weeks". The script uses ISO week numbers modulo 52, so it lines up correctly regardless of what day you start.

---

## License

MIT © 2024 — free to use, fork, and share.
