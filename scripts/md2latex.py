#!/usr/bin/env python3
"""
md2latex.py <input_md> <output_tex>

Converts the english-corrections.md file into a LaTeX document
using template.tex for layout.
"""

import difflib
import os
import re
import sys
from collections import defaultdict
from datetime import datetime


def escape_latex(text):
    """Escape special LaTeX characters."""
    # Order matters: backslash first
    text = text.replace('\\', '\\textbackslash{}')
    text = text.replace('&', '\\&')
    text = text.replace('%', '\\%')
    text = text.replace('$', '\\$')
    text = text.replace('#', '\\#')
    text = text.replace('_', '\\_')
    text = text.replace('{', '\\{')
    text = text.replace('}', '\\}')
    text = text.replace('~', '\\textasciitilde{}')
    text = text.replace('^', '\\textasciicircum{}')
    text = text.replace('→', '$\\rightarrow$')
    text = text.replace('—', '---')
    text = text.replace('\u2018', '`')
    text = text.replace('\u2019', "'")
    text = text.replace('\u201c', '``')
    text = text.replace('\u201d', "''")
    return text


def highlight_diff(wrote, natural):
    """Compare two strings word-by-word and return (wrote_highlighted, natural_highlighted)
    with LaTeX color commands: red for errors, green for corrections."""
    wrote_words = wrote.split()
    natural_words = natural.split()

    sm = difflib.SequenceMatcher(None, wrote_words, natural_words)

    wrote_parts = []
    natural_parts = []

    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'equal':
            wrote_parts.extend(escape_latex(w) for w in wrote_words[i1:i2])
            natural_parts.extend(escape_latex(w) for w in natural_words[j1:j2])
        elif op == 'replace':
            for w in wrote_words[i1:i2]:
                wrote_parts.append('\\textcolor{errcolor}{' + escape_latex(w) + '}')
            for w in natural_words[j1:j2]:
                natural_parts.append('\\textcolor{fixcolor}{' + escape_latex(w) + '}')
        elif op == 'delete':
            for w in wrote_words[i1:i2]:
                wrote_parts.append('\\textcolor{errcolor}{' + escape_latex(w) + '}')
        elif op == 'insert':
            for w in natural_words[j1:j2]:
                natural_parts.append('\\textcolor{fixcolor}{' + escape_latex(w) + '}')

    return ' '.join(wrote_parts), ' '.join(natural_parts)


def parse_md(filepath):
    """Parse the markdown into a structured dict."""
    with open(filepath, encoding='utf-8') as f:
        lines = f.readlines()

    data = {}  # date -> {project -> {category -> [rows]}}
    current_date = None
    current_project = None
    current_category = None
    total_corrections = 0

    for line in lines:
        line = line.rstrip('\n')

        m = re.match(r'^## (\d{4}-\d{2}-\d{2})$', line)
        if m:
            current_date = m.group(1)
            data[current_date] = {}
            current_project = None
            current_category = None
            continue

        m = re.match(r'^### (.+)$', line)
        if m and current_date:
            current_project = m.group(1)
            data[current_date][current_project] = {}
            current_category = None
            continue

        m = re.match(r'^\*\*(.+)\*\*$', line)
        if m and current_project:
            current_category = m.group(1)
            data[current_date][current_project][current_category] = []
            continue

        if line.startswith('|') and current_category:
            if '---' in line or 'What you wrote' in line:
                continue
            cells = [c.strip() for c in line.split('|')[1:-1]]
            if len(cells) >= 2 and cells[0]:
                row = {
                    'wrote': cells[0].replace('\\|', '|'),
                    'natural': cells[1].replace('\\|', '|') if len(cells) > 1 else '',
                    'why': cells[2].replace('\\|', '|') if len(cells) > 2 else '',
                }
                data[current_date][current_project][current_category].append(row)
                total_corrections += 1

    return data, total_corrections


def compute_stats(data):
    """Compute summary statistics."""
    cat_counts = defaultdict(int)
    date_counts = defaultdict(int)
    proj_counts = defaultdict(int)

    for date, projects in data.items():
        for proj, categories in projects.items():
            for cat, rows in categories.items():
                count = len(rows)
                cat_counts[cat] += count
                date_counts[date] += count
                proj_counts[proj] += count

    return cat_counts, date_counts, proj_counts


def format_date_range(dates):
    """Format a list of ISO dates into a human-readable range."""
    sorted_d = sorted(dates)
    first = datetime.strptime(sorted_d[0], '%Y-%m-%d')
    last = datetime.strptime(sorted_d[-1], '%Y-%m-%d')
    if first.year == last.year and first.month == last.month:
        return f"{first.strftime('%b')} {first.day} -- {last.day}, {first.year}"
    elif first.year == last.year:
        return f"{first.strftime('%b')} {first.day} -- {last.strftime('%b')} {last.day}, {first.year}"
    else:
        return f"{first.strftime('%b')} {first.day}, {first.year} -- {last.strftime('%b')} {last.day}, {last.year}"


