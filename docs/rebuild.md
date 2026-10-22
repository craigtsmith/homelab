# Rebuild runbook

This runbook rebuilds the lab from bare hardware, as the lab is now: PVE 9, Ceph Tentacle,
PBS 4. Ansible does all the work after the installers, except the creation of the Ceph
cluster.

Steps marked **not rehearsed** come from the live config on 2026-10-17. Nobody has run them
from start to end.

Guest rebuilds (Ubuntu VMs, Debian LXCs) are in `docs/operations.md`, "Rebuilding a VM on
24.04 or an LXC on Debian 13". This file covers the layers below the guests.

## Facts

| Item | Value |
| --- | --- |
| Nodes | pve1-3, `192.168.100.10/.20/.30` on `vmbr0`, gateway `.1`. Ceph cluster network `192.168.5.10/.20/.30` (`proxmox_node_ceph_address`) |
| Node disks | `sda` Samsung 870 EVO 250 GB: PVE (`local`, `local-lvm`). `nvme0n1` Samsung 980 PRO 1 TB: the OSD of the node |
| Consoles | network KVMs at 192.168.90.10/.20/.30 (LAN path, port 80) |
| Ceph | Tentacle 20.2 (since 2026-10-19), cephx `aes256k` only. 3 mons, 3 mgrs, 3 MDS (1 active), 3 OSDs. `public_network 192.168.100.0/24`, `cluster_network 192.168.5.0/24` |
| Pools | `cephfs_rbd` (RBD, storage `ceph_rbd`), `cephfs_data` and `cephfs_metadata` (CephFS `cephfs`, storage `ceph_fs`), `.mgr`. All with size 3, min_size 2, 32 PGs, autoscale on, `replicated_rule` |
| CephFS user | `client.vm_cephfs` (aes256k): mon `allow r`, mds `allow rw`, osd `allow rw pool=cephfs_data`. The key is in 1Password `ceph-vm-cephfs` |
| PBS | VM 900 on `ceph_rbd` (32 GB, 6 cores, 16 GB), `192.168.100.199`, PBS 4. Datastore `pbs-nas` on NFS `192.168.1.50:/volume2/pbs-backup` (`/mnt/pbs-nas`) |
| Backups | vzdump of every guest to `pbs` each night at 02:00 (`jobs.cfg`). CephFS `/docker` to namespace `cephfs` at 03:30 (`docs/operations.md`, "CephFS backup"). db1 dumps to the NAS each hour |

## 1. Proxmox VE nodes (installer, by hand)

1. Install PVE 9 from the ISO on `sda` (ext4 or LVM, the default). Use these values:
   - hostname `pveN.<domain>`,
   - address `192.168.100.N0/24`, gateway `192.168.100.1`,
   - DNS `192.168.100.53` (or `1.1.1.1` while dns1 is down),
   - the root password from 1Password `pve-root` (the item does not exist yet: backlog
     "Rebuild gaps").
2. Put the key of the controller on root: `ssh-copy-id root@192.168.100.N0`.
3. If you replaced a NIC or the board, write the new MACs in `host_vars/pveN.yml`. The NIC
   pins hold the live MACs.
4. Run `uv run ansible-playbook playbooks/proxmox_nodes.yml --limit pveN`. It writes the apt
   sources (Ceph Tentacle from `proxmox_node_ceph_repo`), the NIC name pins, `interfaces`
   with the Ceph network, the ZFS pin, the `ansible` user and the NAS mount.
5. Reboot, so that `interfaces` and the kernel command line apply.
6. Run `playbooks/proxmox_cluster_bootstrap.yml`. It creates `homelab` on pve1
   (`cluster_role: manager`) and adds the other nodes. It skips nodes that are in the
   cluster. If a node is in a different cluster, the run stops.

To replace one node in a running cluster (**not rehearsed**):

1. On a healthy node, run `pvecm delnode pveN`.
2. Destroy the Ceph mon, mgr, MDS and OSD entries of the dead node.
3. Do steps 1-6 for the new node.

## 2. Ceph (by hand, not in Ansible, **not rehearsed**)

Run the commands on pve1, unless the comment says "every node". `pveceph` writes
`/etc/pve/ceph.conf`, so all nodes share it.

```bash
# every node: the release in group_vars (proxmox_node_ceph_repo, Tentacle)
pveceph install --repository no-subscription --version tentacle

pveceph init --network 192.168.100.0/24 --cluster-network 192.168.5.0/24
# every node
pveceph mon create
pveceph mgr create
pveceph osd create /dev/nvme0n1
pveceph mds create

pveceph pool create cephfs_rbd --size 3 --min_size 2 --pg_num 32 --add_storages 0
pveceph fs create --name cephfs --pg_num 32 --add-storage 0
```

Then:

1. Add the storages `ceph_rbd` and `ceph_fs` from `storage.cfg`:
   `proxmox_cluster_config.yml -e proxmox_cluster_config_write=true -e '{"proxmox_cluster_config_only": ["storage:ceph_rbd", "storage:ceph_fs"]}'`.
