# english-record-learner

Record all Claude Code conversations from a specific date — across all projects — into a single dated Apple Note.

## What This Skill Does

1. Finds **all** session files across **all** projects for the target date
2. Extracts all Q&A — user prompts kept **exact**, assistant responses **summarized**
3. Groups Q&A by project so the note is organized
4. Collects all English corrections made across all sessions, grouped by project
5. Analyzes all user prompts for English errors and generates additional corrections
6. Saves everything to a dated Apple Note (`YYYYMMDD`)

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
SKILL="$HOME/.claude/skills/english-record-learner"

bash "$SKILL/scripts/find-sessions.sh" "$DATE_ISO" > /tmp/sessions_${DATE}.txt
cat /tmp/sessions_${DATE}.txt
```

Output is one line per session in `/tmp/sessions_YYYYMMDD.txt`: `project-name|/path/to/session.jsonl`

If no sessions are found, tell the user there are no conversations recorded for that date.

### Step 3 — Extract Q&A

Use `xargs` to pass each session as a separate argument:

```bash
SKILL="$HOME/.claude/skills/english-record-learner"

xargs python3 "$SKILL/scripts/extract-qa.py" --date "$DATE_ISO" < /tmp/sessions_${DATE}.txt > /tmp/qa_${DATE}.json
```

Output is a JSON array in `/tmp/qa_YYYYMMDD.json` — user prompts exact, assistant text included for Claude to summarize.

### Step 4 — Extract English corrections

```bash
xargs python3 "$SKILL/scripts/extract-corrections.py" --date "$DATE_ISO" < /tmp/sessions_${DATE}.txt > /tmp/corrections_${DATE}.json
```

Output is a JSON object in `/tmp/corrections_YYYYMMDD.json` grouped by project — correction rows already extracted.

### Step 5 — Analyze user prompts for English errors (subagent)

First, extract all user prompts from QA_JSON into a plain text list (numbered, one per line). Then launch a **Task subagent** (subagent_type: `general-purpose`) with the following prompt:

```
You are an expert English teacher analyzing prompts written by a Chinese English learner.
These are messages they typed to an AI coding assistant (Claude Code).

Your job:
1. Identify ALL English errors in each prompt (grammar, word choice, spelling, sentence structure, capitalization)
2. Skip prompts that are correct or too short to meaningfully correct
3. Skip pasted content (quotes, documentation, code) — only analyze the user's own words
4. Ignore technical content — don't correct code, IPs, file paths, CLI commands, or product names
5. For each error, provide:
   - The exact phrase they wrote (preserve original)
   - A more natural version
   - A brief explanation of the error type and WHY the correction is better
   - Category: Grammar, Word Choice, Spelling, Sentence Structure, or Capitalization

Output ONLY the raw JSON array (no markdown fences, no extra text). Each entry:
{
  "prompt_num": 1,
  "original": "how can i using",
  "corrected": "How can I use",
  "category": "Grammar",
  "explanation": "After 'can' (modal verb), use the base form 'use', not the -ing form."
}

Be thorough and educational. Group related errors from the same prompt into separate entries.

Here are the prompts to analyze:

[paste the numbered user prompts here]
```

**Important:** The subagent may not be able to write files to disk. Handle both cases:
1. If the subagent returns the JSON in its response text, parse it directly from the response
2. If the subagent successfully writes to `/tmp/subagent_corrections_YYYYMMDD.json`, read it from there

Either way, merge the subagent corrections with any corrections from Step 4. Do not duplicate — if an extracted correction already covers the same phrase, skip it.

### Step 6 — Build the Apple Note content

Using the JSON from Steps 3, 4, and 5, build the note as HTML.

Use `<h2>` and `<h3>` headings — Apple Notes makes these **collapsible**, so users can expand/collapse sections.

**Corrections come first** (the learning part), **Conversations at the end** (the reference/archive part).

```
<div><h1>YYYYMMDD</h1></div>
<div><br></div>

<div><h2>English Corrections</h2></div>

For each project that has corrections:
  <div><h3>[project name]</h3></div>

  Group corrections by category (Grammar, Sentence Structure, Word Choice, Spelling, Capitalization).
  For each category:
    <div><b>[Category] ([count])</b></div>
    <table border="1" cellpadding="4" cellspacing="0">
      <tr><th>What you wrote</th><th>More natural</th><th>Why</th></tr>
      <tr><td>[original]</td><td>[corrected]</td><td>[explanation]</td></tr>
      ...
    </table>
    <div><br></div>

<div><h2>Conversations</h2></div>

For each project in QA_JSON:
  <div><h3>[project name]</h3></div>
  <div><br></div>

  For each Q&A pair:
    <div>❯ [exact user prompt]</div>
    <div><br></div>
    <div>⏺ [summarized assistant response — 1 to 3 sentences]</div>
    <div><br></div>
```

### Step 7 — Save to Apple Note

Check if a note for the date already exists:

```bash
bash "$HOME/.claude/skills/apple-note/scripts/search-notes.sh" iCloud Notes "$DATE"
```

- If it **exists** → use `update-note.sh` (full replacement)
- If it **does not exist** → use `create-note.sh`

```bash
# Create
bash "$HOME/.claude/skills/apple-note/scripts/create-note.sh" iCloud Notes "$DATE" "<html content>"

# Update
bash "$HOME/.claude/skills/apple-note/scripts/update-note.sh" iCloud Notes "$DATE" "<html content>"
```

**Important:** Always use the `iCloud Notes` folder. Do not try `Daily` or other folders — they may be Smart Folders that reject direct writes.

### Step 8 — Confirm

Tell the user:
- The note title saved
- How many projects were included
- How many Q&A pairs were recorded in total
- How many English corrections were collected (extracted + newly generated)

## Rules

- **Never summarize user prompts** — keep them exactly as written, typos and all
- **Always summarize assistant responses** — 1 to 3 sentences max
- **Group by project** — makes it easy to see which conversation belongs where
- **Always use a subagent for prompt analysis** — launch a Task subagent to analyze user prompts for English errors; this produces more thorough, educational corrections than inline analysis
- **Ignore technical content** — don't correct code, file paths, CLI commands, or technical terms
- **Merge corrections** — combine extracted corrections with subagent-generated ones, avoiding duplicates
- **Group corrections by category** — Grammar, Sentence Structure, Word Choice, Spelling, Capitalization
- **Include explanations** — each correction must have a "Why" column explaining the grammar rule
- **Corrections section is optional** — only include if there are corrections (extracted or generated)
- **Skip system messages, tool calls, and progress entries** — scripts handle this automatically
- **If no date is given, default to today**
