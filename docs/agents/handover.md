# Handover

State on 2026-11-20. Read `AGENTS.md` first. Then read this file,
`docs/agents/learnings.md` and `docs/agents/backlog.md` (open work only).

## Where things are

- Phases 1 (drift audit) and 2 (the repo matches production) are done. In phase 3, steps
  0-10 and the old guest cleanup (9e) are done.
- Ansible builds every guest. `playbooks/patch.yml` patched every host on 2026-10-16/17.
  Monthly runs use ride mode.
- The lab is off for the house move since 2026-10-23 (below). Ceph runs Tentacle 20.2.4
  with cephx `aes256k` only. It was HEALTH_OK at shutdown, with `noout` set. The rebuild
  runbook is `docs/rebuild.md`, and it installs Tentacle. The roles do not support focal.
- The repo is public on GitHub (`craigtsmith/homelab`) since 2026-10-22, squashed into one
  initial commit. Only `main` is on GitHub. The local branches `fix-setup` and `pre-squash`
  hold the private values in their history: never push them.

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

### Repo tooling (2026-10-22)

- Each role has a `README.md` and a `meta/argument_specs.yml`. Ansible validates the role
  inputs when a role starts, also in check mode. `tasks_from` is written without `.yml`, so
  the entry points of `patch` and `proxmox_guests` validate too.
- CI (all green on 2026-10-22): Ansible Lint, Ansible Syntax Check and Python (ruff,
  basedpyright, `pytest tests`). `tests/test_argument_specs.py` keeps the spec defaults
  equal to `defaults/main.yml`.
- `docs/drift.md` explains report, revert and promote. `CLAUDE.md` is a symlink to
  `AGENTS.md`. `.zed/settings.json` uses ruff and basedpyright from `.venv`.

### Checks on 2026-10-22

- `scripts/drift` at 13:12: `changed=0` and `failed=0` on all 23 runs, no drift, 73
  argument validations passed. The newest CephFS backup was 9.8 h old.
- The reMarkable checklist `/homelab/move-shutdown-2026-10-22` had no marks at about 14:00.

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
- Nightly vzdump (job `nightly-pbs`, 02:00 Europe/London) backs up every guest, 900
  included (`agent: 1,freeze-fs=0` on pbs).
- Network KVMs for pve1-3 are at 192.168.90.10, .20, .30 (LAN path, web UI on port 80).

## The lab is off (shutdown on 2026-10-23)

The lab shut down for the move with `docs/move.md`, "Shut down". agent-smith ran steps 1-7
with craig's approval per step. craig did step 8 and packed the Ceph switch.

- Pre-checks at 11:22: HEALTH_OK, 10 HA resources `started`, nightly vzdump OK on pve1-3,
  `cephfs-snapshot` (pve1-3) and `cephfs-backup` (util1, 03:31) succeeded, 18 swarm services
  at 1/1 and the agent at 3/3, `media-remote` 10 containers up.
- 11:25: sabnzbd, slskd and aurral stopped on appbox1 (exit 0). Deluge, Resilio, prowlarr,
  postgres, byparr, dispatcharr and the Portainer agent run.
- 11:34: step 2 done (vm:114, 113, 115, 111, 116, ct:117, vm:112 `stopped`). When tailscale1
  stopped, the Mac lost the lab IPs. craig turned off "Use Tailscale subnets", and the LAN
  route worked.
- 11:37: step 3 done (ct:119, ct:118, vm:900). Step 4: all 10 HA resources `stopped`, no
  guest runs. Step 5: HEALTH_OK, 97 PGs active+clean. Step 6: `noout` set.
- Step 7: pve3 off at 11:39, pve2 off at 11:41. pve1 lost quorum, and its HA CRM watchdog
  reset it at about 11:42 (`last -x` marks the old boot `crash`). It came up without quorum,
  with the watchdog `standby`, and started no guest. A clean `shutdown -h now` put it off
  at 11:48.
- Step 8: craig shut down the NAS (no ping at 12:03).
- reMarkable `/homelab/move-shutdown-2026-10-22` (`offmark read`): rows 1-9 bracketed with
  "assume you did this?" (yes, agent-smith ran them). Rows 10 (NAS) and 11 (pack the Ceph
  switch) marked pass. Row 12 (new network) is open.
- The HA resources stay `stopped` at power-on until `docs/move.md` steps 8-9 start them.
- The reMarkable CLI is now `offmark` (`offmark read /homelab/<name>`), not `pilcrow`.

## New UniFi network (2026-11-20)

- The lab is still off. craig moves into the new house (UK) in about a month, about
  2026-12-20. The UniFi gear stays at the old place, so new gear is set up on a bench first.
- Gear: UCG-Fiber (craig exchanged the UXG-Fiber, which has no Network app; delivery
  pending), USW-Flex-2.5G-8, the old Ceph switch (USW-Flex-2.5G-5, adopted again after a factory reset),
  U7 Pro XG Wall (wired, 10G PoE injector) and two U7 Pro Wall (mesh, injectors).
- The spec is `inventories/prod/group_vars/all/unifi.yml` (networks, Wi-Fi, fixed IPs,
  switch ports). Hardware, WAN and setup order are in `docs/network.md`.
