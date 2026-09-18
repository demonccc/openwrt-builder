# TP-Link Archer A9 v6 — OpenWrt 25.12.5

This is the exact-release Archer A9 v6 profile. The public profile ID ends in `25.12.5`, and the catalog validator requires that version to match the profile's exact release contract.

Internally it uses `release-patched`: `openwrt-25.12.5-archerA9v6` is based on official `v25.12.5` plus the Archer/QCN5502 support.

The release boundary is intentional:

- the patched target/device image pipeline and selected kmods use the custom source tree;
- package roots listed in `source-build-targets` are compiled locally only when the patch requires them;
- the SDK may build genuine dependencies of those roots, but only the declared custom APKs are injected into the final ImageBuilder;
- the official ImageBuilder seeds `base-files`, `libc` and `kernel`; they are not rebuilt as unrelated local userspace roots;
- unchanged userspace packages come from the exact official OpenWrt 25.12.5 release;
- the custom ImageBuilder repositories and host tools are pinned back to the exact official base release.

This prevents a `release-patched` build from drifting into `selective-source` behavior. A package appearing in the SDK dependency log is not automatically a custom firmware package. Packages such as `hostapd`, `netifd`, `uci`, `ubus`, `libubox` and other unchanged userspace dependencies remain official release binaries.

If adding an AudioWRT package causes additional compilation, inspect its `DEPENDS`/`PKG_BUILD_DEPENDS` and compare the SDK targets with `CUSTOM_APK_PACKAGES` in `BUILD_INFO`. Add a source root only when the dependency is patched or required for the custom ABI; do not copy the whole dependency closure into `source-build-targets`.

Use [the dependency troubleshooting guide](../../docs/usage.md#dependency-expansion-and-troubleshooting) for the detailed procedure.

`BUILD_INFO` records the local package policy, official seeded packages and exact injected package list.

Use this profile when you want a reproducible firmware based on one exact OpenWrt point release.

For the moving OpenWrt 25.12 stable branch, use [`archer-a9-v6-25.12`](../archer-a9-v6-25.12/README.md).
