# TP-Link Archer A9 v6 — release-patched example

This profile demonstrates **build mode 2: `release-patched`**.

The Archer A9 v6 needs the custom QCN5502/ath9k work from `demonccc/openwrt@openwrt-25.12-archerA9v6` so its integrated 2.4 GHz radio is recognized. The patch changes the kernel wireless driver, but it does not justify recompiling unrelated userspace packages such as LuCI, dnsmasq, mosquitto, or openNDS.

For that reason this profile is anchored to OpenWrt **25.12.5** and declares:

```text
PATCH_PACKAGES=kmod-ath9k
```

Only the patched kernel/target path and the source package that produces `kmod-ath9k` are custom-built, together with the minimal local artifacts required to generate a patched ImageBuilder. The final package list in `packages` is then assembled using the official 25.12.5 binary repositories whenever a package is unchanged.

The official 25.12.5 `ath79/generic` SDK is also reused so the normal host tools and target toolchain do not need to be rebuilt for every clean run.

Use this profile as a template when a custom fork is based on a specific released OpenWrt version and only a small set of packages/kernel components are affected by the patch. If the source does not correspond to a published release, use `selective-source` instead.
