"""Shared helpers for reading and editing speaker-skill Markdown files (profile, archive).

The files are plain Markdown: `## ` sections, some containing a pipe table. These helpers
find sections and tables and edit rows in place, leaving everything else untouched.
"""
import re
from pathlib import Path

VOCAB_HEADER = ["Word / phrase", "Context sentence", "Meaning", "Source", "Added",
                "Next review", "Interval (days)", "Strength"]
MISTAKES_HEADER = ["Pattern", "Example (wrong → right)", "Times seen", "Last seen"]
VOCAB_COLS = {
    "word": ("word",), "sentence": ("context",), "meaning": ("meaning",), "source": ("source",),
    "added": ("added",), "next": ("next",), "interval": ("interval",), "strength": ("strength",),
}
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def split_row(line):
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", body)]


def join_row(cells):
    return "| " + " | ".join(cells) + " |"


def clean(text):
    """Make text safe for a table cell (a literal pipe would break the table)."""
    return (text or "").replace("|", "/").replace("\n", " ").strip()


def is_separator(cells):
    return all(set(c) <= set("-: ") for c in cells)


class Table:
    def __init__(self, header_idx, sep_idx, header, rows, cols):
        self.header_idx, self.sep_idx, self.header, self.rows = header_idx, sep_idx, header, rows
        self.col = {}
        for name, prefixes in (cols or {}).items():
            for j, h in enumerate(header):
                if h.lower().startswith(prefixes):
                    self.col[name] = j
                    break

    def get(self, cells, name):
        j = self.col.get(name)
        return cells[j] if j is not None and j < len(cells) else ""

    def set(self, cells, name, value):
        j = self.col[name]
        while len(cells) <= j:
            cells.append("")
        cells[j] = value

    @property
    def insert_at(self):
        return (self.rows[-1][0] if self.rows else self.sep_idx) + 1


class Doc:
    def __init__(self, path, template=None):
        self.path = Path(path)
        if self.path.exists():
            self.lines = self.path.read_text(encoding="utf-8").splitlines()
            self.created = False
        elif template is not None:
            self.lines = template.splitlines()
            self.created = True
        else:
            raise FileNotFoundError(path)

    def save(self):
        self.path.write_text("\n".join(self.lines).rstrip("\n") + "\n", encoding="utf-8")

    # --- sections -------------------------------------------------------------
    def section(self, prefix):
        """(heading index, end index exclusive) of the first `## ` section starting with prefix."""
        prefix = prefix.lower()
        for i, line in enumerate(self.lines):
            if line.startswith("## ") and line[3:].strip().lower().startswith(prefix):
                end = i + 1
                while end < len(self.lines) and not self.lines[end].startswith("## "):
                    end += 1
                return i, end
        return None

    def ensure_section(self, heading, before=None, body=None):
        """Create `## heading` (optionally before another section) if it doesn't exist."""
        if self.section(heading):
            return self.section(heading)
        block = [f"## {heading}"] + (body or []) + [""]
        at = None
        if before:
            s = self.section(before)
            at = s[0] if s else None
        if at is None:
            if self.lines and self.lines[-1].strip():
                self.lines.append("")
            self.lines.extend(block)
        else:
            self.lines[at:at] = block
        return self.section(heading)

    # --- tables ---------------------------------------------------------------
    def table(self, prefix, cols=None, create_header=None):
        sec = self.section(prefix)
        if sec is None:
            return None
        start, end = sec
        header_idx = sep_idx = None
        header, rows = None, []
        for i in range(start + 1, end):
            line = self.lines[i]
            if not line.strip().startswith("|"):
                if header_idx is not None and rows and line.strip():
                    break  # text after the table ends it
                continue
            cells = split_row(line)
            if header_idx is None:
                header_idx, header = i, cells
            elif sep_idx is None and is_separator(cells):
                sep_idx = i
            else:
                rows.append((i, cells))
        if header_idx is None:
            if not create_header:
                return None
            at = start + 1
            new = [join_row(create_header), join_row(["---"] * len(create_header))]
            if at >= len(self.lines) or self.lines[at].startswith("## "):
                new.append("")
            self.lines[at:at] = new
            return self.table(prefix, cols)
        if sep_idx is None:
            self.lines.insert(header_idx + 1, join_row(["---"] * len(header)))
            return self.table(prefix, cols)
        return Table(header_idx, sep_idx, header, rows, cols)

    def append_row(self, prefix, cells, cols=None, create_header=None):
        t = self.table(prefix, cols, create_header)
        self.lines.insert(t.insert_at, join_row(cells))

    def delete_lines(self, idxs):
        for i in sorted(set(idxs), reverse=True):
            del self.lines[i]

    def bullets(self, prefix):
        sec = self.section(prefix)
        if not sec:
            return []
        return [(i, self.lines[i]) for i in range(sec[0] + 1, sec[1]) if self.lines[i].lstrip().startswith(("- ", "* "))]


def language_name(profile_doc):
    for line in profile_doc.lines:
        if line.startswith("# "):
            return re.sub(r"(?i)\s*learning profile\s*$", "", line[2:]).strip() or "Language"
    return "Language"


def archive_path(profile_path):
    p = Path(profile_path)
    return p.with_name(p.stem.replace("-profile", "") + "-archive.md")


def archive_template(language):
    return f"""# {language} archive

Older material moved out of the profile to keep it short. Known words here are still reviewed when they come due.

## Vocabulary (known)
{join_row(VOCAB_HEADER)}
{join_row(["---"] * len(VOCAB_HEADER))}

## Resolved mistakes
{join_row(MISTAKES_HEADER)}
{join_row(["---"] * len(MISTAKES_HEADER))}

## Milestones earned
| ID | Can-do | Evidence | Earned |
|---|---|---|---|

## Session log (older)
"""
