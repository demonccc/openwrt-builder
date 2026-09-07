# OpenWrt snapshot full source — no SDK example

This profile demonstrates mode 4, `full-source`, from current OpenWrt `main`.

`REF=main` shows that full-source can use an arbitrary branch rather than a release. `SDK=none` forces host tools and target toolchain to build from source. `FEED_NAMES=packages luci routing` shows that a full build can still limit which feeds contribute their complete package universe.

The builder enables `CONFIG_ALL`, `CONFIG_ALL_KMODS`, and `CONFIG_ALL_NONSHARED`. Unlike `selective-source`, package scope is intentionally broad rather than limited to firmware packages plus dependencies.

See [Profile reference](../../docs/profiles.md).
