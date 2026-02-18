# english-record-learner

Record all Claude Code conversations from a specific date — across all projects — into a single dated Apple Note.

## What This Skill Does

1. Finds **all** session files across **all** projects for the target date
2. Extracts all Q&A — user prompts kept **exact**, assistant responses **summarized**
3. Groups Q&A by project so the note is organized
4. Collects all English corrections made across all sessions, grouped by project
5. Saves everything to a dated Apple Note (`YYYYMMDD`)

## Storage Locations

- **Session files:** `~/.claude/projects/*/[sessionId].jsonl`
- **Apple Notes:** iCloud → Notes folder, title = date in `YYYYMMDD` format

## Scripts

All scripts are in `scripts/` inside this skill folder.

| Script | Purpose |
|---|---|
| `find-sessions.sh [DATE]` | Find all session files for a date across all projects |
| `extract-qa.py [--date DATE] PROJECT\|FILE ...` | Extract clean Q&A pairs as JSON |
| `extract-corrections.py [--date DATE] PROJECT\|FILE ...` | Extract English correction tables as JSON |

DATE format: `YYYY-MM-DD`. Defaults to today if omitted.

## Steps to Follow

### Step 1 — Get the target date

If the user did not specify a date, use today:

```bash
DATE=$(date +%Y%m%d)         # Apple Note title  e.g. 20260218
DATE_ISO=$(date +%Y-%m-%d)   # Filter sessions   e.g. 2026-02-18
```

### Step 2 — Find all session files for that date

```bash
SKILL=~/.claude/skills/english-record-learner

SESSIONS=$(bash "$SKILL/scripts/find-sessions.sh" "$DATE_ISO")
echo "$SESSIONS"
```

Output is one line per session: `project-name|/path/to/session.jsonl`

If no sessions are found, tell the user there are no conversations recorded for that date.

### Step 3 — Extract Q&A

```bash
QA_JSON=$(python3 "$SKILL/scripts/extract-qa.py" --date "$DATE_ISO" $SESSIONS)
echo "$QA_JSON"
```

Output is a JSON array — user prompts exact, assistant text included for Claude to summarize.

### Step 4 — Extract English corrections

```bash
CORRECTIONS_JSON=$(python3 "$SKILL/scripts/extract-corrections.py" --date "$DATE_ISO" $SESSIONS)
echo "$CORRECTIONS_JSON"
```

Output is a JSON object grouped by project — correction rows already extracted.

### Step 5 — Build the Apple Note content

Using the JSON from Steps 3 and 4, build the note as HTML:

```
<div><h1>YYYYMMDD</h1></div>
<div><br></div>

For each project in QA_JSON:
  <div><h2>[project name]</h2></div>
  <div><br></div>

  For each Q&A pair:
    <div>❯ [exact user prompt]</div>
    <div><br></div>
    <div>⏺ [summarized assistant response — 1 to 3 sentences]</div>
    <div><br></div>

If CORRECTIONS_JSON has any entries:
  <div><h2>English Corrections</h2></div>

  For each project in CORRECTIONS_JSON:
    <div><h3>[project name]</h3></div>
    <div>[correction table for that project]</div>
```

### Step 6 — Save to Apple Note

Check if a note for the date already exists:

```bash
~/.claude/skills/apple-note/scripts/search-notes.sh iCloud Notes "$DATE"
```

- If it **exists** → use `update-note.sh` (full replacement)
- If it **does not exist** → use `create-note.sh`

```bash
# Create
~/.claude/skills/apple-note/scripts/create-note.sh iCloud Notes "$DATE" "<html content>"

# Update
~/.claude/skills/apple-note/scripts/update-note.sh iCloud Notes "$DATE" "<html content>"
```

### Step 7 — Confirm

Tell the user:
- The note title saved
- How many projects were included
- How many Q&A pairs were recorded in total
- How many English corrections were collected

## Rules

- **Never summarize user prompts** — keep them exactly as written, typos and all
- **Always summarize assistant responses** — 1 to 3 sentences max
- **Group by project** — makes it easy to see which conversation belongs where
- **Corrections section is optional** — only include if corrections were actually made
- **Skip system messages, tool calls, and progress entries** — scripts handle this automatically
- **If no date is given, default to today**
