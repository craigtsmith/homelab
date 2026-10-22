# Changelog

This file comes from the git history on 2026-10-21, before the squash into one initial
commit. The entries are grouped by day, newest first. "Step N" refers to the phase 3 plan
below. craig did the work with an AI agent. craig approved each change to production
separately.

## Phases

- **Phase 1, drift audit (2026-10-14):** a read-only audit of every host against the repo
  (`scripts/drift-audit`). Manual edits had made the repo different from production.
- **Phase 2, the repo matches production (2026-10-14/15):** the roles were fixed until a
  check run against production reported `changed=0`. Secrets moved to 1Password. Drift
  handling (report, revert, promote) was added.
- **Phase 3, rebuild everything from Ansible (2026-10-14 to 2026-10-20):** the goal was that
  Ansible alone can rebuild every host. The steps:
  - 0: retire code1 and coder1. 1: PVE apt fix. 2: cluster config and API token.
  - 3: Ubuntu 24.04 template and test VM pipeline. 4: util1 pilot. 5: tailscale1.
  - 6: docker2, docker3, docker1. 7: db1. 8: DNS and proxy as LXCs built by Ansible.
  - 9: patch playbook. 10: rebuild runbook and cleanup of leftovers.
  - Follow-ups: 9a patch playbook, 9b Ceph Tentacle, 9c CephFS backup, 9d cephx `aes256k`,
    9e old guest cleanup, 6e Traefik v3, 7b idle databases, 8a second DNS server.
- **After phase 3 (2026-10-20/21):** app upgrades, dns2, appbox1, the runbook for the house
  move and the preparation for a public repo.

## 2026-10-21

- Public repo preparation:
  - The real domain and the Appbox host moved to the gitignored
    `inventories/prod/group_vars/all/private.yml`. Later the same day, the SSH port of
    appbox1, the tailnet IPs and the AdGuard device IDs moved there too. The template
    `private.yml.example` is next to it.
  - group_vars, roles and docs use `{{ domain }}`, `${domain}` (`/etc/pve` files) or
    `<domain>`. Check mode stayed at `changed=0`.
  - The docs no longer show the public IP, the SSH port or the tailnet IPs of appbox1.
- Swarm stacks in git: `stacks/swarm/` (homepage, karakeep, media-server, paperless, rustfs)
  with the new `portainer_stacks` role and playbook. The playbook compares the stacks with
  Portainer, and the stack env by hash.
  - The inline secrets of karakeep and paperless moved to stack env from 1Password.
  - The compose file `media-remote` of appbox1 moved to `stacks/appbox1/`.
  - Stacks that are not ready to publish are in the gitignored `stacks/_private/`.
- New paperless database password.
- The README is a public overview. `docs/architecture.md` has Mermaid diagrams. The
  networks diagram uses `architecture-beta` with one NAS. The procedures moved to
  `docs/operations.md`. All docs use simple English (ASD-STE100 rules).
- The agent files moved to `docs/agents/`: handover, backlog and the new `learnings.md`,
  which holds all lessons.
- `proxmox_node` uses Ceph Tentacle as its default release, and `docs/rebuild.md` installs
  Tentacle.
- `scripts/drift-audit` no longer prints keyrings, certbot credentials, shell histories and
  cloud-init snippets.
- byparr on appbox1 was recreated after Xvfb did not start (stale lock file).
- appbox1: the NAS mount waits for `network-online.target` and has 180 s at boot, after a
  reboot left `/media` empty.
- appbox1: an Ubuntu 24.04 VPS at Appbox in Amsterdam on the tailnet (role `appbox_server`).
  - It runs prowlarr (with its own PostgreSQL), byparr, dispatcharr, Deluge, sabnzbd,
    slskd, aurral, Resilio and a Portainer agent as compose stack `media-remote`. They moved
    from the swarm in two batches.
  - The NAS share `Media` is mounted over Tailscale with `rslave` binds.
  - ufw permits only SSH, the tailnet and the P2P ports. It is enabled with `async`, so a
    lost SSH session cannot hang the play.
- The tailnet route 100.64.0.0/10 goes through tailscale1 on docker1-3 and proxy1 (a
  static-routes unit on the LXC). proxy1 serves the appbox1 apps.
- `scripts/drift` includes appbox1.
- `docs/move.md`: a runbook to shut down and power on for the house move, with the
  dependencies on the old network.
- The MAC of dns2 is pinned in `guests.yml`. The nightly vzdump backs up pbs again.

## 2026-10-20

- dns2 (LXC 119, pve2, .54): a second AdGuard Home with the same config. The HA rule
  `dns-apart` (negative resource affinity) keeps it off the node of dns1. The Ubuntu VMs use
  both servers. Handlers skip in check mode on new hosts.
- The DNS rewrites for the dns1 and proxy1 names point to their own hosts.
- 6e: Traefik v3.7.15 with the swarm provider, no insecure API and no database entrypoints.
  `min-api-version` was removed from Docker.
