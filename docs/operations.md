# Operations

Procedures for the homelab. Each step that writes to production needs approval for that
step (`AGENTS.md`, "Safety rules"). The layout is in `docs/architecture.md`. The rebuild
from bare hardware is in `docs/rebuild.md`.

## Rebuilding a VM on 24.04 or an LXC on Debian 13 (side by side)

This procedure worked for util1 (VMID 111, 2026-10-14), tailscale1 (VMID 112), docker1-3
(VMIDs 115, 113, 114, 2026-10-15) and db1 (VMID 116, 2026-10-16).

If apps depend on the host (the swarm, db1), stop the apps first:

1. Record the replica counts (`docker service ls`).
2. Scale every app service to 0 (all stacks except `portainer-traefik` and `rustfs`).
3. Migrate, and make sure that the result is correct.
4. Scale back to the recorded counts.

Note: After a scale-up, tasks can start on different nodes and pull their images first.
This takes approximately 10 minutes.

### 1. Compare on a test VM (VMIDs 800-899)

1. Build the test VM:
   `uv run ansible-playbook playbooks/test_vm.yml -e test_vmid=8NN -e test_node=<node> -e test_keep=true -e test_as=<host> -e test_mounts=true -e '{"test_roles": [...], "test_config": {"cores": "2", "memory": "2048", "cpu": "host"}}'`
2. Reboot the VM.
3. Audit the production host: `scripts/drift-audit/run.sh <host>`.
4. Audit the test VM: `ssh serveradmin@<ip> 'sudo -n bash -s' < scripts/drift-audit/audit.sh`.
   Split the output into sections, as `scripts/drift-audit/run.sh` does.
5. Compare the two audits section by section. craig reads the diff.

Note: `test_as` applies the groups and host_vars of the host, except `ansible_host`,
`hostname` and `vm_name`. `test_config` makes the clone match the planned guest.

### 2. Build side by side

1. Declare the new VMID in `guests.yml`:
   - `clone_from` the noble template of the node,
   - `cicustom: user=ceph_fs:snippets/user-noble.yml`,
   - `ipconfig0: ip=dhcp,ip6=dhcp`,
   - no MAC and no `ha` key,
   - `boot: c` and `bootdisk` (the template sets them).
2. Run `proxmox_guests.yml --check`. It must report only the new guest as missing.
3. Run `qm set <old> --name <name>-old`.
4. Run `proxmox_guests.yml`. It creates and starts the new VM. Read the DHCP address of the
   VM from the guest agent.
5. Before each run, make sure that the address points to the new VM:
   `ansible <host> -e ansible_host=<dhcp-ip> -m command -a hostname`. Without the override,
   the inventory name is still the old VM.
6. Apply the roles with `--limit <host> -e ansible_host=<dhcp-ip>`. Do not use `--check` on
   an empty VM. It fails on repos that are not added yet.
7. If a role delegates (docker workers read the join token on docker1), do not use the
   extra var. An extra var also changes the address of the delegate. Use a second inventory:
   - `<dir>/hosts.yml` lists the host.
   - `<dir>/host_vars/<host>.yml` sets `ansible_host`.
   - Give every command `-i inventories/prod/hosts.yml -i <dir>/hosts.yml`.
8. Reboot the VM and make sure that it works. Then run `--check` (`changed=0`) and audit
   again.

### 3. Cutover

1. Make a protected backup: `vzdump <old> --storage pbs --mode snapshot`. Then run
   `pvesh set /nodes/<node>/storage/pbs/content/<volid> --protected 1`.
2. Run `ha-manager set vm:<old> --state stopped`, then `qm set <old> --onboot 0`.
3. Run `qm set <new> --ipconfig0 ip=<prod>/24,gw=192.168.100.1,ip6=dhcp`, then
   `qm reboot <new>`.
4. The new instance-id makes cloud-init apply the static netplan. The VM keeps its hostname
   (`99-homelab.cfg`) and gets new SSH host keys. Run `ssh-keygen -R` for the IP, the name
   and the FQDN.
5. Move the `ha` key in `guests.yml` and the VMID in the `pool:` lines of `user.cfg` to the
   new VM.
6. Run `proxmox_cluster_config.yml --check`. Then run it with
   `-e proxmox_cluster_config_write=true -e '{"proxmox_cluster_config_only": ["ha:<name>", "pool:<id>"]}'`.
7. Run `ha-manager remove vm:<old>`. The role never removes unmanaged resources.
8. Run `uv run scripts/promote-guest <new>`. It records the live MAC, the static IP and the
   cloud-init drive.
9. Make sure that `scripts/drift` shows `changed=0` and no drift.

### 4. Rollback (until the old VM is destroyed)

