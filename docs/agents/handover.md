# Handover

State on 2026-10-21. Read `AGENTS.md` first. Then read this file,
`docs/agents/learnings.md` and `docs/agents/backlog.md` (open work only).

## Where things are

- Phases 1 (drift audit) and 2 (the repo matches production) are done. In phase 3, steps
  0-10 and the old guest cleanup (9e) are done.
- Ansible builds every guest. `playbooks/patch.yml` patched every host on 2026-10-16/17.
  Monthly runs use ride mode.
- Ceph runs Tentacle 20.2.4 with cephx `aes256k` only, and is HEALTH_OK. The rebuild
  runbook is `docs/rebuild.md`, and it installs Tentacle. The roles do not support focal.

### Hosts

- Ubuntu 24.04 VMs: util1 (VMID 111, pve3, .12), tailscale1 (112, pve2, .32, the only subnet
  router), docker1 (115, pve1, .11), docker2 (113, pve2, .21), docker3 (114, pve3, .31), db1
  (116, pve2, .22).
- docker1-3 and util1 mount CephFS as `client.vm_cephfs`. They run the HWE kernel 7.0.0-38
  and `ceph-common` 20.2.4 from `download.ceph.com`. db1 and tailscale1 have no CephFS mount
  and stay on 6.8.
- docker1-3 have scsi1 on `virtio-scsi-single` (iothread active). The guests use only the
  cloud-init snippet `user-noble.yml`.
- Debian 13 LXCs: dns1 (LXC 118, pve1, .53) and dns2 (LXC 119, pve2, .54, built 2026-10-20)
  run AdGuard Home v0.107.79 with the same config. proxy1 (LXC 117, pve3, .27) runs nginx
  1.26 and certbot 4.0.
- The HA rule `dns-apart` (negative resource affinity) keeps dns1 and dns2 apart.
  `proxmox_cluster_config` manages it from `proxmox_cluster_config_ha_resource_affinity` in
  `guests.yml`.
- The Ubuntu VMs list both DNS servers (`dns_hosts`). The LAN (UniFi DHCP) and Tailscale
  still list only .53, until craig adds .54.
- The `*.<domain>` rewrite points to proxy1. `db1`, `dns1`, `dns2` and `proxy1.<domain>`
  resolve to their hosts. The UI of dns2 is `adguard2.<domain>`. The `~/.ssh/config` of the
  controller has aliases for `dns1`, `dns2` and `proxy1`.
- The AdGuard config and the 30 proxy hosts are in `group_vars/dns_servers.yml` and
  `group_vars/proxy_servers.yml`. UI edits on dns1 or dns2 are drift.
- Three Let's Encrypt certificates (`wildcard`, `minio-nassie`, `s3-nassie`) expire on
  2027-01-14. `certbot.timer` renews them.
- db1: PostgreSQL 17, MySQL 8.4 LTS, Valkey 8.0. Dumps go to `/var/backups` and the NAS each
  hour. PostgreSQL holds db1, paperless and the sonarr, radarr, lidarr and prowlarr databases
  (main and log). Apps connect to db1 directly.
- db1 has no ufw. MySQL listens on `*:3306`. Valkey listens on `0.0.0.0` without a password.
  craig accepts this (no inbound internet access). Do not open this item again.
- HA: 10 resources (ct:117-119, vm:111-116, vm:900), each on its home node.
- PBS keeps one protected snapshot of each destroyed old guest. No guests exist in the 800
  range.

### Swarm and stacks

- docker1 is the only manager. Docker 29.9.1 uses the default minimum API 1.40.
- Traefik v3.7.15 uses the swarm provider, with no insecure API and INFO logs. It has only
  the entrypoints `web` (:80, published 8080) and `traefik` (:8080, published 8081). The
  dashboard answers only for `traefik.<domain>`.
