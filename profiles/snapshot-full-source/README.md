# OpenWrt snapshot — full-source example

This profile demonstrates **mode 4: full-source** against the current OpenWrt `main` branch.

Use this mode when the goal is to build a distribution/package set from source rather than only one firmware's dependency graph. The builder enables OpenWrt's `CONFIG_ALL`, `CONFIG_ALL_KMODS`, and `CONFIG_ALL_NONSHARED` selections after installing the configured feeds.

By default this example leaves `FEED_NAMES` unset, so all default feeds are prepared and their available packages participate in the full build. A copied profile may set, for example, `FEED_NAMES=packages luci routing` to make a full build of only those feeds plus the OpenWrt core tree.

This profile intentionally does not use an SDK or external toolchain. It is the slowest and most complete example: host tools, target toolchain, kernel, target, and the selected full package universe are built from source.

For normal firmware creation, prefer ImageBuilder, release-patched, or selective-source. Full-source exists for cases where producing or validating a broad package repository is actually required.

See the [profile reference](../../docs/profiles.md) for feed semantics and the four build modes.