1. Take the new VM off the production IP, or stop it.
2. Start the old VM through HA. If you removed it from HA, run
   `ha-manager add vm:<old> --state started`.
3. Run `qm set <old> --onboot 1`.
4. Run `git revert` on the repo commits.

### 5. After one week

Run `qm destroy <old> --purge 1` by hand, with approval. `destroy.yml` refuses VMIDs out of
the test range. The protected backup stays on PBS.

### Docker swarm (docker1-3, done 2026-10-15)

- Workers: build them side by side with `-e docker_host_join_swarm=false` and the address
  from a second inventory. At the cutover, run `docker swarm leave` on the old VM. Then run
  `docker node rm <id>` on docker1 (the hostname is the same, so use the ID). After the IP
  swap, run `docker_hosts.yml` to join the swarm.
- Manager: the new VM cannot share pve1 with the old VM (memory). The procedure:
  1. Stop Docker on the old docker1.
  2. Make a tar of `/var/lib/docker/swarm` and `/var/lib/portainer` (`--numeric-owner`).
  3. Stop the old VM.
  4. Build the new VM with `docker_host_join_swarm=false` and give it .11.
  5. Extract the tar and start Docker.
  6. Run `docker swarm init --force-new-cluster --advertise-addr 192.168.100.11`. The workers
     connect again without help.
  7. Restart Docker on the new docker1 one time. The ingress sandbox starts before gossip
     forms, so the workers do not learn its address. Until the restart, the routing mesh on
     docker1 does not reach tasks on other nodes.
- Bind-mount paths on local node disks (sabnzbd on `/mnt/scratch`) must exist before a task
  starts there. List them in `docker_host_dirs`.
- New nodes start without images. Images that are no longer published (minio, 2026) cannot
  be pulled again. RustFS replaced minio.

### Database server (db1, done 2026-10-16)

- Use dump and restore. Never copy the data directory: the glibc change from 2.31 to 2.39
  changes the `en_US.utf8` collation. Valkey cannot read Redis 7.4 RDB files, so start it
  empty.
- Do a restore test first. Restore the dumps into a test VM with the new versions. Then
  compare the row counts per table.
- Before the final dumps, every app service must be at 0. `pg_stat_activity`, the MySQL
  processlist and `CLIENT LIST` must show no clients.
- Dump with `pg_dumpall --globals-only`, `pg_dump -Fc` per database and
  `mysqldump --single-transaction` per schema. Make a protected PBS backup of the old VM.
- Restore `globals.sql` first (the roles `postgres` and the admin role exist already). Then
  restore each database with `pg_restore --create --exit-on-error` (`postgres` without
  `--create`).
- Then run `grant create on schema public to public` in each app database
  (`docs/agents/learnings.md`, "Apps and network services").
- MySQL 8.4 does not load `mysql_native_password`. `SHOW CREATE USER` output loads again only
  with `print_identified_with_as_hex=ON` (`db-backup` writes `users.sql` that way). Without
  it, create the users from their passwords with `caching_sha2_password`.
- The new VM keeps its DHCP address until the IP swap. Thus the `db-backup.timer` of the role
  writes dumps of empty servers to the NAS before the cutover. After the first real run,
  look at `db-backups/<host>`.

### Stacks and proxy

- The Portainer API changes the Portainer stacks (`AGENTS.md`, "How to run"). The stack
  files are in `stacks/swarm/` (`playbooks/portainer_stacks.yml`).
- `group_vars/proxy_servers.yml` declares the proxy hosts.
- Apps reach db1 as `db1.<domain>`. dns1 resolves that name to 192.168.100.22, with an exact
  rewrite in front of the `*.<domain>` wildcard.

### LXCs (dns1, proxy1, done 2026-10-16)

- `build: lxc` in `guests.yml` creates the LXC from `proxmox_guests_lxc_template` (Debian 13
  on `ceph_fs`, downloaded if missing) with the SSH key of root. The API token can set only
  `features: nesting=1`. Other feature flags need root@pam.
- Restore test:
  1. With the guest stopped, run `pct restore` of the old LXC to a VMID in the 800 range.
  2. Before the first start, run `pct set --net0 ...ip=dhcp`. A restore keeps the IP of the
     backup, also when you give `--net0`.
  3. Before the first start, disable the timers that act outside the guest (certbot)
     through `pct mount`.
- Test build: `playbooks/test_lxc.yml -e test_vmid=8xx -e test_as=<host> -e '{"test_roles": [...]}' -e test_keep=true`.
  A second run applies the roles to the kept LXC again.
- Compare the test build with the restored copy:
  - with `scripts/drift-audit` (run it with `pct exec <vmid> -- bash -s`),
  - by behavior: DNS answers per name, proxy status, size, redirect and HSTS per host.
