# Profile reference

A profile is a directory under `profiles/` that describes one OpenWrt firmware build. Generic builder behavior belongs here; a profile's own `README.md` should explain only why that profile exists and its profile-specific choices.

## Profile structure

Every profile contains `settings`, `packages`, `feeds`, and `git-packages`. `README.md` and `files/` are optional. `source-build-targets` is required only by `release-patched`.

## 1. ImageBuilder

ImageBuilder downloads an already-built OpenWrt ImageBuilder and assembles firmware from binary packages:

```text
METHOD=imagebuilder
IMAGEBUILDER_URL=https://downloads.openwrt.org/releases/.../openwrt-imagebuilder-....tar.zst
DEVICE=generic
```

No OpenWrt source packages compile. `packages` controls final firmware contents. `feeds` and `git-packages` are ignored. This is the fastest mode.

## 2. `release-patched`

Use this when a custom source tree is based on an exact released OpenWrt version and only part of that tree must be rebuilt:

```text
METHOD=source
BUILD_MODE=release-patched
REPOSITORY=https://github.com/example/openwrt.git
REF=my-patched-branch
BASE_REF=v25.12.5
SDK=auto
TARGET=ath79
SUBTARGET=generic
DEVICE=vendor_device
```

`REF` is the custom source ref. `BASE_REF` is the exact official release compatibility contract and must be a tag such as `v25.12.5`. The builder checks that it is an ancestor of the custom source.

The profile declares affected OpenWrt make targets in `source-build-targets`, for example:

```text
package/kernel/mac80211/compile
```

The builder compiles the target/kernel and those targets, creates a custom ImageBuilder, injects the locally built APKs, and replaces its repository configuration with the repository configuration from the official ImageBuilder matching `BASE_REF`. Unchanged packages therefore resolve from the exact base release rather than a snapshot.

`BASE_REF` cannot prove arbitrary ABI compatibility. The profile author must ensure that differences from the base release are limited to changes whose affected targets are rebuilt.

## 3. `selective-source`

```text
METHOD=source
BUILD_MODE=selective-source
REPOSITORY=https://github.com/openwrt/openwrt.git
REF=main
TARGET=x86
SUBTARGET=64
DEVICE=generic
FEED_NAMES=packages luci routing
```

`REF` may be any branch, tag, or commit. Packages selected for the firmware plus their dependencies compile from that same source tree.

`FEED_NAMES` limits which feeds are available for package resolution; it does not compile every package in those feeds.

## 4. `full-source`

`full-source` accepts the same kinds of source refs as `selective-source`, but changes package scope:

```text
METHOD=source
BUILD_MODE=full-source
REPOSITORY=https://github.com/openwrt/openwrt.git
REF=main
TARGET=x86
SUBTARGET=64
DEVICE=generic
SDK=none
FEED_NAMES=packages luci routing
```

The builder enables `CONFIG_ALL=y`, `CONFIG_ALL_KMODS=y`, and `CONFIG_ALL_NONSHARED=y`. With `FEED_NAMES`, it installs all package definitions from those feeds before the build. Without it, all default feeds are installed.

The difference between `selective-source` and `full-source` is package scope, not SDK usage.

## SDK acceleration

SDK selection is independent from `BUILD_MODE` and is available to all source modes.

### `SDK=auto`

`SDK=auto` is also the default when neither `SDK` nor `SDK_URL` is set.

For `release-patched`, the release is derived from `BASE_REF`. For `selective-source` and `full-source`, automatic resolution is possible only when `REF` is an exact release tag such as `v25.12.5`.

The builder reads the official target directory under `downloads.openwrt.org` and finds the matching SDK automatically, including its GCC/libc suffix.

For arbitrary refs such as `main`, `openwrt-25.12`, or a custom branch, `SDK=auto` safely falls back to building host tools and the target toolchain from source.

### `SDK=none`

Disables SDK reuse. OpenWrt builds host tools and target toolchain from source. It does not change package scope. `release-patched + SDK=none` still reuses unchanged packages from `BASE_REF`.

### `SDK_URL`

An explicit override:

```text
SDK_URL=https://downloads.openwrt.org/releases/.../openwrt-sdk-....tar.zst
```

Use it to pin a known-compatible SDK. `SDK` and `SDK_URL` are mutually exclusive.

## Source references

`selective-source` and `full-source` accept any branch, tag, or commit in `REF`. `release-patched` additionally requires exact `BASE_REF=vX.Y.Z` because it reuses release binaries.

## Feed selection

`FEED_NAMES=packages luci routing` accepts space- or comma-separated names.

In `selective-source` and `release-patched`, feeds are package sources; compilation remains driven by firmware selection, dependencies, and explicit patched targets. In `full-source`, selected feeds expose their complete package universe to the `CONFIG_ALL*` build.

If `git-packages` is used in a non-full build, all feeds are indexed because dependencies of external packages cannot be known in advance.

## `packages`

One package per line. A leading `-` excludes a package:

```text
luci
dnsmasq-full
-dnsmasq
```

List deliberate firmware choices and let OpenWrt resolve dependencies.

## `feeds`

Source modes accept standard OpenWrt feed entries such as `src-git`, `src-git-full`, `src-link`, and `src-cpy`. ImageBuilder ignores this file.

## `git-packages`

Source modes can import OpenWrt package directories directly from Git using `REPOSITORY [REF] [PATH]`. The package must still be selected in `packages` if it should enter the firmware. ImageBuilder ignores this file.

## Embedded files

An optional `files/` directory mirrors the generated root filesystem. Prefer `/etc/uci-defaults/` scripts for changes that should apply after OpenWrt creates device defaults.

## Validation

Run `python3 scripts/build.py validate`, or use Docker as documented in [Using OpenWrt Builder](usage.md). Validation checks mode requirements, SDK combinations, package/feed syntax, and release-patched target declarations.
