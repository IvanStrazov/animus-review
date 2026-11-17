#!/usr/bin/env python3
"""animus-review: send work to another model for review, then bring its answer back.

A review is a pair of files kept next to the project's journal
(<project>/.journal/review/, or ~/journal/review/ for sessions with no project):
  <id>.request.md    the package for the reviewer: context, questions, files, answer format
  <id>.response.md   the reviewer's answer, copied in with `in`
and one line per review in review/INDEX.md: id | open|answered|closed | title.

Commands:
  gather [--topic WORDS]       facts for the package: git state, STATE.md, journal entries on the topic
  sizes FILE...                lines and ~tokens per file, to keep the reviewer's reading budget honest
  save --title T               stdin -> a new request; prints its path and id
  in FILE [--id ID]            copy a reviewer's answer in (to the newest open request by default) and print both
  close ID [--note TEXT]       mark a review closed (after triage)
  list                         reviews with their status
  where                        print the review dir

Standard library only, Python 3.9+. No network.
"""
import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

JOURNAL_GLOBAL = Path(os.environ.get("JOURNAL_GLOBAL_DIR") or Path.home() / "journal").expanduser()
CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude").expanduser()
ECO_FILE = Path(os.environ.get("CLAUDE_ECOSYSTEM_FILE") or CLAUDE_DIR / "ecosystem.json").expanduser()
MAX_REQUEST = int(os.environ.get("REVIEW_MAX_LINES") or 200)
MAX_PRINT = int(os.environ.get("REVIEW_MAX_PRINT_CHARS") or 60000)
SCRIPT = Path(__file__).resolve()
SELF = "animus-review"

for _s in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


def run(args, cwd):
    try:
        return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=10).stdout.strip()
    except Exception:
        return ""


def journal_dir(cwd):
    """Same rule as animus-journal: git root/.journal, or the global dir for projectless sessions."""
    p = Path(cwd)
    s = str(p).replace("\\", "/").lower()
    if "scratch-workspaces" in s or not p.exists():
        return JOURNAL_GLOBAL
    for base in (Path.home(), Path(tempfile.gettempdir())):
        try:
            if p.resolve() == base.resolve():
                return JOURNAL_GLOBAL
        except OSError:
            pass
    top = run(["git", "rev-parse", "--show-toplevel"], p)
    return Path(top or p) / ".journal"


def review_dir():
    return journal_dir(os.getcwd()) / "review"


def ensure(d):
    d.mkdir(parents=True, exist_ok=True)
    gi = d.parent / ".gitignore"
    if d.parent != JOURNAL_GLOBAL and not gi.exists():
        gi.write_text("*\n", encoding="utf-8")  # same convention as animus-journal
    return d


def read_index(d):
    rows = []
    f = d / "INDEX.md"
    if f.is_file():
        for line in f.read_text(encoding="utf-8").splitlines():
            parts = [p.strip() for p in line.split("|", 2)]
            if len(parts) == 3:
                rows.append(parts)
    return rows


def write_index(d, rows):
    (d / "INDEX.md").write_text("".join(f"{i} | {s} | {t}\n" for i, s, t in rows), encoding="utf-8")


def set_status(d, rid, status):
    rows = read_index(d)
    for r in rows:
        if r[0] == rid:
            r[1] = status
    write_index(d, rows)