# --- Content generators for each placeholder ---

def gen_category_rows(cat_counts, grand_total):
    """Generate LaTeX rows for the category summary table."""
    lines = []
    for cat in ['Grammar', 'Sentence Structure', 'Spelling', 'Word Choice', 'Capitalization', 'Expression']:
        c = cat_counts.get(cat, 0)
        pct = (c / grand_total * 100) if grand_total > 0 else 0
        lines.append(f"{escape_latex(cat)} & {c} & {pct:.1f}\\% \\\\")
    return '\n'.join(lines)


def gen_date_rows(date_counts):
    """Generate LaTeX rows for the date summary table (two-column layout)."""
    lines = []
    sorted_dates = sorted(date_counts.keys())
    mid = (len(sorted_dates) + 1) // 2
    for i in range(mid):
        left_date = sorted_dates[i]
        left_count = date_counts[left_date]
        if i + mid < len(sorted_dates):
            right_date = sorted_dates[i + mid]
            right_count = date_counts[right_date]
            lines.append(f"{escape_latex(left_date)} & {left_count} & {escape_latex(right_date)} & {right_count} \\\\")
        else:
            lines.append(f"{escape_latex(left_date)} & {left_count} & & \\\\")
    return '\n'.join(lines)


def gen_project_rows(proj_counts, grand_total):
    """Generate LaTeX rows for the project summary table (top 10)."""
    lines = []
    sorted_projs = sorted(proj_counts.items(), key=lambda x: -x[1])[:10]
    for proj, count in sorted_projs:
        pct = (count / grand_total * 100) if grand_total > 0 else 0
        lines.append(f"{escape_latex(proj)} & {count} & {pct:.1f}\\% \\\\")
    return '\n'.join(lines)


def gen_corrections_content(data):
    """Generate LaTeX content for all correction tables grouped by date."""
    lines = []
    for date in sorted(data.keys()):
        projects = data[date]
        total_for_date = sum(
            len(rows)
            for proj in projects.values()
            for rows in proj.values()
        )
        lines.append(f"\\section{{{escape_latex(date)} ({total_for_date} corrections)}}")
        lines.append("")

        for proj, categories in projects.items():
            lines.append(f"\\subsection{{{escape_latex(proj)}}}")
            lines.append("")

            for cat, rows in categories.items():
                if not rows:
                    continue
                lines.append(f"\\subsubsection{{{escape_latex(cat)} ({len(rows)})}}")
                lines.append("")
                lines.append(r"\begin{longtable}{|L{4cm}|L{4cm}|L{6.5cm}|}")
                lines.append(r"\hline")
                lines.append(r"\rowcolor{headerrow}")
                lines.append(r"\textbf{What you wrote} & \textbf{More natural} & \textbf{Why} \\")
                lines.append(r"\hline")
                lines.append(r"\endhead")

                for i, row in enumerate(rows):
                    wrote, natural = highlight_diff(row['wrote'], row['natural'])
                    why = escape_latex(row['why'])
                    if i % 2 == 1:
                        lines.append(r"\rowcolor{lightgray}")
                    lines.append(f"{wrote} & {natural} & {why} \\\\")
                    lines.append(r"\hline")

                lines.append(r"\end{longtable}")
                lines.append("")

    return '\n'.join(lines)


def generate_latex(data, total, template_path, output_path):
    """Read template.tex, fill placeholders, write output."""
    cat_counts, date_counts, proj_counts = compute_stats(data)
    grand_total = sum(cat_counts.values())
    date_range = format_date_range(list(data.keys())) if data else "No dates"

    with open(template_path, encoding='utf-8') as f:
        template = f.read()

    # Fill placeholders
    replacements = {
        '%%DATE_RANGE%%': escape_latex(date_range),
        '%%NUM_DATES%%': str(len(data)),
        '%%NUM_PROJECTS%%': str(len(proj_counts)),
        '%%TOTAL_CORRECTIONS%%': str(grand_total),
        '%%CATEGORY_TABLE_ROWS%%': gen_category_rows(cat_counts, grand_total),
        '%%DATE_TABLE_ROWS%%': gen_date_rows(date_counts),
        '%%PROJECT_TABLE_ROWS%%': gen_project_rows(proj_counts, grand_total),
        '%%CORRECTIONS_CONTENT%%': gen_corrections_content(data),
    }

    output = template
    for placeholder, value in replacements.items():
        output = output.replace(placeholder, value)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output)


def main():
    if len(sys.argv) < 3:
        print("Usage: md2latex.py <input_md> <output_tex>", file=sys.stderr)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    # template.tex lives next to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, 'template.tex')

    if not os.path.exists(template_path):
        print(f"Error: template.tex not found at {template_path}", file=sys.stderr)
        sys.exit(1)

    data, total = parse_md(input_path)
    print(f"Parsed {total} corrections from {len(data)} dates.", file=sys.stderr)

    generate_latex(data, total, template_path, output_path)
    print(f"LaTeX written to {output_path}", file=sys.stderr)


if __name__ == '__main__':
    main()
