# Architecture

This file shows the layout on 2026-10-21. The data comes from the inventory
(`inventories/prod/`) and the live hosts. `<domain>` is the private domain
(`inventories/prod/group_vars/all/private.yml`).

## Hosts and guests

Three Proxmox VE 9 nodes make the cluster `homelab`. All guest disks are on Ceph RBD
(storage `ceph_rbd`). When a node fails, HA starts its guests on a different node.

```mermaid
flowchart TB
  subgraph pve1["pve1 · 192.168.100.10"]
    docker1["docker1 · VM 115 · .11<br/>swarm manager"]
    dns1["dns1 · LXC 118 · .53<br/>AdGuard Home"]
    pbs["pbs · VM 900 · .199<br/>Proxmox Backup Server"]
  end
  subgraph pve2["pve2 · 192.168.100.20"]
    docker2["docker2 · VM 113 · .21<br/>swarm worker"]
    db1["db1 · VM 116 · .22<br/>PostgreSQL, MySQL, Valkey"]
    tailscale1["tailscale1 · VM 112 · .32<br/>subnet router"]
    dns2["dns2 · LXC 119 · .54<br/>AdGuard Home"]
  end
  subgraph pve3["pve3 · 192.168.100.30"]
    docker3["docker3 · VM 114 · .31<br/>swarm worker"]
    util1["util1 · VM 111 · .12<br/>CephFS backup"]
    proxy1["proxy1 · LXC 117 · .27<br/>nginx, certbot"]
  end
  subgraph ams["Appbox, Amsterdam"]
    appbox1["appbox1 · VPS<br/>download services"]
  end
  nas[("NAS · 192.168.1.50")]
```

| Host | Type | OS | Node | Address | Function |
| --- | --- | --- | --- | --- | --- |
| pve1-3 | hardware | PVE 9.2 (Debian 13) | - | .10, .20, .30 | hypervisor, Ceph mon, mgr, OSD and MDS |
| pbs | VM 900 | PBS 4.2 | pve1 | .199 | backups, datastore `pbs-nas` on the NAS |
| docker1 | VM 115 | Ubuntu 24.04 | pve1 | .11 | swarm manager, Portainer, Traefik |
| docker2, docker3 | VM 113, 114 | Ubuntu 24.04 | pve2, pve3 | .21, .31 | swarm workers |
| db1 | VM 116 | Ubuntu 24.04 | pve2 | .22 | PostgreSQL 17, MySQL 8.4, Valkey 8.0 |
| util1 | VM 111 | Ubuntu 24.04 | pve3 | .12 | CephFS backup to PBS, database client tools |
| tailscale1 | VM 112 | Ubuntu 24.04 | pve2 | .32 | Tailscale subnet router for 192.168.100.0/24 |
| dns1, dns2 | LXC 118, 119 | Debian 13 | pve1, pve2 | .53, .54 | AdGuard Home. The HA rule `dns-apart` keeps them on different nodes |
| proxy1 | LXC 117 | Debian 13 | pve3 | .27 | nginx reverse proxy for `*.<domain>` |
| appbox1 | VPS | Ubuntu 24.04 | Appbox | tailnet only | download services (`docs/appbox.md`) |

## Networks

There is one NAS. It is on the home network, and it is also a member of the tailnet.

```mermaid
architecture-beta
    group tailnet(internet)[Tailscale tailnet]
    group lan(cloud)[LAN 192.168.100.0/24]
    group cephnet(cloud)[Ceph network 192.168.5.0/24]
    group home(cloud)[Home network 192.168.1.0/24]

    service appbox1(server)[appbox1] in tailnet
    service guests(server)[guests and tailscale1] in lan
    junction lansw in lan
    service nodes(server)[pve1 to pve3] in lan
    service cephsw(disk)[Ceph switch] in cephnet
    service gw(internet)[gateway .1]
    service nas(database)[NAS .50] in home
    service mac(server)[controller] in home
    service kvm(server)[network KVMs]

    guests:T -- B:appbox1
    guests:R -- L:lansw
    nodes:T -- B:lansw
    nodes:R -- L:cephsw
    lansw:R -- L:gw
    gw:T -- B:nas
    appbox1:R -- L:nas
    nas:R -- L:mac
    gw:R -- L:kvm
```

- The LAN is `vmbr0` on `eno1`. Corosync (`ring0_addr`) and the Ceph mons
  (`public_network`) use the LAN.
- OSD replication uses the Ceph network on `enp2s0`, with its own switch (.5.10, .5.20,
  .5.30).
- The gateway routes between the LAN, the home network and the network KVMs
  (192.168.90.10, .20, .30, one for each node).
