# github-alive — A living contribution graph

Your GitHub contribution graph becomes a self-evolving abstract pattern.
Real commits blend seamlessly into the design — a sprint of 50 commits looks
like a natural peak, not a disruption.

```
Jan ─────────────────────── Jun ──────────────────────── Dec
Sun  ░ ░ ░ ░ ░ ░ ▒ ▒ ▒ ▓ ▓ ▓ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ░ ░ ░ ▒ ▒ ▒ ▓ ▓ ▓ ▓ ▓ ▓ ▒ ▒ ░ ░ ░ ░ ░ ░ ░ ░ ▒ ▒ ▒ ▒ ▒
Mon  ░ ░ ░ ░ ▒ ▒ ▒ ▓ ▓ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ░ ░ ░ ▒ ▒ ▓ ▓ ▓ ▓ ▓ ▓ ▓ ▒ ▒ ▒ ░ ░ ░ ░ ░ ░ ▒ ▒ ▒ ▒ ▒ ▒ ▒
Tue  ░ ░ ░ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ░ ░ ░ ▒ ▒ ▒ ▓ ▓ ▓ ▓ ▓ ▓ ▒ ▒ ▒ ▒ ░ ░ ░ ░ ░ ░ ▒ ▒ ▒ ▒ ▒ ▒ ▒
Wed  ░ ░ ░ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ░ ░ ▒ ▒ ▒ ▓ ▓ ▓ ▓ ▓ ▓ ▓ ▒ ▒ ▒ ░ ░ ░ ░ ░ ░ ░ ▒ ▒ ▒ ▒ ▒ ▒ ▒
Thu  ░ ░ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ░ ░ ░ ▒ ▒ ▓ ▓ ▓ ▓ ▓ ▓ ▓ ▒ ▒ ▒ ░ ░ ░ ░ ░ ░ ░ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒
Fri  ░ ░ ░ ░ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ░ ░ ░ ░ ▒ ▒ ▒ ▓ ▓ ▓ ▓ ▓ ▒ ▒ ▒ ░ ░ ░ ░ ░ ░ ░ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒
Sat  ░ ░ ░ ░ ▒ ▒ ▒ ▓ ▓ ▓ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ░ ░ ▒ ▒ ▒ ▓ ▓ ▓ ▓ ▓ ▒ ▒ ▒ ░ ░ ░ ░ ░ ░ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒ ▒

Legend:  · 1–5   ░ 6–15   ▒ 16–25   ▓ 26–35   █ 36–40  commits/day
```

---

## How it works

github-alive runs daily (via GitHub Actions) and computes how many commits
your contribution graph *should* show for today using a deterministic
mathematical function. It then counts your real commits for today and fills
the gap if needed.

**Real activity blends in naturally.** If you push 30 commits during a sprint,
that lands right in a peak zone of the pattern. It looks like the wave
was always meant to be there — because mathematically, it was.

```
target  = base_commits(today)   # from the wave function
real    = count_real_commits()  # your actual GitHub activity (excl. alive repo)
delta   = max(0, target - real) # only fill the gap
```

---

## Features

- **Deterministic** — same date always produces the same pattern. No state, no config files.
- **Self-healing** — real commits count toward the target. Work more, fill less.
- **No config** — just set two env vars (`GITHUB_TOKEN` + `GITHUB_USER`) and run.
- **Organic** — overlapping sine waves at different frequencies create texture that looks hand-drawn.
- **No backfill** — runs daily, shapes only the present moment.

---

## Installation

### 1. Create the `alive` repo on GitHub

Create a public (or private) repository named `alive` in your GitHub account.
It just needs to exist — github-alive will commit to it.

### 2. Clone this repo and install dependencies

```bash
git clone https://github.com/YOUR_USERNAME/github-alive
cd github-alive
pip install requests
```

### 3. Configure credentials

Copy the example config and fill in your details:

```bash
cp config.example.json config.json
```

```json
{
  "github_token": "ghp_...",
  "github_user": "your-username",
  "alive_repo": "alive"
}
```

> `config.json` is in `.gitignore` — it will never be committed.

Alternatively, use environment variables:

```bash
export GITHUB_TOKEN=ghp_...
export GITHUB_USER=your-username
```

### 4. Run manually

```bash
python3 alive.py
```

