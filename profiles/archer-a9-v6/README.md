# TP-Link Archer A9 v6 — release-patched example

This profile demonstrates mode 2, `release-patched`.

The router needs custom QCN5502 support in ath9k for its integrated 2.4 GHz radio, so the official ImageBuilder alone is insufficient. Recompiling every normal userspace package would also waste time.

The profile builds the custom `openwrt-25.12-archerA9v6` ref, declares `BASE_REF=v25.12.5`, uses `SDK=auto`, and rebuilds the target/kernel plus `package/kernel/mac80211/compile`. The final custom ImageBuilder is pinned to the repository configuration from the official 25.12.5 ImageBuilder, so unchanged packages come from that base release.

`source-build-targets` contains `package/kernel/mac80211/compile` because the QCN5502 patch changes ath9k through OpenWrt's mac80211 package.

This is intentionally the `SDK=auto` example. `SDK=none` would remain release-patched; it would only rebuild host tools/toolchain locally.

See [Profile reference](../../docs/profiles.md).
