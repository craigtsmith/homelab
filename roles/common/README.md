# common

Adds the controller's public key (`ssh_public_key`) to the become user (root). Most roles
depend on it.

- Playbook: none (a dependency)
- Depends on: none

## What it does

1. Adds the key to `authorized_keys` of root, when `common_authorized_key` is true.

## Variables

`meta/argument_specs.yml` lists the inputs, with their types and defaults. Ansible
validates them when the role starts. To read them:
`uv run ansible-doc -t role -r roles common`. The values are in `defaults/main.yml`.

Overrides: `common_authorized_key: false` in `group_vars/proxmox_nodes.yml`.
