#!/usr/bin/env python3
"""Build a self-contained HTML progress dashboard from a speaker-skill learner profile.

Usage:
  python3 build_dashboard.py <profile.md> [--out dashboard.html] [--today YYYY-MM-DD]
                             [--next "step one" --next "step two" ...]

Uses only the Python standard library. The output is a single HTML file (no external
requests) that works in light and dark mode and can be opened in any browser.
"""
import argparse
import datetime as dt
import json
import re
from pathlib import Path

DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
STRENGTHS = ["new", "learning", "familiar", "known"]


def parse_date(s):
    m = DATE_RE.search(s or "")
    if not m:
        return None
    try:
        return dt.date.fromisoformat(m.group(0))
    except ValueError:
        return None


def split_sections(text):
    """Return {heading_lower: [lines]} for level-2 headings, plus the H1 title."""
    sections, current, title = {}, None, ""
    for line in text.splitlines():
        if line.startswith("# ") and not title:
            title = line[2:].strip()
        elif line.startswith("## "):
            current = line[3:].strip().lower()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return title, sections


def find_section(sections, *names):
    for key, lines in sections.items():
        if any(key.startswith(n) for n in names):
            return lines
    return []


def parse_table(lines):
    rows = [l.strip() for l in lines if l.strip().startswith("|")]
    if len(rows) < 2:
        return []
    split = lambda r: [c.strip() for c in r.strip().strip("|").split("|")]
    header = [h.lower() for h in split(rows[0])]
    out = []
    for r in rows[1:]:
        cells = split(r)
        if all(set(c) <= set("-: ") for c in cells):
            continue  # separator row
        if not any(cells):
            continue
        out.append({header[i]: cells[i] if i < len(cells) else "" for i in range(len(header))})
    return out


def col(row, *names):
    for key, val in row.items():
        if any(key.startswith(n) for n in names):
            return val
    return ""


def parse_bullets(lines):
    return [l.strip()[2:].strip() for l in lines if l.strip().startswith(("- ", "* "))]


def split_dash(item):
    parts = re.split(r"\s+[—–-]\s+", item, maxsplit=1)
    return (parts[0].strip(), parts[1].strip()) if len(parts) == 2 else (item.strip(), "")


def parse_story(text):
    """Summarize a <language>-story.md file for the dashboard (None if empty)."""
    if not text:
        return None
    title, sec = split_sections(text)
    meta = {}
    for line in text.splitlines():
        if line.startswith("## "):
            break
        if line.strip().startswith("- ") and ":" in line:
            k, v = line.strip()[2:].split(":", 1)
            meta[k.strip().lower()] = v.strip()
    season, question = meta.get("season", ""), ""
    m = re.match(r"(\d+)\s*[—–-]\s*(?:central question:\s*)?(.*)", season, re.I)
    if m:
        season, question = m.group(1), m.group(2).strip()
    clues = [c for c in find_section(sec, "clues") if re.match(r"\s*(\d+\.|-)\s+\S", c)]
    episodes = [e[2:].strip() for e in find_section(sec, "episode") if e.strip().startswith("- ")]
    latest = ""
    if episodes:
        latest = re.split(r"\s+—\s+new:", episodes[-1])[0]
    return {
        "title": title, "genre": meta.get("genre", ""), "setting": meta.get("setting", ""),
        "season": season, "question": question,
        "episodes": len(episodes) or meta.get("episodes so far", ""),
        "clues": len(clues), "latest": latest,
    }


