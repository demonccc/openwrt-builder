# OpenWrt 25.12 — selective-source example

This profile demonstrates **mode 3: selective-source** on the stable OpenWrt 25.12 branch.

Use this mode when source compilation is required, but there is no released-binary reuse strategy such as release-patched. The builder compiles the selected target plus only the packages listed in `packages` and the dependencies OpenWrt resolves for them. It does not intentionally build every package in the distribution.

`FEED_NAMES=packages luci routing` limits feed preparation to those feeds. In selective-source mode that setting means "these feeds are available to resolve selected packages"; it does **not** mean "compile every package in these feeds".

This profile intentionally omits `SDK_URL` and `TOOLCHAIN_URL`, so host tools and the target toolchain are also produced by the source build. A copied profile can add compatible acceleration artifacts when appropriate.

This is the stable-release counterpart of the `snapshot-source` example.

See the [profile reference](../../docs/profiles.md) for the generic selective-source algorithm.
