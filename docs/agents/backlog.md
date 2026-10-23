# Backlog

This file holds open work only. At each session handover, remove the ticked items.
`CHANGELOG.md` records what was done and when.

- The proven rebuild procedures are in `docs/operations.md`, "Rebuilding a VM on 24.04 or an
  LXC on Debian 13".
- The findings come from the drift audit on 2026-10-14 and from phase 3. The audit report
  is `_private/audit/2026-10-14/drift-report.md` in
  `~/Projects/homelab-private-archive-2026-10-21.tar.gz`.

## Fixes (behavior changes, approval per item)

- [ ] Ombi logs `Table 'Ombi.sqlite_sequence' doesn't exist` (5 Sonarr and 5 Radarr sync runs
      in 12 h). This is Ombi bug #5435: the sync jobs use SQL for SQLite. Thus on MySQL, the
      Sonarr and Radarr cache does not refresh.
      - The fix is upstream commit `968aeb3` (2026-06-18), only in the 4.60.x pre-releases
        (lscr `:development` is v4.60.17).
      - We run the stable `:latest` v4.53.10-ls273, which is still the newest stable release.
      - craig (2026-10-20): wait for a stable 4.60. Then a `media-server` redeploy with
        `pullImage: true` gets it.
- [ ] Remove the old `client.vm_access` key from the cloud-init snippet `user-noble.yml`
      (`proxmox_guests_snippet_ceph_key`, mount line and keyring), then delete the 1Password
      item `ceph-vm-access`. Ceph deleted the key on 2026-10-19, so the key is useless.
      Risk: a changed snippet can give every VM a new instance-id at its next boot, with new
      SSH host keys. Find out first whether cloud-init does that for `cicustom` changes.
- [ ] The Proxmox API tasks use `validate_certs: false` (`proxmox_guests`, HA tasks in
      `proxmox_cluster_config`, `group_vars/proxmox_nodes.yml`). Pin the cluster CA
      (`/etc/pve/pve-root-ca.pem`) and turn validation on.

## Move (2026-10-22)

- [x] Stop sabnzbd, slskd and aurral on appbox1 (approval), before the NAS goes off.
      - [x] Stopped 2026-10-23 11:25 CEST (exit 0). The other 7 containers run.
- [ ] craig shuts down the cluster and the NAS (`docs/move.md`, reMarkable checklist
      `/homelab/move-shutdown-2026-10-22`). agent-smith runs steps 2-7 with craig's approval
      per step.
      - [x] Pre-checks 2026-10-23 11:22: HEALTH_OK, 10 HA resources started, vzdump OK on
            pve1-3, `cephfs-snapshot` and `cephfs-backup` succeeded, 19 swarm services up.
      - [x] Step 2 (HA stop of the apps and tailscale1): done 11:34, 7 guests stopped.
- [ ] At the new place, before power-on: decide the network.
      - The same 192.168.100.0/24 with gateway .1 and a route to the NAS at 192.168.1.50
        needs no repo change.
      - Each other layout needs a plan for new addresses.
      - Then power on per `docs/move.md`. Do 8a and the KVM addresses again for the new
        network.

## appbox1 (download services in Amsterdam, `docs/appbox.md`)

- [ ] Portainer environment `appbox1`: the Business Edition licence permits 3 nodes, and the
      swarm uses all 3. craig gets a bigger licence. Until then, the agent runs on the
      tailnet on port 9001.
- [ ] Delete the old configs on CephFS (`prowlarr`, `sabnzbd` with its 5.8 GB June
      `Downloads/`, `slskd`, `aurral`, `dispatcharr`) when appbox1 has run for some time.
- [ ] Drop the databases `prowlarr-main` and `prowlarr-log` on db1 after a final dump, when
      appbox1 has run for some time.
- [ ] Delete the copies of the old app state on appbox1 when appbox1 has run for some time:
      `/srv/appbox/resilio/app-backup-2026-10-21` and
      `/srv/appbox/deluge/torrents/config/deluge.pre-appbox1-202610211434`. Then remove
      "Copies of the state" and "Rollback" from `docs/appbox.md`.
- [ ] Prowlarr has a download client "Transmission (Seedbox)" on the old Appbox account
      host. No Transmission runs on appbox1. Remove the client.
- [ ] Apps on appbox1 reach the other apps on appbox1 through proxy1 (`extra_hosts`). When
      the lab is off, these connections fail. Point them at the container names instead:
      - Prowlarr download clients "SABnzbd" (`nzb`) and "Deluge (seedbox)" (`deluge`).
      - aurral: `prowlarr`, `nzb` and `slskd` (in `aurral.db`).
      - Then remove `prowlarr`, `nzb`, `deluge` and `slskd` from `extra_hosts` in
        `stacks/appbox1/media-remote.yml.j2`. Keep the swarm apps (sonarr, radarr, lidarr,
        navidrome).
      - Prowlarr's `prowlarrUrl` stays on `prowlarr.<domain>`. The swarm arr apps use it.
- [ ] Replace Resilio (appbox1 container to the swarm `sync`) with a one-way copy from
      appbox1 to the NAS. First find out how the import and the deletions must work.
      - Resilio stays for now. It continues while the NAS is off (the move), and it seeds
        from appbox1, not from craig's home line.
      - But deletions at home delete seeding data on appbox1 (95 torrents lost their data).
