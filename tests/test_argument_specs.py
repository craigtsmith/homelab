"""meta/argument_specs.yml of every role agrees with its defaults/main.yml.

Ansible takes a role variable's value from defaults/main.yml. The `default` in the
spec only documents it (ansible-doc), so the two must not drift apart.
"""

from pathlib import Path

import pytest
from ansible.parsing.utils.yaml import from_yaml

ROOT = Path(__file__).resolve().parents[1]
SPECS = sorted(ROOT.glob("roles/*/meta/argument_specs.yml"))


def _load(path):
    return from_yaml(path.read_text(), file_name=str(path)) or {}


def _options(spec_path):
    for entry, spec in _load(spec_path)["argument_specs"].items():
        for name, opt in (spec.get("options") or {}).items():
            yield entry, name, opt


def test_every_role_has_a_spec():
    roles = {p.name for p in (ROOT / "roles").iterdir() if (p / "tasks").is_dir()}
    assert roles == {p.parent.parent.name for p in SPECS}


@pytest.mark.parametrize("spec_path", SPECS, ids=lambda p: p.parent.parent.name)
def test_spec_defaults_match_role_defaults(spec_path):
    dpath = spec_path.parent.parent / "defaults/main.yml"
    defaults = _load(dpath) if dpath.exists() else {}
    for entry, name, opt in _options(spec_path):
        where = "%s %s" % (entry, name)
        if name in defaults:
            assert "default" in opt, "%s: add default from defaults/main.yml" % where
            assert opt["default"] == defaults[name], "%s: default differs from defaults/main.yml" % where
            assert not opt.get("required"), "%s: required, but defaults/main.yml sets it" % where
        else:
            assert "default" not in opt, "%s: default without a value in defaults/main.yml" % where
