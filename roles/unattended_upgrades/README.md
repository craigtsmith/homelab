# unattended_upgrades

Daily security updates, without reboots. Everything else (point releases, Proxmox, Docker,
pgdg, MySQL) waits for `playbooks/patch.yml`.

- Playbook: none (a dependency of `debian_lxc`, `pbs_server`, `proxmox_node` and `ubuntu_vm`)
- Depends on: none

## What it does

1. Installs unattended-upgrades and enables the daily run.
2. Limits it to the security origins of the distribution, and turns off the reboot.

## Variables

`meta/argument_specs.yml` lists the inputs, with their types and defaults. Ansible
validates them when the role starts. To read them:
`uv run ansible-doc -t role -r roles unattended_upgrades`. The values are in `defaults/main.yml`.
