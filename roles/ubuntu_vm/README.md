# ubuntu_vm

Base for the Ubuntu 24.04 VMs (docker1-3, db1, util1, tailscale1).

- Playbook: `playbooks/ubuntu_vms.yml` (ubuntu_vms)
- Depends on: `common`, `unattended_upgrades`

## What it does

1. Adds the pgdg repository when `ubuntu_vm_pgdg_repo` is true.
2. Installs the base packages and the QEMU guest agent. `apt upgrade` runs only when
   `ubuntu_vm_upgrade` is true.
3. Sets the timezone and the hostname, and keeps the hostname across cloud-init runs.
4. Configures split DNS for the lab domain.
5. Tunes the network: sysctls, and NIC queues and RPS with oneshot units.
6. Adds the static routes and the mounts.

## Variables

`meta/argument_specs.yml` lists the inputs, with their types and defaults. Ansible
validates them when the role starts. To read them:
`uv run ansible-doc -t role -r roles ubuntu_vm`. The values are in `defaults/main.yml`.

Overrides: `group_vars/docker_hosts.yml`, `group_vars/db_servers.yml`, `group_vars/util_servers.yml`, `host_vars/db1.yml`, `host_vars/util1.yml`.
