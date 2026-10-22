"""Parse Proxmox cluster config files into objects, report drift, plan pvesh commands.

An object is {kind, id, type, keys}; its name is "<kind>:<id>" (storage:pbs,
acl:/vms:ansible@pam). Revert runs `pvesh` as root on a cluster node, which goes
through the same API handlers and locks as the UI. Nothing is ever deleted:
live objects missing from the repo are reported as unmanaged.
"""

import shlex
from urllib.parse import unquote

# dest file -> (kind, typed sections)
SECTION_FILES = {
    "storage.cfg": ("storage", True),
    "jobs.cfg": ("job", True),
    "domains.cfg": ("realm", True),
    "mapping/usb.cfg": ("usb-mapping", False),
}

# Revert order: things that others reference come first
KIND_ORDER = [
    "role",
    "group",
    "pool",
    "user",
    "membership",
    "acl",
    "token",
    "storage",
    "realm",
    "job",
    "usb-mapping",
    "datacenter",
]

# Comma lists compared and written as sets
SORTED_LISTS = {("group", "members"), ("pool", "vms"), ("pool", "storage"), ("role", "privs"), ("acl", "roles")}


def _obj(kind, id_, keys, type_=None):
    return {"kind": kind, "id": id_, "type": type_, "keys": keys}


def _csv(value):
    return ",".join(sorted(v for v in value.split(",") if v))


def _parse_sections(text, kind, typed):
    out, keys = {}, None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0] in " \t":
            if keys is None:
                raise ValueError("%s: key line before the first section: %r" % (kind, line))
            k, _, v = line.strip().partition(" ")
            v = v.strip()
            if k in keys:  # repeated keys (usb `map`) become a sorted list
                keys[k] = sorted((keys[k] if isinstance(keys[k], list) else [keys[k]]) + [v])
            else:
                keys[k] = v
            continue
        if typed:
            type_, _, id_ = (s.strip() for s in line.partition(":"))
        else:
            type_, id_ = None, line.strip()
        keys = {}
        out["%s:%s" % (kind, id_)] = _obj(kind, id_, keys, type_)
    return out


def _parse_datacenter(text):
    keys = {}
    for line in text.splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            k, _, v = line.partition(":")
            keys[k.strip()] = v.strip()
    return {"datacenter:options": _obj("datacenter", "options", keys)}


def _parse_user(text):
    out = {}
    for line in text.splitlines():
        f = line.strip().split(":")
        kind = f[0]
        if kind == "user":
            names = ["enable", "expire", "firstname", "lastname", "email", "comment", "keys"]
            vals = (f[2:9] + [""] * 7)[:7]
            keys = {
                n: unquote(v) if n in ("firstname", "lastname", "comment") else v
                for n, v in zip(names, vals, strict=True)
            }
            out["user:" + f[1]] = _obj("user", f[1], keys)
        elif kind == "token":
            out["token:" + f[1]] = _obj("token", f[1], {"expire": f[2], "privsep": f[3], "comment": unquote(f[4])})
        elif kind == "group":
            out["group:" + f[1]] = _obj("group", f[1], {"members": _csv(f[2]), "comment": unquote(f[3])})
        elif kind == "pool":
            out["pool:" + f[1]] = _obj(
                "pool", f[1], {"comment": unquote(f[2]), "vms": _csv(f[3]), "storage": _csv(f[4])}
            )
        elif kind == "role":
            out["role:" + f[1]] = _obj("role", f[1], {"privs": _csv(f[2])})
        elif kind == "acl":
            # acl:<propagate>:<path>:<ugid,...>:<role,...>: -> one object per path and ugid
            for ugid in f[3].split(","):
                id_ = "%s:%s" % (f[2], ugid)
                out["acl:" + id_] = _obj("acl", id_, {"propagate": f[1], "roles": _csv(f[4])})
    return out


def pve_cfg_parse(text, dest):
    """Objects in one /etc/pve file, keyed by "<kind>:<id>"."""
    text = text or ""
    if dest in SECTION_FILES:
        return _parse_sections(text, *SECTION_FILES[dest])
    if dest == "datacenter.cfg":
        return _parse_datacenter(text)
    if dest == "user.cfg":
        return _parse_user(text)
    raise ValueError("no parser for %s" % dest)