2. Add `client.vm_cephfs` with its key. Do one of these:
   - Build a keyring from 1Password `ceph-vm-cephfs` with the caps in "Facts". Run
     `ceph auth import -i <keyring>`. Do not print the key.
   - Create a new key with
     `ceph auth get-or-create client.vm_cephfs <caps> --key_type aes256k`. Update the
     1Password item, then run `ubuntu_vms.yml` on every VM.
3. Permit only `aes256k` keys (`--restrict-ciphers`), as on the live cluster since
   2026-10-19.

Note: Kernel CephFS clients need kernel 7.0 and the `ceph-common` 20.2 package from Ceph.
`ceph_client` installs the HWE kernel and the `download.ceph.com` package. The Ubuntu package
19.2.3 cannot load an `aes256k` key.

Note: When `ceph_fs` exists, `proxmox_nodes.yml` adds the daily CephFS snapshots for the
backup (`cephfs-snapshot.timer`).

## 3. Cluster config

1. Run `uv run ansible-playbook playbooks/proxmox_cluster_config.yml --check --diff`. It
   shows what is different from the repo: storages, the vzdump job, users, pools, ACLs and
   HA.
2. Revert per object with `-e proxmox_cluster_config_write=true` (`README.md`, "Drift
   handling").
3. Create the API token `ansible@pam!ansible` in the UI. It is not in the files. Give it
   privilege separation and the roles in `AGENTS.md`, "How to run". Store the secret in
   1Password `pve-api-ansible`.

## 4. Proxmox Backup Server (installer, by hand, **not rehearsed**)

1. Create VM 900 with the `config` of `pbs` in `guests.yml`. The role does not create it
   (`build: manual`). Put the PBS 4 ISO on `synnas01:iso/` and attach it as `ide2`.
2. Install PBS with hostname `pbs.<domain>`, address `192.168.100.199/24` and gateway `.1`.
   The root password is in 1Password `pbs-root`.
3. Run `ssh-copy-id root@192.168.100.199`.
4. Run `uv run ansible-playbook playbooks/pbs_servers.yml --limit pbs`.
   - It installs `qemu-guest-agent` and mounts the NAS.
   - It writes `datastore.cfg`, which points to the chunk store in `/mnt/pbs-nas`. Thus the
     old backups come back. On an empty share, there is no chunk store: create the
     datastore first (`proxmox-backup-manager datastore create pbs-nas /mnt/pbs-nas`).
   - It creates namespace `cephfs`, user `cephfs-backup@pbs` and its token. The new token
     secret replaces 1Password `pbs-cephfs-backup` (the old item is archived).
5. The new install has a new certificate. Read it with `proxmox-backup-manager cert info`.
6. Set the fingerprint on the PVE storage `pbs`: `pvesh set /storage/pbs --fingerprint ...`.
   Then promote `storage.cfg` (`-e proxmox_cluster_config_capture=true`).
7. Set `cephfs_backup_pbs_fingerprint` in `roles/cephfs_backup/defaults/main.yml`. Then run
   `util_servers.yml`.
8. Set the PVE storage password:
   `proxmox_cluster_config.yml -e proxmox_cluster_config_write=true -e '{"proxmox_cluster_config_only": ["priv/storage/pbs.pw"]}'`.

## 5. Guests and data

Build the guests in this sequence: dns1, dns2, tailscale1, util1, db1, docker1 (manager),
docker2, docker3, proxy1. There are two methods:

- **Restore from PBS.** This is the fastest method. It gives the state of the last nightly
  backup.
  - VMs: `qmrestore pbs:backup/vm/<vmid>/<time> <vmid> --storage ceph_rbd`.
  - LXCs: `pct restore <vmid> pbs:backup/ct/<vmid>/<time> --storage ceph_rbd`.
  - A restore keeps the IP and the MAC. Add HA with `proxmox_cluster_config.yml` (object
    `ha:<name>`).
- **Build from Ansible.** `proxmox_guests.yml` creates the guests in `guests.yml`. Then run
  the playbook of each host (`docs/operations.md`, "Rebuilding a VM on 24.04 or an LXC on
  Debian 13"). Then restore the data:
  - db1: restore the newest dumps from the NAS, `lab-backup/db-backups/db1`
    (`docs/operations.md`, "Database server").
  - CephFS app state: before the stacks start, restore `host/cephfs-docker` from the PBS
    namespace `cephfs` into `/mnt/cephfs/docker` (`docs/operations.md`, "CephFS backup").
  - Swarm and Portainer: `docker_hosts.yml` starts the swarm on docker1 and deploys
    `portainer-traefik`.
  - App stacks: the templates are in `stacks/swarm/`. `portainer_stacks.yml` updates stacks
    that exist and refuses missing stacks. Thus create each stack one time in Portainer (any
    content). Then run the playbook to write the template and its env.

appbox1 is not in the lab. To rebuild it, see `docs/appbox.md`.

At the end, make sure that `scripts/drift` reports `changed=0` and no drift on every run.
