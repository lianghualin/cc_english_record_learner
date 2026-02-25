#!/usr/bin/env python3
"""
parse-daily-corrections.py <notes_dir> <output_file>

Reads Apple Notes HTML files from <notes_dir>, extracts the
"English Corrections" section tables, and writes a consolidated
Markdown file to <output_file>.
"""

import os
import re
import sys
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

    # Collect all corrections grouped by date
    all_data = {}  # date -> list of correction dicts

    for filename in sorted(os.listdir(notes_dir)):
        if not filename.endswith('.html'):
            continue
        filepath = os.path.join(notes_dir, filename)
        with open(filepath, encoding='utf-8') as f:
            html = f.read()

        corrections = extract_corrections_from_html(html)
        if corrections:
            date_str = format_date(filename)
            all_data[date_str] = corrections

    # Write Markdown output
    total = sum(len(v) for v in all_data.values())
    print(f"Extracted {total} corrections from {len(all_data)} notes.", file=sys.stderr)

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

    print(f"Written to {output_file}", file=sys.stderr)


if __name__ == '__main__':
    main()