def pve_cfg_parse_all(texts, dests):
    """Objects from several files: texts and dests are parallel lists."""
    out = {}
    for text, dest in zip(texts, dests, strict=True):
        out.update(pve_cfg_parse(text, dest))
    return out


def _show(v):
    return ",".join(v) if isinstance(v, list) else v


def _key_diff(want, have):
    """(changed {k: wanted value}, keys only live)"""
    changed = {k: v for k, v in want.items() if have.get(k) != v}
    return changed, sorted(k for k in have if k not in want)


def pve_cfg_drift(repo, live):
    """Report lines: missing, per-key differences, type changes, unmanaged."""
    lines = []
    for name in sorted(set(repo) | set(live)):
        if name not in live:
            lines.append("%s: missing" % name)
        elif name not in repo:
            lines.append("%s: unmanaged" % name)
        else:
            r, l = repo[name], live[name]
            if r["type"] != l["type"]:
                lines.append("%s type: declared=%s live=%s" % (name, r["type"], l["type"]))
            for k in sorted(set(r["keys"]) | set(l["keys"])):
                a, b = r["keys"].get(k, "<absent>"), l["keys"].get(k, "<absent>")
                if a != b:
                    lines.append("%s %s: declared=%s live=%s" % (name, k, _show(a), _show(b)))
    return lines


def _args(keys):
    argv = []
    for k, v in sorted(keys.items()):
        for item in v if isinstance(v, list) else [v]:
            argv += ["--" + k, item]
    return argv


def _plan(name, r, l, repo):
    """pvesh argv lists that make live object l match repo object r (l may be None)."""
    kind, id_, keys = r["kind"], r["id"], r["keys"]
    if l is not None and r["type"] != l["type"]:
        return None, "type declared=%s live=%s; recreate by hand" % (r["type"], l["type"])
    changed, extra = _key_diff(keys, l["keys"]) if l else (keys, [])
    delete = ["--delete", ",".join(extra)] if extra else []

    if kind == "token":
        return None, "tokens are report-only (creating one mints a secret)"
    if kind == "storage":
        if l is None:
            return [["pvesh", "create", "/storage", "--storage", id_, "--type", r["type"]] + _args(keys)], None
        return [["pvesh", "set", "/storage/" + id_] + _args(changed) + delete], None
    if kind == "job":
        if r["type"] != "vzdump":
            return None, "only vzdump jobs are managed"
        if l is None:
            return [["pvesh", "create", "/cluster/backup", "--id", id_] + _args(keys)], None
        return [["pvesh", "set", "/cluster/backup/" + id_] + _args(changed) + delete], None
    if kind == "realm":
        if l is None:
            return [["pvesh", "create", "/access/domains", "--realm", id_, "--type", r["type"]] + _args(keys)], None
        return [["pvesh", "set", "/access/domains/" + id_] + _args(changed) + delete], None
    if kind == "usb-mapping":
        if l is None:
            return [["pvesh", "create", "/cluster/mapping/usb", "--id", id_] + _args(keys)], None
        # `map` is replaced as a whole
        if "map" in changed:
            changed["map"] = keys["map"]
        return [["pvesh", "set", "/cluster/mapping/usb/" + id_] + _args(changed) + delete], None
    if kind == "datacenter":
        return [["pvesh", "set", "/cluster/options"] + _args(changed) + delete], None
    if kind == "role":
        verb, path = ("create", "/access/roles") if l is None else ("set", "/access/roles/" + id_)
        return [["pvesh", verb, path] + (["--roleid", id_] if l is None else []) + ["--privs", keys["privs"]]], None
    if kind == "group":
        # members are applied per user ("membership" commands)
        if l is None:
            return [["pvesh", "create", "/access/groups", "--groupid", id_, "--comment", keys["comment"]]], None
        if "comment" in changed:
            return [["pvesh", "set", "/access/groups/" + id_, "--comment", keys["comment"]]], None
        return [], None
    if kind == "pool":
        cmds = []
        if l is None:
            cmds.append(["pvesh", "create", "/pools", "--poolid", id_, "--comment", keys["comment"]])
        elif "comment" in changed:
            cmds.append(["pvesh", "set", "/pools", "--poolid", id_, "--comment", keys["comment"]])
        have = l["keys"] if l else {"vms": "", "storage": ""}
        for member in ("vms", "storage"):
            want_set, have_set = set(filter(None, keys[member].split(","))), set(filter(None, have[member].split(",")))
            if want_set - have_set:
                cmds.append(
                    ["pvesh", "set", "/pools", "--poolid", id_, "--" + member, _csv(",".join(want_set - have_set))]
                )
            if have_set - want_set:
                cmds.append(
                    [
                        "pvesh",
                        "set",
                        "/pools",
                        "--poolid",
                        id_,
                        "--" + member,
                        _csv(",".join(have_set - want_set)),
                        "--delete",
                        "1",
                    ]
                )
        return cmds, None
    if kind == "user":
        if l is None:
            return [
                ["pvesh", "create", "/access/users", "--userid", id_] + _args({k: v for k, v in keys.items() if v})
            ], None
        return [["pvesh", "set", "/access/users/" + id_] + _args(changed)], None
    if kind == "acl":
        path, ugid = id_.rsplit(":", 1)
        if ugid.startswith("@"):
            who = ["--groups", ugid[1:]]
        elif "!" in ugid:
            who = ["--tokens", ugid]
        else:
            who = ["--users", ugid]
        base = ["pvesh", "set", "/access/acl", "--path", path] + who
        want = set(keys["roles"].split(","))
        have = set(l["keys"]["roles"].split(",")) if l else set()
        cmds = []
        if have - want:
            cmds.append(base + ["--roles", _csv(",".join(have - want)), "--delete", "1"])
        if want - have or (l and l["keys"]["propagate"] != keys["propagate"]):
            roles = want if l and l["keys"]["propagate"] != keys["propagate"] else want - have
            cmds.append(base + ["--roles", _csv(",".join(roles)), "--propagate", keys["propagate"]])
        return cmds, None
    return None, "no revert for kind %s" % kind


