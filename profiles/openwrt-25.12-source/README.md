# OpenWrt 25.12 — selective source example

This profile demonstrates **build mode 3: `selective-source`** against the OpenWrt 25.12 source branch.

Use this mode when the firmware must be built from source, but there is no reason to compile packages that are not selected for the image and are not dependencies of those packages.

`FEED_NAMES=packages luci routing` is intentionally present to show that feed selection in this mode only limits which feeds are fetched/indexed for dependency resolution. It does **not** request a full compilation of those feeds.

The `packages` file remains the intentional firmware package list. OpenWrt resolves and builds the required dependency graph.
