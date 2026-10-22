# proxy_server

The nginx reverse proxy on proxy1, with certbot from Debian. The proxy hosts ran in Nginx
Proxy Manager (ct104) until 2026-10. The hosts and certificates are in the inventory and
render into one file. There is no UI.

- Playbook: `playbooks/proxy_servers.yml` (proxy_servers)
- Depends on: `debian_lxc`

## What it does

1. Installs nginx, certbot and the Cloudflare DNS plugin.
2. Writes the Cloudflare credentials and a certbot deploy hook that reloads nginx.
3. Issues missing certificates (DNS-01). `certbot.timer` renews them.
4. Writes the nginx snippets and the proxy config. The handlers test the config before they
   reload nginx.

## Variables

`meta/argument_specs.yml` lists the inputs, with their types and defaults. Ansible
validates them when the role starts. To read them:
`uv run ansible-doc -t role -r roles proxy_server`. The values are in `defaults/main.yml`.

Overrides: `group_vars/proxy_servers.yml` (`proxy_server_hosts`, `proxy_server_certs`).

Secrets from 1Password (not validated, see the spec header): `cloudflare-dns`.
