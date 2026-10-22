# Homelab

This repo holds the Ansible code for a homelab:

- a Proxmox VE cluster with three nodes and Ceph,
- a Docker Swarm, a database server, DNS and a reverse proxy,
- Proxmox Backup Server and a remote VPS.

Ansible builds and maintains every host and guest. A check run against production
reports `changed=0`.

This is the working repo of one real lab, published as a reference. The private IP
addresses, host names and versions are the real ones. The domain, e-mail addresses, public
and tailnet addresses and secrets are not in git.

## What runs

- **pve1-3:** Proxmox VE 9.2 cluster `homelab` with Ceph Tentacle (3 mons, 3 OSDs, CephFS).
  HA manages every guest.
- **Ubuntu 24.04 VMs:** docker1-3 (Docker Swarm, Portainer, Traefik), db1 (PostgreSQL 17,
  MySQL 8.4, Valkey 8.0), util1 (CephFS backup) and tailscale1 (Tailscale subnet router).
- **Debian 13 LXCs:** dns1 and dns2 (AdGuard Home), proxy1 (nginx and certbot).
- **pbs:** Proxmox Backup Server 4.2. Its datastore is on a Synology NAS.
- **appbox1:** an Ubuntu 24.04 VPS in Amsterdam on the tailnet. It runs the download
  services as a compose stack.
- **Swarm stacks:** homepage, karakeep, media-server, paperless and rustfs
  (`stacks/swarm/`).

[`docs/architecture.md`](docs/architecture.md) has diagrams of the hosts, networks, storage,
request path and backup flow.

## Getting started

