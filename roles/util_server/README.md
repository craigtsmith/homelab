# util_server

Database clients and media tools on util1.

- Playbook: `playbooks/util_servers.yml` (util_servers)
- Depends on: `common`

## What it does

1. Installs the Redis, MySQL and PostgreSQL clients (from pgdg, needs `ubuntu_vm_pgdg_repo`), ffmpeg and unzip.

## Variables

`meta/argument_specs.yml` lists the inputs, with their types and defaults. Ansible
validates them when the role starts. To read them:
`uv run ansible-doc -t role -r roles util_server`. The values are in `defaults/main.yml`.
