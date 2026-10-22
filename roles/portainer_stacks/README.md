# portainer_stacks

Compares the Portainer stacks on the swarm with `stacks/swarm/<name>.yml.j2`, and updates
them through the API. A check run compares each stack file and the stack env (by hash, only
the names show). A real run updates the stacks that differ with `pullImage: false`, so the
running image digests stay. A stack that is missing from Portainer fails the play. Create it
by hand.

- Playbook: `playbooks/portainer_stacks.yml` (localhost)
- Depends on: none

## What it does

1. Reads the stacks from Portainer and fails on stacks that are missing.
2. Compares each rendered file with Portainer's copy, with env values masked.
3. Compares the stack env by hash.
4. In a real run, updates the stacks that differ.

To run one stack only, add `-e '{"portainer_stacks_only": [name]}'`.

## Variables

`meta/argument_specs.yml` lists the inputs, with their types and defaults. Ansible
validates them when the role starts. To read them:
`uv run ansible-doc -t role -r roles portainer_stacks`. The values are in `defaults/main.yml`.

The stacks and their env are in `group_vars/all/stacks.yml`. `portainer_stacks` is not validated, because its env values are 1Password lookups.

Secrets from 1Password (not validated, see the spec header): `portainer-api`, and the items in the stack env.
