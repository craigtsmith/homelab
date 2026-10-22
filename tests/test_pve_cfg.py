"""Tests for roles/proxmox_cluster_config/filter_plugins/pve_cfg.py."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = ROOT / "roles/proxmox_cluster_config/files"
_spec = importlib.util.spec_from_file_location(
    "pve_cfg", ROOT / "roles/proxmox_cluster_config/filter_plugins/pve_cfg.py"
)
pve_cfg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pve_cfg)

parse = pve_cfg.pve_cfg_parse
drift = pve_cfg.pve_cfg_drift
commands = pve_cfg.pve_cfg_commands


def objs(**files):
    out = {}
    for dest, text in files.items():
        out.update(parse(text, dest.replace("_", "/").replace("/cfg", ".cfg")))
    return out


def test_section_config():
    o = parse("dir: local\n\tpath /var/lib/vz\n\tshared 0\n\nrbd: ceph_rbd\n\tkrbd 0\n", "storage.cfg")
    assert o["storage:local"] == {"kind": "storage", "id": "local", "type": "dir",
                                  "keys": {"path": "/var/lib/vz", "shared": "0"}}
    assert o["storage:ceph_rbd"]["type"] == "rbd"


def test_untyped_sections_and_repeated_keys():
    o = parse("HAZBT-2\n\tmap id=1:2,node=pve3\n\tmap id=1:2,node=pve1\n", "mapping/usb.cfg")
    assert o["usb-mapping:HAZBT-2"]["keys"]["map"] == ["id=1:2,node=pve1", "id=1:2,node=pve3"]


def test_datacenter():
    o = parse("keyboard: en-us\nmigration: secure,network=10.0.0.0/24\n", "datacenter.cfg")
    assert o["datacenter:options"]["keys"] == {"keyboard": "en-us", "migration": "secure,network=10.0.0.0/24"}


def test_user_cfg_live_file():
    o = parse((FILES / "user.cfg").read_text(), "user.cfg")
    assert o["user:ansible@pam"]["keys"]["comment"] == "Ansible User"
    assert o["token:ansible@pam!ansible"]["keys"]["privsep"] == "1"
    assert o["group:APIUsers"]["keys"]["members"] == "ansible@pam,homepage@pam"
    assert o["pool:VMPool"]["keys"]["vms"] == "112,900"
    assert o["role:HAManager"]["keys"]["privs"] == "Sys.Console"
    # grouped acl lines expand to one object per path and ugid
    assert o["acl:/:@Ops"]["keys"] == {"propagate": "1", "roles": "Administrator"}
    assert o["acl:/:homepage@pam!homepage"]["keys"]["roles"] == "PVEAuditor"


def test_user_cfg_decodes_escaped_text():
    o = parse("group:g::a%3Ab%25c:\n", "user.cfg")
    assert o["group:g"]["keys"]["comment"] == "a:b%c"


def test_drift_reports_missing_changed_unmanaged():
    repo = parse("dir: a\n\tpath /x\n\ndir: b\n\tpath /y\n", "storage.cfg")
    live = parse("dir: a\n\tpath /z\n\tshared 1\n\ndir: c\n\tpath /q\n", "storage.cfg")
    assert drift(repo, live) == [
        "storage:a path: declared=/x live=/z",
        "storage:a shared: declared=<absent> live=1",
        "storage:b: missing",
        "storage:c: unmanaged",
    ]


def test_drift_ignores_key_order():
    assert drift(parse("dir: a\n\tpath /x\n\tshared 0\n", "storage.cfg"),
                 parse("dir: a\n\tshared 0\n\tpath /x\n", "storage.cfg")) == []


def test_commands_storage():
    repo = parse("dir: a\n\tpath /x\n\tcontent iso\n\nnfs: b\n\tserver s\n", "storage.cfg")
    live = parse("dir: a\n\tpath /x\n\tcontent images\n\tshared 1\n", "storage.cfg")
    assert [c["argv"] for c in commands(repo, live, [])] == [
        ["pvesh", "set", "/storage/a", "--content", "iso", "--delete", "shared"],
        ["pvesh", "create", "/storage", "--storage", "b", "--type", "nfs", "--server", "s"],
    ]


def test_commands_type_change_is_refused():
    out = commands(parse("dir: a\n\tpath /x\n", "storage.cfg"), parse("nfs: a\n\tpath /x\n", "storage.cfg"), [])
    assert out == [{"id": "storage:a", "argv": [], "note": "type declared=dir live=nfs; recreate by hand"}]


def test_commands_respect_selection():
    repo = parse("dir: a\n\tpath /x\n\ndir: b\n\tpath /y\n", "storage.cfg")
    assert [c["id"] for c in commands(repo, {}, ["storage:b"])] == ["storage:b"]


def test_commands_job_and_mapping_and_datacenter():
    repo = objs(jobs_cfg="vzdump: n\n\tschedule 02:00\n\tstorage pbs\n",
                mapping_usb_cfg="m\n\tmap id=1:2,node=pve3\n",
                datacenter_cfg="keyboard: en-us\n")
    live = objs(jobs_cfg="vzdump: n\n\tschedule 03:00\n\tstorage pbs\n",
                mapping_usb_cfg="m\n\tmap id=1:2,node=pve1\n",
                datacenter_cfg="keyboard: de\nconsole: html5\n")
    assert [c["argv"] for c in commands(repo, live, [])] == [
        ["pvesh", "set", "/cluster/backup/n", "--schedule", "02:00"],
        ["pvesh", "set", "/cluster/mapping/usb/m", "--map", "id=1:2,node=pve3"],
        ["pvesh", "set", "/cluster/options", "--keyboard", "en-us", "--delete", "console"],
    ]


def test_commands_access_control():
    repo = parse(
        "user:u@pve:1:0:A:B:a@b:::\n"
        "group:g:u@pve:c:\n"
        "pool:p:pc:101::\n"
        "role:r:Sys.Audit,VM.Audit:\n"
        "acl:1:/vms:@g,u@pve!t:r:\n",
        "user.cfg")
    live = parse(
        "user:u@pve:1:0:A:X:a@b:::\n"
        "group:g::c:\n"
        "pool:p:pc:102::\n"
        "role:r:Sys.Audit:\n"
        "acl:1:/vms:@g:r,PVEAuditor:\n",
        "user.cfg")
    assert [c["argv"] for c in commands(repo, live, [])] == [
        ["pvesh", "set", "/access/roles/r", "--privs", "Sys.Audit,VM.Audit"],
        ["pvesh", "set", "/pools", "--poolid", "p", "--vms", "101"],
        ["pvesh", "set", "/pools", "--poolid", "p", "--vms", "102", "--delete", "1"],
        ["pvesh", "set", "/access/users/u@pve", "--lastname", "B"],
        ["pvesh", "set", "/access/users/u@pve", "--groups", "g"],
        ["pvesh", "set", "/access/acl", "--path", "/vms", "--groups", "g", "--roles", "PVEAuditor", "--delete", "1"],
        ["pvesh", "set", "/access/acl", "--path", "/vms", "--tokens", "u@pve!t", "--roles", "r", "--propagate", "1"],
    ]


def test_commands_tokens_are_report_only():
    out = commands(parse("token:u@pve!t:0:1::\n", "user.cfg"), {}, [])
    assert out == [{"id": "token:u@pve!t", "argv": [], "note": "tokens are report-only (creating one mints a secret)"}]


def test_repo_files_parse_without_drift_against_themselves():
    for dest, src in [("datacenter.cfg", "datacenter.cfg"), ("domains.cfg", "domains.cfg"),
                      ("storage.cfg", "storage.cfg"), ("jobs.cfg", "jobs.cfg"),
                      ("user.cfg", "user.cfg"), ("mapping/usb.cfg", "mapping-usb.cfg")]:
        o = parse((FILES / src).read_text(), dest)
        assert o and drift(o, o) == []


def test_plan_lines():
    plan = [{"id": "job:n", "argv": ["pvesh", "set", "/cluster/backup/n", "--notes-template", "{{guestname}} x"]},
            {"id": "token:t", "argv": [], "note": "tokens are report-only"}]
    assert pve_cfg.pve_cfg_plan_lines(plan) == [
        "job:n: pvesh set /cluster/backup/n --notes-template '{{guestname}} x'",
        "token:t: refused, tokens are report-only",
    ]
