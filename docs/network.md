# Network at the new house

The networks, Wi-Fi, fixed IPs and switch ports are in
`inventories/prod/group_vars/all/unifi.yml`. This file covers the hardware, the cabling and
the setup order. The subnets are the same as at the old place, so the hosts need no change
(`docs/move.md`, "What depends on the old network").

## Hardware

| Device | Role |
| --- | --- |
| UCG-Fiber | Gateway and UniFi Network app. WAN: Openreach ONT on port 1 (2.5 GbE) |
| USW-Flex-2.5G-8 | Rack switch, uplink on its SFP+ to UCG port 6 (DAC) |
| Ceph switch (UniFi, model not known) | Ceph network only (`enp2s0` of pve1-3). Uplink to the Flex for management |
| U7 Pro XG Wall | Wired AP: UCG port 5 (10 GbE) to the LAN in of a 10G PoE injector, PoE out to the AP |
| U7 Pro Wall (2) | Wireless mesh to the XG Wall, power from injectors |

The UCG-Fiber replaces a UXG-Fiber (ordered by mistake). The UXG has no Network app.

## Decisions (craig, 2026-11-20)

- The subnets and VLAN IDs of the old place stay. Lab is VLAN 100 and KVM is VLAN 90. The
  Relays network (VLAN 60) and the UK Routed network (192.168.200.0/24) are not used.
- Home, IoT and Lab DHCP give only .53 and .54 as DNS. When the lab is off, these clients
  have no DNS.
- No DHCP domain name. The old `local` is reserved for mDNS (RFC 6762).
- New SSID names and new passphrases. The passphrases are in 1Password
  (`unifi-wifi-home`, `unifi-wifi-iot`, `unifi-wifi-guest`).
- The Ceph switch is adopted. VLAN 5 stays on that switch.

## WAN

The plan is EE full fibre at 1.6 Gbps, so a 2.5 GbE port is enough. Port 5 (10 GbE, the
default WAN) is set to LAN for the XG Wall. The settings come from EE's third-party router
page, through [eggg.uk/scraps/fttp](https://eggg.uk/scraps/fttp/):

- Connection PPPoE, username `bthomehub@btbroadband.com`, password `bt`, CHAP, DNS from the
  ISP. These are EE's shared values, not account secrets.
- EE says VLAN 101. That author had a UXG-Fiber on an Openreach ONT, and the connection
  worked only without a VLAN tag. Try 101 first, then untagged.
- IPv6 off at first.

## Setup order (bench, before the move)

1. Set up the UCG-Fiber with a local admin. Put the login and an API key
   (Settings, Control Plane, Integrations) in 1Password.
2. Adopt the Flex, the Ceph switch and the APs. A switch that was adopted at the old place
   needs a factory reset first.
3. Run the `unifi_network` role: `--check --diff`, then a real run.
4. Set the Ceph switch ports before you connect pve1-3 to it. After a reset, all its ports
   are on Home. The Ceph traffic then floods into Home through the uplink.
5. Read the MACs of the NAS, the KVMs and Home Assistant from the client list into
   `unifi_network_clients`.

## Not known yet

- The SSID names (craig).
- Whether EE needs VLAN 101 on this line.
- The Ceph switch model and its port numbers.
- Whether the UCG answers DNS on 192.168.100.1. pve1-3 and pbs use it as their first
  resolver. Check with `dig @192.168.100.1`.
- Whether the legacy API (fixed IPs, port overrides) accepts the API key, or needs a local
  admin login.
