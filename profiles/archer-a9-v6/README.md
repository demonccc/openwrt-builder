# TP-Link Archer A9 v6

Builds OpenWrt 25.12 for the TP-Link Archer A9 v6 from a custom OpenWrt fork containing the QCN5502 ath9k support required by the router's 2.4 GHz radio.

- Method: `source`
- Target: `ath79/generic`
- Device: `tplink_archer-a9-v6`
- Repository: `https://github.com/demonccc/openwrt.git`
- Ref: `openwrt-25.12-archerA9v6`
- Host tools: OpenWrt `ghcr.io/openwrt/tools:openwrt-25.12` prebuilt tools image
- Target toolchain: official OpenWrt 25.12.5 `ath79/generic` toolchain
- Indexed feeds: `packages`, `luci`, `routing`

The custom source repository is the profile-specific requirement. Host-tool acceleration follows OpenWrt's own CI pattern: the builder extracts `/prebuilt_tools/staging_dir/host` and `/prebuilt_tools/build_dir/host` from the OpenWrt tools image, links them into the source checkout, and runs `scripts/ext-tools.sh --refresh` so `tools/compile` does not rebuild the standard host tools.

The official external toolchain avoids rebuilding GCC, binutils, musl, kernel headers, fortify headers, GDB, and the rest of the target compiler toolchain.

The patched target, kernel, wireless stack, selected packages, package dependencies, and final firmware image are still built from the configured source tree.

Only the default feeds needed by this profile are updated and indexed. The selected packages still resolve their normal transitive dependencies from those feeds and the OpenWrt core tree.

`TOOLS_IMAGE`, `TOOLCHAIN_URL`, and `FEED_NAMES` are optional at the builder level. Removing any of them restores the corresponding native OpenWrt work; removing all three makes the profile a normal full source build.

See the [profile reference](../../docs/profiles.md) for source-build behavior and profile file semantics.
