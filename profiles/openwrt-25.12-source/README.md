# OpenWrt 25.12 selective source

This profile uses mode 3, `selective-source`.

It builds OpenWrt `v25.12.5` for generic x86/64 and compiles only packages selected for the firmware plus dependencies.

It uses an explicit `SDK_URL` to pin a known SDK artifact manually. `selective-source` itself does not require a release: `REF` can be any branch, tag, or commit. This profile uses the exact tag because its explicit SDK URL is known to match.

`FEED_NAMES=packages luci routing` limits package resolution to those feeds; it does not compile every package in them.

See [Profile reference](../../docs/profiles.md).
