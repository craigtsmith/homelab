# nic_names

Keeps the NIC names across kernel updates. Each NIC with a PCI or virtio address gets a
systemd `.link` file that matches its MAC.

- Playbook: none (a dependency of `pbs_server` and `proxmox_node`)
- Depends on: none

## What it does

1. Writes one `.link` file for each NIC, with the name that the NIC has now.

In containers there are no such NICs, so the task does nothing.

## Variables

`meta/argument_specs.yml` lists the inputs, with their types and defaults. Ansible
validates them when the role starts. To read them:
`uv run ansible-doc -t role -r roles nic_names`. The values are in `defaults/main.yml`.
