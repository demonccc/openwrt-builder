# Linksys Velop WHW03 V2

Builds OpenWrt 25.12.5 for the Linksys Velop WHW03 V2 using the official OpenWrt ImageBuilder.

- Method: `imagebuilder`
- Target: `ipq40xx/generic`
- Device: `linksys_whw03v2`
- Release: `25.12.5`
- Source: official OpenWrt ImageBuilder

The profile keeps the normal OpenWrt device defaults and adds only intentional package changes for this hardware:

- replaces the ath10k-ct driver and firmware with the upstream ath10k variants for QCA4019 and QCA9888;
- replaces `wpad-basic-mbedtls` with `wpad-mbedtls`;
- adds LuCI and firmware management tools;
- adds batman-adv mesh packages;
- adds usteer and irqbalance with their LuCI applications;
- adds `iputils-arping`, `tcpdump`, and `ethtool` for diagnostics.

This profile does not embed a custom network topology or device-specific network configuration. Without an optional `files/` directory, the generated firmware uses the normal OpenWrt defaults for the device.

`feeds` and `git-packages` are ignored because this is an ImageBuilder profile.
