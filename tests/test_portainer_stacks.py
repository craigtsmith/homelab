"""Tests for roles/portainer_stacks/filter_plugins/stacks.py."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("stacks", ROOT / "roles/portainer_stacks/filter_plugins/stacks.py")
assert _spec is not None and _spec.loader is not None
stacks = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stacks)

pairs = stacks.portainer_stacks_env_pairs
mask = stacks.portainer_stacks_mask


def test_env_pairs_hide_values_and_sort():
    out = pairs({"B": "secret", "A": "x"})
    assert [p.split("=")[0] for p in out] == ["A", "B"]
    assert not any("secret" in p for p in out)


def test_env_pairs_differ_only_where_values_differ():
    diff = set(pairs({"A": "1", "B": "2"})) ^ set(pairs({"A": "1", "B": "3", "C": "4"}))
    assert sorted({p.split("=")[0] for p in diff}) == ["B", "C"]


def test_mask_assignment_lines_and_long_values():
    text = "      PASS: word\n      - KEY=abcdefghijklmnop\n      url: u:abcdefghijklmnop@h\n"
    out = mask(text, {"PASS": "word", "KEY": "abcdefghijklmnop"})
    assert out == "      PASS: <PASS>\n      - KEY=<KEY>\n      url: u:<KEY>@h\n"


def test_mask_leaves_short_values_elsewhere_and_env_references():
    # masking a common word everywhere would show where it occurs
    text = "image: app/word:1\n      PASS: ${PASS}\n"
    assert mask(text, {"PASS": "word"}) == text
