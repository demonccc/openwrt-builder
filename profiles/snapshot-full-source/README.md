# OpenWrt snapshot full source

This profile uses mode 4, `full-source`, from current OpenWrt `main`.

`REF=main` means the build follows an arbitrary source branch rather than an exact release. `SDK=none` forces host tools and the target toolchain to build from source. `FEED_NAMES=packages luci routing` limits which feeds contribute their complete package universe.

The builder enables `CONFIG_ALL`, `CONFIG_ALL_KMODS`, and `CONFIG_ALL_NONSHARED`. Unlike `selective-source`, package scope is intentionally broad rather than limited to firmware packages plus dependencies.

See [Profile reference](../../docs/profiles.md).