def register():
    try:
        e = json.loads(ECO_FILE.read_text(encoding="utf-8"))
        if not isinstance(e, dict):
            e = {}
    except (OSError, ValueError):
        e = {}
    e.setdefault("plugins", {})
    me = {"cmd": f'"{sys.executable}" "{SCRIPT}"'}
    if e["plugins"].get(SELF) != me:
        e["plugins"][SELF] = me
        try:
            ECO_FILE.parent.mkdir(parents=True, exist_ok=True)
            ECO_FILE.write_text(json.dumps(e, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass


def est_tokens(text):
    a = sum(1 for ch in text if ord(ch) < 128)
    return round(a / 4 + (len(text) - a) / 2.5)


# ---------- commands ----------

def cmd_gather(a):
    register()
    cwd = Path.cwd()
    j = journal_dir(cwd)
    out = [f"cwd: {cwd}", f"journal: {j}"]
    if run(["git", "rev-parse", "--is-inside-work-tree"], cwd) == "true":
        out.append(f"git branch: {run(['git', 'branch', '--show-current'], cwd) or '(detached)'}")
        log = run(["git", "log", "--oneline", "-10"], cwd)
        if log:
            out.append("recent commits:")
            out += [f"  {l}" for l in log.splitlines()]
    state = j / "STATE.md"
    if state.is_file() and j != JOURNAL_GLOBAL:
        out.append("STATE.md:")
        out += [f"  {l}" for l in state.read_text(encoding="utf-8", errors="replace").splitlines()[:40]]
    terms = [t.lower().lstrip("#") for t in (a.topic or [])]
    secs = []
    for log in sorted((j / "log").glob("*.md")) if (j / "log").is_dir() else []:
        for s in re.split(r"(?m)^(?=## \d{4})", log.read_text(encoding="utf-8", errors="replace")):
            s = s.strip()
            if s.startswith("## ") and all(t in s.lower() for t in terms):
                secs.append(s)
    if secs:
        out.append(f"journal entries{' on ' + ' '.join(a.topic) if terms else ''} (newest last):")
        for s in secs[-5:]:
            out += [f"  {l}" for l in s.splitlines()[:12]]
    open_ = [r for r in read_index(review_dir()) if r[1] != "closed"]
    if open_:
        out.append("reviews not closed: " + "; ".join(f"{r[0]} ({r[1]})" for r in open_))
    print("\n".join(out))


def cmd_sizes(a):
    total = 0
    for name in a.files:
        p = Path(name)
        if not p.is_file():
            print(f"missing  {name}")
            continue
        t = p.read_text(encoding="utf-8", errors="replace")
        tok = est_tokens(t)
        total += tok
        print(f"{len(t.splitlines()):>6} lines  ~{tok:>7} tokens  {name}")
    print(f"total ~{total} tokens of files for the reviewer to read (input only; its reasoning budget is separate)")


def slug(s):
    s = re.sub(r"[^\w\s-]", "", s.lower(), flags=re.U).strip()
    return re.sub(r"[\s_-]+", "-", s)[:40] or "review"


def cmd_save(a):
    text = sys.stdin.read().strip()
    n = len(text.splitlines())
    if not text:
        sys.exit("refused: empty request")
    if n > MAX_REQUEST:
        sys.exit(f"refused: {n} lines > {MAX_REQUEST}. Point to files instead of pasting them.")
    if not text.startswith("# "):
        text = f"# {a.title}\n\n{text}"
    d = ensure(review_dir())
    rid = f"{dt.datetime.now():%Y-%m-%d-%H%M}-{slug(a.title)}"
    f = d / f"{rid}.request.md"
    f.write_text(text + "\n", encoding="utf-8")
    rows = read_index(d) + [[rid, "open", " ".join(a.title.split())]]
    write_index(d, rows)
    print(f"[review] request {rid}: {n} lines, ~{est_tokens(text)} tokens -> {f}")


def cmd_in(a):
    src = Path(a.file)
    if not src.is_file():
        sys.exit(f"[review] not a file: {src}")
    d = ensure(review_dir())
    rows = read_index(d)
    if a.id:
        row = next((r for r in rows if r[0] == a.id), None)
        if not row:
            sys.exit(f"[review] no review {a.id}")
    else:
        row = next((r for r in reversed(rows) if r[1] == "open"), None)
        if not row:
            sys.exit("[review] no open request; pass --id")
    rid = row[0]
    dest = d / f"{rid}.response.md"
    if src.resolve() != dest.resolve():
        shutil.copyfile(src, dest)
    set_status(d, rid, "answered")
    req = (d / f"{rid}.request.md").read_text(encoding="utf-8", errors="replace")
    resp = dest.read_text(encoding="utf-8", errors="replace")
    print(f"=== request {rid} ===")
    print(req[:MAX_PRINT // 4] + ("\n(request truncated)" if len(req) > MAX_PRINT // 4 else ""))
    print(f"=== response ({len(resp.splitlines())} lines, ~{est_tokens(resp)} tokens) ===")
    print(resp[:MAX_PRINT])
    if len(resp) > MAX_PRINT:
        print(f"\n[review] response truncated at {MAX_PRINT} chars; the full text is in {dest}")


def cmd_close(a):
    d = review_dir()
    if not any(r[0] == a.id for r in read_index(d)):
        sys.exit(f"[review] no review {a.id}")
    set_status(d, a.id, "closed")
    if a.note:
        with open(d / f"{a.id}.request.md", "a", encoding="utf-8") as f:
            f.write(f"\n---\nClosed {dt.date.today()}: {a.note}\n")
    print(f"[review] {a.id} closed")


def cmd_list(_):
    rows = read_index(review_dir())
    for r in rows:
        print(f"{r[1]:<9} {r[0]}  — {r[2]}")
    if not rows:
        print("[review] no reviews here")


def cmd_where(_):
    print(review_dir())


def main(argv=None):
    ap = argparse.ArgumentParser(prog="review.py", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("gather")
    p.add_argument("--topic", nargs="*")
    p.set_defaults(fn=cmd_gather)
    p = sub.add_parser("sizes")
    p.add_argument("files", nargs="+")
    p.set_defaults(fn=cmd_sizes)
    p = sub.add_parser("save")
    p.add_argument("--title", required=True)
    p.set_defaults(fn=cmd_save)
    p = sub.add_parser("in")
    p.add_argument("file")
    p.add_argument("--id")
    p.set_defaults(fn=cmd_in)
    p = sub.add_parser("close")
    p.add_argument("id")
    p.add_argument("--note")
    p.set_defaults(fn=cmd_close)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    sub.add_parser("where").set_defaults(fn=cmd_where)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
