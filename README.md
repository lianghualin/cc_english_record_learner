# english-record-learner

A Claude Code skill that records your daily conversations into Apple Notes — designed for English learners who practice by working on real projects.

## The Idea

You learn English by having real conversations with Claude Code — asking questions, giving tasks, getting answers. At the end of the day, run `/english-record-learner` to save everything into a dated Apple Note.

The skill also collects all English corrections Claude made during the session, so you can review them in one place.

## What It Records

- All Q&A from every Claude Code session on the target date
- Conversations across **all projects** — not just one
- User prompts kept **exactly as written** (typos preserved for learning)
- Assistant responses **summarized** to 1-3 sentences
- English corrections grouped by project at the bottom

## Output Format

```
┌─────────────────────────────────────────┐
│  20260218                               │
│                                         │
│  ── flutter-morphing-navigation ──      │
│                                         │
│  ❯ you check the 20260213 apple note.  │
│    what is it recording?                │
│                                         │
│  ⏺ The note records two things: git    │
│    submodule question and Flutter       │
│    navigation package swap plan.        │
│                                         │
│  ── english-daily-md ──                 │
│                                         │
│  ❯ change to all project, all          │
│    conversation that specific date      │
│                                         │
│  ⏺ Updated skill to scan all projects  │
│    and group Q&A by project name.       │
│                                         │
│  ── English Corrections ──              │
│                                         │
│  [flutter-morphing-navigation]          │
│  What you wrote    │ More natural       │
│  ──────────────────┼────────────────    │
│  "Am i description"│ "Am I describing"  │
│                                         │
│  [english-daily-md]                     │
│  What you wrote    │ More natural       │
│  ──────────────────┼────────────────    │
│  "more accurity"   │ "more accurate"    │
│  "summary this"    │ "summarize this"   │
│                                         │
└─────────────────────────────────────────┘
```

## Install

### Prerequisites

- macOS with Apple Notes app
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed
- Python 3 (pre-installed on macOS)
- [`apple-note` skill](https://github.com/LeetaoGoooo/apple-note-plugin) installed

### Step 1 — Install the apple-note skill (dependency)

```bash
git clone https://github.com/LeetaoGoooo/apple-note-plugin.git ~/.claude/skills/apple-note
```

### Step 2 — Install english-record-learner

```bash
git clone https://github.com/lianghualin/english_daily_md.git /tmp/english_daily_md
cp -r /tmp/english_daily_md/english-record-learner ~/.claude/skills/english-record-learner
chmod +x ~/.claude/skills/english-record-learner/scripts/*.sh
chmod +x ~/.claude/skills/english-record-learner/scripts/*.py
```

Or if you already cloned the repo:

```bash
cp -r english-record-learner ~/.claude/skills/english-record-learner
chmod +x ~/.claude/skills/english-record-learner/scripts/*.sh
chmod +x ~/.claude/skills/english-record-learner/scripts/*.py
```

### Step 3 — Auto-approve permissions (optional)

To skip permission prompts when running the skill, create `.claude/settings.local.json` in your project folder:

```json
{
  "permissions": {
    "allow": [
      "Bash"
    ]
  }
}
```

This only applies when running Claude Code from that project directory.

### Step 4 — Verify

Open Claude Code and type:

```
/english-record-learner
```

## Usage

```
/english-record-learner              # record today's conversations
/english-record-learner 2026-02-17   # record a specific date
```

## How It Works

The skill uses three scripts to minimize token usage:

```
┌──────────────────┐
│ find-sessions.sh │ → finds session files by date across all projects
└────────┬─────────┘
         ↓
┌──────────────────┐
│  extract-qa.py   │ → strips system noise, outputs clean Q&A as JSON
└────────┬─────────┘
         ↓
┌──────────────────────────┐
│  extract-corrections.py  │ → regex-extracts English correction tables
└────────┬─────────────────┘
         ↓
┌──────────────────┐
│   Claude Code    │ → only summarizes assistant text + saves to Apple Note
└──────────────────┘
```

**Without scripts:** Claude reads raw `.jsonl` files full of system messages, tool calls, and progress entries — wasting tokens on noise.

**With scripts:** Claude only receives clean text — user prompts and assistant responses ready to summarize.

## Scripts Reference

| Script | Input | Output |
|---|---|---|
| `find-sessions.sh [DATE]` | Date (YYYY-MM-DD), defaults to today | `project\|filepath` lines |
| `extract-qa.py --date DATE sessions...` | Session entries from find-sessions | JSON array of Q&A pairs |
| `extract-corrections.py --date DATE sessions...` | Session entries from find-sessions | JSON object of corrections by project |

## File Structure

```
english-record-learner/
├── README.md          ← this file
├── SKILL.md           ← skill instructions for Claude Code
└── scripts/
    ├── find-sessions.sh
    ├── extract-qa.py
    └── extract-corrections.py
```

## Related

- [apple-note skill](https://github.com/LeetaoGoooo/apple-note-plugin) — the dependency for reading/writing Apple Notes
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — Anthropic's CLI for Claude
