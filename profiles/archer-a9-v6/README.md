# TP-Link Archer A9 v6

Builds OpenWrt 25.12 for the TP-Link Archer A9 v6 from a custom OpenWrt fork containing the QCN5502 ath9k support required by the router's 2.4 GHz radio.

- Method: `source`
- Target: `ath79/generic`
- Device: `tplink_archer-a9-v6`
- Repository: `https://github.com/demonccc/openwrt.git`
- Ref: `openwrt-25.12-archerA9v6`

This profile demonstrates why a source build is useful when the required device support or patches are not available in the official stable OpenWrt tree.

Because it is a source build, it supports custom feeds, Git packages and optional embedded profile `files/`.
