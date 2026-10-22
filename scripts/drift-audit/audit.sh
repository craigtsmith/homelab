#!/usr/bin/env bash
# Read-only drift audit for homelab hosts.
#
# Streams sectioned output to stdout and writes nothing to disk on the host.
# Every section starts with a line "@@@SECTION <name>@@@" so run.sh can split
# the stream into one file per section.
#
# Usage: ssh <host> 'sudo -n bash -s' < audit.sh
set -u
export LC_ALL=C
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

if [ "$(id -u)" -ne 0 ]; then
  echo "audit.sh must run as root" >&2
  exit 1
fi

# Lowest CPU and IO priority; child processes inherit both.
renice -n 19 -p $$ >/dev/null 2>&1
ionice -c3 -p $$ >/dev/null 2>&1

MAX_FILE_BYTES=262144
# Keys, credentials and shell histories are not drift information; never print them.
SKIP_CONTENT='(^/etc/(shadow|gshadow)-?$|/ssh_host_[a-z0-9]+_key$|\.key$|/key\.json$|^/etc/pve/priv/|^/etc/ssl/private/|/token\.shadow$|/shadow\.json$|\.keyring$|\.secret$|^/etc/letsencrypt/|/[^/]*credentials[^/]*$|/\.env$|/\.(bash|zsh)_history$|/snippets/)'

section() { printf '\n@@@SECTION %s@@@\n' "$1"; }

has() { command -v "$1" >/dev/null 2>&1; }

# run <timeout-seconds> <command> [args...]
run() {
  local t=$1
  shift
  printf '\n$ %s\n' "$*"
  timeout --kill-after=5 "$t" "$@" 2>&1
  local rc=$?
  [ "$rc" -eq 0 ] || printf '[exit %s]\n' "$rc"
}

# run_sh <timeout-seconds> <shell pipeline>
run_sh() {
  run "$1" bash -c "$2"
}

dump_file() {
  local f=$1
  [ -e "$f" ] || [ -L "$f" ] || return 0
  printf '\n----- FILE %s\n' "$f"
  stat -c 'mode=%a owner=%U:%G size=%s mtime=%y' -- "$f" 2>/dev/null
  if [ -L "$f" ]; then
    printf 'symlink -> %s\n' "$(readlink -- "$f")"
    return 0
  fi
  [ -f "$f" ] || return 0
  if [[ $f =~ $SKIP_CONTENT ]]; then
    echo '[content skipped: secret material]'
    return 0
  fi
  if [ "$(stat -c %s -- "$f")" -gt "$MAX_FILE_BYTES" ]; then
    echo '[content skipped: larger than limit]'
    return 0
  fi
  if [ -s "$f" ] && ! grep -Iq '' -- "$f" 2>/dev/null; then
    echo '[content skipped: binary]'
    return 0
  fi
  cat -- "$f"
}

# dump_tree <dir> [maxdepth]
dump_tree() {
  local dir=$1 depth=${2:-10}
  [ -d "$dir" ] || return 0
  find "$dir" -xdev -maxdepth "$depth" \( -type f -o -type l \) 2>/dev/null | sort |
    while IFS= read -r f; do dump_file "$f"; done
}

home_dirs() {
  awk -F: '$6 ~ /^\/(root|home\/)/ {print $6}' /etc/passwd | sort -u |
    while IFS= read -r d; do [ -d "$d" ] && echo "$d"; done
}

# ---------------------------------------------------------------------------
section meta
run 10 date -u
run 10 hostname -f
dump_file /etc/os-release
run 10 uname -a
run 10 uptime
run 10 systemd-detect-virt
dump_file /proc/cmdline
run 10 timedatectl
dump_file /var/run/reboot-required
dump_file /var/run/reboot-required.pkgs

# ---------------------------------------------------------------------------
section packages
run 60 dpkg-query -W -f '${binary:Package}\t${Version}\t${db:Status-Abbrev}\n'
run 30 apt-mark showmanual
run 30 apt-mark showhold
run 30 dpkg-divert --list
has snap && run 30 snap list
has pip3 && run 60 pip3 list --disable-pip-version-check
run_sh 10 'ls -la /usr/local/lib/python3*/dist-packages 2>/dev/null'

