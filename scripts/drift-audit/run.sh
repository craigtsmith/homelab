#!/usr/bin/env bash
# Runs audit.sh on each host over ssh, one host at a time, and splits the
# output into one file per section under _private/audit/<date>/<host>/.
#
# Usage: scripts/drift-audit/run.sh [host ...]
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../.." && pwd)
out="$repo/_private/audit/$(date +%F)"

hosts=("$@")
if [ ${#hosts[@]} -eq 0 ]; then
  hosts=(pve1 pve2 pve3 pbs docker1 docker2 docker3 db1 util1 tailscale1)
fi

for h in "${hosts[@]}"; do
  dir="$out/$h"
  mkdir -p "$dir"
  echo ">> $h"
  start=$(date +%s)
  if ssh -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=30 "$h" \
    'if [ "$(id -u)" -eq 0 ]; then exec bash -s; else exec sudo -n bash -s; fi' \
    <"$here/audit.sh" >"$dir/raw.txt" 2>"$dir/stderr.txt"; then
    LC_ALL=C awk -v dir="$dir" '
      /^@@@SECTION .*@@@$/ {
        if (f) close(f)
        name = $2; sub(/@@@$/, "", name)
        f = sprintf("%s/%02d-%s.txt", dir, ++n, name)
        next
      }
      f { print > f }
    ' "$dir/raw.txt"
    echo "   done in $(($(date +%s) - start))s"
  else
    echo "!! $h failed, see $dir/stderr.txt"
  fi
done
