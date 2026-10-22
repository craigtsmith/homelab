# pbs_server

The Proxmox Backup Server VM (pbs). The datastore uses the existing chunk store on the NAS
share.

- Playbook: `playbooks/pbs_servers.yml` (pbs_servers)
- Depends on: `common`, `unattended_upgrades`, `nic_names`

## What it does

1. Configures the apt sources and hooks, and the QEMU guest agent.
2. Configures `/etc/hosts` and the network interfaces (applied at a reboot or `ifreload -a`).
3. Mounts the NAS shares.
4. Writes the datastore, prune and verify jobs.
5. Creates the users, the namespaces, the backup tokens and their ACLs. A token whose
   secret is missing from `token.shadow` is generated again. Its secret goes to its
   1Password item.

## Variables

`meta/argument_specs.yml` lists the inputs, with their types and defaults. Ansible
validates them when the role starts. To read them:
`uv run ansible-doc -t role -r roles pbs_server`. The values are in `defaults/main.yml`.

Secrets from 1Password (not validated, see the spec header): `pbs-root` (field `email`), and the item of each token in `pbs_server_tokens` (written).
