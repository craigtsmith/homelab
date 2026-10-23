# Learnings

Mistakes and surprises from earlier sessions. Each item gives the rule first, then the
reason. Add new items to the correct section. Do not put learnings in other files.

## Working method

- Do not build the config of a new host from memory. Compare a test VM with the production
  host that it replaces. Use `scripts/drift-audit` and compare the output section by section
  (`docs/operations.md`, "Rebuilding a VM on 24.04 or an LXC on Debian 13").
- Read dry runs before you act. `apt-get -s purge zfs-dkms` showed that the purge also
  removes the Proxmox ZFS tools.
- Report every deletion and every check run, also the runs that nobody asked for.
- After the first real run of a new night job, make sure that it worked. The CephFS backup
  failed two times and nobody saw it, because there is no alerting.

## Ansible

- Do not set `connection: local` on a play that delegates. It overrides `delegate_to`, and
  the delegated tasks then run on the controller.
- In `.j2` files, `'\1'` inside a Jinja string becomes `\x01`. Use `regex_replace`, not
  backreferences in `regex_search`.
- A wait that retries (`until:`) must fail on errors such as 403. If it does not, it hangs.
- `-e ansible_host=...` is an extra var. It overrides every host, also delegated ones. A
  task delegated to docker1 ran on the test VM. To give one host a different address, add a
  second inventory source (`docs/operations.md`, "Rebuilding a VM on 24.04 or an LXC on
  Debian 13").
- Pin the `checksum` of every `get_url`. Without it, check mode downloads the file and
  reports a change when the Last-Modified time of the server changes (Docker apt key).
- Ansible templates use `trim_blocks`. `{%- ... %}` joins lines, so write block tags on
  their own lines.
- Put a `{# ... #}` comment in a `.j2` file at column 0. The comment keeps the indent in
  front of it, so the next line moves and check mode reports a change.
- PyYAML `safe_dump` does not indent lists, and yamllint rejects that. Dump with an indenting
  dumper. Then compare the loaded data before and after.
- Ansible 2.19 keeps backslashes in folded (`>-`) scalars. Write regexes there with one
  backslash (`'\S+'`, `'\1'`).
- A backreference in a `when:` or `that:` condition becomes `\x01`. Build the value with
  `set_fact` and compare that value.
- A check run fails on a new systemd timer at the enable step, because the unit file does
  not exist yet. Add `when: not (ansible_check_mode and <units>.changed)`.
- A check-mode guard on a task does not cover its handler. Give the handler the same
  `when:`. A restart of a unit that does not exist failed on dns2.
- A play's `vars:` cannot see role defaults. Set such values in the task file of the role
  (`ceph_major_packages.yml`).
- Ansible templates the arguments of ad-hoc `ansible -a` commands. Put Docker formats such as
  `{{.Names}}` between `{% raw %}` and `{% endraw %}`.
- `pkill -f <pattern>` in `ansible -m shell` also matches the shell that runs it. The task
  then stops with rc -15. Use `pgrep -a` to look, and match on the process name.
- Write `tasks_from: packages`, not `tasks_from: packages.yml`. With the suffix, Ansible
  finds no entry point in `meta/argument_specs.yml` and does not validate. It gives no
  warning (Ansible 2.19).
- In `meta/main.yml`, every key of a dependency entry except `role` is a role parameter.
  `allow_duplicates: false` there was a parameter to `common`, and the argument spec
  rejected it. `allow_duplicates` works only at the top level of the role's own
  `meta/main.yml`.
- Role argument validation templates every listed variable when the role starts. Do not
  list 1Password lookups (every run then reads them) or values that come from facts (they
  fail in plays without `gather_facts`).

## Secrets

- Mask a secret before you print it. A `sed` that cut at the first `@` printed part of a
  password that contained `@`. Print only the keys, or parse the value and drop it in the
  same process.
- Do not mask a secret by a replacement of every match in a file. A short or common value
  (a password equal to the app name) then shows where it occurs. Mask the value on its own
  `NAME:` line. Replace other matches only for long values.
- After `[:=]\s*`, a lookahead such as `(?!\$\{)` passes when the regex backtracks over the
  space. Use `[ \t]*(?![ \t]|\$\{)`.
- The AdGuard API needs the admin password. The AdGuard config holds only its bcrypt hash.
  1Password `adguard-admin` holds both.

## Shell and controller

- zsh does not split `$var` into words. Run loops over many fields under `bash`. For a
  command prefix, use an array (`"${A[@]}"`).
- Use `find`, not `ls -R`. `ls` is an alias for `eza`, which can hang.
- `grep` on the controller is ugrep, which has no backreferences (`\1`). Use `awk`.
- `ssh` in a heredoc script reads the rest of the heredoc as stdin. Use `ssh -n`. This is
  also true for `docker exec -i` in a script sent through `ssh host bash -s`. Copy the script
  to the host and run it there.
- A single quote inside a single-quoted `ssh '...'` command ends the quote (`c['id']`
  became `c[id]`). Copy scripts with `scp` and run them.
- The controller reaches 192.168.100.0/24 through the Tailscale subnet route. When Tailscale
  is down, it uses the LAN (router 192.168.1.1).
- A change that moves or restarts the subnet router can stop your session. Run such
  commands on a pve node with `systemd-run`.
- The controller resolves names through MagicDNS, which forwards to .53. Its Tailscale CLI is
  `/Applications/Tailscale.app/Contents/MacOS/Tailscale` (not on `PATH`).
- The reMarkable CLI is `offmark` (it was `pilcrow` before). `offmark read` needs the device
  path (`/homelab/<name>`) for a document in a folder. A bare name looks in the default
  folder.
- `ssh appbox1` has no `~/.ssh/config` alias. MagicDNS resolves the name, and the host key
  is not known ("Host key verification failed"). Use `uv run ansible appbox1`, which
  connects with the host and port from `private.yml`.

## Proxmox

- `pct restore --net0 ...` keeps the IP of the backup. Restore with the guest stopped. Then
  run `pct set --net0` before the first start, or the copy takes the production IP (801).
- A restored copy of a host runs its timers. Before the first start, disable the timers that
  act outside the guest (certbot renewals through Cloudflare) with `pct mount`.
- HA node maintenance in PVE 9.2 sends guests back to their old node when maintenance ends.
  This also occurs without a node-affinity rule (pbs).
- `ha-manager migrate` obeys node-affinity rules. To move a guest away and back, set it to
  `ignored`, run `qm migrate --online` two times, then set it to `started`.
- `ha-manager status` prints `(pve3, started)`. Remove the parentheses before you compare.
- Proxmox helpers that ask a question (`pve-cephx-rotate-service-keys --apply`) answer no
  without a terminal. Under `systemd-run`, add `--assume-yes` after you read the dry run.
- A guest that is its own backup target (pbs) must not freeze its file systems during
  vzdump. The frozen PBS cannot accept the backup. pbs runs `agent: 1,freeze-fs=0`.
- `proxmox-backup-manager user generate-token` has no JSON output. Some PBS CLI calls also
  panic while they print tables, after the change is done. Use
  `proxmox-backup-debug api create ... --output-format json`.
- `proxmox-backup-client restore --pattern` reads the full archive (121 GB of CephFS: 1 MB in
  10 minutes). For a small number of directories, use `proxmox-backup-client mount` and copy.

## Ceph

- Do not trust schedules that the mgr holds without a look at the result. `snap_schedule`
  took no snapshots after the active mgr changed (Squid 19.2.6), and its status still said
  `active`. Snapshots now come from a node timer (`cephfs-snapshot`).
- `ceph pg stat -f json` prints across lines. Send each Ceph JSON command through
  `tr -d '\n'` before you read many commands as one document per line.
- Check mode does not change apt repos, so the package check for a major upgrade shows
  nothing new. Simulate it with a temporary sources directory and lists
  (`-o Dir::Etc::SourceParts=... -o Dir::State::Lists=...`).
- The `ceph-common` 19.2.3 package of Ubuntu 24.04 cannot load an `aes256k` key ("secret is
  not valid base64"), also on kernel 7.0. Kernel CephFS clients get `ceph-common` from
  `download.ceph.com`.
- Stopped LXCs can keep their kernel RBD map (ct100, ct104). The map holds a Ceph session
  with the old key and blocks a key commit. Run `rbd showmapped` on each node.

## Docker, swarm and Portainer

- After `docker swarm init --force-new-cluster`, restart Docker one time on that node. Until
  then, the workers have no ingress neighbor entry for it. Its routing mesh then reaches only
  its local tasks.
- Swarm nodes have FQDN names (`docker2.<domain>`). `docker node` commands with the
  inventory name fail.
- Images can disappear from registries (minio). New swarm nodes start empty and cannot pull
  such an image again.
- Portainer stack updates (`PUT /stacks/<id>`) with `pullImage: true` resolve every tag
  again, so `:latest` services upgrade. `pullImage: false` keeps the digests that run.
  Before a redeploy, compare the running and upstream digests
  (`docker buildx imagetools inspect`).
- A stack update writes every service spec again (swarm fills in defaults). If env and
  images do not change, no task restarts (karakeep).
- `docker stack deploy` accepts `healthcheck.start_interval` only with file
  `version: "3.13"` or no version. "3.9" and older reject it.
- A wedged container continues to run, because compose does not restart unhealthy
  containers. byparr on appbox1 failed every request for 4 hours. Xvfb was dead and
  `/tmp/.tX99-lock` was stale.

## Apps and network services

- Do not redirect `/` on an S3 host. The RustFS console sends signed S3 calls to `/`, and a
  redirect breaks the signature. Redirect page loads only (`Accept: text/html`).
- Traefik v3 drops a router whose rule uses a v2 matcher (`HeadersRegexp` is now
  `HeaderRegexp`) and logs `unsupported function`. Before a Traefik major upgrade, search the
  service labels for v2 matchers.
- nginx loads `conf.d` in name order. A file that defines a `log_format` must sort before the
  files that use it.
- PostgreSQL 15 and later do not give CREATE on schema `public` to PUBLIC. Dumps from 14 hold
  no ACL for that default. After you restore a 14 dump, run
  `grant create on schema public to public` in each database. If you do not, apps that do not
  own their database fail their migrations.
- `community.mysql.mysql_user` with `password:` creates a `mysql_native_password` user, which
  MySQL 8.4 does not load. Give `plugin: caching_sha2_password` and `plugin_auth_string`.
- A new Tailscale router took the primary route at login, against the Tailscale docs. A
  router login is a cutover. Test VMs use `--skip-tags tailscale_login` unless craig approves
  a login.
- Enabling ufw can stop the SSH session of Ansible, and the play then hangs. Enable it with
  `async`, then run `meta: reset_connection`.
- Appbox sends a public port to sshd :22 (NAT). A ufw rule for `ansible_port` locks SSH out.
- An NFS mount over Tailscale can time out at boot, also with
  `x-systemd.requires=tailscaled.service`. The daemon starts before the tailnet path works.
  The mount also waits for `network-online.target` and has 180 s (appbox1).