- App upgrades, with `traefik.swarm.network` on every stack: homepage v2.6.0, karakeep
  0.34.0, paperless 3.3.3 (with `PAPERLESS_SECRET_KEY` from 1Password). The byparr health
  check starts fast. whisparr was removed with its databases and its proxy host.
- 7b: 11 idle PostgreSQL databases were dropped after final dumps.
- 9e: the old guests were destroyed (VMs 101, 102, 103, 106, 108 and 109, LXCs 100 and 104) after
  protected PBS backups. The focal templates and all focal branches were removed from the
  roles.
- The guest agent on pbs runs without fs-freeze, so pbs can back itself up.
- The Ombi MySQL sync bug was diagnosed (it waits for a stable 4.60). Resilio debug logging
  is off.
- The jackett proxy host was removed.

## 2026-10-19

- 9b: Ceph runs Tentacle 20.2.4. The repo and the patch majors record it.
- 9d: every cephx key uses `aes256k`. VMs mount CephFS as `client.vm_cephfs`, with
  `ceph-common` from `download.ceph.com` and the HWE kernel 7.0. db1 and tailscale1 no longer
  mount it.
- 9c: CephFS snapshots come from a node timer (`cephfs-snapshot`), not from the mgr's
  `snap_schedule`, which stopped after a mgr failover. `scripts/drift` reports the backup
  age. A restore test through `proxmox-backup-client mount` passed.
- docker1-3 use `virtio-scsi-single`, so the iothread of the scratch disk applies.
- Leftovers on the nodes and pbs were removed (openipmi, rc.local, cpufreq). pbs got the
  guest agent.
- 9e: 13 dead proxy hosts, the data of old stacks (n8n, penpot, minio) and old cephx key files
  were removed.

## 2026-10-17

- Step 9 done: every host is patched. The nodes run PVE 9.2.21, kernel 7.0 and Ceph 19.2.6.
  pbs runs 4.2.8. The mode `patch_stop_swarm` stops the swarm around node reboots. Swarm
  nodes are addressed by FQDN.
- 9c: a nightly CephFS backup from util1 to the PBS namespace `cephfs`.
- `ceph_upgrade.yml` for the major upgrade from Squid to Tentacle. `ceph.sources` is a
  template.
- pbs_server creates namespaces and tokens through the API.
- `docs/rebuild.md`: a runbook to rebuild from bare hardware.

## 2026-10-16

- Step 7: db1 was rebuilt as VM 116 on 24.04 with PostgreSQL 17, MySQL 8.4 LTS and Valkey
  8.0, with dumps to the NAS each hour. Every app database moved by dump and restore.
- Step 8: a build path for Debian 13 LXCs (`debian_lxc`, `test_lxc.yml`).
  - proxy1 (LXC 117) with nginx and certbot replaces Nginx Proxy Manager. The 45 proxy hosts
    moved across.
  - dns1 (LXC 118, AdGuard Home) replaces the old DNS LXC on .53, with the same MAC.
- Step 9: `unattended_upgrades` (security only, no reboot) on every host. The Debian ZFS
  packages are pinned out on the nodes and pbs. `nic_names` pins the NIC names. `patch.yml`
  does staged node upgrades, Ceph mon and mgr restarts and rolling reboots. The nodes were
  upgraded, and pve3 rebooted on kernel 7.0.
- The checksum of the Docker apt key is pinned, so check mode stays unchanged.

## 2026-10-15

- Step 6: docker2 (113), docker3 (114) and docker1 (115) were rebuilt on 24.04 with Docker
  29.9.1 pinned. The swarm state of docker1 was restored with `--force-new-cluster`. The
  bind-mount directories for swarm services come from the inventory.
- RustFS replaced minio, because the minio image was withdrawn. The console redirect applies
  to page loads only.
- Step 5: tailscale1 was rebuilt as VM 112 with a tagged auth key. The login is the cutover.
- Drift handling: `proxmox_cluster_config` reports per object, and reverts with `pvesh` or
  promotes on request. HA resources and rules come from `guests.yml`. New:
  `scripts/promote-guest`, `playbooks/promote.yml` and `scripts/drift`.
- The vzdump job is now `nightly-pbs`.
- Python caches are no longer tracked.

## 2026-10-14

- Phase 1: read-only drift audit scripts.
- Phase 2: the inventory moved to `inventories/prod` with host_vars. Secrets come from the
  1Password vault `homelab`.
  - ubuntu_vm, docker_host, db_server, util_server, the ceph client, the Proxmox nodes, pbs
    and the cluster bootstrap were fixed to match production.
  - New role `tailscale_router`.
  - `proxmox_guests` declares the guests, reports drift and creates missing guests.
- Step 0: code1 and coder1 were retired.
- Step 1: the bookworm apt sources and Debian kernels were removed from the nodes.
- Step 2: `proxmox_cluster_config` puts the cluster-wide `/etc/pve` config in code.
- Step 3: Ubuntu 24.04 templates 9110, 9120, 9130. `test_vm.yml` applies the roles of a real
  host to a test VM (`test_as`, `test_config`).
- Step 4: util1 was rebuilt as VM 111 on 24.04 (pilot).

## 2025-10-18

- Initial commit of the original playbooks.
