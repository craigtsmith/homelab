# Moving the homelab (2026-10-22)

craig moves house on 2026-10-22. The cluster, the NAS and the Ceph switch move. The UniFi
gateway and the LAN switch stay at the old place.

The network at the new place is not known yet. Thus the cluster shuts down cleanly and stays
off until that network exists. The procedure comes from the Proxmox VE admin guide,
"Shutdown Proxmox VE + Ceph HCI Cluster" (`chapter-pveceph.html`).

## What depends on the old network

This table comes from the hosts, read on 2026-10-21.

| Dependency | Today | Necessary at the new place |
| --- | --- | --- |
| LAN between the nodes | `vmbr0` on `eno1`, 192.168.100.0/24, UniFi switch | A switch that connects `eno1` of pve1-3. Corosync (`ring0_addr` .10/.20/.30) and the Ceph mons (`public_network` 192.168.100.0/24) use it. Without it, there is no quorum and no Ceph |
| Ceph cluster network | `enp2s0`, 192.168.5.0/24, its own switch | The same switch (it moves) |
| Default gateway | 192.168.100.1 on every node and guest | A router on 192.168.100.1, or new addresses for every host |
| NAS | 192.168.1.50, routed by UniFi | 192.168.1.50 reachable from 192.168.100.0/24, or new addresses in the NFS mounts |
| PBS datastore `pbs-nas` | NFS `192.168.1.50:/volume2/pbs-backup` on pbs | The NAS is reachable |
| Swarm volumes, media, paperless | NFS `/volume2/docker`, `Media`, `Paperless` on docker1-3 and util1 (most without `nofail`) | The NAS is reachable before these VMs start |
| db1 dumps | NFS `/volume2/lab-backup` | The NAS is reachable |
| Node and pbs resolvers | 192.168.100.1, then 1.1.1.1 | A resolver on .1, or a change to `resolv.conf` |
| AdGuard upstreams, NTP, certbot, apt, Tailscale | Internet (DoH to Quad9 and Cloudflare, `*.nl.pool.ntp.org`, Cloudflare DNS-01) | Internet through the gateway |
| Tailscale subnet route | tailscale1 advertises 192.168.100.0/24 | The same subnet, or a change to the route |
| Network KVMs | 192.168.90.10/20/30, routed by UniFi | A route to 192.168.90.0/24, or new addresses |

The repo needs no change if the new router gives 192.168.100.0/24 with gateway .1 and a
route to the NAS at 192.168.1.50. All other layouts need new addresses. Make that plan
before the first power-on.

## Shut down (craig, before the move)

appbox1 (`docs/appbox.md`) continues to run in Amsterdam. sabnzbd, slskd and aurral write to
the NAS over a `hard` NFS mount. When the NAS is off, they hang.

1. Stop sabnzbd, slskd and aurral on appbox1. Ask agent-smith, or run
   `sudo docker compose -p media-remote stop sabnzbd slskd aurral` on appbox1.

Note: Stopped containers stay stopped after a reboot. Deluge and Resilio continue to run on
the VPS disk. Resilio syncs with `sync` on the swarm after power-on.

On pve1 as root:

2. Stop the apps and services through HA, so that they stay stopped at power-on:
   `for g in vm:114 vm:113 vm:115 vm:111 vm:116 ct:117 vm:112; do ha-manager set $g --state stopped; done`
3. Stop DNS and PBS: `for g in ct:119 ct:118 vm:900; do ha-manager set $g --state stopped; done`
4. Wait until `ha-manager status` shows every service `stopped`, and `qm list; pct list`
   shows nothing that runs.
5. Make sure that `ceph -s` shows `HEALTH_OK`.
6. Run `ceph osd set noout`.
7. Power off pve3, then pve2, then pve1: `shutdown -h now` on each node. All three nodes run
   a mon, so the order is not important.
8. Shut down the NAS from DSM.

## Power on (at the new place, after the network exists)

1. On each node, connect the Ceph switch to `enp2s0` and the LAN switch to `eno1`.
2. Power on the NAS. From a laptop on the new LAN, make sure that `ping 192.168.1.50` works.
3. Power on pve1-3 at the same time.
4. Make sure that `pvecm status` shows `Quorate: Yes`.
5. Make sure that `ceph -s` shows all mons, mgrs, OSDs and the MDS up. The only warning must
   be `noout`.
6. Run `ceph osd unset noout`. Make sure that `ceph -s` shows `HEALTH_OK`.
7. From pve1, run `ping 192.168.100.1`, `ping 192.168.1.50` and `ping 1.1.1.1`.
8. Start DNS and PBS: `for g in ct:118 ct:119 vm:900; do ha-manager set $g --state started; done`
9. Start the other guests: `for g in vm:116 vm:111 vm:112 ct:117 vm:115 vm:113 vm:114; do ha-manager set $g --state started; done`
10. When the NAS is on the tailnet again, start sabnzbd, slskd and aurral on appbox1:
    `docker compose -p media-remote start sabnzbd slskd aurral`.
11. Run the read-only checks (Ceph, swarm services, NFS mounts) and `scripts/drift`.

Note: The CephFS backup age check fails until the 03:30 run on util1 after power-on.
