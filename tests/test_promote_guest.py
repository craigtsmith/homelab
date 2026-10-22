"""Tests for scripts/promote-guest."""

import importlib.machinery
import importlib.util
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_loader = importlib.machinery.SourceFileLoader("promote_guest", str(ROOT / "scripts/promote-guest"))
_spec = importlib.util.spec_from_loader("promote_guest", _loader)
assert _spec is not None
pg = importlib.util.module_from_spec(_spec)
_loader.exec_module(pg)

SRC = """\
---
# header comment
proxmox_guests:
  - vmid: 101
    name: docker1
    node: pve1
    type: qemu
    ha: {node: pve1}
    config:
      cores: "6"
      memory: "32768"
      onboot: "1"
  # util1 comment
  - vmid: 111
    name: util1
    node: pve3
    type: qemu
    config:
      cores: "6"
"""


def run(live, node="pve1", vmid=101):
    y = pg._yaml()
    doc = y.load(SRC)
    changed = pg.promote(doc, vmid, live, node, {"digest", "vmgenid"})
    buf = io.StringIO()
    y.dump(doc, buf)
    return changed, buf.getvalue()


def test_no_change_keeps_file():
    changed, out = run({"cores": 6, "memory": "32768", "onboot": 1, "digest": "x"})
    assert changed == [] and out == SRC


def test_changed_added_removed_keys():
    changed, out = run({"cores": 8, "memory": "32768", "tags": "a;b", "vmgenid": "y"})
    assert changed == ["cores", "onboot", "tags"]
    assert '      cores: "8"\n      memory: "32768"\n      tags: "a;b"\n  # util1 comment\n' in out
    assert "# header comment" in out and "ha: {node: pve1}" in out


def test_node_and_multiline_description():
    changed, out = run({"cores": "6", "memory": "32768", "onboot": "1", "description": "# Title\nline\n"}, node="pve2")
    assert changed == ["node", "description"]
    assert "    node: pve2\n" in out
    assert "      description: |-\n        # Title\n        line\n" in out


def test_comment_between_guests_stays_last():
    changed, out = run({"cores": "6", "memory": "32768", "onboot": "1", "vga": "serial0"})
    assert changed == ["vga"]
    assert '      onboot: "1"\n      vga: "serial0"\n  # util1 comment\n' in out
