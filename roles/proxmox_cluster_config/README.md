# proxmox_cluster_config

The cluster-wide config in `/etc/pve` (pmxcfs), per object. The files in `files/` are copies
of the live cluster from 2026-10-14. `filter_plugins/pve_cfg.py` parses them into objects.
The files write the domain as `${domain}`, and the role replaces it on read. HA resources and
rules come from the `ha` key in `guests.yml` (`tasks/ha.yml`). The secrets in
`/etc/pve/priv` (token secrets, keyrings) are not managed, except the PBS password.

- Playbook: `playbooks/proxmox_cluster_config.yml` (pve1, the manager)
- Depends on: none

## What it does

The role has three modes. See `docs/drift.md`.

| Mode | Variable | Result |
| --- | --- | --- |
| Report (default) | none | Drift per object. Unmanaged live objects are listed. |
| Revert | `proxmox_cluster_config_write: true` | `pvesh create` or `set` per object. Never deletes. |
| Promote | `proxmox_cluster_config_capture: true` | Copies the live files into `files/` |

Do not set revert and promote in the same run. `proxmox_cluster_config_only` limits a run
to some objects or files.

## Variables

`meta/argument_specs.yml` lists the inputs, with their types and defaults. Ansible
validates them when the role starts. To read them:
`uv run ansible-doc -t role -r roles proxmox_cluster_config`. The values are in `defaults/main.yml`.

HA resource-affinity rules: `group_vars/all/guests.yml`.

Secrets from 1Password (not validated, see the spec header): `pve-api-ansible`, `pbs-root` (field `password`).
