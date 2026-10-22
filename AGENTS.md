# AGENTS.md

Rules for AI agents that work on this repo. Files for agents are in `docs/agents/`:

- `docs/agents/handover.md`: the current state and the next steps.
- `docs/agents/backlog.md`: the open work.
- `docs/agents/learnings.md`: mistakes from earlier sessions. Read it before you start.

## What this repo is

This repo is the Ansible code for craig's live homelab. Real services run on it.

- A Proxmox VE 9 cluster `homelab` with three nodes (pve1-3). Ceph Tentacle runs on the
  nodes, with cephx `aes256k` keys only.
- Proxmox Backup Server `pbs` (VM 900).
- Ubuntu 24.04 VMs: util1, tailscale1, db1 and the docker1-3 swarm.
- Debian 13 LXCs: dns1 (LXC 118, .53) and dns2 (LXC 119, .54) run AdGuard Home. proxy1
  (LXC 117, .27) runs nginx.
- appbox1, a VPS at Appbox in Amsterdam, runs the download services (`docs/appbox.md`).

Apps run as Portainer stacks on the swarm. proxy1 serves every `*.<domain>` name.

## Safety rules

- Do not change running services without craig's explicit approval for that action.
  Approval for one action does not apply to the next action.
- You can run read-only commands against hosts. Every command that writes needs approval.
- Run every playbook against production with `--check --diff` first, one host at a time.
  Start with the canary: docker3 for VMs, pve3 for nodes. Do a real run only after craig
  reads the check run and approves.
- A role is correct when a check run against production reports `changed=0`.
- The live state wins by default. A routine run must not revert manual changes. On drift,
  craig selects per object: revert (apply the repo) or promote (copy the live state into the
  repo). Details: `README.md`, "Drift handling".
- Use per-object API changes, not copies of full files. Never use `blockinfile` on
  `/etc/pve` files, because PVE deletes the marker comments.
- Use readable IDs, never IDs that a UI generates.
- Throwaway VMs and LXCs use VMIDs 800-899 only (`proxmox_guests_test_range`). The destroy
  task refuses all other IDs.
- The repo is public. Keep sensitive data out of tracked files: the domain, e-mail
  addresses, account names, public IPs, tailnet IPs, SSH ports and device IDs. IPs in the
  private ranges are permitted.
- Put such values in the gitignored `inventories/prod/group_vars/all/private.yml`, and use
  the variable. Add each new variable to `private.yml.example` (in the same directory) and to
  the assert in `playbooks/common/validate_env.yml`.
- In docs, write `<domain>`. The `/etc/pve` files in `proxmox_cluster_config` write
  `${domain}`.
- Never print secrets. Tasks that touch secrets use `no_log: true`. Compare secret values by
  hash, never by printing them.
- Before you delete data on a host, make a backup (PBS for guests, a
  `proxmox-backup-client` host backup for nodes). Tell craig what the deletion removes.

## How to run

```bash
direnv allow            # loads .env: OP_SERVICE_ACCOUNT_TOKEN
uv sync
uv run ansible-galaxy collection install -r requirements.yml
uv run ansible-playbook playbooks/<name>.yml --check --diff --limit <host>
uv run ansible-lint
uv run pytest tests       # filter plugin tests
uv run ruff check && uv run ruff format --check && uv run basedpyright   # Python
scripts/drift [pattern]   # every playbook in check mode, one host at a time; _private/drift/<date>/
```

- Secrets: 1Password vault `homelab` (service account, read and write). `README.md` lists
  the items.
- Proxmox API: token `ansible@pam!ansible` (item `pve-api-ansible`) with privilege
  separation. The token has PVEAuditor, PVEVMAdmin, PVEDatastoreAdmin and HAManager on `/`
  (`Sys.Console`, for HA writes), and PVESDNUser on `/sdn/zones`. `ansible@pam` is
  Administrator and has PVEVMAdmin on `/vms`.
- SSH: pve1-3 and pbs as root. Ubuntu VMs as `serveradmin` with sudo without a password.
  The host aliases are in `~/.ssh/config`.
- Docker runs on the controller. You can use Debian containers for fast role tests.
- Portainer API: `https://portainer.<domain>/api`, header `X-API-Key` from `portainer-api`,
  swarm endpoint 7. The stacks are templates in `stacks/swarm/`. `group_vars/all/stacks.yml`
  lists them with their env. `playbooks/portainer_stacks.yml` compares them (env by hash) and
  updates them with `pullImage: false`. To run one stack only, add
  `-e '{"portainer_stacks_only": [name]}'`.
- Stacks that are not ready for the repo are in the gitignored `stacks/_private/`.
- Proxy hosts: edit `proxy_server_hosts` in `group_vars/proxy_servers.yml`, then run
  `proxy_servers.yml`. There is no UI.
- DNS rewrites, filters and clients: edit `group_vars/dns_servers.yml`, then run
  `dns_servers.yml`. A UI edit on dns1 or dns2 is drift.
- AdGuard API: `http://192.168.100.53/control` (dns2: `.54`), Basic auth from `adguard-admin`
  (fields `username`, `password`). Send each API change to both servers.
- Stateful migrations (swarm, db1): record the replica counts. Scale every app service to 0
  (all stacks except `portainer-traefik` and `rustfs`). Then migrate, make sure that the
  result is correct, and scale back up. Docker on the nodes needs `sudo`.

## Conventions

- craig follows progress in `docs/agents/backlog.md`. Update it in the same commit as the
  work. Tick finished items, add a ticked sub-item for each finished part of a step, write
  what remains on items that are not finished, and add new findings as open items.
- Update `docs/agents/handover.md` at the same time. At the end of a session, remove the
  ticked items from the backlog. `CHANGELOG.md` and git history keep them.
- Add each new learning to `docs/agents/learnings.md`, in the correct section. Do not put
  learnings in other files.
- Use conventional commits. Keep them short, and commit often. End each message with
  `Co-Authored-By: agent smith <craigts-agent@users.noreply.github.com>`. craig merges and
  pushes. Never push.
- Role variables are flat and have the role name as prefix (`ubuntu_vm_*`). Overrides are in
  `inventories/prod/group_vars` and `host_vars`.
- Each role has a `README.md` (purpose, what it does) and a `meta/argument_specs.yml` (the
  inputs). Put role descriptions in the README, not in header comments. When you add a
  variable, add it to the spec with the same `default` (`uv run pytest tests` checks this).
  Leave out 1Password lookups and values from facts, and name them in the spec header.
- Write `tasks_from: <name>` without `.yml`, and give each entry point that a playbook calls
  its own spec. With the suffix, Ansible does not validate.
- A major-upgrade playbook is `playbooks/<component>_upgrade.yml` (`ceph_upgrade.yml`). Put
  the release names and the per-release facts in variables, never in the playbook name. For
  the next release, read its Proxmox upgrade guide, update the variables and add new steps.
- Stateful resources are create-only: the swarm, Portainer stacks, the MySQL admin user and
  Proxmox guests.
- You can delete files in the gitignored `_private/`, `roles/private/` and
  `playbooks/private/` when they change Ansible runs. The old files are in
  `~/Projects/homelab-private-archive-2026-10-21.tar.gz`.
- If you need more than one input from craig, use AskUserQuestion. Never open windows or take
  the keyboard focus.
