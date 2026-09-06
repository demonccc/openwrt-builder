# OpenWrt snapshot — full source example

This profile demonstrates **build mode 4: `full-source`**.

Use it when the goal is intentionally to build the broad OpenWrt package/distribution set from source rather than only the dependency graph required by one firmware image. This is the slowest mode and is expected to consume substantially more CPU, storage, and time than the other modes.

The example scopes the external feed build to:

```text
FEED_NAMES=packages luci routing
```

In `full-source` mode that selection is significant: the listed feeds are fetched and installed for the full package build. Change the list to match the distribution you want to produce, or omit `FEED_NAMES` to use every default feed.

This profile deliberately uses current `main` so it also serves as the example for a from-zero snapshot/distribution build.