### 5. Set up GitHub Actions (automated daily run)

The included workflow runs three times a day at **02:00, 10:00, and 18:00 UTC**.

Add these secrets to your repository (`Settings → Secrets → Actions`):

| Secret | Value |
|---|---|
| `ALIVE_TOKEN` | Personal access token with `repo` + `user` scope |
| `GH_USER` | Your GitHub username |

The workflow file is already at `.github/workflows/alive.yml`.

---

## Visualizing the pattern

Preview the next 52 weeks in your terminal:

```bash
python3 designer.py
```

```
  github-alive — pattern preview (next 52 weeks)
  Anchor: 2012-09-09  |  Today: 2024-06-10

  Legend:  · 1–5   ░ 6–15   ▒ 16–25   ▓ 26–35   █ 36–40  commits

  ────────────────────────────────────────────────────────────────────
  Sun  ░ ░ ▒ ▒ ▓ ▓ ▓ ▒ ▒ ░ ░ ░ ▒ ▒ ▓ ▓ █ ▓ ▓ ▒ ▒ ░ ░ ░ ▒ ▒ ▓ ...
  Mon  ░ ▒ ▒ ▓ ▓ ▓ ▒ ▒ ░ ░ ░ ▒ ▒ ▓ ▓ █ █ ▓ ▒ ▒ ░ ░ ░ ▒ ▒ ▓ ▓ ...
  Tue  ▒ ▒ ▓ ▓ ▓ ▒ ▒ ░ ░ ░ ▒ ▒ ▓ ▓ █ █ ▓ ▓ ▒ ▒ ░ ░ ░ ▒ ▒ ▓ ▓ ...
  Wed  ▒ ▓ ▓ ▓ ▒ ▒ ░ ░ ░ ▒ ▒ ▓ ▓ █ █ █ ▓ ▒ ▒ ░ ░ ░ ░ ▒ ▒ ▓ ▓ ...
  Thu  ▓ ▓ ▓ ▒ ▒ ░ ░ ░ ▒ ▒ ▓ ▓ █ █ █ ▓ ▒ ▒ ░ ░ ░ ░ ▒ ▒ ▓ ▓ ▓ ...
  Fri  ▓ ▓ ▒ ▒ ░ ░ ░ ▒ ▒ ▓ ▓ █ █ █ ▓ ▒ ▒ ░ ░ ░ ░ ▒ ▒ ▓ ▓ ▓ ▒ ...
  Sat  ░ ░ ░ ▒ ▒ ▓ ▓ ▓ ▒ ▒ ░ ░ ░ ▒ ▒ ▓ ▓ █ ▓ ▓ ▒ ▒ ░ ░ ░ ▒ ▒ ...
  ────────────────────────────────────────────────────────────────────
        ↑ today (Mon Jun 10)
```

---

## How the pattern is generated

The pattern is produced by five overlapping sine waves, each operating at a
different timescale:

| Wave | Period | Role |
|---|---|---|
| `w1` | 26 weeks | Primary rhythm — broad rise and fall |
| `w2` | 13 weeks | Harmonic — mid-scale structure |
| `w3` | 52 weeks | Yearly drift — slow background mood |
| `w4` | 7 days + slow phase drift | Day-of-week texture |
| `w5` | diagonal | Cross-grid ripple |

They combine with weighted mixing:

```python
combined = w1*0.35 + w2*0.25 + w3*0.15 + w4*0.15 + w5*0.10
commits  = round(3 + (combined + 1) * 18.5)   # maps [-1,1] → [3, 40]
```

The result is a pattern where no two weeks are identical, yet the whole
graph flows with visual coherence — peaks cluster, valleys breathe,
and diagonal streaks emerge from the interference of the waves.

---

## Files

| File | Purpose |
|---|---|
| `alive.py` | Daily runner — computes target, counts real commits, fills gap |
| `designer.py` | Terminal visualizer — preview the next 52 weeks |
| `backfill.py` | One-time historical backfill for a date range |
| `noise_backfill.py` | Adds sparse noise commits to "quiet" days (makes graph look more organic) |
| `config.example.json` | Config template (copy to `config.json`) |
| `.github/workflows/alive.yml` | GitHub Actions schedule (3× daily) |

---

## License

MIT
