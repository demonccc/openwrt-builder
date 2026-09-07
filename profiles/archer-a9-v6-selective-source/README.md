# TP-Link Archer A9 v6 — selective source

This profile uses mode 3, `selective-source`.

It follows the custom `openwrt-25.12-archerA9v6` branch instead of pinning the firmware to an exact point release. That branch contains the Archer A9 v6 / QCN5502 ath9k support on top of the OpenWrt `openwrt-25.12` stable line.

The branch lineage was verified against upstream OpenWrt: the commit immediately below the Archer/QCN5502 commit (`30d53697c798e61043da296681b9c219ef6b484b`) is an ancestor of the official `openwrt-25.12` branch. At the time of verification it was four commits behind the current upstream stable head.

Because this is a moving stable-derived source tree rather than an exact release base, this profile intentionally does not use `BASE_REF` and does not reuse a point-release SDK. `SDK=none` makes that choice explicit.

`selective-source` selects only the packages requested for this firmware plus their dependencies; it does not enable the `CONFIG_ALL*` package universe used by `full-source`.

The package list is intentionally the same as the `archer-a9-v6` release-patched profile so the two modes can be compared while changing only the source/build strategy.

Use [`archer-a9-v6`](https://github.com/demonccc/openwrt-builder/blob/main/profiles/archer-a9-v6/README.md) when you want the exact `v25.12.5 + Archer/QCN5502` source lineage and official 25.12.5 package repositories.

See [Profile reference](https://github.com/demonccc/openwrt-builder/blob/main/docs/profiles.md).
