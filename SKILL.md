# english-record-learner

Record all Claude Code conversations from a specific date — across all projects — into a single dated Apple Note.

## Commands

This skill supports arguments. Check what the user typed after `/english-record-learner`:

| Argument | Action |
|---|---|
| *(none)* or a date | Run the **full recording workflow** (Steps 1–9 below) |
| `unfin` | Run the **extract unfinished** workflow — extract English corrections from all unfinished notes in the `Notes` folder into a Markdown file |
| `pdf` | Run the **PDF generation** workflow — extract corrections from all `_fin` notes, convert to PDF, output only the PDF to the current directory |

### `unfin` workflow

Extract English corrections from all Apple Notes named `YYYYMMDD` (without `_fin`) in the iCloud `Notes` folder, and write them to `english-corrections-unfin.md` in the current directory.

**Step 1 — Extract corrections and detect repetitions:**

```bash
SKILL="$HOME/.claude/skills/english-record-learner"
bash "$SKILL/scripts/extract-daily-corrections.sh" --unfin
```

The script extracts corrections, user prompts, and appends a "Repeated Patterns" section with frequency data.

**Step 2 — Analyze repetitions with a subagent:**

If the output file contains a "## Repeated Patterns" section, read the entire file and launch a **Task subagent** (`subagent_type: general-purpose`) with this prompt:

```
You are an expert English teacher helping a Chinese English learner improve their expression variety.

Below is a Markdown file containing:
1. English corrections grouped by date (with "What you wrote" / "More natural" / "Why" tables)
2. A "Repeated Patterns" section with:
   - Repeated Mistakes: same phrases corrected on multiple dates
   - Frequently Used Words: overused words in their prompts
   - Frequently Used Phrases: overused two-word phrases in their prompts

Your job:
1. For each "Repeated Mistake", explain WHY the user keeps making this error (the underlying grammar/vocabulary habit), and give 2-3 varied correct alternatives they can use instead.
2. For the frequently used words and phrases, identify which ones indicate LIMITED vocabulary or unnatural expression (skip words that are naturally frequent like technical terms). For each problematic one, suggest 2-3 richer alternatives with example sentences.
3. Look across ALL corrections for recurring ERROR PATTERNS — not just exact duplicates, but the same TYPE of mistake (e.g., always confusing "make" vs "do", always dropping articles, always using "-ing" after modals). List each pattern with examples from the data and a clear rule to remember.

Output as Markdown with these sections:

## Improvement Suggestions

### Habitual Mistakes
For each repeated mistake:
- **"[phrase]"** (appeared X times on [dates])
  - Why this keeps happening: [explanation of the underlying habit]
  - Try instead: "[alt1]", "[alt2]", "[alt3]"

### Recurring Error Patterns
For each pattern found across corrections:
- **[Pattern name]** (e.g., "Missing articles before countable nouns")
  - Examples from your writing: "[example1]", "[example2]"
  - Rule: [clear, memorable rule]

### Vocabulary Expansion
For each overused word/phrase:
- **"[word/phrase]"** (used X times)
  - Try instead: "[alt1]" — [when to use it]
  - Try instead: "[alt2]" — [when to use it]
  - Example: "[natural sentence using the alternative]"

Be specific, educational, and encouraging. Only include patterns where improvement would be meaningful.

Here is the full corrections file:

[paste the full content of english-corrections-unfin.md here]
```

**Step 3 — Append results:**

Read the subagent's response and append it to `english-corrections-unfin.md` (after a `---` separator). Then tell the user how many notes and corrections were found, highlight the key repeated patterns discovered, and the output file path. Then **stop** — do not continue to the recording steps below.

### `pdf` workflow

Extract English corrections from all `_fin` notes in `Daily_fin`, convert to a styled PDF, and output only the PDF to the current directory. All intermediate files (`.md`, `.tex`, `.log`, `.aux`, `.out`, `.toc`) are generated in a temp directory and cleaned up automatically.

Run these steps sequentially (each as a separate bash command):

```bash
# Step 1 — Create temp dir and extract corrections
WORK=$(mktemp -d)
SKILL="$HOME/.claude/skills/english-record-learner"
bash "$SKILL/scripts/extract-daily-corrections.sh" "$WORK/english-corrections.md"
```

```bash
# Step 2 — Convert markdown to LaTeX
SKILL="$HOME/.claude/skills/english-record-learner"
python3 "$SKILL/scripts/md2latex.py" "$WORK/english-corrections.md" "$WORK/english-corrections.tex"
```