- Stacks: homepage, karakeep, media-server (8 services), paperless, portainer-traefik and
  rustfs. 18 services run at 1/1, and the Portainer agent at 3/3. Every stack uses
  `traefik.swarm.network`.
- The five app stacks are templates in `stacks/swarm/`. `playbooks/portainer_stacks.yml`
  deploys them (in `scripts/drift`, `changed=0`). Every secret is stack env from 1Password
  (`group_vars/all/stacks.yml`).
- The old stacks that are not in git (cv, grafana, langfuse, minio, n8n and more) are in the
  gitignored `stacks/_private/`.
- RustFS: `https://s3.<domain>`, console `https://rustfs.<domain>`, login in 1Password
  `rustfs-root`.
- The Plex widget of homepage uses the token that Ombi got at craig's Plex login
  (2026-10-20). No 1Password item holds it.

### appbox1

- appbox1 (`docs/appbox.md`) is an Ubuntu 24.04 VPS at Appbox in Amsterdam, with 4 boost
  slots (5.60 CPUs, 11.20 GB RAM). It is on the tailnet with `tag:appbox`. Its playbook is
  `appbox_servers.yml`.
- The compose stack `media-remote` (`stacks/appbox1/media-remote.yml.j2`) runs prowlarr (with
  its own postgres), byparr, dispatcharr, Deluge, sabnzbd, slskd, aurral, Resilio and a
  Portainer agent. The NAS share `Media` is mounted over Tailscale at `/media`.
- proxy1 serves their `*.<domain>` names over the tailnet. docker1-3 and proxy1 send
  100.64.0.0/10 through tailscale1.
- appbox1 rebooted at 18:58 on 2026-10-21 (a clean shutdown, not from the session). The cause
  is not known. `/media` failed at boot. With craig's approval, it was mounted by hand and
  sabnzbd, slskd and aurral were restarted. `appbox_server` now waits for
  `network-online.target` and gives the mount 180 s (applied, `changed=0` after).

### Private values

- `inventories/prod/group_vars/all/private.yml` (gitignored) holds the domain, the Appbox
  host and SSH port, the tailnet IPs of appbox1 and the NAS, and the AdGuard "Personal
  Devices" IDs. The template is `private.yml.example` in the same directory.
  `playbooks/common/validate_env.yml` stops a run if a value is missing.
- The old `_private/` (audit, drift, patch and session logs up to 2026-10-21, and old stack
  copies) is in `~/Projects/homelab-private-archive-2026-10-21.tar.gz` (mode 600). It holds
  secrets from old audit logs (backlog, "Public repo"). `_private/` now holds only new drift
  logs.
- `scripts/drift-audit/audit.sh` now skips keyrings, `/etc/letsencrypt/`, credential files,
  `.env` files, shell histories and cloud-init snippets.

### Checks on 2026-10-21

- At 17:37: Ceph HEALTH_OK. The nightly vzdump was OK. `cephfs-snapshot` (pve1-3, 3
  snapshots) and `cephfs-backup` (util1) succeeded. The swarm had 18 services at 1/1 and the
  agent at 3/3. `media-remote` had 10 containers up.
- `scripts/drift` at 18:54: `changed=0` on 22 of 23 runs. appbox1 failed because of the
  reboot. After the fix, appbox1 showed `changed=0`.
- After the move of the identifiers to `private.yml` (20:52): proxy1, dns1, dns2 and appbox1
  `changed=0`. After the Tentacle default in `proxmox_node`: pve3 `changed=0`.

### Versions (2026-10-20)

- pve1-3: PVE 9.2.21, kernel 7.0.14-24 only (NIC names pinned by the `nic_names` `.link`
  files), Proxmox ZFS 2.4.4-pve1 (the Debian ZFS is pinned out).
