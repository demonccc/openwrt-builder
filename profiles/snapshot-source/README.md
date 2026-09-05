# Snapshot source build

Builds the current OpenWrt development snapshot directly from the official `openwrt/openwrt` repository `main` branch.

- Method: `source`
- Target: `x86/64`
- Device: `generic`
- Source: official OpenWrt repository

Use this profile when you want the newest OpenWrt source tree and need full source-build capabilities such as custom feeds, Git packages, source patches or embedded profile `files/`.

This is also a useful base profile to copy when creating another snapshot source build.