- tailscale1 advertises 192.168.100.0/24 to the tailnet. docker1-3 and proxy1 send
  100.64.0.0/10 through tailscale1. Thus the arr apps and proxy1 reach appbox1.
- appbox1 mounts the NAS share `Media` over the tailnet.
- The controller reaches the LAN through the tailscale1 subnet route. When Tailscale is
  down, it uses the gateway.
- The network KVMs do not need the lab DNS or the subnet route.

## Storage

```mermaid
flowchart TB
  subgraph ceph["Ceph Tentacle · 3 OSDs, one per node"]
    rbd["pool cephfs_rbd<br/>storage ceph_rbd"]
    cephfs["CephFS cephfs<br/>/docker: app state"]
  end
  subgraph nasbox["NAS 192.168.1.50 (NFS)"]
    shdocker["/volume2/docker"]
    shmedia["/volume2/Media"]
    shpaper["/volume2/Paperless"]
    shbackup["/volume2/lab-backup"]
    shpbs["/volume2/pbs-backup"]
    shlab["/volume2/HomeLab<br/>storage synnas01"]
  end
  guests["guest disks<br/>10 guests"] --> rbd
  swarm["docker1-3, util1<br/>/mnt/cephfs (client.vm_cephfs)"] --> cephfs
  swarm --> shdocker
  swarm --> shmedia
  swarm --> shpaper
  db1["db1 dumps"] --> shbackup
  pbsds["pbs datastore pbs-nas"] --> shpbs
  nodes["pve1-3"] --> shlab
  appbox["appbox1 /media"] -. tailnet .-> shmedia
```

- Swarm stacks keep their state on CephFS in `/mnt/cephfs/docker/<app>`. Media and
  documents are on the NAS.
- Kernel CephFS clients use `ceph-common` 20.2 from `download.ceph.com` and the HWE kernel
  7.0. The reason is that all Ceph keys are `aes256k`.

## Request path

```mermaid
flowchart LR
  client["client"] -- "app.&lt;domain&gt;?" --> dns["dns1 .53 / dns2 .54<br/>*.&lt;domain&gt; → .27"]
  client -- "HTTPS" --> proxy1["proxy1 .27<br/>nginx, wildcard cert"]
  proxy1 -- "13 app hosts" --> traefik["Traefik on the swarm<br/>docker1:8080"]
  traefik --> svc["swarm services<br/>homepage, karakeep, media-server,<br/>paperless, rustfs"]
  proxy1 -- "tailnet" --> appbox1["appbox1<br/>prowlarr, deluge, sabnzbd and more"]
  proxy1 --> direct["pve1-3 :8006, Portainer :9000,<br/>AdGuard, NAS, Plex"]
  svc --> db1["db1 .22"]
```

- Each `*.<domain>` name resolves to proxy1. Exact rewrites for hosts (`db1`, `dns1`,
  `docker1` and more) are the exceptions. `group_vars/dns_servers.yml` holds the list.
- proxy1 holds the Let's Encrypt certificates (DNS-01 through Cloudflare). It has 30 proxy
  hosts, which are in `group_vars/proxy_servers.yml`.
- Traefik routes by the `Host()` labels on the swarm services. The stack files are in
  `stacks/swarm/`.

## Backup flow

```mermaid
flowchart LR
  subgraph nightly["nightly"]
    snap["01:15 UTC<br/>cephfs-snapshot.timer on pve1-3"]
    vz["02:00 Europe/Amsterdam<br/>vzdump job nightly-pbs"]
    cb["03:30<br/>cephfs-backup.timer on util1"]
  end
  hourly["hourly<br/>db-backup.timer on db1"]
  cephfs["CephFS /docker/.snap<br/>keeps 3"]
  pbs["pbs datastore pbs-nas<br/>prune: last 3, daily 7,<br/>weekly 2, monthly 3"]
  nas[("NAS /volume2/pbs-backup")]
  dumps[("NAS lab-backup/db-backups<br/>and db1 /var/backups")]
  snap --> cephfs
  cephfs --> cb
  cb -- "namespace cephfs" --> pbs
  vz -- "every guest" --> pbs
  pbs --> nas
  hourly --> dumps
```

- The VM backups do not include CephFS. The CephFS backup does.
- `scripts/drift` fails when the newest CephFS backup is more than 26 hours old. There is no
  alerting.
- pbs backs itself up with `freeze-fs=0`. A frozen PBS cannot accept its own backup.
- Restore steps are in `docs/operations.md`, "CephFS backup". The full rebuild is in
  `docs/rebuild.md`.
