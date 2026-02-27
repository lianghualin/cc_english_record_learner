#!/usr/bin/env python3
"""
parse-daily-corrections.py <notes_dir> <output_file>

Reads Apple Notes HTML files from <notes_dir>, extracts the
"English Corrections" section tables, and writes a consolidated
Markdown file to <output_file>.

Also extracts user prompts from the Conversations section and
analyzes repeated patterns across all dates.
"""

import os
import re
import sys
from collections import Counter
from html.parser import HTMLParser


class TableExtractor(HTMLParser):
    """Extract text content from HTML table rows."""

    def __init__(self):
        super().__init__()
        self.tables = []       # list of tables, each table is list of rows
        self.current_table = None
        self.current_row = None
        self.current_cell = None
        self.in_td = False

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.current_table = []
        elif tag == 'tr' and self.current_table is not None:
            self.current_row = []
        elif tag == 'td' and self.current_row is not None:
            self.current_cell = []
            self.in_td = True

    def handle_endtag(self, tag):
        if tag == 'td' and self.in_td:
            text = ''.join(self.current_cell).strip()
            self.current_row.append(text)
            self.current_cell = None
            self.in_td = False
        elif tag == 'tr' and self.current_row is not None:
            if self.current_table is not None:
                self.current_table.append(self.current_row)
            self.current_row = None
        elif tag == 'table' and self.current_table is not None:
            if self.current_table:
                self.tables.append(self.current_table)
            self.current_table = None

    def handle_data(self, data):
        if self.in_td and self.current_cell is not None:
            self.current_cell.append(data)


def extract_corrections_from_html(html_content):
    """
    Parse the HTML of a Daily note and extract the English Corrections section.

    Returns a list of dicts:
      [{"category": "Grammar", "project": "flutter-tmp",
        "rows": [{"wrote": "...", "natural": "...", "why": "..."}]}]
    """
    # Find the English Corrections section
    # It starts with "English Corrections" heading and ends at "Conversations" heading
    corrections_match = re.search(
        r'English Corrections</span></b></div>(.*?)(?:<b><span style="font-size: 12px">Conversations</span></b>|$)',
        html_content,
        re.DOTALL
    )
    if not corrections_match:
        return []

    section_html = corrections_match.group(1)

    # Split by project name and category headers
    # Project names are bold 9px spans
    # Categories are bold 9px spans with count like "Grammar (2)"
    results = []
    current_project = "unknown"

    # Extract project names and categories with their positions
    # Project: <b><span style="font-size: 9px">project-name</span></b> (not followed by count)
    # Category: <b><span style="font-size: 9px">Grammar (2)</span></b>
    project_pattern = re.compile(
        r'<b><span style="font-size: 9px">([^<]+?)</span></b>'
    )
    category_pattern = re.compile(
        r'^(.+?)\s*\((\d+)\)$'
    )

    # Split the section by tables
    # Find all bold spans and tables in order
    parts = re.split(r'(<object>.*?</object>)', section_html, flags=re.DOTALL)

    pending_category = None
    for part in parts:
        if '<object>' in part and '<table' in part:
            # This is a table — extract it
            extractor = TableExtractor()
            extractor.feed(part)
            for table in extractor.tables:
                if not table:
                    continue
                # Check if first row is header
                header = table[0]
                has_header = any('What you wrote' in cell for cell in header)
                data_rows = table[1:] if has_header else table

                for row in data_rows:
                    if len(row) >= 2:
                        entry = {
                            "wrote": row[0],
                            "natural": row[1],
                            "why": row[2] if len(row) >= 3 else "",
                        }
                        if entry["wrote"] and entry["natural"]:
                            results.append({
                                "project": current_project,
                                "category": pending_category or "Other",
                                **entry,
                            })
        else:
            # Look for project/category labels in this text chunk
            matches = project_pattern.findall(part)
            for m in matches:
                cat_match = category_pattern.match(m.strip())
                if cat_match:
                    pending_category = cat_match.group(1)
                else:
                    # It's a project name
                    current_project = m.strip()

    return results