def _memberships(repo, live, selected):
    """Users whose group list differs, for selected groups: set the full repo list."""

    def groups_of(objs, user):
        return _csv(
            ",".join(o["id"] for o in objs.values() if o["kind"] == "group" and user in o["keys"]["members"].split(","))
        )

    users = set()
    for name, g in repo.items():
        if g["kind"] != "group" or not _selected(name, selected):
            continue
        want = set(filter(None, g["keys"]["members"].split(",")))
        have = set(filter(None, live[name]["keys"]["members"].split(","))) if name in live else set()
        users |= want ^ have
    return [
        {
            "id": "membership:" + u,
            "kind": "membership",
            "argv": ["pvesh", "set", "/access/users/" + u, "--groups", groups_of(repo, u)],
        }
        for u in sorted(users)
        if groups_of(repo, u) != groups_of(live, u)
    ]


def _selected(name, selected):
    return not selected or name in selected


def pve_cfg_commands(repo, live, selected):
    """Revert plan for drifted objects: [{id, argv}] or [{id, argv: [], note}] when refused."""
    planned = []
    for name in sorted(repo):
        if not _selected(name, selected):
            continue
        r, l = repo[name], live.get(name)
        if l is not None and l["type"] == r["type"] and l["keys"] == r["keys"]:
            continue
        cmds, note = _plan(name, r, l, repo)
        if note:
            planned.append({"id": name, "kind": r["kind"], "argv": [], "note": note})
        for argv in cmds or []:
            if len(argv) > 3 or argv[1] == "create":
                planned.append({"id": name, "kind": r["kind"], "argv": argv})
    planned += _memberships(repo, live, selected)
    planned.sort(key=lambda c: KIND_ORDER.index(c["kind"]))
    return [{k: v for k, v in c.items() if k != "kind"} for c in planned]


def pve_cfg_plan_lines(plan):
    """One readable line per planned command or refusal."""
    return ["%s: %s" % (c["id"], shlex.join(c["argv"]) if c["argv"] else "refused, " + c["note"]) for c in plan]


class FilterModule:
    def filters(self):
        return {
            "pve_cfg_parse": pve_cfg_parse,
            "pve_cfg_parse_all": pve_cfg_parse_all,
            "pve_cfg_drift": pve_cfg_drift,
            "pve_cfg_commands": pve_cfg_commands,
            "pve_cfg_plan_lines": pve_cfg_plan_lines,
        }
