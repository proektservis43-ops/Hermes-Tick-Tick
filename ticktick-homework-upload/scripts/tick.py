#!/usr/bin/env python3
"""TickTick Open API v1 helper. Stdlib only. Reads token from ~/.hermes/.env.
Endpoints per current official docs. NOTE: /task/undone enforces a max ~14-day
range and silently returns [] for wider ones -> chunked fetches below."""
import argparse, datetime, json, os, re, sys, urllib.request, urllib.error, urllib.parse

BASE = "https://api.ticktick.com/open/v1"
ENV = os.path.expanduser("~/.hermes/.env")
STATE = os.path.expanduser("~/.hermes/ticktick_reminded.json")

def token():
    for line in open(ENV):
        line = line.strip()
        if line.startswith("TICKTICK_API_TOKEN="):
            return line.split("=", 1)[1].strip()
    sys.exit("TICKTICK_API_TOKEN not found in " + ENV)

TOK = token()

def api(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Authorization", "Bearer " + TOK)
    req.add_header("Content-Type", "application/json")
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data=data, timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        sys.exit("HTTP %s: %s" % (e.code, e.read().decode(errors="replace")[:400]))

def now_local():
    return datetime.datetime.now().astimezone()

def api_dt(dt):
    return dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000+0000")

def strip_emoji(s):
    return re.sub(r"[^\w\sа-яА-ЯёЁ-]", "", s or "").strip()

def load_projects():
    return api("GET", "/project") or []

def resolve_project(name_or_id):
    if not name_or_id:
        return None
    low = name_or_id.lower()
    if low == "inbox" or low == "входящие":
        return {"id": "inbox", "name": "Входящие"}
    projs = load_projects()
    for p in projs:
        if p["id"] == name_or_id or strip_emoji(p["name"]).lower() == strip_emoji(name_or_id).lower():
            return p
    q = strip_emoji(name_or_id).lower()
    for p in projs:
        if q and q in strip_emoji(p["name"]).lower():
            return p
    return None

def _undone_raw(project_ids=None, start=None, end=None, task_ids=None):
    body = {}
    if project_ids: body["projectIds"] = project_ids
    if task_ids: body["taskIds"] = task_ids
    if start: body["startDate"] = api_dt(start)
    if end: body["endDate"] = api_dt(end)
    return api("POST", "/task/undone", body) or []

def _completed_raw(project_ids=None, start=None, end=None):
    body = {}
    if project_ids: body["projectIds"] = project_ids
    if start: body["startDate"] = api_dt(start)
    if end: body["endDate"] = api_dt(end)
    return api("POST", "/task/completed", body) or []

def _merge(acc, items):
    seen = {t["id"] for t in acc}
    for t in items:
        if t["id"] not in seen:
            acc.append(t)
    return acc

def undone_range(start, end, project_ids=None, task_ids=None, span_days=12):
    """Chunked undone fetch (server rejects ranges > ~14 days)."""
    acc, cur = [], start
    span = datetime.timedelta(days=span_days)
    while cur < end:
        nxt = min(cur + span, end)
        acc = _merge(acc, _undone_raw(project_ids, cur, nxt, task_ids))
        cur = nxt
    return acc

def completed_range(start, end, project_ids=None, span_days=12):
    acc, cur = [], start
    span = datetime.timedelta(days=span_days)
    while cur < end:
        nxt = min(cur + span, end)
        acc = _merge(acc, _completed_raw(project_ids, cur, nxt))
        cur = nxt
    return acc

def all_open_tasks():
    now = now_local()
    return undone_range(now - datetime.timedelta(days=12), now + datetime.timedelta(days=2))

def is_open(t):
    return int(t.get("status", 0) or 0) == 0

def due_dt(t):
    d = t.get("dueDate") or t.get("startDate")
    return datetime.datetime.fromisoformat(d).astimezone() if d else None

def parse_iso(s):
    return datetime.datetime.fromisoformat(s).astimezone()

def rel_str(dt, now):
    m = int((dt - now).total_seconds() // 60)
    if m < 0: return "просрочено на %d мин" % -m
    if m < 60: return "через %d мин" % m
    h, mm = divmod(m, 60)
    if h < 24: return "через %d ч %d мин" % (h, mm)
    return "через %d дн" % (h // 24)

def fmt_dt(dt):
    return dt.strftime("%d.%m %H:%M")

def find_task(task_id):
    now = now_local()
    res = undone_range(now - datetime.timedelta(days=6), now + datetime.timedelta(days=7), task_ids=[task_id])
    for t in res:
        if t.get("id") == task_id:
            return t
    for t in completed_range(now - datetime.timedelta(days=30), now):
        if t.get("id") == task_id:
            return t
    return None

def proj_display(pid, projs):
    if not pid: return ""
    if pid in projs: return projs[pid]
    if str(pid).startswith("inbox"): return "Входящие"
    return "?"

def cmd_projects(args):
    print(json.dumps([{"id": p["id"], "name": p["name"], "kind": p.get("kind")} for p in load_projects()], ensure_ascii=False))

def cmd_add(args):
    proj = resolve_project(args.list) if args.list else resolve_project("inbox")
    body = {"title": args.title, "projectId": proj["id"]}
    if args.due:
        body["dueDate"] = args.due
        body["startDate"] = args.due
        dt = parse_iso(args.due)
        body["timeZone"] = getattr(dt.tzinfo, "key", "Europe/Moscow")
        body["isAllDay"] = bool(args.allday)
        if args.remind is not None:
            body["reminders"] = ["TRIGGER:PT%dM" % int(args.remind)]
    if args.priority:
        body["priority"] = int(args.priority)
    if args.note:
        body["content"] = args.note
    if args.tags:
        body["tags"] = [x.strip() for x in args.tags.split(",") if x.strip()]
    created = api("POST", "/task", body)
    print(json.dumps(created, ensure_ascii=False))

def cmd_get(args):
    t = find_task(args.id)
    if not t:
        sys.exit("task not found")
    print(json.dumps(t, ensure_ascii=False))

def cmd_tasks(args):
    proj = resolve_project(args.list) if args.list else None
    now = now_local()
    frm = parse_iso(args.frm) if args.frm else now - datetime.timedelta(hours=1)
    to = parse_iso(args.to) if args.to else now + datetime.timedelta(days=1)
    tasks = undone_range(frm - datetime.timedelta(days=1), to + datetime.timedelta(days=1),
                         project_ids=[proj["id"]] if proj else None)
    if proj:
        tasks = [t for t in tasks if str(t.get("projectId")).startswith(proj["id"]) or t.get("projectId") == proj["id"]]
    tasks = [t for t in tasks if is_open(t) and due_dt(t) and frm <= due_dt(t) <= to]
    print(json.dumps(tasks, ensure_ascii=False))

def _resolve_and_call(args, action):
    if args.list:
        proj = resolve_project(args.list)
        if not proj:
            sys.exit("list not found: " + args.list)
        pid = proj["id"]
    else:
        t = find_task(args.id)
        if not t:
            sys.exit("task not found (дата вне окна поиска? укажи --list)")
        pid = t["projectId"]
    if action == "complete":
        print(json.dumps(api("POST", "/project/%s/task/%s/complete" % (pid, args.id), {}) or {"ok": True}, ensure_ascii=False))
    else:
        api("DELETE", "/project/%s/task/%s" % (pid, args.id))
        print(json.dumps({"ok": True}))

def cmd_complete(args):
    _resolve_and_call(args, "complete")

def cmd_delete(args):
    _resolve_and_call(args, "delete")

def cmd_digest(args):
    now = now_local()
    today = now.date()
    tasks = [t for t in all_open_tasks() if is_open(t) and due_dt(t)]
    projs = {p["id"]: strip_emoji(p["name"]).strip() for p in load_projects()}
    late = [t for t in tasks if due_dt(t) < now]
    over = [t for t in late if due_dt(t) >= now - datetime.timedelta(days=3)]
    old_n = len(late) - len(over)
    tod = [t for t in tasks if due_dt(t).date() == today]
    tmw = [t for t in tasks if due_dt(t).date() == today + datetime.timedelta(days=1)]
    out = ["📋 Сводка на %s" % today.strftime("%d.%m")]
    def block(title, arr):
        if not arr: return
        out.append("\n%s:" % title)
        arr.sort(key=lambda t: due_dt(t))
        for t in arr:
            pid = t.get("projectId")
            ln = (" [" + proj_display(pid, projs) + "]") if pid else ""
            out.append("• %s%s — %s" % (t["title"], ln, fmt_dt(due_dt(t))))
    block("⚠️ Просрочено", over)
    block("🗓 Сегодня", tod)
    block("🌤 Завтра", tmw)
    if not over and not tod and not tmw:
        out.append("\nЗадач на ближайшие дни нет — можно выдохнуть 😌")
    if old_n:
        out.append("\n…и ещё %d старых просроченных задач (в TickTick)" % old_n)
    print("\n".join(out))

def cmd_remind(args):
    now = now_local()
    tasks = [t for t in all_open_tasks() if is_open(t) and due_dt(t)]
    seen = {}
    if os.path.exists(STATE):
        try: seen = json.load(open(STATE))
        except Exception: seen = {}
    now_ts = now.timestamp()
    seen = {k: v for k, v in seen.items() if now_ts - v < 2 * 86400}
    due = []
    for t in tasks:
        d = due_dt(t)
        if now < d <= now + datetime.timedelta(minutes=args.within) and t["id"] not in seen:
            due.append((t, d))
    lines = []
    for t, d in sorted(due, key=lambda x: x[1]):
        lines.append("⏰ %s — %s (%s)" % (t["title"], fmt_dt(d), rel_str(d, now)))
        seen[t["id"]] = now_ts
    json.dump(seen, open(STATE, "w"))
    if lines:
        print("\n".join(lines))

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("projects")
    p = sub.add_parser("add"); p.add_argument("--title", required=True); p.add_argument("--list")
    p.add_argument("--due"); p.add_argument("--remind", type=int); p.add_argument("--priority", type=int)
    p.add_argument("--note"); p.add_argument("--tags"); p.add_argument("--allday", action="store_true")
    p = sub.add_parser("get"); p.add_argument("id")
    p = sub.add_parser("tasks"); p.add_argument("--list"); p.add_argument("--from", dest="frm"); p.add_argument("--to")
    p = sub.add_parser("complete"); p.add_argument("id"); p.add_argument("--list")
    p = sub.add_parser("delete"); p.add_argument("id"); p.add_argument("--list")
    sub.add_parser("digest")
    p = sub.add_parser("remind"); p.add_argument("--within", type=int, default=90)
    args = ap.parse_args()
    {"projects": cmd_projects, "add": cmd_add, "get": cmd_get, "tasks": cmd_tasks,
     "complete": cmd_complete, "delete": cmd_delete, "digest": cmd_digest, "remind": cmd_remind}[args.cmd](args)

if __name__ == "__main__":
    main()
