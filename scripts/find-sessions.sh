#!/bin/bash
# find-sessions.sh [YYYY-MM-DD]
# Finds all Claude Code session files that contain entries from the given date.
# Defaults to today if no date is provided.
#
# Output format (one line per session file found):
#   PROJECT_NAME|FILE_PATH

DATE=${1:-$(date +%Y-%m-%d)}
PROJECTS_DIR="$HOME/.claude/projects"

extract_project_name() {
    local dir_name="$1"
    python3 -c "
import re, sys
d = sys.argv[1].lstrip('-')
parts = d.split('-')
markers = {'Project', 'Desktop', 'Documents', 'home', 'opt', 'workspace'}
for i, p in enumerate(parts):
    if p in markers and i + 1 < len(parts):
        print('-'.join(parts[i+1:]))
        sys.exit()
print(d)
" "$dir_name"
}

find "$PROJECTS_DIR" -name "*.jsonl" | while IFS= read -r jsonl_file; do
    if grep -ql "\"$DATE" "$jsonl_file" 2>/dev/null; then
        project_dir=$(basename "$(dirname "$jsonl_file")")
        project_name=$(extract_project_name "$project_dir")
        echo "${project_name}|${jsonl_file}"
    fi
done