- pbs: PBS 4.2.8, kernel 7.0.14-24 only.
- Every host runs unattended-upgrades for security only, without reboots.
- Ceph: Tentacle 20.2.4-pve5 on all 12 daemons, from the `ceph-tentacle` no-subscription repo
  (`proxmox_node_ceph_repo`). `require_osd_release tentacle`. Every key is `aes256k`, and
  `auth_allowed_ciphers` is `aes256k`. `patch_ceph_ignored_checks` is empty. mgr modules:
  `iostat`, `nfs`. The RBD pool of storage `ceph_rbd` is `cephfs_rbd`.
- CephFS backup: `cephfs-snapshot.timer` on pve1-3 (01:15 UTC, keeps 3 `scheduled-*` in
  `docker/.snap`) and `cephfs-backup.timer` on util1 (03:30) to the PBS namespace `cephfs`.
  The age limit is 26 h. `scripts/drift` reports the age of the newest backup.
- Nightly vzdump (job `nightly-pbs`, 02:00 Europe/Amsterdam) backs up every guest, 900
  included (`agent: 1,freeze-fs=0` on pbs).
- Network KVMs for pve1-3 are at 192.168.90.10, .20, .30 (LAN path, web UI on port 80).

## Next session

craig moves house on 2026-10-22. craig will ask for help with the steps before the move:

1. Stop sabnzbd, slskd and aurral on appbox1 (`docs/move.md`). They write to the NAS.
2. craig does the shutdown checklist `/homelab/move-shutdown-2026-10-22`. On 2026-10-21,
   nobody had opened it on the device, so it had no marks.

appbox1 stays up in Amsterdam (Deluge, Resilio, prowlarr, byparr and dispatcharr continue to
run). After the move:

1. Pull craig's marks from the checklist: `pilcrow pull /homelab/move-shutdown-2026-10-22`.
2. Ask craig what the new network is.
3. Plan the new addresses, if necessary, against the dependency table in `docs/move.md`,
   before power-on.
4. After power-on, start the NAS writers on appbox1.
5. Run the read-only checks and `scripts/drift` (23 runs, with `portainer_stacks.yml`).

Public repo: craig reads the README, `docs/architecture.md` and `CHANGELOG.md`, then squashes
and pushes. The open items are in the backlog, "Public repo". Other open work: the appbox1
items, 3b, 7c, 8b and the rebuild gaps. Ombi waits for a stable 4.60. The reMarkable CLI is
`pilcrow`.

## Dates and things craig owes

- craig (reMarkable `/homelab/dns2-checks-2026-10-20`): .54 as DNS server 2 in UniFi DHCP
  and in the Tailscale admin, and the adguard2 login. Deferred until the new network exists.
- craig: delete the protected old-guest PBS snapshots when they are no longer needed. Create
  1Password `pve-root`. The proxy routing review (8b) when craig wants it. Decide what to do
  with the private archive.
- About 2026-12-15: make sure that proxy1 renewed its certificates. By 2027-01-13: renew
  `tailscale-authkey`. By 2027-01-19: renew `tailscale-authkey-appbox`.

## Kickoff prompt for the next session

```
We're continuing the homelab Ansible work in ~/Projects/homelab.fix-setup (branch fix-setup).

Before doing anything, read AGENTS.md, docs/agents/handover.md, docs/agents/learnings.md and
docs/agents/backlog.md, then summarise back to me in a few lines where we are.

The house move: help me with the pre-move steps in docs/move.md, or, if the lab is already
moved, pull my marks from /homelab/move-shutdown-2026-10-22 with pilcrow, ask me what the new
network looks like and plan the power-on against docs/move.md. After power-on run the
read-only checks (Ceph health, nightly vzdump, CephFS snapshot and backup timers, swarm
services, appbox1's media-remote stack) and scripts/drift.

Rules: nothing that affects running services without my explicit approval for that
specific action; --check first, one host at a time; never print secrets; tick
docs/agents/backlog.md and update docs/agents/handover.md as work lands; add learnings only to
docs/agents/learnings.md; commit often with conventional commits on fix-setup; never push;
ask through AskUserQuestion.
```
