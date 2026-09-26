#!/usr/bin/env python3
"""Print a text progress dashboard (Markdown) from a speaker-skill learner profile.

Usage:
  python3 dashboard.py <profile.md> [--today YYYY-MM-DD] [--story story.md]
                       [--next "step one" --next "step two" ...] [--json]

Uses only the Python standard library. Paste the output straight into the chat.
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
    split = lambda r: [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", r.strip().strip("|"))]
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


def parse_milestones(sec):
    lines = find_section(sec, "milestones")
    if not lines:
        return None
    completed = ""
    for l in lines:
        if l.startswith("- Levels completed:"):
            completed = l.split(":", 1)[1].strip()
    rows = []
    for r in parse_table(lines):
        mid = col(r, "id")
        if not mid:
            continue
        ev = [e for e in col(r, "evidence").split(";") if e.strip()]
        rows.append({"id": mid, "level": mid.split("-")[0].replace("PreA1", "Pre-A1"),
                     "cando": col(r, "can"), "status": col(r, "status").lower(),
                     "evidence": len(ev), "days": len({e.strip()[:10] for e in ev}),
                     "earned": col(r, "earned")})
    return {"completed": completed, "rows": rows}


def build_data(profile_text, today, next_steps, story_text=None, archive_text=None):
    title, sec = split_sections(profile_text)
    arch_sec = split_sections(archive_text)[1] if archive_text else {}

    about = {}
    for b in parse_bullets(find_section(sec, "about")):
        if ":" in b:
            k, v = b.split(":", 1)
            about[k.strip().lower()] = v.strip()

    vocab = []
    for r in parse_table(find_section(sec, "vocab")) + parse_table(find_section(arch_sec, "vocab")):
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
        "milestones": parse_milestones(sec),
    }


BAR = "█"
SPARK = "▁▂▃▄▅▆▇█"


def bar(n, top, width=24):
    if n <= 0 or top <= 0:
        return ""
    return BAR * max(1, round(n / top * width))


def spark(values):
    top = max(values) if values else 0
    if top == 0:
        return SPARK[0] * len(values)
    return "".join(SPARK[min(7, round(v / top * 7))] for v in values)


def plural(n, word):
    return f"{n} {word}" + ("" if n == 1 else "s")


def render_text(d):
    about = d["about"]
    level_raw = about.get("level", "")
    level = level_raw.split("(")[0].strip() or "—"
    detail = re.search(r"\((.*)\)", level_raw)
    skills = []
    if detail:
        for part in detail.group(1).split(","):
            if ":" in part:
                k, v = part.split(":", 1)
                skills.append(f"{k.strip()} {v.strip()}")
    test = about.get("last placement test", "")
    provisional = "provisional" in level_raw.lower() or "in progress" in test.lower()
    lang = about.get("target language") or re.sub(r"(?i)learning profile", "", d["title"]).strip()

    out = []
    head = f"**{lang} · {level}**"
    if provisional:
        head += " (provisional, placement test not finished)"
    if skills:
        head += " · " + " · ".join(skills)
    out.append(head)
    out.append("")

    ms = d.get("milestones")
    if ms and ms["rows"]:
        levels = []
        for r in ms["rows"]:
            if r["level"] not in levels:
                levels.append(r["level"])
        cur = levels[0]
        cur_rows = [r for r in ms["rows"] if r["level"] == cur]
        earned = [r for r in cur_rows if r["status"] == "earned"]
        line = f"**Can do · {cur}**: {len(earned)} of {len(cur_rows)} earned"
        if ms["completed"]:
            done = re.sub(r"\s*\([^)]*\)", "", ms["completed"]).replace(";", ",")
            line += f" · completed: {done}"
        out.append(line)
        order = {"earned": 0, "focus": 1}
        for r in sorted(cur_rows, key=lambda r: (order.get(r["status"], 2), r["earned"] or "")):
            if r["status"] == "earned":
                when = dt.date.fromisoformat(r["earned"]).strftime("%b %-d") if DATE_RE.match(r["earned"] or "") else ""
                out.append(f"- 🏅 {r['cando']}" + (f" *({when})*" if when else ""))
            elif r["status"] == "focus":
                out.append(f"- 🎯 **{r['cando']}** · {r['evidence']}/3" + (" (needs another day)" if r["evidence"] >= 3 else ""))
            else:
                out.append(f"- ○ {r['cando']}" + (f" · {r['evidence']}/3" if r["evidence"] else ""))
        ahead = [r for r in ms["rows"] if r["level"] != cur and r["evidence"]]
        for r in ahead:
            out.append(f"- ⤴ {r['level']} · {r['cando']} · {r['evidence']}/3 already")
        out.append("")

    # --- the aligned block ---
    b = []
    b.append(f"{plural(d['total'], 'word')} saved · {d['dueToday']} due today · "
             f"{d['streak']}-day streak · {plural(d['sessionsThisMonth'], 'session')} this month")
    b.append("")
    if d["total"]:
        b.append("VOCABULARY BY STRENGTH")
        top = max(d["counts"].values())
        for s in STRENGTHS:
            n = d["counts"][s]
            b.append(f"  {s:<9}{n:>4}  {bar(n, top)}")
        b.append("")
    weeks = [w["count"] for w in d["addedByWeek"]]
    if any(weeks):
        b.append(f"WORDS ADDED, LAST 12 WEEKS   {spark(weeks)}   ({sum(weeks)} total, {weeks[-1]} this week)")
        b.append("")
    due = d["dueNext7"]
    if any(x["count"] for x in due):
        b.append("REVIEWS COMING UP")
        top = max(x["count"] for x in due)
        for i, x in enumerate(due):
            day = "today" if i == 0 else dt.date.fromisoformat(x["date"]).strftime("%a")
            b.append(f"  {day:<6}{x['count']:>4}  {bar(x['count'], top)}")
    else:
        b.append("REVIEWS COMING UP   nothing due in the next 7 days")
    out.append("```")
    out.extend(line.rstrip() for line in b)
    out.append("```")

    st = d.get("story")
    if st:
        out.append("")
        meta = " · ".join(x for x in [st.get("genre"), st.get("setting")] if x)
        out.append(f"**📖 {st['title']}**" + (f"  ({meta})" if meta else ""))
        if st.get("question"):
            out.append(f"Season {st['season']}: {st['question']}")
        out.append(f"{plural(int(st['episodes']) if str(st['episodes']).isdigit() else 0, 'episode')} · "
                   f"{plural(st['clues'], 'clue')} found")
        if st.get("latest"):
            out.append(f"Latest: {st['latest']}")

    if d["recentWords"]:
        out.append("")
        out.append("**Recently learned**")
        for w in d["recentWords"]:
            line = f"- **{w['word']}**: {w['meaning']}" if w["meaning"] else f"- **{w['word']}**"
            out.append(line)
            if w["sentence"]:
                out.append(f"  *{w['sentence']}*")

    if d["mistakes"]:
        out.append("")
        out.append("**Recurring mistakes**")
        for m in d["mistakes"][:5]:
            ex = f": {m['example']}" if m["example"] else ""
            out.append(f"- {m['times']}× {m['pattern']}{ex}")

    if d["grammar"]:
        out.append("")
        groups = {}
        for g in d["grammar"]:
            st_ = g["status"].lower()
            # Classify by keyword, so statuses like "reading ok, producing shaky" land in the right group.
            key = next((k for k in ("shaky", "comfortable", "new") if k in st_), "other")
            groups.setdefault(key, []).append(g["topic"])
        labels = [("comfortable", "✓ Comfortable"), ("shaky", "~ Shaky"), ("new", "· New")]
        out.append("**Grammar**")
        seen = set()
        for key, label in labels:
            if key in groups:
                out.append(f"- {label}: " + "; ".join(groups[key]))
                seen.add(key)
        if "other" in groups:
            out.append("- Other: " + "; ".join(groups["other"]))

    if d["nextSteps"]:
        out.append("")
        out.append("**Next steps**")
        for i, s in enumerate(d["nextSteps"], 1):
            out.append(f"{i}. {s}")

    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Print a text progress dashboard (Markdown) from a learner profile.")
    ap.add_argument("profile")
    ap.add_argument("--today")
    ap.add_argument("--story", help="story file (default: <language>-story.md next to the profile, if present)")
    ap.add_argument("--next", action="append", default=[], help="a suggested next step (repeatable)")
    ap.add_argument("--json", action="store_true", help="print the computed numbers as JSON instead")
    a = ap.parse_args()

    profile = Path(a.profile)
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    story_path = Path(a.story) if a.story else profile.with_name(profile.stem.replace("-profile", "") + "-story.md")
    story_text = story_path.read_text(encoding="utf-8") if story_path.exists() else None
    arch_path = profile.with_name(profile.stem.replace("-profile", "") + "-archive.md")
    archive_text = arch_path.read_text(encoding="utf-8") if arch_path.exists() else None
    data = build_data(profile.read_text(encoding="utf-8"), today, a.next, story_text, archive_text)
    print(json.dumps(data, ensure_ascii=False, indent=2) if a.json else render_text(data))


if __name__ == "__main__":
    main()
