# debian_lxc

Base for the Debian LXCs that Ansible builds (dns1, dns2, proxy1). Proxmox manages the
hostname, `/etc/hosts`, `/etc/resolv.conf` and the network inside the container.

- Playbook: none (a dependency of `dns_server` and `proxy_server`)
- Depends on: `common`, `unattended_upgrades`

## What it does

1. Sets the timezone and installs the base packages.
2. Adds `debian_lxc_static_routes` on eth0 with a oneshot unit.

## Variables

`meta/argument_specs.yml` lists the inputs, with their types and defaults. Ansible
validates them when the role starts. To read them:
`uv run ansible-doc -t role -r roles debian_lxc`. The values are in `defaults/main.yml`.

Overrides: `group_vars/proxy_servers.yml` (static routes).
