# TP-Link Archer A9 v6 — OpenWrt 25.12.5

This is the exact-release Archer A9 v6 profile. The public profile ID ends in `25.12.5`, and the catalog validator requires that version to match the profile's exact release contract.

Internally it uses `release-patched`: `openwrt-25.12.5-archerA9v6` is based on official `v25.12.5` plus the Archer/QCN5502 support, while unchanged userspace packages remain pinned to the official 25.12.5 repositories. The patched kernel, selected kmods and declared affected source targets are rebuilt locally.

Use this profile when you want a reproducible firmware based on one exact OpenWrt point release.

For the moving OpenWrt 25.12 stable branch, use [`archer-a9-v6-25.12`](../archer-a9-v6-25.12/README.md).