def extract_prompts_from_html(html_content):
    """
    Extract user prompts from the Conversations section of a Daily note.
    Prompts are lines starting with ❯ inside <div> tags.

    Returns a list of prompt strings.
    """
    # Find the Conversations section (after "Conversations" heading)
    conv_match = re.search(
        r'<b><span style="font-size: 12px">Conversations</span></b>(.*)',
        html_content,
        re.DOTALL
    )
    if not conv_match:
        return []

    section_html = conv_match.group(1)

    # Extract text from divs that start with ❯
    prompts = []
    # Match content inside <div> tags that starts with ❯
    for m in re.finditer(r'<div[^>]*>\s*❯\s*(.*?)</div>', section_html, re.DOTALL):
        text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        if text:
            prompts.append(text)

    return prompts


# Common English stop words to exclude from frequency analysis
STOP_WORDS = {
    'i', 'me', 'my', 'we', 'our', 'you', 'your', 'it', 'its', 'he', 'she',
    'they', 'them', 'this', 'that', 'these', 'those', 'the', 'a', 'an',
    'is', 'are', 'was', 'were', 'be', 'been', 'being', 'am',
    'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing',
    'will', 'would', 'could', 'should', 'may', 'might', 'shall', 'can',
    'not', "don't", "doesn't", "didn't", "won't", "wouldn't", "can't",
    'and', 'but', 'or', 'so', 'if', 'then', 'than', 'when', 'while',
    'of', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'from', 'as',
    'into', 'about', 'up', 'out', 'off', 'over', 'after', 'before',
    'what', 'which', 'who', 'how', 'where', 'there', 'here',
    'all', 'each', 'some', 'any', 'no', 'just', 'only', 'very',
}


def analyze_repetitions(all_corrections, all_prompts):
    """
    Analyze corrections and prompts for repeated patterns.

    Returns a dict with:
      - repeated_mistakes: list of (wrote_phrase, count, dates, naturals)
      - frequent_phrases: list of (phrase, count) bigrams/trigrams from prompts
    """
    # 1. Find repeated "wrote" phrases across dates
    # Normalize and group by similar phrases
    wrote_index = {}  # normalized_wrote -> [(date, wrote_original, natural)]
    for date_str, corrections in all_corrections.items():
        for c in corrections:
            key = c['wrote'].strip().lower()
            if key not in wrote_index:
                wrote_index[key] = []
            wrote_index[key].append((date_str, c['wrote'], c['natural']))

    repeated_mistakes = []
    for key, entries in wrote_index.items():
        if len(entries) >= 2:
            dates = sorted(set(e[0] for e in entries))
            naturals = list(set(e[2] for e in entries))
            repeated_mistakes.append((entries[0][1], len(entries), dates, naturals))
    repeated_mistakes.sort(key=lambda x: -x[1])

    # 2. Find frequently repeated words/phrases in user prompts
    # Tokenize and count bigrams/trigrams
    all_tokens = []
    for prompts in all_prompts.values():
        for prompt in prompts:
            # Simple tokenization: lowercase, split on non-alpha
            words = re.findall(r"[a-z']+", prompt.lower())
            words = [w for w in words if w not in STOP_WORDS and len(w) > 1]
            all_tokens.extend(words)

    # Count individual words (only if frequent enough to matter)
    word_counts = Counter(all_tokens)

    # Count bigrams from prompts
    bigram_counts = Counter()
    for prompts in all_prompts.values():
        for prompt in prompts:
            words = re.findall(r"[a-z']+", prompt.lower())
            words = [w for w in words if w not in STOP_WORDS and len(w) > 1]
            for i in range(len(words) - 1):
                bigram_counts[(words[i], words[i + 1])] += 1

    # Filter to repeated phrases (3+ occurrences)
    frequent_words = [(w, c) for w, c in word_counts.most_common(30) if c >= 3]
    frequent_bigrams = [
        (' '.join(bg), c) for bg, c in bigram_counts.most_common(20) if c >= 3
    ]

    return {
        'repeated_mistakes': repeated_mistakes,
        'frequent_words': frequent_words,
        'frequent_bigrams': frequent_bigrams,
    }


def format_date(filename):
    """Convert '20260220' to '2026-02-20'."""
    name = filename.replace('.html', '')
    if len(name) == 8 and name.isdigit():
        return f"{name[:4]}-{name[4:6]}-{name[6:8]}"
    return name