# ---------------------------------------------------------------------------
section apt
dump_file /etc/apt/sources.list
dump_tree /etc/apt/sources.list.d
dump_tree /etc/apt/preferences.d
dump_tree /etc/apt/apt.conf.d
run_sh 10 'ls -la /etc/apt/trusted.gpg /etc/apt/trusted.gpg.d /etc/apt/keyrings /usr/share/keyrings 2>/dev/null'

# ---------------------------------------------------------------------------
section dpkg-verify
verify=$(timeout --kill-after=10 3600 dpkg --verify 2>&1)
echo "[exit $?]"
printf '%s\n' "$verify"

section modified-files
# Content of every package-owned file that differs from the package version.
printf '%s\n' "$verify" | awk '$1 != "missing" && NF >= 2 {print $NF}' | grep '^/' | sort -u |
  while IFS= read -r f; do dump_file "$f"; done

# ---------------------------------------------------------------------------
section etc-unowned
# Files under /etc that no package owns: generated or hand-made config.
unowned=$(comm -23 \
  <(find /etc -xdev \( -type f -o -type l \) 2>/dev/null | sort -u) \
  <(cat /var/lib/dpkg/info/*.list /var/lib/dpkg/info/*.conffiles 2>/dev/null |
    grep -E '^/etc(/|$)' | sort -u))
printf '%s\n' "$unowned"

section etc-unowned-content
printf '%s\n' "$unowned" | grep -vE '^/etc/(ssl/certs|alternatives)/|^/etc/ld\.so\.cache$|^/etc/\.pwd\.lock$' |
  while IFS= read -r f; do [ -n "$f" ] && dump_file "$f"; done

section etc-mtimes
run_sh 60 "find /etc -xdev -type f -printf '%TY-%Tm-%Td %TH:%TM %p\n' | sort -r"

# ---------------------------------------------------------------------------
section services
run 30 systemctl list-units --type=service --all --no-pager --plain
run 30 systemctl list-unit-files --no-pager --plain
run 30 systemctl list-units --failed --no-pager --plain
run 30 systemctl list-timers --all --no-pager
dump_tree /etc/systemd/system
dump_tree /etc/systemd 1

# ---------------------------------------------------------------------------
section cron
dump_file /etc/crontab
dump_file /etc/anacrontab
dump_tree /etc/cron.d
run_sh 10 'ls -la /etc/cron.hourly /etc/cron.daily /etc/cron.weekly /etc/cron.monthly 2>/dev/null'
dump_tree /var/spool/cron/crontabs

# ---------------------------------------------------------------------------
section users
dump_file /etc/passwd
dump_file /etc/group
dump_file /etc/sudoers
dump_tree /etc/sudoers.d
home_dirs | while IFS= read -r d; do
  dump_file "$d/.ssh/authorized_keys"
  dump_file "$d/.ssh/config"
done

section ssh
dump_file /etc/ssh/sshd_config
dump_tree /etc/ssh/sshd_config.d
run 10 sshd -T

section shell-history
home_dirs | while IFS= read -r d; do
  dump_file "$d/.bash_history"
  dump_file "$d/.zsh_history"
done

section home-dirs
home_dirs | while IFS= read -r d; do
  run_sh 30 "find '$d' -xdev -maxdepth 2 -not -path '*/.cache/*' -printf '%M %u:%g %10s %TY-%Tm-%Td %p\n' | sort -k5"
done

# ---------------------------------------------------------------------------
section kernel
run 10 lsmod
dump_file /etc/modules
dump_tree /etc/modules-load.d
dump_tree /etc/modprobe.d
dump_file /etc/default/grub
dump_tree /etc/default/grub.d
dump_file /etc/kernel/cmdline
dump_file /etc/sysctl.conf
dump_tree /etc/sysctl.d

section sysctl-runtime
run 30 sysctl -a

# ---------------------------------------------------------------------------
section network
run 10 ip -d addr
run 10 ip -d link
run 10 ip route show table all
run 10 ip rule
dump_file /etc/network/interfaces
dump_tree /etc/network/interfaces.d
dump_tree /etc/netplan
dump_file /etc/hosts
dump_file /etc/hostname
dump_file /etc/resolv.conf
dump_file /etc/systemd/resolved.conf
dump_tree /etc/systemd/resolved.conf.d
has resolvectl && run 10 resolvectl status
run 10 ss -tulpn
for i in $(ls /sys/class/net); do
  [ -e "/sys/class/net/$i/device" ] && has ethtool && run 10 ethtool -l "$i"
done
has tailscale && run 15 tailscale status

section firewall
has nft && run 30 nft list ruleset
# Only query iptables if its tables already exist, so no kernel module gets loaded.
grep -q . /proc/net/ip_tables_names 2>/dev/null && has iptables-save && run 30 iptables-save
grep -q . /proc/net/ip6_tables_names 2>/dev/null && has ip6tables-save && run 30 ip6tables-save
has ufw && run 10 ufw status verbose
has pve-firewall && run 10 pve-firewall status

# ---------------------------------------------------------------------------
section storage
run 10 lsblk -o NAME,TYPE,FSTYPE,SIZE,MOUNTPOINT,MODEL
# findmnt reads /proc only, so stale network mounts cannot hang it.
run 10 findmnt -l
dump_file /etc/fstab
run 15 df -hT -x nfs -x nfs4 -x ceph -x fuse -x fuse.ceph-fuse -x cifs -x fuse.pmxcfs -x tmpfs -x overlay
if has pvs; then
  run 20 pvs
  run 20 vgs
  run 20 lvs
fi
dump_tree /etc/exports
dump_tree /etc/exports.d

# ---------------------------------------------------------------------------
section local-paths
for d in /opt /srv /usr/local; do
  run_sh 60 "find '$d' -xdev -maxdepth 4 -printf '%M %u:%g %10s %TY-%Tm-%Td %p\n' 2>/dev/null | sort -k5"
done
dump_tree /usr/local/bin 1
dump_tree /usr/local/sbin 1
dump_tree /usr/local/etc

# ---------------------------------------------------------------------------
if has docker; then
  section docker
  run 30 docker version
  run 30 docker info
  dump_tree /etc/docker
  run 30 docker node ls
  run 30 docker network ls
  run 30 docker volume ls
  run 30 docker plugin ls
fi

# ---------------------------------------------------------------------------
if has pg_lsclusters || has mysql || has redis-cli || has valkey-cli; then
  section databases
  if has pg_lsclusters; then
    run 10 pg_lsclusters
    run 20 runuser -u postgres -- psql -XAt -c 'select rolname, rolsuper, rolcanlogin from pg_roles order by 1'
    run 20 runuser -u postgres -- psql -XAt -c 'select datname from pg_database order by 1'
  fi
  if has mysql; then
    run 20 mysql --batch -e 'select user, host from mysql.user order by 1, 2; show databases'
  fi
  has redis-cli && run 10 redis-cli INFO server
  has valkey-cli && run 10 valkey-cli INFO server
fi

# ---------------------------------------------------------------------------
if has pveversion; then
  section proxmox
  run 30 pveversion -v
  run 30 pvecm status
  run 30 qm list
  run 30 pct list
  run 30 pvesh get /cluster/resources --output-format json-pretty
  run 60 pvesm status
  run 30 ha-manager status
  run_sh 10 'find /var/lib/vz -maxdepth 2 -printf "%M %10s %TY-%Tm-%Td %p\n" | sort -k4'

  section proxmox-etc-pve
  # /etc/pve is the pmxcfs FUSE mount; skip its virtual dotfiles and priv/.
  find /etc/pve -name '.*' -prune -o -path /etc/pve/priv -prune -o \( -type f -o -type l \) -print 2>/dev/null | sort |
    while IFS= read -r f; do dump_file "$f"; done

  section proxmox-snippets
  dump_tree /root/snippets
  dump_tree /var/lib/vz/snippets

  section ceph
  dump_tree /etc/ceph
  if has ceph; then
    run 20 ceph -s
    run 20 ceph versions
    run 20 ceph osd tree
    run 20 ceph df
    run 20 ceph fs ls
    run 20 ceph osd pool ls detail
    run 20 ceph config dump
  fi
fi

# ---------------------------------------------------------------------------
if has proxmox-backup-manager; then
  section pbs
  run 30 proxmox-backup-manager versions --verbose
  run 30 proxmox-backup-manager datastore list
  run 30 proxmox-backup-manager sync-job list
  run 30 proxmox-backup-manager verify-job list
  run 30 proxmox-backup-manager prune-job list
  run 30 proxmox-backup-manager remote list
  dump_tree /etc/proxmox-backup
fi

section end
run 10 date -u