```bash
# Step 3 — Compile LaTeX to PDF (two passes for TOC, use -output-directory to avoid cd)
pdflatex -interaction=nonstopmode -output-directory="$WORK" "$WORK/english-corrections.tex" > /dev/null 2>&1
pdflatex -interaction=nonstopmode -output-directory="$WORK" "$WORK/english-corrections.tex" > /dev/null 2>&1
```

```bash
# Step 4 — Copy PDF to current directory and clean up
cp "$WORK/english-corrections.pdf" ./english-corrections.pdf
rm -rf "$WORK"
```

Tell the user the output file path and how many corrections/notes were included. Then **stop**.

---

## What This Skill Does

1. Finds **all** session files across **all** projects for the target date
2. Extracts all Q&A — user prompts kept **exact**, assistant responses extracted
3. Groups Q&A by project so the note is organized
4. Collects all English corrections made across all sessions, grouped by project
5. Launches **parallel subagents**: one to analyze prompts for English errors (with conversation context), one to summarize assistant responses
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
| `extract-daily-corrections.sh [--unfin] [output]` | Extract corrections from Apple Notes to Markdown |
| `parse-daily-corrections.py <dir> <output>` | Parse note HTML files into consolidated Markdown |
| `md2latex.py <input_md> <output_tex>` | Convert corrections Markdown to styled LaTeX for PDF |

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

### Step 5 — Parallel subagents: corrections + summarization

Launch **two Task subagents in parallel** (both `subagent_type: general-purpose`). Both receive the Q&A JSON from Step 3. Use a single message with two Task tool calls so they run concurrently.

#### Step 5a — Correction subagent

Format the Q&A pairs from QA_JSON into a numbered list **with conversation context**. For each user prompt, include a brief excerpt from the preceding assistant response (~100 chars) so the subagent understands what the user was replying to. Format:

```
--- Project: project-name ---

[1] (After assistant: "I've created the helper function that handles...")
    User: "how can i using this function in my code"

[2] User: "please help me fix the bug"
```

Then launch the subagent with this prompt:

```
You are an expert English teacher analyzing prompts written by a Chinese English learner.
These are messages they typed to an AI coding assistant (Claude Code).
Each prompt includes brief context from the preceding assistant response so you can understand what the user was replying to — use this context to better judge what the user was trying to say, but only analyze the user's own words.

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
6. ALSO look for prompts where the overall expression could be improved — even if individual words are grammatically acceptable, the whole sentence may sound unnatural or non-idiomatic. For these, provide:
   - The full prompt (or the key sentence) as "original"
   - A more natural, idiomatic way to express the same meaning as "corrected"
   - An explanation of why the new version sounds more natural
   - Category: "Expression"
   - Only suggest expression improvements when the difference is meaningful — skip if the original is already natural enough

Output ONLY the raw JSON array (no markdown fences, no extra text). Each entry:
{
  "prompt_num": 1,
  "original": "how can i using",
  "corrected": "How can I use",
  "category": "Grammar",
  "explanation": "After 'can' (modal verb), use the base form 'use', not the -ing form."
}

Expression example:
{
  "prompt_num": 3,
  "original": "I want to know this function do what thing",
  "corrected": "I'd like to understand what this function does",
  "category": "Expression",
  "explanation": "The whole sentence follows Chinese word order ('do what thing'). In English, use 'what [subject] does' — and 'I'd like to understand' is more natural than 'I want to know'."
}

Be thorough and educational. Group related errors from the same prompt into separate entries.

Here are the prompts to analyze (with conversation context):

[paste the formatted Q&A pairs here]
```

**Important:** The subagent may not be able to write files to disk. Handle both cases:
1. If the subagent returns the JSON in its response text, parse it directly from the response
2. If the subagent successfully writes to `/tmp/subagent_corrections_YYYYMMDD.json`, read it from there

Either way, merge the subagent corrections with any corrections from Step 4. Do not duplicate — if an extracted correction already covers the same phrase, skip it.

#### Step 5b — Summarization subagent

Launch **in parallel** with the correction subagent (same message, second Task tool call). Pass the full QA_JSON from Step 3 with this prompt:

