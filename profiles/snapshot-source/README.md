# OpenWrt snapshot — selective source example

This profile demonstrates **build mode 3: `selective-source`** against current OpenWrt `main`.

A snapshot or arbitrary source commit cannot safely reuse the package set from an older released firmware as if it were ABI-identical. This mode therefore builds the requested firmware from the selected source tree, but still avoids the wasteful distribution-wide build: only packages selected in `packages` and their required dependencies are compiled.

`FEED_NAMES=packages luci routing` demonstrates optional feed scoping. Those feeds are made available for resolution; their complete contents are not compiled merely because the feeds are listed.
