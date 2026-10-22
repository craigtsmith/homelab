# tailscale_router

Tailscale on tailscale1 (subnet router for 192.168.100.0/24) and appbox1 (a node that
accepts routes).

- Playbook: `playbooks/tailscale_routers.yml`, `playbooks/appbox_servers.yml`
- Depends on: `common`

## What it does

1. Adds the Tailscale apt repository and installs tailscale.
2. Configures UDP GRO forwarding, the advertised routes and the DNS and route settings.
3. Logs in with an auth key only when the node is logged out (tag `tailscale_login`). Test
   VMs skip this tag.

## Variables

`meta/argument_specs.yml` lists the inputs, with their types and defaults. Ansible
validates them when the role starts. To read them:
`uv run ansible-doc -t role -r roles tailscale_router`. The values are in `defaults/main.yml`.

Overrides: `group_vars/appbox_servers.yml`.

Secrets from 1Password (not validated, see the spec header): `tailscale-authkey` (read only at a login).
