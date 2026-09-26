#!/usr/bin/env python3
"""Can-do milestones for speaker-skill learner profiles.

The milestone list lives in references/milestones.md (6 strands × Pre-A1…C1). The profile
keeps only the current level's rows; completed levels are summarized on one line and their
earned milestones move to <language>-archive.md.

Commands:
  init    After placement, or when a level is complete: credit levels up to --level and add
          the next level's milestones.
            python3 milestones.py init hebrew-profile.md --level A1+ --today 2026-09-25
  focus   Set the 1–2 focus milestones (others go back to open).
            python3 milestones.py focus hebrew-profile.md A2-people A2-stories
  log     Record one piece of evidence. Prints EARNED / LEVEL COMPLETE when it happens.
            python3 milestones.py log hebrew-profile.md A2-stories --note "retold S1E2" --today 2026-09-27
  status  Progress on the current level.

Rule: a milestone is earned with 3 pieces of evidence on at least 2 different days.
Always pass --today with the learner's local date.
"""
import argparse
import datetime as dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from profile_md import Doc, clean, join_row, archive_path, archive_template, language_name  # noqa: E402

LEVELS = ["PreA1", "A1", "A2", "B1", "B2", "C1"]
LABEL = {"PreA1": "Pre-A1"}
STRANDS = {"people": "People", "daily": "Daily life", "getting": "Getting things done",
           "stories": "Telling stories", "opinions": "Opinions", "material": "Real material"}
NEEDED, NEEDED_DAYS = 3, 2
HEADER = ["ID", "Can-do", "Status", "Evidence", "Earned"]
COLS = {"id": ("id",), "cando": ("can",), "status": ("status",), "evidence": ("evidence",), "earned": ("earned",)}
ARCH_COLS = {"id": ("id",), "cando": ("can",), "evidence": ("evidence",), "earned": ("earned",)}
COMPLETED_PREFIX = "- Levels completed:"


def label(level):
    return LABEL.get(level, level)


def norm_level(text):
    t = re.sub(r"[\s_-]", "", (text or "").split("(")[0]).upper().rstrip("+")
    t = "PreA1" if t in ("PREA1", "A0") else t
    if t not in LEVELS:
        sys.exit(f"Unknown level '{text}'. Use one of: " + ", ".join(label(l) for l in LEVELS))
    return t


