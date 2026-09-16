# TP-Link Archer A9 v6 — OpenWrt 25.12 stable

This profile follows the moving OpenWrt `openwrt-25.12` stable line through the custom `openwrt-25.12-archerA9v6` branch.

The public ID ends in `25.12` to make that rolling stable-line behavior explicit without calling it a snapshot. The catalog validator requires an `openwrt-25.12...` source ref for this form and rejects a pinned point-release SDK URL.

Internally the builder uses `selective-source`, compiling the selected firmware packages and their dependencies from that source tree. The build mode is intentionally not part of the public profile name.

For the exact OpenWrt 25.12.5 base, use [`archer-a9-v6-25.12.5`](../archer-a9-v6-25.12.5/README.md).
