# proxmox_node

The Proxmox VE nodes pve1-3. Kernel command line, module and network changes take effect
only after a reboot or `ifreload -a`. This role never reboots and never reloads the
network.

- Playbook: `playbooks/proxmox_nodes.yml` (proxmox_nodes)
- Depends on: `common`, `unattended_upgrades`, `nic_names`

## What it does

1. Configures the apt sources and the Ceph source (`ceph_repo` entry point, also used by
   `ceph_upgrade.yml`), and removes obsolete sources, packages and files.
2. Installs the utility packages.
3. Configures GRUB, kernel modules, sysctl, chrony and the NIC offload fix unit.
4. Configures `/etc/hosts` and the network interfaces.
5. Creates the ansible user with its key and passwordless sudo.
6. Mounts the NAS lab-backup share.
7. Installs the daily CephFS snapshot timer.

## Variables

`meta/argument_specs.yml` lists the inputs, with their types and defaults. Ansible
validates them when the role starts. To read them:
`uv run ansible-doc -t role -r roles proxmox_node`. The values are in `defaults/main.yml`.

Overrides: `group_vars/proxmox_nodes.yml`, and `host_vars/pve1-3.yml` (Ceph address, ansible user key).
