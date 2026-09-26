#!/usr/bin/env python3
"""Spaced-repetition helper for connie learner profiles.

Reads and updates the Vocabulary table in <language>-profile.md (and the known words kept in
<language>-archive.md), so review dates and intervals are computed exactly rather than by hand.
Python 3 standard library only.

Commands:
  due    List the words that are due (overdue first).
           python3 review.py due german-profile.md [--limit 12] [--ahead 0] [--json]
  grade  Record review results and reschedule.
           python3 review.py grade german-profile.md --got "gießen" --shaky "ausgerechnet" \
               --missed "der Zufall"
  add    Save a new word with its context sentence (due tomorrow).
           python3 review.py add german-profile.md --word "die Spur" \
               --sentence "Der Dieb hat keine Spur hinterlassen." --meaning "trace" --source "story S1E1"
  stats  One-line summary (total, due today, due this week, by strength).
  tidy   Keep the profile short: move known words, old resolved mistakes and older session-log
         entries to <language>-archive.md. Safe to run at the end of every session.

Common options: --today YYYY-MM-DD (pass the learner's local date; the default is the system
date, which is often UTC), --dry-run (grade/add/tidy: show what would change, write nothing).

Schedule: intervals step through 1 → 3 → 7 → 14 → 30 → 60 → 120 days.
  got → next step up · shaky → same interval · missed → back to 1 day
Strength: new → learning after the first correct answer; familiar at 14+ days; known at 60+
days; a missed word drops back to learning (and moves back from the archive to the profile).
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from profile_md import (VOCAB_HEADER, MISTAKES_HEADER, VOCAB_COLS, DATE_RE, Doc, clean,  # noqa: E402
                        join_row, archive_path, archive_template, language_name)

LADDER = [1, 3, 7, 14, 30, 60, 120]
KEEP_LOG = 15          # session-log entries kept in the profile
MISTAKE_QUIET_DAYS = 45  # a mistake not seen for this long counts as resolved


def parse_date(s):
    m = DATE_RE.search(s or "")
    try:
        return dt.date.fromisoformat(m.group(0)) if m else None
    except ValueError:
        return None


def parse_int(s):
    m = re.search(r"\d+", s or "")
    return int(m.group(0)) if m else 0


def norm(word):
    return re.sub(r"\s+", " ", word).strip().casefold()


def next_step(interval):
    return next((s for s in LADDER if s > interval), LADDER[-1])


def strength_for(interval, old, result):
    if result == "missed":
        return "new" if old == "new" else "learning"
    if result == "shaky":
        return old or "new"
    if interval >= 60:
        return "known"
    if interval >= 14:
        return "familiar"
    return "learning"


class Store:
    """The profile's vocabulary plus the archive's known words, treated as one list."""

    def __init__(self, profile_path):
        self.profile = Doc(profile_path)
        if not self.profile.section("vocab"):
            sys.exit("No '## Vocabulary' section found in the profile.")
        self.arch_path = archive_path(profile_path)
        self.archive = Doc(self.arch_path, archive_template(language_name(self.profile)))

    def vtable(self, doc):
        return doc.table("vocab", VOCAB_COLS, create_header=VOCAB_HEADER)

    def entries(self):
        """[(doc, line index, cells)] for every saved word."""
        out = []
        for doc in (self.profile, self.archive):
            t = self.vtable(doc)
            if not t:
                continue
            for idx, cells in t.rows:
                w = t.get(cells, "word")
                if w and not w.startswith("<"):
                    out.append((doc, idx, cells))
        return out

    def save(self, dry):
        if dry:
            return
        self.profile.save()
        if not self.archive.created or self.archive_dirty:
            self.archive.save()

    archive_dirty = False


def entry_dict(t, cells, today, archived=False):
    nxt = parse_date(t.get(cells, "next"))
    return {
        "word": t.get(cells, "word"), "sentence": t.get(cells, "sentence"),
        "meaning": t.get(cells, "meaning"), "source": t.get(cells, "source"),
        "next": str(nxt) if nxt else "", "days_overdue": (today - nxt).days if nxt else None,
        "interval": parse_int(t.get(cells, "interval")),
        "strength": (t.get(cells, "strength") or "new").lower(), "archived": archived,
    }


def all_dicts(st, today):
    out = []
    for doc, _, cells in st.entries():
        out.append(entry_dict(st.vtable(doc), cells, today, doc is st.archive))
    return out


def cmd_due(st, a, today):
    horizon = today + dt.timedelta(days=a.ahead)
    due = [e for e in all_dicts(st, today) if not e["next"] or parse_date(e["next"]) <= horizon]
    due.sort(key=lambda e: (e["next"] or "0000", e["interval"]))
    total = len(due)
    if a.limit:
        due = due[: a.limit]
    if a.json:
        print(json.dumps({"today": str(today), "due_total": total, "words": due}, ensure_ascii=False, indent=2))
        return
    if not due:
        upcoming = sorted(filter(None, (parse_date(e["next"]) for e in all_dicts(st, today))))
        print(f"Nothing due as of {today}." + (f" Next review: {upcoming[0]}." if upcoming else ""))
        return
    shown = f"{len(due)} of {total}" if total > len(due) else str(total)
    print(f"{shown} due as of {today} (overdue first):\n")
    for e in due:
        late = e["days_overdue"]
        when = ("no date" if late is None else "due today" if late == 0 else
                f"{late} days overdue" if late > 0 else f"due in {-late} days")
        print(f"- {e['word']}  [{e['strength']}, {e['interval']}d, {when}]")
        if e["sentence"]:
            print(f"    {e['sentence']}")
        meta = " · ".join(x for x in (e["meaning"], e["source"]) if x)
        if meta:
            print(f"    {meta}")


def cmd_grade(st, a, today):
    results = [(w, "got") for w in a.got] + [(w, "shaky") for w in a.shaky] + [(w, "missed") for w in a.missed]
    if not results:
        sys.exit("Nothing to grade: pass --got, --shaky and/or --missed.")
    changes, unknown, back_to_profile = [], [], []
    for word, result in results:
        hit = next(((d, i, c) for d, i, c in st.entries() if norm(st.vtable(d).get(c, "word")) == norm(word)), None)
        if not hit:
            unknown.append(word)
            continue
        doc, i, cells = hit
        t = st.vtable(doc)
        old_int = parse_int(t.get(cells, "interval"))
        old_str = (t.get(cells, "strength") or "new").lower()
        new_int = next_step(old_int) if result == "got" else (old_int or 1) if result == "shaky" else 1
        new_str = strength_for(new_int, old_str, result)
        new_next = today + dt.timedelta(days=new_int)
        t.set(cells, "interval", str(new_int))
        t.set(cells, "strength", new_str)
        t.set(cells, "next", str(new_next))
        doc.lines[i] = join_row(cells)
        if doc is st.archive and new_str != "known":
            back_to_profile.append((i, list(cells)))
        changes.append((t.get(cells, "word"), result, old_int, new_int, old_str, new_str, new_next))
    if back_to_profile:
        st.archive.delete_lines([i for i, _ in back_to_profile])
        for _, cells in back_to_profile:
            st.profile.append_row("vocab", cells, VOCAB_COLS, VOCAB_HEADER)
        st.archive_dirty = True
    st.save(a.dry_run or not changes)
    for w, r, oi, ni, os_, ns, nx in changes:
        s_change = f"{os_} → {ns}" if os_ != ns else ns
        print(f"- {w}: {r} · {oi}d → {ni}d · {s_change} · next {nx}")
    counts = {r: sum(1 for c in changes if c[1] == r) for r in ("got", "shaky", "missed")}
    tomorrow = sum(1 for c in changes if c[6] == today + dt.timedelta(days=1))
    print(f"\n{len(changes)} reviewed: {counts['got']} got it, {counts['shaky']} shaky, "
          f"{counts['missed']} missed · {tomorrow} back tomorrow" + (" (dry run, nothing saved)" if a.dry_run else ""))
    if back_to_profile:
        print(f"{len(back_to_profile)} archived word(s) moved back to the profile for more practice.")
    if unknown:
        print("Not found in the vocabulary: " + ", ".join(unknown), file=sys.stderr)
        sys.exit(2)


def cmd_add(st, a, today):
    if any(norm(st.vtable(d).get(c, "word")) == norm(a.word) for d, _, c in st.entries()):
        print(f"Already saved: {a.word} (not added again)")
        return
    if not a.sentence.strip():
        sys.exit("A context sentence is required: words are always saved with a sentence.")
    values = {"word": clean(a.word), "sentence": clean(a.sentence), "meaning": clean(a.meaning),
              "source": clean(a.source), "added": str(today),
              "next": str(today + dt.timedelta(days=1)), "interval": "1", "strength": "new"}
    t = st.vtable(st.profile)
    cells = [""] * len(t.header)
    for name, j in t.col.items():
        cells[j] = values.get(name, "")
    st.profile.lines.insert(t.insert_at, join_row(cells))
    if not a.dry_run:
        st.profile.save()
    print(f"Added: {a.word} · next review {values['next']}" + (" (dry run)" if a.dry_run else ""))


def cmd_stats(st, a, today):
    es = all_dicts(st, today)
    week = today + dt.timedelta(days=7)
    due_today = sum(1 for e in es if not e["next"] or parse_date(e["next"]) <= today)
    due_week = sum(1 for e in es if not e["next"] or parse_date(e["next"]) <= week)
    by = {s: sum(1 for e in es if e["strength"] == s) for s in ("new", "learning", "familiar", "known")}
    archived = sum(1 for e in es if e["archived"])
    print(f"{len(es)} words ({archived} archived) · {due_today} due today · {due_week} due within 7 days · "
          + " · ".join(f"{k} {v}" for k, v in by.items()))


def cmd_tidy(st, a, today):
    p, ar = st.profile, st.archive
    moved = {"words": 0, "mistakes": 0, "log": 0}

    # 1. Known words → archive.
    t = st.vtable(p)
    rows = [(i, c) for i, c in t.rows if (t.get(c, "strength") or "").lower() == "known"]
    if rows:
        p.delete_lines([i for i, _ in rows])
        at = st.vtable(ar)
        for _, c in rows:
            cells = [""] * len(at.header)
            for name, j in at.col.items():
                cells[j] = t.get(c, name)
            ar.append_row("vocab", cells, VOCAB_COLS, VOCAB_HEADER)
        moved["words"] = len(rows)

    # 2. Mistakes not seen for a while → resolved.
    cols = {"last": ("last",), "pattern": ("pattern",)}
    mt = p.table("recurring", cols)
    if mt and "last" in mt.col:
        cutoff = today - dt.timedelta(days=MISTAKE_QUIET_DAYS)
        old = [(i, c) for i, c in mt.rows
               if parse_date(mt.get(c, "last")) and parse_date(mt.get(c, "last")) < cutoff]
        if old:
            p.delete_lines([i for i, _ in old])
            for _, c in old:
                ar.append_row("resolved", c, create_header=MISTAKES_HEADER)
            moved["mistakes"] = len(old)

    # 3. Session log: keep the newest entries in the profile.
    entries = [(i, line) for i, line in p.bullets("session") if DATE_RE.search(line)]
    if len(entries) > KEEP_LOG:
        by_date = sorted(entries, key=lambda e: DATE_RE.search(e[1]).group(0))
        old = by_date[: len(entries) - KEEP_LOG]
        p.delete_lines([i for i, _ in old])
        sec = ar.ensure_section("Session log (older)")
        insert = sec[1]
        while insert > sec[0] + 1 and not ar.lines[insert - 1].strip():
            insert -= 1
        ar.lines[insert:insert] = [line for _, line in old]
        moved["log"] = len(old)

    if not any(moved.values()):
        print("Nothing to tidy: the profile is already short.")
        return
    if not a.dry_run:
        p.save()
        ar.save()
    print(f"Moved to {ar.path.name}: {moved['words']} known words, {moved['mistakes']} resolved mistakes, "
          f"{moved['log']} older log entries" + (" (dry run, nothing saved)" if a.dry_run else ""))


def main():
    ap = argparse.ArgumentParser(description="Spaced-repetition helper for connie profiles.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(sp, dry=False):
        sp.add_argument("profile")
        sp.add_argument("--today", help="YYYY-MM-DD: the learner's local date (default: system date)")
        if dry:
            sp.add_argument("--dry-run", action="store_true")
        return sp

    d = common(sub.add_parser("due"))
    d.add_argument("--limit", type=int, default=15)
    d.add_argument("--ahead", type=int, default=0, help="also include words due within N days")
    d.add_argument("--json", action="store_true")
    g = common(sub.add_parser("grade"), dry=True)
    g.add_argument("--got", action="append", default=[])
    g.add_argument("--shaky", action="append", default=[])
    g.add_argument("--missed", action="append", default=[])
    ad = common(sub.add_parser("add"), dry=True)
    ad.add_argument("--word", required=True)
    ad.add_argument("--sentence", required=True)
    ad.add_argument("--meaning", default="")
    ad.add_argument("--source", default="")
    common(sub.add_parser("stats"))
    common(sub.add_parser("tidy"), dry=True)

    a = ap.parse_args()
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    st = Store(a.profile)
    {"due": cmd_due, "grade": cmd_grade, "add": cmd_add, "stats": cmd_stats, "tidy": cmd_tidy}[a.cmd](st, a, today)


if __name__ == "__main__":
    main()
