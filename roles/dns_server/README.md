# dns_server

AdGuard Home on dns1 and dns2. `AdGuardHome.yaml` is rendered from the inventory, so an edit
in the UI is drift. A run reverts it, unless you promote it into the inventory first.

- Playbook: `playbooks/dns_servers.yml` (dns_servers)
- Depends on: `debian_lxc`

## What it does

1. Installs the pinned AdGuard Home release, when the installed version differs.
2. Reports the drift of `AdGuardHome.yaml`, with the password hash masked.
3. Writes `AdGuardHome.yaml` and the systemd unit, and starts AdGuard Home.

## Variables

`meta/argument_specs.yml` lists the inputs, with their types and defaults. Ansible
validates them when the role starts. To read them:
`uv run ansible-doc -t role -r roles dns_server`. The values are in `defaults/main.yml`.

Overrides: `group_vars/dns_servers.yml` (upstreams, filters, rewrites, clients).

Secrets from 1Password (not validated, see the spec header): `adguard-admin` (field `bcrypt`).
