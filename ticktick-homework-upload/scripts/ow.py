#!/usr/bin/env python3
"""Read local OpenWhispr data (read-only). Prints JSON."""
import argparse, json, os, sqlite3, datetime

DB = os.path.expanduser("~/Library/Application Support/open-whispr/transcriptions.db")

def ts_fmt(v):
    if not v:
        return ""
    try:
        return datetime.datetime.fromisoformat(str(v).replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(v)

def cmd_recent(args):
    con = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT id, text, raw_text, timestamp, created_at, provider, status "
        "FROM transcriptions WHERE deleted_at IS NULL ORDER BY id DESC LIMIT ?",
        (args.n,)).fetchall()
    out = [{"id": r["id"], "text": r["text"] or "", "timestamp": ts_fmt(r["created_at"] or r["timestamp"]),
            "provider": r["provider"], "status": r["status"]} for r in rows]
    print(json.dumps(out, ensure_ascii=False))

def cmd_notes(args):
    con = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT id, title, content, transcript, note_type, created_at, updated_at "
        "FROM notes WHERE deleted_at IS NULL ORDER BY id DESC LIMIT ?",
        (args.n,)).fetchall()
    out = [{"id": r["id"], "title": r["title"], "content": r["content"] or "",
            "transcript": (r["transcript"] or "")[:2000], "note_type": r["note_type"],
            "updated_at": ts_fmt(r["updated_at"])} for r in rows]
    print(json.dumps(out, ensure_ascii=False))

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("recent"); p.add_argument("-n", type=int, default=10)
    p = sub.add_parser("notes"); p.add_argument("-n", type=int, default=10)
    args = ap.parse_args()
    {"recent": cmd_recent, "notes": cmd_notes}[args.cmd](args)

if __name__ == "__main__":
    main()
