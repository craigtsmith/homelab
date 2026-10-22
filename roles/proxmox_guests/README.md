# proxmox_guests

The Proxmox guests in `group_vars/all/guests.yml`. The role is create-only: it builds a
missing guest and never changes an existing one. For existing guests it reports drift
against `config`. `scripts/promote-guest` copies the live config into the repo.

- Playbook: `playbooks/proxmox_guests.yml`, `playbooks/test_vm.yml`, `playbooks/test_lxc.yml` (localhost, Proxmox API)
- Depends on: none

## What it does

1. Writes the cloud-init user snippets to the shared CephFS storage.
2. Lists the cluster guests and reports the drift of each declared guest.
3. Builds each missing guest by its `build` key: `clone` (full clone of the node's
   template), `template` (from a cloud image), `lxc` (Debian LXC) or `manual` (only
   reported).

The test playbooks use these entry points:

| Entry point | Use |
| --- | --- |
| `list` | List the cluster guests |
| `clone`, `lxc` | Build one guest (`guest`) |
| `agent_ip`, `lxc_ip` | Wait for the address of a VM or an LXC |
| `destroy` | Destroy a guest. Refuses VMIDs outside `proxmox_guests_test_range` |

## Variables

`meta/argument_specs.yml` lists the inputs, with their types and defaults. Ansible
validates them when the role starts. To read them:
`uv run ansible-doc -t role -r roles proxmox_guests`. The values are in `defaults/main.yml`.

Secrets from 1Password (not validated, see the spec header): `pve-api-ansible`, `cloud-init-serveradmin`, `ceph-vm-access`.
