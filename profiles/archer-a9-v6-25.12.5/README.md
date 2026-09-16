# TP-Link Archer A9 v6 — OpenWrt 25.12.5

This is the exact-release Archer A9 v6 profile. The public profile ID ends in `25.12.5`, and the catalog validator requires that version to match the profile's exact release contract.

Internally it uses `release-patched`: `openwrt-25.12.5-archerA9v6` is based on official `v25.12.5` plus the Archer/QCN5502 support.

The release boundary is intentional:

- the custom kernel/target layer is built from the patched source tree;
- selected kmods are rebuilt against that custom kernel;
- package roots listed in `source-build-targets` are compiled locally only when the patch requires them;
- local package roots are built with `NO_DEPS=1`, so unchanged runtime userspace is not rebuilt transitively;
- the generated ImageBuilder receives only an explicit allowlist of local APKs: `base-files`, `kernel`, selected kmods and selected outputs of `source-build-targets`;
- `libc` and unchanged userspace packages come from the exact official OpenWrt 25.12.5 release;
- the custom ImageBuilder repositories and host tools are pinned back to the exact official base release.

This prevents a `release-patched` build from drifting into `selective-source` behavior. Packages such as `hostapd`, `netifd`, `uci`, `ubus`, `libubox` and other unchanged userspace dependencies must be installed from the official release repositories rather than rebuilt locally.

`BUILD_INFO` records the local package policy and exact injected package list so the boundary is auditable after each build.

Use this profile when you want a reproducible firmware based on one exact OpenWrt point release.

For the moving OpenWrt 25.12 stable branch, use [`archer-a9-v6-25.12`](../archer-a9-v6-25.12/README.md).
