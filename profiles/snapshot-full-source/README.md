# OpenWrt snapshot full source build

Builds the current OpenWrt snapshot from the official source tree without using any prebuilt SDK or external toolchain acceleration.

- Method: `source`
- Target: `x86/64`
- Device: `generic`
- Ref: `main`
- Host tools: built from source
- Target toolchain: built from source
- Feed indexing: all default feeds

This profile intentionally omits `SDK_URL`, `TOOLCHAIN_URL`, and `FEED_NAMES`.

"Full source build" means OpenWrt builds its own host tools and target toolchain, then builds the selected target, firmware packages, and their dependencies. It does **not** mean compiling every package available in every feed.

Use this profile when validating current OpenWrt snapshot behavior from a completely clean source build, especially on a self-hosted runner intended to build everything itself.

See the [profile reference](../../docs/profiles.md) for source-build behavior and profile file semantics.
