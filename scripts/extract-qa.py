#!/usr/bin/env python3
# extract-qa.py [--date YYYY-MM-DD] PROJECT|FILE_PATH [PROJECT|FILE_PATH ...]
#
# Reads session .jsonl files and extracts clean Q&A pairs.
# Strips system messages, tool calls, and progress entries.
#
# Output: JSON array
# [
#   {
#     "project": "english-daily-md",
#     "messages": [
#       {"role": "user", "text": "exact user prompt"},
#       {"role": "assistant", "text": "full assistant text for Claude to summarize"}
#     ]
#   }
# ]

import sys
import json
import argparse


def extract_project_name(dir_name):
    d = dir_name.lstrip('-')
    parts = d.split('-')
    markers = {'Project', 'Desktop', 'Documents', 'home', 'opt', 'workspace'}
    for i, p in enumerate(parts):
        if p in markers and i + 1 < len(parts):
            return '-'.join(parts[i + 1:])
    return d


def is_valid_user_text(text):
    """Filter out internal system content from user entries."""
    skip_prefixes = (
        '<',            # XML system tags
        'Caveat:',      # system caveats
        'Base directory for this skill:',  # skill loading content
        'Launching skill:',               # skill invocation
    )
    skip_contains = (
        '## Available Scripts',    # skill documentation
        '## Prerequisites',        # skill documentation
        '<command-name>',          # CLI commands
        '<local-command',          # local command output
    )
    if not text or not text.strip():
        return False
    t = text.strip()
    for prefix in skip_prefixes:
        if t.startswith(prefix):
            return False
    for pattern in skip_contains:
        if pattern in t:
            return False
    return True


def extract_from_file(project_name, file_path, target_date):
    messages = []
    current_assistant_parts = []

    def flush_assistant():
        if current_assistant_parts:
            text = '\n'.join(current_assistant_parts).strip()
            if text:
                messages.append({'role': 'assistant', 'text': text})
            current_assistant_parts.clear()

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

                entry_type = obj.get('type')

                if entry_type == 'user':
                    flush_assistant()
                    msg = obj.get('message', {})
                    content = msg.get('content', '')

                    if isinstance(content, str):
                        if is_valid_user_text(content):
                            messages.append({'role': 'user', 'text': content.strip()})

                    elif isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and item.get('type') == 'text':
                                text = item.get('text', '')
                                if is_valid_user_text(text):
                                    messages.append({'role': 'user', 'text': text.strip()})

                elif entry_type == 'assistant':
                    msg = obj.get('message', {})
                    for item in msg.get('content', []):
                        if isinstance(item, dict) and item.get('type') == 'text':
                            text = item.get('text', '').strip()
                            if text:
                                current_assistant_parts.append(text)

        flush_assistant()

    except Exception as e:
        print(f"[error reading {file_path}]: {e}", file=sys.stderr)

    return messages


def main():
    parser = argparse.ArgumentParser(description='Extract Q&A from Claude session files.')
    parser.add_argument('--date', default='', help='Filter by date (YYYY-MM-DD). Defaults to all entries.')
    parser.add_argument('--max-assistant', type=int, default=500,
                        help='Max characters per assistant response (default 500). Set 0 for unlimited.')
    parser.add_argument('sessions', nargs='+', help='Session entries in format PROJECT|FILE_PATH')
    args = parser.parse_args()

    results = []

    for session in args.sessions:
        if '|' not in session:
            print(f"[skip] Invalid format (expected PROJECT|FILE_PATH): {session}", file=sys.stderr)
            continue
        project_name, file_path = session.split('|', 1)
        messages = extract_from_file(project_name, file_path, args.date)
        if messages:
            # Truncate assistant texts to save tokens
            if args.max_assistant > 0:
                for msg in messages:
                    if msg['role'] == 'assistant' and len(msg['text']) > args.max_assistant:
                        msg['text'] = msg['text'][:args.max_assistant] + '...[truncated]'
            results.append({'project': project_name, 'messages': messages})

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
