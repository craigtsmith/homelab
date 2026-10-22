# patch

The monthly upgrade and reboot (`playbooks/patch.yml`) and the Ceph major upgrade
(`playbooks/ceph_upgrade.yml`). Everything runs one host at a time. Nothing reboots unless
the reboot tasks run. See `docs/operations.md`, "Patching".

- Playbook: `playbooks/patch.yml`, `playbooks/ceph_upgrade.yml`
- Depends on: none

## What it does

The playbooks include one task file for each stage (`tasks_from`). Each file is an entry
point with its own argument spec:

| Entry point | Stage |
| --- | --- |
| `main` | A guest's whole run: `packages`, then `guest_reboot` |
| `packages` | dist-upgrade after a dry run. Stops on removals outside `patch_allowed_removals` and on a new major |
| `reboot_needed` | Decides if the host needs a reboot (`patch_reboot`) |
| `guest_reboot` | Reboots a VM or LXC. Docker hosts are drained first. pbs waits for its running tasks |
| `node_reboot` | Reboots a node. Docker VMs ride, other guests move with HA |
| `ceph_restart` | Restarts the node's mon or mgr when a newer version is installed |
| `swarm_stop`, `swarm_start` | Swarm-down mode (`patch_stop_swarm`) around the node reboots |
| `ceph_major_check` | Ceph major upgrade: starting point, mgr modules, noout |
| `ceph_major_packages` | Ceph major upgrade: new repository and dist-upgrade on one node |
| `ceph_restart_osd`, `ceph_restart_mds` | Ceph major upgrade: OSD and MDS restarts |
| `ceph_major_finish` | Ceph major upgrade: require-osd-release, unset noout |

## Variables

`meta/argument_specs.yml` lists the inputs, with their types and defaults. Ansible
validates them when the role starts. To read them:
`uv run ansible-doc -t role -r roles patch`. The values are in `defaults/main.yml`.

Overrides: `group_vars/proxmox_nodes.yml` and `group_vars/pbs_servers.yml` (`patch_majors`, `patch_allowed_removals`, `patch_purge`).