def load_reference():
    ref = Path(__file__).resolve().parent.parent / "references" / "milestones.md"
    out = {}
    for line in ref.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*((?:PreA1|A1|A2|B1|B2|C1)-[a-z]+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$", line)
        if m:
            out[m.group(1)] = {"cando": m.group(2), "evidence": m.group(3)}
    if not out:
        sys.exit("Could not read the milestone list from references/milestones.md")
    return out


def level_of(mid):
    return mid.split("-")[0]


def strand_of(mid):
    return STRANDS.get(mid.split("-")[1], mid.split("-")[1])


def evidence_list(cell):
    return [e.strip() for e in (cell or "").split(";") if e.strip()]


def evidence_days(items):
    return {m.group(0) for e in items for m in [re.match(r"\d{4}-\d{2}-\d{2}", e)] if m}


class Profile:
    def __init__(self, path):
        self.doc = Doc(path)
        self.ref = load_reference()
        self.arch = Doc(archive_path(path), archive_template(language_name(self.doc)))
        self.arch_changed = False

    def ensure(self):
        if not self.doc.section("milestones"):
            self.doc.ensure_section("Milestones", before="Session log")
        return self.doc.table("milestones", COLS, create_header=HEADER)

    def table(self):
        return self.doc.table("milestones", COLS)

    def rows(self):
        t = self.table()
        return [] if not t else [(i, c) for i, c in t.rows if t.get(c, "id")]

    def completed_line(self):
        sec = self.doc.section("milestones")
        if not sec:
            return None, []
        for i in range(sec[0] + 1, sec[1]):
            if self.doc.lines[i].startswith(COMPLETED_PREFIX):
                parts = self.doc.lines[i][len(COMPLETED_PREFIX):]
                return i, [p.strip() for p in parts.split(";") if p.strip()]
        return None, []

    def completed_levels(self):
        _, parts = self.completed_line()
        found = set()
        for p in parts:
            for lvl in LEVELS:
                if re.search(rf"(?<![\w-]){re.escape(label(lvl))}(?![\w+])", p):
                    found.add(lvl)
        return found

    def set_completed(self, parts):
        idx, _ = self.completed_line()
        line = f"{COMPLETED_PREFIX} " + "; ".join(parts)
        if idx is not None:
            self.doc.lines[idx] = line
        else:
            sec = self.doc.section("milestones")
            self.doc.lines[sec[0] + 1:sec[0] + 1] = [line, ""]  # blank line keeps the table separate

    def save(self):
        self.doc.save()
        if self.arch_changed:
            self.arch.save()


def cmd_init(p, a, today):
    target = norm_level(a.level)
    ti = LEVELS.index(target)
    p.ensure()
    done = p.completed_levels()
    _, parts = p.completed_line()
    t = p.table()
    rows_by_level = {}
    for i, c in p.rows():
        rows_by_level.setdefault(level_of(t.get(c, "id")), []).append((i, c))

    newly = []
    to_delete = []
    for lvl in LEVELS[: ti + 1]:
        if lvl in done:
            continue
        rows = rows_by_level.get(lvl, [])
        earned = [(i, c) for i, c in rows if t.get(c, "status").lower() == "earned"]
        for i, c in earned:  # keep the record of earned milestones in the archive
            p.arch.append_row("milestones earned",
                              [t.get(c, "id"), t.get(c, "cando"), t.get(c, "evidence"), t.get(c, "earned")],
                              ARCH_COLS, ["ID", "Can-do", "Evidence", "Earned"])
            p.arch_changed = True
        to_delete += [i for i, _ in rows]
        how = "milestones" if rows and len(earned) == len(rows) else "placement"
        newly.append((lvl, how))
    p.doc.delete_lines(to_delete)

    # Summarize credited levels on one line, grouped by how and when.
    groups = {}
    for lvl, how in newly:
        groups.setdefault(how, []).append(label(lvl))
    for how, lvls in groups.items():
        parts.append(f"{', '.join(lvls)} ({how}, {today})")
    if newly:
        p.set_completed(parts)

    added = []
    if ti + 1 < len(LEVELS):
        nxt = LEVELS[ti + 1]
        have = {p.table().get(c, "id") for _, c in p.rows()}
        for mid, info in p.ref.items():
            if level_of(mid) == nxt and mid not in have:
                t = p.table()
                p.doc.lines.insert(t.insert_at, join_row([mid, info["cando"], "open", "", ""]))
                added.append(mid)
    p.save()
    if newly:
        print("Credited: " + ", ".join(f"{label(l)} ({h})" for l, h in newly))
    if ti + 1 < len(LEVELS):
        print(f"Working on {label(LEVELS[ti + 1])}: " + (", ".join(added) if added else "rows already present"))
        print("Next: pick 1–2 focus milestones with `focus`.")
    else:
        print("C1 complete: no more milestones. Time for the learner's own goals.")


def cmd_focus(p, a, today):
    if len(a.ids) > 2:
        sys.exit("Choose at most 2 focus milestones.")
    t = p.table()
    ids = {t.get(c, "id"): i for i, c in p.rows()} if t else {}
    missing = [m for m in a.ids if m not in ids]
    if missing:
        sys.exit("Not in the profile's current milestones: " + ", ".join(missing) + ". Run `status` to see them.")
    for i, c in p.rows():
        st = t.get(c, "status").lower()
        mid = t.get(c, "id")
        if mid in a.ids and st != "earned":
            t.set(c, "status", "focus")
        elif st == "focus" and mid not in a.ids:
            t.set(c, "status", "open")
        p.doc.lines[i] = join_row(c)
    p.save()
    for m in a.ids:
        print(f"Focus: {m} · {strand_of(m)} · {p.ref.get(m, {}).get('cando', '')}")


def cmd_log(p, a, today):
    mid = a.id
    if mid not in p.ref:
        sys.exit(f"Unknown milestone ID: {mid}")
    if level_of(mid) in p.completed_levels():
        print(f"{label(level_of(mid))} is already complete; nothing to log for {mid}.")
        return
    p.ensure()
    t = p.table()
    hit = next(((i, c) for i, c in p.rows() if t.get(c, "id") == mid), None)
    if not hit:  # evidence for a milestone above the current level: add its row
        p.doc.lines.insert(t.insert_at, join_row([mid, p.ref[mid]["cando"], "open", "", ""]))
        t = p.table()
        hit = next((i, c) for i, c in p.rows() if t.get(c, "id") == mid)
    i, c = hit
    status = t.get(c, "status").lower()
    items = evidence_list(t.get(c, "evidence"))
    if status == "earned":
        print(f"{mid} is already earned ({t.get(c, 'earned')}).")
        return
    items.append(f"{today} {clean(a.note)}")
    t.set(c, "evidence", "; ".join(items))
    days = evidence_days(items)
    earned_now = len(items) >= NEEDED and len(days) >= NEEDED_DAYS
    if earned_now:
        t.set(c, "status", "earned")
        t.set(c, "earned", str(today))
    p.doc.lines[i] = join_row(c)
    p.save()

    if earned_now:
        print(f"EARNED {mid} · {label(level_of(mid))} · {strand_of(mid)}")
        print(f"  {p.ref[mid]['cando']}")
        print("  Evidence: " + " · ".join(items))
        lvl = level_of(mid)
        t = p.table()
        same = [c for _, c in p.rows() if level_of(t.get(c, "id")) == lvl]
        if same and all(t.get(c, "status").lower() == "earned" for c in same) and len(same) == 6:
            print(f"LEVEL COMPLETE {label(lvl)}: celebrate, update the level, then run "
                  f"`init --level {label(lvl)}` to start the next one.")
        else:
            left = sum(1 for c in same if t.get(c, "status").lower() != "earned")
            print(f"  {left} left on {label(lvl)}.")
    else:
        print(f"Logged {mid}: {len(items)}/{NEEDED} pieces of evidence, "
              f"{len(days)}/{NEEDED_DAYS} days (earned at {NEEDED} pieces on {NEEDED_DAYS}+ different days)")


def cmd_status(p, a, today):
    done = p.completed_levels()
    _, parts = p.completed_line()
    if parts:
        print("Completed: " + "; ".join(parts))
    rows = p.rows()
    if not rows:
        print("No milestones yet. Run `init --level <placement level>` after the placement test.")
        return
    t = p.table()
    levels = sorted({level_of(t.get(c, "id")) for _, c in rows}, key=LEVELS.index)
    for lvl in levels:
        cs = [c for _, c in rows if level_of(t.get(c, "id")) == lvl]
        earned = sum(1 for c in cs if t.get(c, "status").lower() == "earned")
        print(f"\n{label(lvl)}: {earned}/{len(cs)} earned")
        order = {"earned": 0, "focus": 1, "open": 2}
        for c in sorted(cs, key=lambda c: order.get(t.get(c, "status").lower(), 3)):
            st = t.get(c, "status").lower()
            n = len(evidence_list(t.get(c, "evidence")))
            mark = {"earned": "🏅", "focus": "🎯"}.get(st, "○")
            extra = f"earned {t.get(c, 'earned')}" if st == "earned" else f"{n}/{NEEDED}"
            print(f"  {mark} {t.get(c, 'id'):<12} {t.get(c, 'cando')}  ({extra})")


def main():
    ap = argparse.ArgumentParser(description="Can-do milestones for speaker-skill profiles.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("profile")
        sp.add_argument("--today", help="YYYY-MM-DD: the learner's local date (default: system date)")
        return sp

    i = common(sub.add_parser("init"))
    i.add_argument("--level", required=True, help="placement level (e.g. A1+) or the level just completed")
    f = common(sub.add_parser("focus"))
    f.add_argument("ids", nargs="+")
    lg = common(sub.add_parser("log"))
    lg.add_argument("id")
    lg.add_argument("--note", required=True, help="what the learner did, e.g. 'retold S1E2'")
    common(sub.add_parser("status"))

    a = ap.parse_args()
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    p = Profile(a.profile)
    {"init": cmd_init, "focus": cmd_focus, "log": cmd_log, "status": cmd_status}[a.cmd](p, a, today)


if __name__ == "__main__":
    main()