You need Python 3.13, [uv](https://docs.astral.sh/uv/), the 1Password CLI (`op`) and
[direnv](https://direnv.net/).

```bash
cp .env.example .env                    # OP_SERVICE_ACCOUNT_TOKEN for the 1Password vault
cp inventories/prod/group_vars/all/private.yml.example inventories/prod/group_vars/all/private.yml
direnv allow
uv sync
uv run ansible-galaxy collection install -r requirements.yml
```

Then write your values in `inventories/prod/group_vars/all/private.yml`. This file is
gitignored. It holds the values that are not in the public repo:

- the domain,
- the host name and SSH port of appbox1,
- the tailnet addresses,
- the device IDs of the AdGuard client "Personal Devices".

Every playbook stops if one of these values is missing. The group and host settings are in
`inventories/prod/group_vars/` and `host_vars/`.

Run every playbook with `--check --diff` first, one host at a time:

```bash
uv run ansible-playbook playbooks/ubuntu_vms.yml --check --diff --limit docker3
scripts/drift                     # every playbook in check mode; logs in _private/drift/<date>/
uv run ansible-lint
uv run pytest tests               # tests for the filter plugins and scripts
uv run ruff check && uv run ruff format --check   # Python lint and format
uv run basedpyright               # Python type check (config in pyproject.toml)
```

## Secrets

Ansible reads the secrets from the 1Password vault `homelab`. It uses the
`community.general.onepassword` lookup and a service account token. Tasks that touch secrets
set `no_log: true`. Drift checks compare secrets by hash.

| 1Password item | Use |
| --- | --- |
| `ubuntu-vm-user` | `serveradmin` password in cloud-init (`vm_user_pass`) |
| `cloud-init-serveradmin` | `serveradmin` password hash in the cloud-init snippet |
| `db1-mysql`, `db1-postgres` | MySQL admin user and PostgreSQL admin role `db1` |
| `pve-api-ansible` (field `credential`) | Proxmox API token `ansible@pam!ansible` (privilege separation, with PVEAuditor, PVEVMAdmin, PVEDatastoreAdmin and HAManager on `/`) |
| `pve-root` | root@pam password. Only used to bootstrap a node that is not in a cluster |
| `ceph-vm-cephfs` | CephFS key `client.vm_cephfs` (aes256k) for the kernel mounts on the VMs (`ceph_client`) |
| `ceph-vm-access` | the old `client.vm_access` key (deleted from Ceph on 2026-10-19). The cloud-init snippet still holds it, so keep the item |
| `pbs-root` (fields `password`, `email`) | PBS root@pam for the PVE storage `pbs`, and the notification e-mail |
| `pbs-cephfs-backup` (field `credential`) | PBS token `cephfs-backup@pbs!util1` for the CephFS backup from util1. `pbs_servers.yml` writes it when it creates the token |
| `tailscale-authkey`, `tailscale-authkey-appbox` (field `credential`) | `tailscale up` on tailscale1 and appbox1. Only used when the node is logged out |
| `adguard-admin` (fields `username`, `password`, `bcrypt`) | AdGuard Home web UI and API on dns1 and dns2. `bcrypt` goes into `AdGuardHome.yaml` |
| `cloudflare-dns` (field `credential`) | Cloudflare API token for certbot DNS-01 on proxy1 |
| `portainer-api` (field `credential`) | Portainer API token (`X-API-Key`) for `portainer_stacks` |
| `paperless-secret-key`, `paperless-db` | stack env `PAPERLESS_SECRET_KEY` and `PAPERLESS_DBPASS` of `paperless` |
| `karakeep-meili-master-key`, `karakeep-nextauth-secret`, `karakeep-openai-api-key` | stack env of `karakeep` |
| `rustfs-root` | RustFS access key (username) and secret key (password), stack env of `rustfs` |
| `appbox-prowlarr-pg` | PostgreSQL password of prowlarr on appbox1 (compose `.env`) |
| `appbox1` | appbox1 VM password |

## Playbooks

| Playbook | Hosts | What it manages |
| --- | --- | --- |
| `proxmox_nodes.yml` | pve1-3 | apt sources, the Debian ZFS pin, the no-nag hook, NIC name pins, GRUB, modules, sysctl, CPU governor, chrony, NIC offload unit, hosts, interfaces, the `ansible` user, the NAS backup mount and daily CephFS snapshots |
| `pbs_servers.yml` | pbs | apt sources, the Debian ZFS pin, NIC name pin, hosts, interfaces, NAS mounts, datastore, prune and verify config, users, namespaces, backup tokens (secret to 1Password) and their ACLs |
| `proxmox_cluster_bootstrap.yml` | pve1-3 | creates the cluster `homelab` and adds the nodes. Nodes in the cluster stay as they are |
| `proxmox_cluster_config.yml` | pve1 (manager) | the cluster config in `/etc/pve`: storages, the vzdump job, users, groups, roles, pools, ACLs, HA resources and rules. See "Drift handling" |
| `proxmox_guests.yml` | localhost (Proxmox API) | a drift report for the guests. It creates missing VMs, LXCs and templates, and writes the shared cloud-init snippet. To promote a live guest config, run `uv run scripts/promote-guest <vmid>` |
| `ubuntu_vms.yml` | Ubuntu VMs | base packages, timezone, hostname, DNS override, network tuning, NAS and scratch mounts, the CephFS client |
| `docker_hosts.yml` | docker1-3 | pinned Docker Engine, `daemon.json`, bind-mount directories for stacks (`docker_host_dirs`), swarm membership, the Portainer and Traefik bootstrap |
| `portainer_stacks.yml` | localhost (Portainer API) | the swarm stacks in `stacks/swarm/`. It compares them with Portainer (env by hash) and updates them with `pullImage: false` |
| `db_servers.yml` | db1 | PostgreSQL 17 (pgdg), MySQL 8.4 LTS, Valkey 8.0 (Percona), hourly dumps to `/var/backups` and the NAS |
| `util_servers.yml` | util1 | database client tools and the nightly CephFS backup to PBS |
| `tailscale_routers.yml` | tailscale1 | the Tailscale subnet router: package, forwarding, UDP GRO hook, prefs, and the login with the tagged auth key when logged out (tag `tailscale_login`) |
| `dns_servers.yml` | dns1, dns2 | AdGuard Home (pinned release). `AdGuardHome.yaml` comes from the inventory: upstreams, filters, user rules, rewrites and clients |
| `proxy_servers.yml` | proxy1 | nginx and certbot (Cloudflare DNS-01). The proxy hosts come from the inventory. Certificates are issued one time, then `certbot.timer` renews them |
| `appbox_servers.yml` | appbox1 | ufw, Tailscale, the NAS mount over the tailnet, Docker and the compose stack `media-remote` (`stacks/appbox1/`) |
| `patch.yml` | every host (`--limit`, `--tags`) | the monthly upgrade and rolling reboot (`docs/operations.md`, "Patching") |
| `ceph_upgrade.yml` | pve1-3 | a Ceph major upgrade, stage by stage (`docs/operations.md`) |
| `test_vm.yml`, `test_lxc.yml` | throwaway guests (VMID 800-899) | applies the roles of a host to a test guest (`-e test_as=<host>`) |
| `promote.yml` | one host (`--limit`) | copies one live file into the repo file that deploys it. It writes only to the repo |

## Drift handling

The full procedure, with a diagram, is in [`docs/drift.md`](docs/drift.md).

The live state wins by default. A routine run never reverts manual changes. On drift, select
one of these actions per object:

- **Report:** `scripts/drift [pattern]` runs every playbook with `--check --diff`, one host
  at a time. It writes logs and `summary-<HHMM>.md` to `_private/drift/<date>/`.
- **Revert** (apply the repo): do a real playbook run for host roles and stacks. For cluster
  objects, add `-e proxmox_cluster_config_write=true` and `proxmox_cluster_config_only`.
  Guests are report-only.
- **Promote** (copy the live state into the repo): for the cluster config, add
  `-e proxmox_cluster_config_capture=true`, then keep the hunks with `git add -p`. For a
  guest, run `scripts/promote-guest <vmid>`. For files that a host role copies without
  change, run `playbooks/promote.yml`.

`proxmox_cluster_config.yml` reports drift per object. A revert changes one object at a time
with `pvesh` and never deletes. Live objects that are not in the repo show as unmanaged.
`proxmox_cluster_config_only` limits a revert to objects (`storage:pbs`, `ha:docker1`), and a
promote to files. HA comes from the `ha` key in `guests.yml`.

The role never copies full `/etc/pve` files. `blockinfile` does not work there: PVE deletes
comment lines, and thus the markers, when it writes a file again (`PVE/SectionConfig.pm`
`parse_config` skips `^\s*#`). Use readable IDs (`nightly-pbs`, `<name>-affinity`), never IDs
that the UI generates. The `/etc/pve` files in `roles/proxmox_cluster_config/files/` write
the domain as `${domain}`.

## Role conventions

- **Flat variables with a prefix:** role variables have the name `<role>_<setting>` (for
  example `ubuntu_vm_nic_queues`). Overrides are in `inventories/prod/group_vars` or
  `host_vars`.
- **Match production, never disturb it:** roles describe what is deployed. A role never
  starts a package upgrade, a reboot or a network reload. Handlers only reload the service
  whose config file changed.
- **Create-only for stateful resources:** the swarm init and join, the Portainer bootstrap
  stack, the MySQL admin user and the Proxmox guests. Ansible creates them when they do not
  exist, and does not touch them after that.
- **Check before every run:** `--check --diff --limit <host>` must report `changed=0`
  against production before a real run. Tasks that only read state set
  `check_mode: false` and `changed_when: false`.
- **Documented and validated inputs:** each role has a `README.md` and a
  `meta/argument_specs.yml`. Ansible validates the inputs when the role starts.
  `uv run ansible-doc -t role -r roles <role>` shows them. `tests/test_argument_specs.py`
  keeps the spec defaults equal to `defaults/main.yml`.

## Repository layout

```
├── ansible.cfg                  # inventory, role and collection paths
├── inventories/prod/
│   ├── hosts.yml                # groups and hosts
│   ├── group_vars/              # variables per group. all/private.yml is gitignored,
│   │                            # all/private.yml.example is its template
│   └── host_vars/               # connection and identity per host
├── playbooks/                   # one playbook per host group, plus patch, upgrade and test
├── roles/                       # the roles
├── stacks/                      # swarm/ (Portainer stacks), appbox1/ (compose),
│                                # _private/ (gitignored, not ready to publish)
├── scripts/drift                # drift report: every playbook in check mode
├── scripts/drift-audit/         # read-only host audit to compare rebuilds
├── scripts/promote-guest        # copies a live guest config into guests.yml
├── tests/                       # pytest for the filter plugins and scripts
├── docs/                        # architecture, operations, rebuild, appbox, move
├── docs/agents/                 # handover, backlog and learnings for AI agents
├── AGENTS.md                    # rules for AI agents
└── CHANGELOG.md                 # history up to the public initial commit
```

Paths that contain `private/` or `_private/` are gitignored. They hold run logs, audits and
helpers for this lab only.

## Documentation

- [`docs/architecture.md`](docs/architecture.md): hosts, networks, storage, request path
  and backup flow.
- [`docs/operations.md`](docs/operations.md): how to rebuild a guest next to the old one,
  the CephFS backup and restore, a Ceph major upgrade and patching.
- [`docs/drift.md`](docs/drift.md): how to find drift, and how to revert or promote it.
- [`docs/rebuild.md`](docs/rebuild.md): how to rebuild the full lab from bare hardware.
- [`docs/appbox.md`](docs/appbox.md): appbox1, the remote VPS for downloads.
- [`docs/move.md`](docs/move.md): how to shut down and move the lab.
- [`CHANGELOG.md`](CHANGELOG.md): what changed and when, from the git history before the
  squash.
- [`docs/agents/`](docs/agents/): the handover, backlog and learnings for AI agents.

## License

GPL-3.0. See [`LICENSE`](LICENSE).
