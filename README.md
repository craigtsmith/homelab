# Homelab Automation

This repository automates provisioning and maintenance tasks for a self-hosted lab built around Proxmox hypervisors, Docker Swarm nodes, database servers, utility hosts, and supporting services. Playbooks are written in Ansible and organised by role so they can be safely re-run as infrastructure evolves.

## Requirements

- Python ≥ 3.13
- `ansible-dev-tools` (provides `ansible`, `ansible-playbook`, `ansible-lint`)
- Required Ansible collections (installed automatically when using `ansible-dev-tools`):
  - `ansible.posix`
  - `community.postgresql`
  - `community.mysql`
  - `community.docker`
  - `community.general`
  - `community.proxmox`

Install dependencies with your preferred workflow:

```bash
# Using uv (recommended)
uv sync

# or using pip
pip install ansible-dev-tools
ansible-galaxy collection install -r collections/requirements.yml
```

## Configuration

Global defaults are environment-driven. Set these before running playbooks, or provide an alternative vars file for CI/testing.

| Variable | Purpose |
| --- | --- |
| `TZ` | Default timezone (`Europe/Amsterdam` if unset). |
| `DNS_HOST` | Upstream resolver used in Docker host configuration. |
| `DOMAIN` | Reserved for future templating (currently unused). |
| `VM_USER_PASS` | Password applied during Ubuntu VM provisioning. |
| `MYSQL_PASSWORD`, `POSTGRES_PASSWORD` | Database admin credentials. |

Generate secrets with `gpg --gen-random --armor 1 32`

## Project Layout

```
homelab/
├── ansible.cfg                  # Inventory & role path defaults
├── homelab.yml                  # Inventory entry point
├── group_vars/                  # Global variables (env-driven)
├── playbooks/                   # Playbooks for Docker, Proxmox, DB, etc.
├── roles/                       # Role implementations
├── collections/requirements.yml # External collection dependencies
├── AGENTS.md                    # Quick-start guide for future assistants
└── _private/                    # Lab-specific content kept out of git by default
```

## Role Conventions

- **Namespaced defaults:** Role variables live under a single top-level key (for example `db_server.postgres.backup_schedule`). Reference them with dot notation inside tasks/templates to keep intent clear.
- **Ephemeral Proxmox auth:** The `proxmox_api_token` role seeds `proxmox_api.*` facts (`user`, `token.id`, `token.secret`). Compose module arguments from these facts—most tasks stash them in a local `proxmox_api_connection` dictionary before calling `community.proxmox.*`.
- **Modules before CLI:** Prefer collection modules (`community.proxmox`, `community.general`, etc.) over direct `qm`/`pveum`/shell commands. Remaining CLI usage is limited to image preparation (`qemu-img`, `virt-customize`) where no module equivalent exists.

## Private Resources

The repository treats any path that contains `private/` or `_private/` as
homelab-specific. These folders are listed in `.gitignore`, so new files placed
inside them stay out of commits unless you explicitly `git add -f` the file.

Typical usage:

- `playbooks/private/` – runbooks and ad-hoc helpers that are tied to your lab. Example: `playbooks/private/upgrade/document_cluster_config.yml` snapshots the current Proxmox configuration before upgrades.
- `roles/private/` – site-specific roles (for example, `roles/private/mount-nas`) that shared playbooks can include when you need to integrate lab-only services.
- `_private/` – static assets and secrets (for example Ceph keyrings or Portainer backups) that private roles copy into place.

When you create new private automation, keep it under one of these paths and document how to run it so future operators can pick up where you left off.

## Features

- **Proxmox automation:** `playbooks/proxmox_nodes.yml` provisions and tunes hypervisor nodes, applies networking tweaks, and enforces consistent VM templates.
- **Ubuntu VM lifecycle:** `playbooks/ubuntu_vms.yml` builds cloud-init images, configures virtio drivers, and applies baseline hardening for guest operating systems.
- **Docker Swarm hosts:** `playbooks/docker_hosts.yml` installs the engine, manages cluster membership, and configures DNS/iptables rules for overlay networking.
- **Database servers:** `playbooks/db_servers.yml` deploys Postgres/MySQL instances with opinionated defaults and secret sourcing from environment variables.

## Usage

Run playbooks from the repository root. Examples:

```bash
# Bootstrap Docker hosts and swarm
ansible-playbook playbooks/docker_hosts.yml

# Configure Proxmox nodes (dry-run first)
ansible-playbook playbooks/proxmox_nodes.yml --check

# Provision database servers
ansible-playbook playbooks/db_servers.yml
```

