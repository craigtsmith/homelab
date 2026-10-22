# cephfs_backup

Nightly backup of CephFS directories to PBS, on util1. The nodes take a daily snapshot of each
directory (`proxmox_node`, `cephfs-snapshot.timer`). This host backs up the newest scheduled
snapshot, read-only, so its cephx user needs no snapshot right. The apps continue to run,
and the copy is crash-consistent.

- Playbook: `playbooks/util_servers.yml` (util_servers)
- Depends on: `common`

## What it does

1. Adds the Proxmox pbs-client repository with an apt pin for the static client only, and
   installs the client.
2. Writes the PBS credentials, the backup script and the systemd service and timer.
3. Enables the timer. A newest snapshot older than `cephfs_backup_max_age_hours` fails the
   run.

`scripts/drift` reports the age of the newest backup.

## Variables

`meta/argument_specs.yml` lists the inputs, with their types and defaults. Ansible
validates them when the role starts. To read them:
`uv run ansible-doc -t role -r roles cephfs_backup`. The values are in `defaults/main.yml`.

Secrets from 1Password (not validated, see the spec header): `pbs-cephfs-backup` (the token secret, written by `pbs_server`).
