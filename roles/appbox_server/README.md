# appbox_server

appbox1, the VPS at Appbox in Amsterdam. It runs the download services as one compose
project. The web UIs bind to the tailnet IP only. The P2P ports listen on all addresses.
See `docs/appbox.md`.

- Playbook: `playbooks/appbox_servers.yml` (appbox_servers)
- Depends on: `common`

## What it does

1. Installs the base packages, and sets the timezone and the hostname.
2. Configures ufw: SSH and `appbox_server_open_ports` from the internet, everything else
   over tailscale0.
3. Installs Docker (`docker_host`, entry point `install-docker`). Docker starts after
   tailscaled, and can bind to the tailnet IP before the IP exists.
4. Mounts the NAS shares over Tailscale at boot.
5. Renders `appbox_server_compose_src` (`stacks/appbox1/`) and its `.env`, and starts the
   services.

## Variables

`meta/argument_specs.yml` lists the inputs, with their types and defaults. Ansible
validates them when the role starts. To read them:
`uv run ansible-doc -t role -r roles appbox_server`. The values are in `defaults/main.yml`.

Overrides: `inventories/prod/host_vars/appbox1.yml`. The `.env` values come from 1Password.
