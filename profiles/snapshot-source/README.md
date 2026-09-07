# OpenWrt snapshot — selective-source example

This profile demonstrates **mode 3: selective-source** against the current OpenWrt `main` branch.

Use it when building from a snapshot or arbitrary source revision where matching release binaries cannot be trusted or reused. The builder compiles the selected target plus only the packages in `packages` and the dependencies OpenWrt resolves for them. Packages that are merely present in OpenWrt feeds are not intentionally compiled.

`FEED_NAMES=packages luci routing` limits feed preparation. In this mode the feed list defines where selected packages may come from; it does not select whole feeds for compilation.

The profile intentionally does not use an SDK because a moving snapshot must match its exact build state. If a compatible snapshot SDK is deliberately pinned to the same revision, a copied profile may use it, but the safe generic example is a clean selective source build.

Use `snapshot-full-source` instead only when the goal is to compile the broad distribution/package universe, not merely firmware contents.

See the [profile reference](../../docs/profiles.md) for the generic selective-source algorithm.
