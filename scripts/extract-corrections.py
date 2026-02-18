#!/usr/bin/env python3
# extract-corrections.py [--date YYYY-MM-DD] PROJECT|FILE_PATH [PROJECT|FILE_PATH ...]
#
# Scans assistant messages for English correction tables and extracts them.
# Correction tables look like:
#
#   | What you wrote | More natural |
#   |---|---|
#   | "original text" | "corrected text" |
#
# Output: JSON object grouped by project
# {
#   "english-daily-md": [
#     ["original text", "corrected text"],
#     ...
#   ],
#   "flutter-morphing-navigation": [...]
# }

import sys
import json
import re
import argparse


def extract_correction_rows(text):
    """Find all correction table rows in a block of text."""
    corrections = []
    lines = text.split('\n')
    in_table = False

    for line in lines:
        # Detect correction table header
        if re.search(r'\|\s*What you wrote\s*\|\s*More natural\s*\|', line, re.IGNORECASE):
            in_table = True
            continue

        if in_table:
            # Skip separator row like |---|---|
            if re.match(r'\s*\|[-|\s]+\|\s*$', line):
                continue

            # Match a data row: | "text" | "text" |
            if line.strip().startswith('|') and line.count('|') >= 3:
                parts = [p.strip().strip('"') for p in line.split('|') if p.strip()]
                if len(parts) >= 2:
                    original = parts[0].strip()
                    natural = parts[1].strip()
                    if original and natural:
                        corrections.append([original, natural])
            else:
                # End of table
                in_table = False

    return corrections


def extract_from_file(project_name, file_path, target_date):
    all_corrections = []

    try:
        with open(file_path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Filter by date if provided
                ts = obj.get('timestamp', '')
                if target_date and isinstance(ts, str) and not ts.startswith(target_date):
                    continue

                if obj.get('type') != 'assistant':
                    continue

                msg = obj.get('message', {})
                for item in msg.get('content', []):
                    if isinstance(item, dict) and item.get('type') == 'text':
                        text = item.get('text', '')
                        rows = extract_correction_rows(text)
                        all_corrections.extend(rows)

    except Exception as e:
        print(f"[error reading {file_path}]: {e}", file=sys.stderr)

    return all_corrections


def main():
    parser = argparse.ArgumentParser(description='Extract English corrections from Claude session files.')
    parser.add_argument('--date', default='', help='Filter by date (YYYY-MM-DD). Defaults to all entries.')
    parser.add_argument('sessions', nargs='+', help='Session entries in format PROJECT|FILE_PATH')
    args = parser.parse_args()

    results = {}

    for session in args.sessions:
        if '|' not in session:
            print(f"[skip] Invalid format (expected PROJECT|FILE_PATH): {session}", file=sys.stderr)
            continue
        project_name, file_path = session.split('|', 1)
        corrections = extract_from_file(project_name, file_path, args.date)
        if corrections:
            if project_name not in results:
                results[project_name] = []
            results[project_name].extend(corrections)

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
