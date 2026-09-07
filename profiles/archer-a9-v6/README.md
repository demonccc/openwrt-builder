# TP-Link Archer A9 v6 — release-patched

This profile uses mode 2, `release-patched`.

The router needs custom QCN5502 support in ath9k for its integrated 2.4 GHz radio, so the official ImageBuilder alone is insufficient. Recompiling every normal userspace package would also waste time.

The profile builds `openwrt-25.12.5-archerA9v6`, declares `BASE_REF=v25.12.5`, uses `SDK=auto`, and rebuilds the target/kernel plus `package/kernel/mac80211/compile`. The final custom ImageBuilder is pinned to the repository configuration from the official 25.12.5 ImageBuilder, so unchanged packages come from that exact base release.

`openwrt-25.12.5-archerA9v6` is based directly on the official `v25.12.5` commit and contains one Archer/QCN5502 commit on top. It does not include the later commits from the moving `openwrt-25.12` stable branch.

`source-build-targets` contains `package/kernel/mac80211/compile` because the QCN5502 patch changes ath9k through OpenWrt's mac80211 package.

With `SDK=auto`, the SDK is resolved from `BASE_REF`. Using `SDK=none` would keep the same `release-patched` package scope while rebuilding host tools and the target toolchain locally.

This source lineage is appropriate for the `release-patched` compatibility model. A successful firmware build and device test are still required before treating a new image as validated for deployment.

For a build that follows the moving OpenWrt 25.12 stable branch instead, use [`archer-a9-v6-selective-source`](https://github.com/demonccc/openwrt-builder/blob/main/profiles/archer-a9-v6-selective-source/README.md).

See [Profile reference](https://github.com/demonccc/openwrt-builder/blob/main/docs/profiles.md).