- On test proxies, use Let's Encrypt staging:
  `-e proxy_server_acme_server=https://acme-staging-v02.api.letsencrypt.org/directory`.
- Proxy cutover: build the proxy on a spare IP. Then change the `*.<domain>` rewrite on the
  DNS server through the AdGuard API (no restart). Add the specific rewrites before the
  wildcard moves. An exact rewrite wins over the wildcard. Client connections in a pool stay
  on the old proxy until it stops, then they connect again.
- DNS cutover: build the server on a spare IP. Then run one script on the node under
  `systemd-run`, with an automatic rollback:
  1. Stop the old LXC through HA.
  2. Run `pct set <new> --net0` with .53 and the old MAC (a live change, less than one
     second).
  3. Make sure that `dig @192.168.100.53` answers.

  The gap is approximately 7 s (the shutdown of the old LXC). Keep the old MAC, so that the
  ARP caches stay correct. Promote the new guest after the cutover.
- craig's Mac during a DNS gap: it resolves through Tailscale MagicDNS, which forwards to
  .53. It also reaches the lab over the LAN (router 192.168.1.1). The Tailscale CLI is not on
  `PATH`:

  ```bash
  TS=/Applications/Tailscale.app/Contents/MacOS/Tailscale
  $TS down && sudo networksetup -setdnsservers Wi-Fi 1.1.1.1 1.0.0.1   # before
  sudo networksetup -setdnsservers Wi-Fi 192.168.100.53 && $TS up      # after
  ```

### Subnet router (tailscale1)

1. Build and test with `--skip-tags tailscale_login`, so that the VM stays off the tailnet.
   A new router takes the primary route when it logs in. Thus the login is the cutover.
2. Log in the new router while the old router still runs.
3. Stop the old router.

CAUTION: Run commands that restart the router (for example `qm reboot`) on a pve node with
`systemd-run`. A session that uses the subnet route stops when the router restarts.

## CephFS backup

CephFS holds the app state of every swarm stack (`/docker`, 113 GiB). The VM backups do not
include it.

- `cephfs-snapshot.timer` on pve1-3 (`proxmox_node`) makes a snapshot of `/docker` each day
  at 01:15 UTC (03:15 CEST, 02:15 CET). It uses the `ceph_fs` mount of the node and keeps
  three snapshots.
- The snapshot name holds only the date (`scheduled-2026-10-19-01_15_00_UTC`). The first node
  creates it, and the other nodes find it. Thus any node can be down.
- At 03:30, `cephfs-backup.timer` on util1 backs up the newest `scheduled-*` snapshot with
  `proxmox-backup-client` (static build from the pbs-client repo). The target is datastore
  `pbs-nas`, namespace `cephfs`, group `host/cephfs-docker`.
- The prune (last 3, daily 7, weekly 2, monthly 3) and verify jobs of the datastore include
  it.
- The copy is crash-consistent, as after a power cut. The apps continue to run.
- The backup fails when the newest snapshot is more than 26 hours old. Failures show only in
  the journal (`journalctl -u cephfs-backup -u cephfs-snapshot`). There is no alerting.

The token `cephfs-backup@pbs!util1` (1Password `pbs-cephfs-backup`) has DatastoreBackup on
`/datastore/pbs-nas/cephfs` only. If the token secret is lost, `pbs_servers.yml` makes a new
token and archives the old item. Then run `util_servers.yml`.

To restore a file or a directory:

```bash
ssh util1
sudo -i; set -a; . /etc/cephfs-backup/pbs.env; set +a
proxmox-backup-client snapshot list --ns cephfs
# a few directories: mount the archive and copy (seconds)
proxmox-backup-client mount --ns cephfs host/cephfs-docker/<time> docker.pxar /var/tmp/pbs &
cp -a /var/tmp/pbs/paperless /var/tmp/restore/; umount /var/tmp/pbs
# everything (restore with --pattern also reads the full archive, hours)
proxmox-backup-client restore --ns cephfs host/cephfs-docker/<time> docker.pxar /var/tmp/restore
```

CAUTION: Scale the stack to 0 before you restore over its live directory. If you do not, the
app writes to the directory during the restore.

The restore test on 2026-10-19 used `mount` for `bazarr`, `homepage` and `ombi`. The result
was identical to the snapshot in content, owners, modes and mtimes. `scripts/drift` reports
the age of the newest backup and fails after 26 hours.

## Ceph major upgrade

`playbooks/ceph_upgrade.yml` follows the Proxmox guide "Ceph Squid to Tentacle", without node
reboots (used 2026-10-17/19). Run it stage by stage with `--tags`, and `--check` first:

