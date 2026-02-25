#!/bin/bash
# extract-daily-corrections.sh
#
# Extracts "English Corrections" from Daily Apple Notes into a Markdown file.
#
# Usage:
#   ./scripts/extract-daily-corrections.sh [--unfin] [output_file]
#
# Options:
#   --unfin   Extract only unfinished notes (YYYYMMDD without _fin, from Notes folder)
#             Default: extract finished notes (YYYYMMDD_fin, from Daily_fin folder)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APPLE_NOTE_SCRIPTS="$HOME/.claude/skills/apple-note/.claude-plugin/skills/apple-note/scripts"

# Parse flags
UNFIN=false
OUTPUT_FILE=""
for arg in "$@"; do
    case "$arg" in
        --unfin) UNFIN=true ;;
        *) OUTPUT_FILE="$arg" ;;
    esac
done

if [ "$UNFIN" = true ]; then
    FOLDER="Notes"
    NAME_PATTERN='^[0-9]{8}$'
    DEFAULT_OUTPUT="$(dirname "$SCRIPT_DIR")/english-corrections-unfin.md"
    echo "Fetching unfinished notes from Notes folder..." >&2
else
    FOLDER="Daily_fin"
    NAME_PATTERN='^[0-9]{8}_fin$'
    DEFAULT_OUTPUT="$(dirname "$SCRIPT_DIR")/english-corrections.md"
    echo "Fetching finished notes from Daily_fin folder..." >&2
fi

OUTPUT_FILE="${OUTPUT_FILE:-$DEFAULT_OUTPUT}"

# 1. Get sorted list of note names
NOTE_NAMES=$(bash "$APPLE_NOTE_SCRIPTS/list-notes.sh" "iCloud" "$FOLDER" \
    | cut -d'|' -f1 \
    | sed 's/^ *//;s/ *$//' \
    | grep -E "$NAME_PATTERN" \
    | sort)

COUNT=$(echo "$NOTE_NAMES" | grep -c . || true)
if [ "$COUNT" -eq 0 ]; then
    echo "No notes found." >&2
    exit 0
fi
echo "Found $COUNT notes." >&2

# 2. Fetch each note
TMPDIR_NOTES=$(mktemp -d)
trap 'rm -rf "$TMPDIR_NOTES"' EXIT

for name in $NOTE_NAMES; do
    echo "  Fetching $name..." >&2
    # Strip _fin suffix for the output filename so the parser gets clean dates
    clean_name="${name%_fin}"
    bash "$APPLE_NOTE_SCRIPTS/get-note.sh" "iCloud" "$FOLDER" "$name" \
        > "$TMPDIR_NOTES/$clean_name.html" 2>/dev/null || true
done

# 3. Run the Python extractor
python3 "$SCRIPT_DIR/parse-daily-corrections.py" "$TMPDIR_NOTES" "$OUTPUT_FILE"

echo "Done! Output written to $OUTPUT_FILE" >&2
