# db_server

PostgreSQL, MySQL and Valkey on db1, with hourly dumps.

- Playbook: `playbooks/db_servers.yml` (db_servers)
- Depends on: `common`

## What it does

1. PostgreSQL from pgdg (needs `ubuntu_vm_pgdg_repo`), with `postgresql.conf` settings and
   `pg_hba.conf`.
2. MySQL from repo.mysql.com. The noble archive has only 8.0.
3. Valkey from Percona. The noble archive has only 7.2.
4. Hourly dumps: the latest copy in `/var/backups` (in the nightly PBS backup), and on the
   NAS in `hourly/<HH>` and `daily/<weekday>` slots.

The MySQL admin user is create-only.

## Variables

`meta/argument_specs.yml` lists the inputs, with their types and defaults. Ansible
validates them when the role starts. To read them:
`uv run ansible-doc -t role -r roles db_server`. The values are in `defaults/main.yml`.