```
You are summarizing assistant responses from Claude Code conversations.

Rules:
- Keep user prompts EXACTLY as-is — do not correct, rephrase, or modify them in any way
- Summarize each assistant response into 1-3 concise sentences that capture the key action or answer
- If an assistant response is already short (under 50 words), keep it as-is
- Preserve the project grouping structure

Output a JSON array with the same structure as the input, but with assistant texts replaced by summaries:
[
  {
    "project": "project-name",
    "messages": [
      {"role": "user", "text": "exact user prompt unchanged"},
      {"role": "assistant", "text": "Summarized response in 1-3 sentences."}
    ]
  }
]

Output ONLY the raw JSON array (no markdown fences, no extra text).

Here is the Q&A data to summarize:

[paste the full QA_JSON here]
```

**Important:** Same file-handling as Step 5a — parse from response text or from `/tmp/summarized_qa_YYYYMMDD.json`.

### Step 6 — Build the Apple Note content

Using the corrections from Steps 4 + 5a and the summarized Q&A from Step 5b, build the note as HTML. The main agent no longer needs to summarize responses — Step 5b already did that.

Use `<h2>` and `<h3>` headings — Apple Notes makes these **collapsible**, so users can expand/collapse sections.

**Corrections come first** (the learning part), **Conversations at the end** (the reference/archive part).

```
<div><h1>YYYYMMDD</h1></div>
<div><h2>English Corrections</h2></div>

For each project that has corrections:
  <div><h3>[project name]</h3></div>

  Group corrections by category (Grammar, Sentence Structure, Word Choice, Spelling, Capitalization, Expression).
  For each category:
    <div><b>[Category] ([count])</b></div>
    <table border="1" cellpadding="4" cellspacing="0">
      <tr><th>What you wrote</th><th>More natural</th><th>Why</th></tr>
      <tr><td>[original]</td><td>[corrected]</td><td>[explanation]</td></tr>
      ...
    </table>
    <div><br></div>

<div><h2>Conversations</h2></div>

For each project in the summarized Q&A from Step 5b:
  <div><h3>[project name]</h3></div>
  <div><br></div>

  For each Q&A pair:
    <div>❯ [exact user prompt — unchanged from original]</div>
    <div><br></div>
    <div>⏺ [summarized assistant response from Step 5b]</div>
    <div><br></div>
```

### Step 7 — Save to Apple Note

Check if a note for the date already exists:

```bash
bash "$HOME/.claude/skills/apple-note/.claude/skills/apple-note/scripts/search-notes.sh" iCloud Notes "$DATE"
```

- If it **exists** → use `update-note.sh` (full replacement)
- If it **does not exist** → use `create-note.sh`

```bash
# Create
bash "$HOME/.claude/skills/apple-note/.claude/skills/apple-note/scripts/create-note.sh" iCloud Notes "$DATE" "<html content>"

# Update
bash "$HOME/.claude/skills/apple-note/.claude/skills/apple-note/scripts/update-note.sh" iCloud Notes "$DATE" "<html content>"
```

**Important:** Always use the `iCloud Notes` folder. Do not try `Daily` or other folders — they may be Smart Folders that reject direct writes.

### Step 8 — Move to Daily_fin folder

After the note is created or updated, move it to the `Daily_fin` folder:

```bash
bash "$HOME/.claude/skills/apple-note/.claude/skills/apple-note/scripts/move-note.sh" iCloud Notes "$DATE" "Daily_fin"
```

### Step 9 — Confirm

Tell the user:
- The note title saved
- How many projects were included
- How many Q&A pairs were recorded in total
- How many English corrections were collected (extracted + newly generated)

## Rules

- **Never summarize user prompts** — keep them exactly as written, typos and all
- **Always use parallel subagents** — launch two Task subagents in a single message: one for English corrections (Step 5a), one for response summarization (Step 5b). This keeps the main context lean and lets both run concurrently.
- **Give the correction subagent conversation context** — include preceding assistant response excerpts so it can better understand what the user was trying to say
- **Group by project** — makes it easy to see which conversation belongs where
- **Ignore technical content** — don't correct code, file paths, CLI commands, or technical terms
- **Merge corrections** — combine extracted corrections with subagent-generated ones, avoiding duplicates
- **Group corrections by category** — Grammar, Sentence Structure, Word Choice, Spelling, Capitalization, Expression
- **Include explanations** — each correction must have a "Why" column explaining the grammar rule
- **Expression improvements** — suggest more natural/idiomatic ways to express the same meaning when the overall phrasing sounds non-native, even if individual words are grammatically acceptable
- **Corrections section is optional** — only include if there are corrections (extracted or generated)
- **Skip system messages, tool calls, and progress entries** — scripts handle this automatically
- **If no date is given, default to today**
