# Homelab Automation – Agent Notes

Welcome, future agent! This repo manages a Proxmox‑based homelab with Docker Swarm, database, and Ubuntu VM roles. 
Start by skimming `README.md` for an architectural refresher.

## Workflow

Use `bd` (agent tooling for task management) to coordinate work with other agents that might be working in the codebase:

1. Run `bd list` / `bd ready` when you start.
2. Claim tasks with `bd update <issue> --status in_progress`.
3. Capture findings and changes in the issue notes before you move it to done.

Key patterns in play:

- **Modules before CLI:** Reach for collection modules first. Only the image-prep helpers (`qemu-img`, `virt-customize`) still use raw commands.
- **Temporary Proxmox tokens:** `playbooks/proxmox_nodes.yml` provisions an API token per run (role `proxmox_api_token`) and revokes it afterwards. Build a local `proxmox_api_connection` fact from the exposed variables (`proxmox_api.user`, `proxmox_api.token.id`, `proxmox_api.token.secret` / `proxmox_api_token_secret`) before calling `community.proxmox` modules.
- **Centralized defaults:** Role defaults live under a single namespaced key (`db_server.postgres`, `docker_host.engine`, etc.). Mirror that structure if you introduce new settings.
- **Linting:** Run `ANSIBLE_LOCAL_TEMP=.ansible/tmp ansible-lint ...` before handing off. Galaxy downloads may fail offline—retry with `--offline` in that case.

Getting started quickly:

```bash
bd ready              # see unblocked work items
bd update <id> --status in_progress
ANSIBLE_LOCAL_TEMP=.ansible/tmp ansible-lint <scope>
```

Document any new decisions in `bd` issue notes so the next agent can resume smoothly. Good luck!

## Quality Gates

- **Linting:** Run `ANSIBLE_LOCAL_TEMP=.ansible/tmp ansible-lint`. Warnings are treated as failures; the only tolerated noise today is the ArgsRule message that notes large Proxmox payloads.
- **Syntax checks:** `ANSIBLE_LOCAL_TEMP=.ansible/tmp ansible-playbook --syntax-check playbooks/{docker_hosts,proxmox_nodes,db_servers}.yml`.
- **Fact sharing:** When tasks compute data for other hosts, use `delegate_facts: true`.
- **Modules first:** Prefer purpose-built modules over shell commands and ensure shell usage includes proper idempotency guards.
- **File permissions:** Always specify `owner`, `group`, and `mode` when writing to privileged paths.

> If you change behaviour in a way that invalidates `README.md` or this guide, update them in the same pull request. When work touches sensitive data, prefer storing instructions inside `_private/` so they stay out of version control.
