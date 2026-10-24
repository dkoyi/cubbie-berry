#!/usr/bin/env python3
"""Link this student's personal Cubbie to a Group Cubbie study group.

Cubbie gathers the data (Canvas, memory, calendar), writes profile.json with
only the fields the student agreed to share, and passes it here. This script
sends only the whitelisted fields below, so nothing else can leak.

  python3 scripts/groupsync.py join --code ABCD-1234 --server https://x.trycloudflare.com --profile profile.json
  python3 scripts/groupsync.py update --profile profile.json [--group ID]
  python3 scripts/groupsync.py results [--group ID]
  python3 scripts/groupsync.py leave [--group ID]
  python3 scripts/groupsync.py list
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse

# Must match network.runtime in cubbie.yaml.
ALLOWED_HOST_SUFFIXES = (".trycloudflare.com", ".onrender.com")
DATA_DIR = os.environ.get("SKILL_DATA_DIR") or os.path.expanduser("~")
STATE_FILE = os.path.join(DATA_DIR, "group-chat-assistant-groups.json")
MAX_OUTPUT = 7000


def fail(msg, code=1):
    print(f"ERROR: {msg}")
    sys.exit(code)


def clean_list(value, max_items, max_len):
    if not isinstance(value, list):
        return []
    return [str(v).strip()[:max_len] for v in value if str(v).strip()][:max_items]


def clean_profile(path):
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        fail(f"could not read profile file: {e}")
    name = str(raw.get("display_name", "")).strip()[:32]
    if not name:
        fail("profile needs display_name (first name or nickname)")
    profile = {"display_name": name}
    if str(raw.get("course", "")).strip():
        profile["course"] = str(raw["course"]).strip()[:40]
    for key, max_items, max_len in (
        ("exam_dates", 10, 60),
        ("weak_topics", 10, 60),
        ("free_slots", 14, 40),
    ):
        items = clean_list(raw.get(key), max_items, max_len)
        if items:
            profile[key] = items
    if str(raw.get("notes_excerpt", "")).strip():
        profile["notes_excerpt"] = str(raw["notes_excerpt"]).strip()[:12000]
    return profile


def check_server(server):
    u = urlparse(server)
    host = (u.hostname or "").lower()
    if u.scheme != "https" or not host.endswith(ALLOWED_HOST_SUFFIXES):
        fail(f"server must be https on {', '.join(ALLOWED_HOST_SUFFIXES)}; got {server!r}")
    return f"https://{host}"


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"groups": {}}


def save_state(state):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)


def pick_group(state, group_id):
    groups = state["groups"]
    if group_id:
        if group_id not in groups:
            fail(f"not linked to group {group_id}; run list")
        return group_id, groups[group_id]
    if len(groups) == 1:
        return next(iter(groups.items()))
    if not groups:
        fail("not linked to any group yet; type /link in the group chat to get a code")
    fail("linked to several groups; pass --group (see list)")


def call(method, url, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            text = resp.read().decode() or "{}"
            return json.loads(text)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        fail(f"group server said {e.code}: {detail}")
    except (urllib.error.URLError, TimeoutError) as e:
        fail(f"group server is unreachable (it may be offline): {e}", code=2)
    except json.JSONDecodeError:
        fail("group server sent a reply that is not JSON")


def cmd_join(args):
    server = check_server(args.server)
    profile = clean_profile(args.profile)
    res = call("POST", f"{server}/api/link", {"code": args.code.strip().upper(), "profile": profile})
    state = load_state()
    state["groups"][res["group_id"]] = {
        "server": server,
        "token": res["member_token"],
        "name": res.get("group_name", res["group_id"]),
    }
    save_state(state)
    print(f"Linked to {res.get('group_name', res['group_id'])} as {profile['display_name']}.")
    print(f"Members linked: {res.get('members_linked', '?')}. Shared fields: {', '.join(profile)}.")


def cmd_update(args):
    state = load_state()
    gid, g = pick_group(state, args.group)
    profile = clean_profile(args.profile)
    call("PUT", f"{g['server']}/api/member", {"profile": profile}, g["token"])
    print(f"Updated {g['name']}. Shared fields: {', '.join(profile)}.")


def cmd_results(args):
    state = load_state()
    gid, g = pick_group(state, args.group)
    res = call("GET", f"{g['server']}/api/member/results", token=g["token"])
    print(json.dumps(res, separators=(",", ":"))[:MAX_OUTPUT])


def cmd_leave(args):
    state = load_state()
    gid, g = pick_group(state, args.group)
    call("DELETE", f"{g['server']}/api/member", token=g["token"])
    del state["groups"][gid]
    save_state(state)
    print(f"Left {g['name']}. The group server deleted your profile.")


def cmd_list(args):
    groups = load_state()["groups"]
    if not groups:
        print("Not linked to any group.")
    for gid, g in groups.items():
        print(f"{gid}: {g['name']} ({urlparse(g['server']).hostname})")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    j = sub.add_parser("join")
    j.add_argument("--code", required=True)
    j.add_argument("--server", required=True)
    j.add_argument("--profile", required=True)
    u = sub.add_parser("update")
    u.add_argument("--profile", required=True)
    u.add_argument("--group")
    for name in ("results", "leave"):
        sub.add_parser(name).add_argument("--group")
    sub.add_parser("list")
    args = p.parse_args()
    {"join": cmd_join, "update": cmd_update, "results": cmd_results,
     "leave": cmd_leave, "list": cmd_list}[args.cmd](args)


if __name__ == "__main__":
    main()