| Tag | What it does |
| --- | --- |
| `check` | makes sure that all daemons run `patch_ceph_major_from`, Ceph is healthy and PVE is 9.2 or later. Disables the removed mgr modules and sets noout |
| `repo` | sets `ceph.sources` to the new release and runs dist-upgrade per node, pve3 first |
| `mon`, `mgr` | restarts the mons, then the mgrs |
| `osd` | restarts the OSDs per node and waits for active+clean |
| `mds` | stops the standby MDS daemons, restarts the active MDS, starts the standbys |
| `finish` | sets `require-osd-release` and unsets noout |

After the upgrade, set `proxmox_node_ceph_repo` and `patch_majors` in
`group_vars/proxmox_nodes.yml`.

Note: Check mode does not change the repo, so its package step shows nothing new. Simulate
the step with a temporary apt list. The mgrs start on the new version when the first mon
restarts.

## Patching

Every host runs unattended-upgrades for security updates only (role `unattended_upgrades`)
and never reboots. `51unattended-upgrades-homelab` clears the origin lists of the package.

- pve1-3 and pbs pin the Debian ZFS packages out (`/etc/apt/preferences.d/proxmox-zfs`). The
  Debian 2.3.9 package once had a higher rank than the Proxmox 2.3.4-pve1 package and
  replaced it.
- pve1-3 and pbs pin their NIC names to the live MACs (`nic_names`,
  `/etc/systemd/network/10-<nic>.link`). Thus a new kernel cannot change the names.

`playbooks/patch.yml` does the other updates each month, one host at a time. Its plays run
in this sequence:

1. **Guest packages** (`--tags packages`): pbs, Ubuntu VMs, LXCs.
2. **Node packages** (`--tags packages`): pve3, pve2, pve1.
   - The run stops if `apt-get -s dist-upgrade` removes a package that is not in
     `patch_allowed_removals`.
   - The run stops if it moves a `patch_majors` package (pve-manager 9, ceph-common 20,
     proxmox-backup-server 4) to a new major.
   - It purges `patch_purge` packages after a dry run, which must remove nothing else.
   - It reports autoremove candidates, but does not remove them.
3. **Ceph mon and mgr restarts** (`--tags ceph_restart`) where the running version is older
   than the installed version. The mons go first. OSDs and the MDS restart with the node
   reboot.
4. **Node reboots** (`--tags reboot`), only when a newer kernel or `reboot-required` is
   there (`-e patch_reboot=always|never`). See the list below.
5. **Guest reboots** (`--tags reboot`): docker hosts are drained first. pbs waits for running
   tasks.

Node reboots:

- Every node must have the same `pve-qemu-kvm`, so that guests only migrate forward.
- The docker VM of the node is drained in the swarm, set to HA `ignored` and shut down. It
  starts again after the reboot.
- The other guests move with HA node maintenance. LXCs restart. dns2 answers while dns1
  restarts, and the HA rule `dns-apart` keeps the two on different nodes.
- The guests come back by their node-affinity rule. pbs has no rule and stays where HA put
  it.
- Ceph has `noout` while the node is down. The run waits for quorum, the NIC names and Ceph
  health (every PG active+clean, no checks other than `patch_ceph_ignored_checks`).
- Console fallback: the network KVMs at 192.168.90.10, .20, .30 (pve1, pve2, pve3), through
  the LAN without the lab DNS or the subnet route.
- If a node starts without its network, select the previous kernel under "Advanced options"
  in GRUB.

Swarm-down mode (`-e patch_stop_swarm=true`, used for the run on 2026-10-16):

- A play before the first node reboot records the replica counts in
  `/root/patch-swarm-replicas.json` on the manager.
- It scales the app services to 0. The exceptions are `portainer-traefik`, `rustfs` and the
  `portainer-update-*` jobs (`patch_swarm_keep_stacks`).
- It stops docker3, docker2 and docker1 through HA.
- A play after the last reboot starts docker1, then the workers. It scales back to the
  record and deletes the record.
- The apps are down for the full node run, and no docker VM rides.
- A second run keeps a record that exists and skips stopped VMs.
- If a node run fails, start the swarm again with `--tags swarm_start -e patch_stop_swarm=true`.
- In check mode, the node plays still show the docker VM as riding, because nothing stopped.

```bash
uv run ansible-playbook playbooks/patch.yml --check --diff --limit docker3
uv run ansible-playbook playbooks/patch.yml --tags packages --limit pve3
```

Note: In check mode, the packages do not change, so the reboot stages see no new kernel. To
check the reboot plan, add `-e patch_reboot=always`. If the pins or the unattended-upgrades
config are new on a host, run the converge playbooks first.
