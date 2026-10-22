# docker_host

Docker engine and swarm membership on docker1-3.

- Playbook: `playbooks/docker_hosts.yml` (docker_hosts)
- Depends on: `common`

## What it does

1. Installs the pinned Docker engine and holds the packages.
2. Configures the Docker daemon and creates the bind-mount directories of the swarm
   services.
3. On the manager, initialises the swarm and deploys the Portainer and Traefik bootstrap
   stack when the stack is absent. Portainer manages the stack after that.
4. On a worker, joins the swarm through `docker_host_manager`.

## Variables

`meta/argument_specs.yml` lists the inputs, with their types and defaults. Ansible
validates them when the role starts. To read them:
`uv run ansible-doc -t role -r roles docker_host`. The values are in `defaults/main.yml`.

Overrides: `group_vars/docker_hosts.yml`.