def build_data(profile_text, today, next_steps, story_text=None):
    title, sec = split_sections(profile_text)

    about = {}
    for b in parse_bullets(find_section(sec, "about")):
        if ":" in b:
            k, v = b.split(":", 1)
            about[k.strip().lower()] = v.strip()

    vocab = []
    for r in parse_table(find_section(sec, "vocab")):
        word = col(r, "word")
        if not word or word.startswith("<"):
            continue
        strength = col(r, "strength").lower().strip()
        vocab.append({
            "word": word,
            "sentence": col(r, "context"),
            "meaning": col(r, "meaning"),
            "source": col(r, "source"),
            "added": str(parse_date(col(r, "added")) or ""),
            "next": str(parse_date(col(r, "next")) or ""),
            "strength": strength if strength in STRENGTHS else "new",
        })

    mistakes = []
    for r in parse_table(find_section(sec, "recurring")):
        pattern = col(r, "pattern")
        if not pattern or pattern.startswith("<"):
            continue
        try:
            times = int(re.sub(r"\D", "", col(r, "times")) or 0)
        except ValueError:
            times = 0
        mistakes.append({"pattern": pattern, "example": col(r, "example"),
                         "times": times, "last": col(r, "last")})
    mistakes.sort(key=lambda m: -m["times"])

    grammar = []
    for b in parse_bullets(find_section(sec, "grammar")):
        topic, status = split_dash(b)
        if topic.startswith("<"):
            continue
        grammar.append({"topic": topic, "status": status.lower()})

    sessions = []
    for b in parse_bullets(find_section(sec, "session")):
        d = parse_date(b)
        if d:
            sessions.append({"date": str(d), "text": DATE_RE.sub("", b, count=1).strip(" —–-:")})
    sessions.sort(key=lambda s: s["date"], reverse=True)

    # Streak: consecutive days with a session, ending today or yesterday.
    days = {dt.date.fromisoformat(s["date"]) for s in sessions}
    streak, cursor = 0, today if today in days else today - dt.timedelta(days=1)
    while cursor in days:
        streak += 1
        cursor -= dt.timedelta(days=1)

    # Words added per week, last 12 weeks (weeks start Monday).
    week0 = today - dt.timedelta(days=today.weekday())
    weeks = [week0 - dt.timedelta(weeks=i) for i in range(11, -1, -1)]
    added_by_week = {str(w): 0 for w in weeks}
    for v in vocab:
        if v["added"]:
            d = dt.date.fromisoformat(v["added"])
            w = str(d - dt.timedelta(days=d.weekday()))
            if w in added_by_week:
                added_by_week[w] += 1

    # Reviews due over the next 7 days (anything overdue counts toward today).
    due = []
    for i in range(7):
        day = today + dt.timedelta(days=i)
        n = sum(1 for v in vocab if v["next"] and (
            dt.date.fromisoformat(v["next"]) == day or (i == 0 and dt.date.fromisoformat(v["next"]) < today)))
        due.append({"date": str(day), "count": n})

    month_start = today.replace(day=1)
    return {
        "title": title or "Language learning profile",
        "today": str(today),
        "about": about,
        "counts": {s: sum(1 for v in vocab if v["strength"] == s) for s in STRENGTHS},
        "total": len(vocab),
        "dueToday": due[0]["count"],
        "streak": streak,
        "sessionsThisMonth": sum(1 for s in sessions if dt.date.fromisoformat(s["date"]) >= month_start),
        "addedByWeek": [{"week": k, "count": v} for k, v in added_by_week.items()],
        "dueNext7": due,
        "mistakes": mistakes[:6],
        "grammar": grammar,
        "recentWords": sorted([v for v in vocab if v["added"]], key=lambda v: v["added"], reverse=True)[:5],
        "recentSessions": sessions[:5],
        "nextSteps": next_steps,
        "story": parse_story(story_text),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("profile")
    ap.add_argument("--out")
    ap.add_argument("--today")
    ap.add_argument("--story", help="story file (default: <language>-story.md next to the profile, if present)")
    ap.add_argument("--next", action="append", default=[], help="a suggested next step (repeatable)")
    a = ap.parse_args()

    profile = Path(a.profile)
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    story_path = Path(a.story) if a.story else profile.with_name(profile.stem.replace("-profile", "") + "-story.md")
    story_text = story_path.read_text(encoding="utf-8") if story_path.exists() else None
    data = build_data(profile.read_text(encoding="utf-8"), today, a.next, story_text)

    template = (Path(__file__).resolve().parent.parent / "assets" / "dashboard_template.html").read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = template.replace("/*__DATA__*/null", payload)

    out = Path(a.out) if a.out else profile.with_name(profile.stem.replace("-profile", "") + "-dashboard.html")
    out.write_text(html, encoding="utf-8")
    print(f"Wrote {out}  ({data['total']} words, {data['dueToday']} due today, streak {data['streak']})")


if __name__ == "__main__":
    main()
