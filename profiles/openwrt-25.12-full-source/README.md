# OpenWrt 25.12 full source build

This is an additional **mode 4: full source** example pinned to the OpenWrt 25.12 branch.

Unlike `openwrt-25.12-source`, this profile is intended to build the broad distribution/package set rather than only the packages selected for one firmware image. `FEED_NAMES=packages luci routing` deliberately limits the feed trees that participate so a full build does not have to include unrelated feeds.

Use this profile when you need release-branch package output built from source. For the canonical mode-4 example, see `snapshot-full-source`.

See the [profile reference](../../docs/profiles.md) for the generic full-source behavior.
