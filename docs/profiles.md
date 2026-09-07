# Profile reference

A profile is a directory under `profiles/` describing one reproducible OpenWrt firmware build. The profile README explains *why that profile exists*; this document explains *how the builder works*.

For execution, GitHub Actions, runners, and command examples, see [Using OpenWrt Builder](usage.md).

## Profile structure

Every profile has:

```text
profiles/my-profile/
  settings
  packages
  feeds
  git-packages
```

Optional entries:

```text
  README.md
  files/
  source-build-targets   # required by release-patched
```

`packages` always describes the final firmware package selection. `source-build-targets` has a different meaning: it describes OpenWrt make targets whose source must be rebuilt because a release-patched profile changes them.

## The four build modes

### 1. ImageBuilder

```text
METHOD=imagebuilder
IMAGEBUILDER_URL=https://downloads.openwrt.org/.../openwrt-imagebuilder-....tar.zst
DEVICE=generic
```

Use this whenever an official ImageBuilder already supports the device and no source patch is needed.

The builder downloads the official ImageBuilder and runs `make image` with the contents of `packages`. Kernel, toolchain, host tools, and userspace packages are already built by OpenWrt, so this is the fastest mode.

`feeds` and `git-packages` are ignored in this mode.

Reference profiles: `openwrt-25.12-imagebuilder`, `openwrt-24.10-imagebuilder`.

### 2. release-patched

```text
METHOD=source
BUILD_MODE=release-patched
REPOSITORY=https://github.com/example/openwrt.git
REF=my-release-patch
TARGET=ath79
SUBTARGET=generic
DEVICE=vendor_device
SDK_URL=https://downloads.openwrt.org/releases/.../openwrt-sdk-....tar.zst
FEED_NAMES=packages luci routing
```

Use this when the source tree is based on a published OpenWrt release but contains a patch that requires part of the target or package tree to be rebuilt.

The goal is to avoid rebuilding unrelated release packages.

Algorithm:

1. Clone the patched OpenWrt source tree.
2. Reuse host tools and target toolchain from the matching official SDK.
3. Compile the patched target/kernel.
4. Compile only the explicit OpenWrt make targets in `source-build-targets`.
5. Generate an ImageBuilder from the patched source state.
6. Add locally produced APKs to that generated ImageBuilder.
7. Assemble the final firmware using `packages`; unchanged packages are resolved from the official release repositories.

Example `source-build-targets`:

```text
package/kernel/mac80211/compile
```

`target/linux/compile` is automatic and must not be repeated there.

The SDK must match the release baseline, target, subtarget, libc, compiler, and ABI. This mode is intended for release-based patches, not arbitrary moving snapshots.

Reference profile: `archer-a9-v6`.

### 3. selective-source

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

Use this for snapshots, arbitrary source revisions, or any build where source compilation is required and matching release binaries should not be assumed reusable.

The builder selects the target and the entries in `packages`, then lets OpenWrt resolve dependencies. Only that firmware dependency graph is intentionally compiled. Merely being present in a feed does not cause a package to be built.

`FEED_NAMES` in this mode limits which feeds are updated and made available for dependency resolution. It does **not** mean that every package from those feeds is compiled.

Reference profiles: `openwrt-25.12-source`, `snapshot-source`.

### 4. full-source

```text
METHOD=source
BUILD_MODE=full-source
REPOSITORY=https://github.com/openwrt/openwrt.git
REF=main
TARGET=x86
SUBTARGET=64
DEVICE=generic
```

Use this only when the goal is to build the broad distribution/package universe from source rather than one firmware dependency graph.

The builder installs the selected feeds and enables:

```text
CONFIG_ALL=y
CONFIG_ALL_KMODS=y
CONFIG_ALL_NONSHARED=y
```

With no `FEED_NAMES`, all default feeds are prepared. With:

```text
FEED_NAMES=packages luci routing
```

only those feeds are installed before the full package selections are enabled. The OpenWrt core tree still participates.

This is intentionally the slowest mode and is the one expected to produce the largest compile workload.

Reference profile: `snapshot-full-source`.

## Feed semantics by mode

The same `FEED_NAMES` setting intentionally has mode-specific scope:

| Mode | Meaning of `FEED_NAMES` |
| --- | --- |
| ImageBuilder | Not used |
| release-patched | Limit source/feed preparation for patched components; final unchanged packages come from release repositories |
| selective-source | Feeds available to resolve explicitly selected firmware packages and dependencies |
| full-source | Feeds whose package definitions are installed into the source tree before the full package selections are enabled |

This distinction prevents selective builds from accidentally turning into whole-feed builds while still allowing full-source to restrict the package universe.

## Source acceleration

Source modes may use:

```text
SDK_URL=...
TOOLCHAIN_URL=...
```

They are mutually exclusive.

`SDK_URL` reuses the SDK host staging tree and target toolchain. `TOOLCHAIN_URL` reuses only a compatible target toolchain while OpenWrt still builds host tools.

`release-patched` requires `SDK_URL` because its purpose is specifically to reuse the published release build environment while rebuilding only patched components.

For a moving snapshot, do not reuse a random snapshot SDK: it must correspond to the source state closely enough to be ABI-compatible. The generic `snapshot-source` example therefore performs a clean selective source build.

## `packages`

One package per line:

```text
luci
dnsmasq-full
-dnsmasq
```

A normal name includes the package in the final firmware; a leading `-` excludes it.

In ImageBuilder and release-patched modes, the list becomes the ImageBuilder `PACKAGES` argument. In selective/full source modes, entries are translated to `CONFIG_PACKAGE_<name>=y/n` and OpenWrt resolves dependencies.

Do not list every transitive dependency. List intentional firmware contents and let OpenWrt resolve the graph.

## `source-build-targets`

This file is only for `BUILD_MODE=release-patched` and is required there.

It contains one OpenWrt make target per line. These are source components known to be affected by the patch and therefore explicitly rebuilt.

Example:

```text
package/kernel/mac80211/compile
```

Use OpenWrt source-package build targets, not output package names such as `kmod-ath9k`. A single OpenWrt source package can emit several binary packages, so the make target is the unambiguous unit to rebuild.

## `feeds`

For source modes, each non-comment entry uses standard OpenWrt feed syntax and is appended to `feeds.conf.default` before feed update/install.

Supported prefixes:

```text
src-git
src-git-full
src-link
src-cpy
```

For ImageBuilder, the file exists only for consistent profile structure and is ignored.

## `git-packages`

Source profiles may load an OpenWrt package directly from another Git repository:

```text
REPOSITORY [REF] [PATH]
```

Examples:

```text
https://github.com/example/luci-app-example.git
https://github.com/example/luci-app-example.git v1.2.0
https://github.com/example/openwrt-apps.git main luci-app-example
```

The selected package directory is copied under `package/openwrt-builder/` in the temporary source tree.

Because arbitrary Git packages may have feed dependencies that cannot be known beforehand, selective source profiles containing `git-packages` fall back to indexing/installing all configured feeds before the Git package is added.

## Embedded files

An optional `files/` directory mirrors the OpenWrt root filesystem. Source modes merge it into the source tree's `files/`; ImageBuilder mode passes it through `FILES=...`.

Prefer `/etc/uci-defaults/` for first-boot configuration changes when replacing whole `/etc/config/*` files is unnecessary.

## Validation

`python3 scripts/build.py validate` validates every profile.

For source profiles it validates `BUILD_MODE`, source settings, feed syntax, package syntax, SDK/toolchain mutual exclusivity, and the presence of `source-build-targets` for release-patched profiles.

For ImageBuilder profiles it validates the ImageBuilder URL/device settings and the common profile files.