- [ ] Lidarr has 11 indexers on `new-prowlarr.<domain>`, which has no proxy host (TLS
      "unrecognized name"). This was broken before 2026-10-21. Remove the indexers, or sync
      them again from Prowlarr.
- [ ] byparr wedged on 2026-10-21 at 13:43. Xvfb stopped and left `/tmp/.tX99-lock`. Every
      solve failed, but the container continued to run (compose does not restart unhealthy
      containers). It was recreated (craig, 2026-10-21). If this occurs again, think about
      `tmpfs: /tmp` and an autoheal.
- [ ] Prowlarr health: indexers without a definition (GamesTorrents, YourBittorrent,
      TheRARBG, NorTorrent), and indexers that fail for more than 6 hours.
- [ ] slskd rescanned its shares after the restart on 2026-10-21 (slow over NFS). Make sure
      that it is healthy.

## Phase 3 leftovers

Steps 0-10 and 9e are done (rebuild runbook `docs/rebuild.md`).

- [ ] 3b. Debian 13 containers on the controller for fast converge tests of the file and
      package tasks in `proxmox_node` and `pbs_server`. These tests do not replace PVE
      hardware.
- [ ] 7c. MySQL `exporter@%` was not created again on 116 (no prometheus stack runs). The
      prometheus stack file (`stacks/_private/prometheus.yml`) still points to db1. If the
      stack comes back, create the user again.
- [ ] 8a. dns2 (LXC 119, pve2, .54) is built, in HA, and listed by the Ubuntu VMs. Its UI is
      `adguard2.<domain>`. `dns-apart` keeps it off the node of dns1.
      - Left: craig sets .54 as the second DNS server in UniFi DHCP (both networks) and in the
        Tailscale admin (reMarkable `/homelab/dns2-checks-2026-10-20`).
      - Deferred (craig, 2026-10-21): the UniFi gear stays at the old place after the move,
        so the LAN DNS at the new place is not known. Do this item again for the new
        network.
- [ ] 8b. Proxy routing review (craig: a later phase). 30 proxy hosts remain. These still
      fail: `minio.nassie`, `s3.nassie` (NAS :9011/:9010, 502) and `ha`
      (192.168.100.186:8123, 502).
- [ ] Delete the protected PBS snapshots of the old guests when craig does not need them.
      The NAS also keeps `postgres-backups/db1-final-2026-10-16/` and `lab-backup/cephfs`
      from 2026-10-16 (68 GB).

## Checks with a date

- [ ] By about 2026-12-15: make sure that `certbot.timer` on proxy1 renewed the three
      certificates (issued 2026-10-16, expire 2027-01-14, renewal starts 30 days before).
- [ ] By 2027-01-13: renew the 1Password `tailscale-authkey` (reusable, tagged
      `tag:subnet-router`, 90 days maximum). Only a new router login needs it.
- [ ] By 2027-01-19: renew `tailscale-authkey-appbox` (`tag:appbox`, created 2026-10-21,
      90 days maximum). Only a new login of appbox1 needs it.

## Rebuild gaps (goal: Ansible alone can rebuild every host)

- [ ] The Ceph cluster creation (mons, OSDs, CephFS, `client.vm_cephfs` caps) is not in
      Ansible. The steps by hand are in `docs/rebuild.md`.
- [ ] Nobody has rehearsed these steps in `docs/rebuild.md`: the Ceph creation, the PBS
      install on a datastore that exists, the replacement of one node. A rehearsal needs
      spare hardware or nested PVE.
- [ ] The 1Password item `pve-root`, which `proxmox_cluster_bootstrap.yml` reads (craig,
      still missing on 2026-10-15).
- [ ] The keys of the `ansible` user on pve2 and pve3: only the private key of pve1
      (`~/.ssh/ansible-key`) is on the controller.

## Public repo leftovers

The repo is public since 2026-10-22. `main` had none of the `private.yml` values in its
tree or history on that day.

- [ ] The local branches `fix-setup` and `pre-squash` hold the domain, the Appbox host, the
      tailnet IPs and AdGuard device IDs in their history. Never push them. craig decides
      when to delete them.
- [ ] Make sure that GitHub renders the `architecture-beta` diagram in
      `docs/architecture.md`. GitHub does not publish its Mermaid version. mermaid-cli 11
      renders it. If GitHub cannot render it, commit an SVG next to the source.
- [ ] `~/Projects/homelab-private-archive-2026-10-21.tar.gz` (mode 600, the old `_private/`)
      holds secrets from the old audit logs: Ceph keys in 7 files and the Cloudflare token in
      2 files. craig decides: keep it, encrypt it, or delete it.

## Notes

- [ ] `ubuntu_vm`: a changed NIC unit template applies only at the next reboot (the units
      start, but do not restart). This is correct for rebuilds. It is important if the
      queues change on a live VM.

Out of scope for now: monitoring and alerting, scheduled drift runs, Molecule tests (most
roles need the cluster; `test_vm.yml` and `test_lxc.yml` cover rebuilds).
