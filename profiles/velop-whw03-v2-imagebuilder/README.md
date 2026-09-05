# Linksys Velop WHW03 V2

Builds OpenWrt 25.12.5 for the Linksys Velop WHW03 V2 using the official OpenWrt ImageBuilder.

- Method: `imagebuilder`
- Target: `ipq40xx/generic`
- Device: `linksys_whw03v2`
- Release: `25.12.5`
- Source: official OpenWrt ImageBuilder

Profile-specific package choices:

- replace ath10k-ct with the upstream ath10k driver and firmware for QCA4019 and QCA9888;
- replace `wpad-basic-mbedtls` with `wpad-mbedtls`;
- add LuCI and firmware management tools;
- add batman-adv, usteer, and irqbalance packages;
- add `iputils-arping`, `tcpdump`, and `ethtool` for diagnostics.

No custom network topology or network configuration is embedded by this profile.

See the [profile reference](../../docs/profiles.md) for ImageBuilder behavior and profile file semantics.