- Networks: Home 1 (192.168.1.0/24), IoT 10, Guest 30, KVM 90, Lab 100, Ceph 5 (VLAN only,
  stays on the Ceph switch). The subnets of the old place stay, so the hosts need no change
  and `docs/move.md` power-on needs no address plan. Home, IoT and Lab DHCP give .53 and .54
  as DNS. No DHCP domain name.
- Ports: UCG 1 is the WAN (EE PPPoE, Openreach ONT), UCG 5 (10 GbE) the XG Wall, UCG 6 the
  Flex (DAC). Flex 1-3 pve1-3, 4-6 the KVMs, 7-8 the NAS bond. UCG 2 the Ceph switch (its port 1),
  Ceph switch 2-4 `enp2s0` of pve1-3. The NAS bond mode is not known (LACP or not).
- 1Password: `unifi-wifi-home`, `unifi-wifi-iot`, `unifi-wifi-guest` (generated). The SSID
  names in `private.yml` are `TBD-*`.
- The role `unifi_network` does not exist yet. The Integration API writes networks and
  Wi-Fi. The legacy API writes fixed IPs and port overrides. The `linuxserver` controller
  image has no Integration API, so the first test is a check run against the real UCG.
- The house is in the UK. `tz` is `Europe/London`, and chrony on pve1-3 uses
  `*.uk.pool.ntp.org`. `proxmox_node` and `pbs_server` now set the timezone (it was
  `Europe/Amsterdam`, set by hand). The media-server and media-remote stacks use `{{ tz }}`.
  The first `scripts/drift` after power-on shows these changes. Apply them with craig's
  approval (the stacks restart their containers).
- The AdGuard client "UK Routed" is gone from the repo. dns1 and dns2 still have it.

## Next session: UniFi bench setup

1. Pull craig's prep checklist: `offmark read /homelab/unifi-bench-prep`. Put the SSID names
   in `private.yml`, and the MACs in `unifi_network_clients`.
2. The bench WAN is craig's router on 192.168.0.0/24 (double NAT, no clash with the spec).
3. craig sets up the UCG with a local admin. Put the login and an API key in 1Password.
4. Adopt the Flex, the Ceph switch and the APs.
5. Build `unifi_network` (backlog). Prove each API read first, then `--check --diff`, then a
   real run with craig's approval. Set the Ceph switch ports before pve1-3 are cabled to it.
6. Add the role to `scripts/drift`. A check run must show `changed=0`.

## Later: power-on at the new place

1. Cable per `docs/network.md`, and set the WAN (PPPoE, VLAN 101 or untagged).
2. Power on per `docs/move.md`. In step 5, also check `ceph crash ls` for pve1's OSD
   (watchdog reset). The controller reaches the lab over the LAN until tailscale1 runs.
   Then craig turns "Use Tailscale subnets" on again.
3. Start sabnzbd, slskd and aurral on appbox1 (approval). `ssh appbox1` does not work, use
   `uv run ansible appbox1`.
4. Run the read-only checks (Ceph, nightly vzdump, CephFS snapshot and backup timers, swarm
   services, `media-remote`) and `scripts/drift`. Apply the timezone, NTP and "UK Routed"
   changes with approval.
5. Before the next full shutdown, fix `docs/move.md` step 7 (backlog, the watchdog reset).

appbox1 stays up in Amsterdam. While the lab is off, its apps cannot reach `*.<domain>`
(proxy1 is off), so Prowlarr cannot reach Deluge (backlog). The arr apps are off too, so this
has no effect.

Other open work: the appbox1 items, the "Public repo" leftovers, 3b, 7c, 8b and the rebuild
gaps. Ombi waits for a stable 4.60.

## Dates and things craig owes

- craig: the prep checklist `/homelab/unifi-bench-prep` (UCG delivery, SSID names, MACs,
  bench items).
- craig: .54 in the Tailscale admin DNS, and the adguard2 login
  (`/homelab/dns2-checks-2026-10-20`). The new UniFi DHCP gives .54 from the spec.
- craig: delete the protected old-guest PBS snapshots when they are no longer needed. Create
  1Password `pve-root`. The proxy routing review (8b) when craig wants it. Decide what to do
  with the private archive, and with the local branches `fix-setup` and `pre-squash`.
- certbot on proxy1 renews from 2026-12-15, but only when the lab runs. The certificates
  expire on 2027-01-14. Make sure that they renew soon after power-on.
- By 2027-01-13: renew `tailscale-authkey`. By 2027-01-19: renew `tailscale-authkey-appbox`.

## Kickoff prompt for the next session

```
We're continuing the homelab Ansible work in ~/Projects/homelab.

Before doing anything, read AGENTS.md, docs/agents/handover.md, docs/agents/learnings.md and
docs/agents/backlog.md, then summarise back to me in a few lines where we are.

Today is the UniFi bench setup. Pull my prep checklist with
`offmark read /homelab/unifi-bench-prep`, fill in the values it gives, then guide me through
the UCG-Fiber setup and adoption per docs/network.md. Then build the unifi_network role
against the spec in group_vars/all/unifi.yml: API reads first, --check --diff, and a real
run only when I approve.

Rules: nothing that affects running services without my explicit approval for that
specific action; --check first, one host at a time; never print secrets; tick
docs/agents/backlog.md and update docs/agents/handover.md as work lands; add learnings only to
docs/agents/learnings.md; commit often with conventional commits on main; never push;
ask through AskUserQuestion.
```