def main():
    if len(sys.argv) < 3:
        print("Usage: parse-daily-corrections.py <notes_dir> <output_file>", file=sys.stderr)
        sys.exit(1)

    notes_dir = sys.argv[1]
    output_file = sys.argv[2]

    # Collect all corrections and prompts grouped by date
    all_data = {}      # date -> list of correction dicts
    all_prompts = {}   # date -> list of prompt strings

    for filename in sorted(os.listdir(notes_dir)):
        if not filename.endswith('.html'):
            continue
        filepath = os.path.join(notes_dir, filename)
        with open(filepath, encoding='utf-8') as f:
            html = f.read()

        date_str = format_date(filename)

        corrections = extract_corrections_from_html(html)
        if corrections:
            all_data[date_str] = corrections

        prompts = extract_prompts_from_html(html)
        if prompts:
            all_prompts[date_str] = prompts

    # Analyze repetitions
    repetitions = analyze_repetitions(all_data, all_prompts)

    # Write Markdown output
    total = sum(len(v) for v in all_data.values())
    total_prompts = sum(len(v) for v in all_prompts.values())
    print(f"Extracted {total} corrections and {total_prompts} prompts from {len(all_data)} notes.", file=sys.stderr)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# English Corrections\n\n")
        f.write(f"Extracted from {len(all_data)} Daily notes. Total corrections: {total}\n\n")

        for date_str in sorted(all_data.keys()):
            corrections = all_data[date_str]
            f.write(f"## {date_str}\n\n")

            # Group by project, then by category
            projects = {}
            for c in corrections:
                proj = c['project']
                if proj not in projects:
                    projects[proj] = {}
                cat = c['category']
                if cat not in projects[proj]:
                    projects[proj][cat] = []
                projects[proj][cat].append(c)

            for proj, categories in projects.items():
                f.write(f"### {proj}\n\n")
                for cat, items in categories.items():
                    f.write(f"**{cat}**\n\n")
                    f.write("| What you wrote | More natural | Why |\n")
                    f.write("|---|---|---|\n")
                    for item in items:
                        wrote = item['wrote'].replace('|', '\\|')
                        natural = item['natural'].replace('|', '\\|')
                        why = item['why'].replace('|', '\\|')
                        f.write(f"| {wrote} | {natural} | {why} |\n")
                    f.write("\n")

        # Repeated Patterns section
        has_patterns = (
            repetitions['repeated_mistakes']
            or repetitions['frequent_words']
            or repetitions['frequent_bigrams']
        )
        if has_patterns:
            f.write("---\n\n")
            f.write("## Repeated Patterns\n\n")
            f.write("Patterns detected across all dates — repeated mistakes and frequently used expressions.\n\n")

            if repetitions['repeated_mistakes']:
                f.write("### Repeated Mistakes\n\n")
                f.write("These exact phrases appeared in corrections on multiple dates:\n\n")
                f.write("| What you wrote | Times | Dates | Suggested |\n")
                f.write("|---|---|---|---|\n")
                for wrote, count, dates, naturals in repetitions['repeated_mistakes']:
                    dates_str = ', '.join(dates)
                    naturals_str = ' / '.join(naturals).replace('|', '\\|')
                    f.write(f"| {wrote.replace('|', chr(92) + '|')} | {count} | {dates_str} | {naturals_str} |\n")
                f.write("\n")

            if repetitions['frequent_words']:
                f.write("### Frequently Used Words\n\n")
                f.write("Words that appear most often in your prompts (excluding common words):\n\n")
                f.write("| Word | Count |\n")
                f.write("|---|---|\n")
                for word, count in repetitions['frequent_words']:
                    f.write(f"| {word} | {count} |\n")
                f.write("\n")

            if repetitions['frequent_bigrams']:
                f.write("### Frequently Used Phrases\n\n")
                f.write("Two-word phrases that appear most often in your prompts:\n\n")
                f.write("| Phrase | Count |\n")
                f.write("|---|---|\n")
                for phrase, count in repetitions['frequent_bigrams']:
                    f.write(f"| {phrase} | {count} |\n")
                f.write("\n")

    print(f"Written to {output_file}", file=sys.stderr)


if __name__ == '__main__':
    main()
