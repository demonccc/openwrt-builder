# TP-Link Archer A9 v6

Builds OpenWrt 25.12 for the TP-Link Archer A9 v6 from a custom OpenWrt fork containing the QCN5502 ath9k support required by the router's 2.4 GHz radio.

- Method: `source`
- Target: `ath79/generic`
- Device: `tplink_archer-a9-v6`
- Repository: `https://github.com/demonccc/openwrt.git`
- Ref: `openwrt-25.12-archerA9v6`

The custom source repository is the profile-specific requirement; the rest of the build behavior follows the normal source profile contract.

See the [profile reference](../../docs/profiles.md) for source-build behavior and profile file semantics.
