# TP-Link Archer A9 v6 — release-patched example

This profile demonstrates **mode 2: release-patched**.

The router needs the QCN5502 ath9k patch series for its integrated 2.4 GHz radio, so an official 25.12 image cannot be used unchanged. At the same time, packages such as LuCI, dnsmasq, mosquitto, openNDS, and other unchanged userspace software should not be rebuilt just because ath9k is patched.

The profile therefore uses the custom `demonccc/openwrt` branch `openwrt-25.12-archerA9v6`, together with the matching official OpenWrt 25.12.5 `ath79/generic` SDK. The builder compiles the patched target/kernel and the explicit entries in `source-build-targets`, generates an ImageBuilder from that patched source state, and lets that ImageBuilder resolve unchanged packages from the official release repositories.

`source-build-targets` contains `package/kernel/mac80211/compile` because the QCN5502 changes live under `package/kernel/mac80211/patches/ath9k`. `target/linux/compile` is always handled automatically by release-patched mode.

`packages` is still the final firmware package selection. It is intentionally different from `source-build-targets`: being installed in the firmware does not imply that a package must be compiled locally.

`FEED_NAMES=packages luci routing` limits feed preparation to the feeds this firmware uses. The SDK must match the release, target, subtarget, compiler, and libc used by the patched branch.

See the [profile reference](../../docs/profiles.md) for the generic release-patched algorithm.
