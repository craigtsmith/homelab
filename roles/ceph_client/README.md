# ceph_client

ceph-common and the CephFS mount on the Ubuntu VMs. The cephx key is aes256k, so the role
installs ceph-common from download.ceph.com and the HWE kernel 7.0.

- Playbook: `playbooks/ubuntu_vms.yml` (ubuntu_vms)
- Depends on: `common`

## What it does

1. Adds the Ceph repository and installs ceph-common.
2. Removes the keyrings of retired CephFS users.
3. If `ceph_client_mount` is true, writes the keyring and the fstab entry with a systemd
   automount. If false, removes the mount, the automount unit and the key.

The new kernel takes effect at the next reboot. The role never reboots.

## Variables

`meta/argument_specs.yml` lists the inputs, with their types and defaults. Ansible
validates them when the role starts. To read them:
`uv run ansible-doc -t role -r roles ceph_client`. The values are in `defaults/main.yml`.

Overrides: `ceph_client_mount: false` in `host_vars/db1.yml` and `host_vars/tailscale1.yml`.

Secrets from 1Password (not validated, see the spec header): `ceph-vm-cephfs` (the key).
