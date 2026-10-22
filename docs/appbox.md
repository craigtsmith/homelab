# appbox1

appbox1 is an Ubuntu 24.04 KVM guest on craig's Appbox account in Amsterdam ("Ubuntu VPS"
app, Minimal 24.04). It has 4 boost slots: 5.60 CPUs and 11.20 GB RAM. It was built on
2026-10-21.

appbox1 runs the services that connect to trackers, indexers and P2P networks. Their traffic
thus leaves from the Netherlands. The playbook is `playbooks/appbox_servers.yml`, with the
roles `unattended_upgrades`, `tailscale_router` and `appbox_server`.

## Access and network

- SSH: user `appbox` on `appbox1_ansible_host`, port `appbox1_ansible_port` (both in
  `private.yml`), with sudo without a password. Appbox sends that public port to sshd :22
  (NAT). 1Password `appbox1` holds the VM password.
- Appbox sends a range of public TCP ports to the VM without change. Deluge listens on 11158,
  slskd on 11159 and Resilio on 11160 (`appbox_server_open_ports`).
- ufw permits these ports, sshd :22, Tailscale UDP 41641 and all traffic on `tailscale0`.
- Tailscale: tag `tag:appbox` (auth key `tailscale-authkey-appbox`). appbox1 accepts routes
  and ignores the tailnet DNS. The web UIs listen on the tailnet IP only
  (`appbox1_tailnet_ip` in `private.yml`).
- docker1-3 and proxy1 send 100.64.0.0/10 through tailscale1 (`ubuntu_vm_static_routes`,
  `debian_lxc_static_routes`). Thus the arr apps and proxy1 can reach appbox1.
- Containers on appbox1 reach `*.<domain>` through proxy1 (`extra_hosts`).
- `/APPBOX_DATA` (virtiofs) is the shared app storage of the account. The stack does not use
  it. The Deluge and Resilio apps were replaced by containers and deleted on 2026-10-21.

## Stack media-remote

The stack is a compose project in `/opt/media-remote`. Its file is
`stacks/appbox1/media-remote.yml.j2`. All services run since 2026-10-21.

| Service | Port (tailnet) | Data |
| --- | --- | --- |
| postgres 17 | internal | `/srv/appbox/postgres`, databases `prowlarr-main` and `prowlarr-log` (password `appbox-prowlarr-pg`) |
| prowlarr | 9696 | `/srv/appbox/prowlarr` |
| byparr | 8191 | none |
| dispatcharr | 9191 | `/srv/appbox/dispatcharr/data`, its own Redis (before: db1 Valkey) |
| deluge | 8112, P2P 11158 | `/srv/appbox/deluge/torrents` (copied from the app, `/torrents` in the container) |
| resilio | 8888, P2P 11160 | `/srv/appbox/resilio` (state copied from the app, same device identity). Syncs `deluge/torrents/completed` to the `sync` service on the swarm |
| sabnzbd | 8585 | `/srv/appbox/sabnzbd/config`. Temporary files in `/srv/appbox/sabnzbd/incomplete`. Finished files to `/media/downloads/usenet` |
| slskd | 5030, P2P 11159 | `/srv/appbox/slskd`. Temporary files in `/srv/appbox/slskd-incomplete` |
| aurral | 3005 | `/srv/appbox/aurral` (owner 1001) |
| portainer-agent | 9001 | For a Portainer environment `appbox1`. Not added: the licence permits 3 nodes |

`/media` is the NAS share `Media`. appbox1 mounts it with NFS over Tailscale at boot
(`nas_tailnet_ip` in `private.yml`). The Tailscale package on the Synology runs in TUN mode.

- The containers bind `/media` with `:rslave`.
- Docker starts after `remote-fs.target`.
- The playbook renders the stack file and starts the stack. To change the stack, change the
  file in the repo.
- When appbox1 becomes a Portainer environment, Portainer shows the stack as external.

## Apps behind proxy1

proxy1 serves `prowlarr`, `byparr`, `dispatcharr`, `deluge`, `nzb`, `slskd` and
`aurral.<domain>` from appbox1. The swarm stack `media-server` does not have these services
since 2026-10-21.

Sonarr, Radarr, Lidarr and Prowlarr connect to `deluge.<domain>:443`. Their remote path
mappings (`/torrents/completed` to `/media/downloads/torrents/`) did not change.

The resilio container syncs `completed/` to the `sync` service on the swarm. The Resilio
database holds absolute paths. Thus the container mounts its storage at
`/home/appbox/rsldata`, and the folder at the path of the old app:
`/APPBOX_DATA/apps/deluge.<appbox-account>.appboxes.co/torrents/completed`.

Copies of the state of both apps:

- `/srv/appbox/resilio/app-backup-2026-10-21`
- `/srv/appbox/deluge/torrents/config/deluge.pre-appbox1-202610211434`

slskd's API key for aurral is in 1Password `slskd-aurral-key` (new key on 2026-10-21).

## Seeding data loss

On 2026-10-21, 95 of the 97 Deluge torrents had no data in `completed/`. The arr apps
imported the files, and then the files were deleted. Resilio probably sent the deletion
back. `downloading/` also held 12 folders (56 GB) that no torrent used. Both were cleaned
on 2026-10-21. This data loss occurs again until Resilio is replaced (backlog).

## Rollback

1. Stop the stack on appbox1: `docker compose -p media-remote down`.
2. Deploy `media-server` again with the stack file from before the move. The file is
   `_private/session/2026-10-21/media-server-stack.before-appbox1.yml` in
   `~/Projects/homelab-private-archive-2026-10-21.tar.gz`.
3. Revert the proxy upstreams in `group_vars/proxy_servers.yml`, then run
   `proxy_servers.yml`.
4. Restore the Deluge clients of the arr apps from `docker1:~/arr-before-2026-10-21/`.
5. If you need the Deluge and Resilio apps, install them again. Then copy their data back
   from `/srv/appbox`.

Note: The old copies on CephFS and db1 do not have the changes made on appbox1 after the
cutover (the Prowlarr database, the configs).
