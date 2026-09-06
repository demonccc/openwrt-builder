# Profile reference

A profile is a directory under `profiles/` that describes one OpenWrt firmware build. For execution instructions, see [Using OpenWrt Builder](usage.md).

## Profile structure

Every profile contains:

```text
profiles/my-router/
  settings
  packages
  feeds
  git-packages
```

It may also contain a profile-specific `README.md` and a `files/` root filesystem overlay.

## The four build modes

The builder deliberately separates *how the image is assembled* from *how much source must be compiled*.

### 1. ImageBuilder

```text
METHOD=imagebuilder
IMAGEBUILDER_URL=https://downloads.openwrt.org/releases/25.12.5/targets/x86/64/openwrt-imagebuilder-25.12.5-x86-64.Linux-x86_64.tar.zst
DEVICE=generic
```

Use this when no OpenWrt source change is required. The official ImageBuilder downloads/uses already-built packages and assembles the requested firmware. This is the fastest mode and its existing implementation is intentionally unchanged.

`packages` is passed to ImageBuilder through `PACKAGES=...`. `feeds` and `git-packages` are ignored.

### 2. Release patched

```text
METHOD=source
BUILD_MODE=release-patched
REPOSITORY=https://github.com/example/openwrt.git
REF=my-release-patch
TARGET=ath79
SUBTARGET=generic
DEVICE=vendor_device
RELEASE_VERSION=25.12.5
RELEASE_REPOSITORY=https://downloads.openwrt.org/releases/25.12.5
PATCH_PACKAGES=kmod-ath9k
SDK_URL=https://downloads.openwrt.org/releases/25.12.5/targets/ath79/generic/openwrt-sdk-25.12.5-ath79-generic_gcc-14.3.0_musl.Linux-x86_64.tar.zst
```

Use this when the source tree is based on a published OpenWrt release and only a small part of that release is changed.

The builder does **not** compile the user package list from `packages`. Instead it:

1. configures the target/subtarget without selecting the device's normal firmware package defaults;
2. enables only `PATCH_PACKAGES` in the source configuration;
3. reuses SDK host tools and toolchain when `SDK_URL` is provided;
4. compiles the custom target/kernel plus the OpenWrt source package(s) that produce `PATCH_PACKAGES`;
5. builds only the minimal local packages required to seed a generated ImageBuilder (`base-files`, toolchain/libc package, kernel package);
6. generates an ImageBuilder from the patched tree;
7. assembles the final device image with the profile `packages`, resolving unchanged userspace packages from `RELEASE_REPOSITORY` as official release binaries.

`PATCH_PACKAGES` is a space- or comma-separated list of **binary OpenWrt package names**. The builder reads OpenWrt's generated package metadata and maps each binary package back to its source Makefile. For example, `kmod-ath9k` maps to the mac80211 source package, so only that source package is requested for compilation rather than every package in the distribution.

This mode is only appropriate when the fork really matches the published release used by `RELEASE_VERSION`, `RELEASE_REPOSITORY`, and any supplied SDK. A random snapshot must use selective source instead.

### 3. Selective source

```text
METHOD=source
BUILD_MODE=selective-source
REPOSITORY=https://github.com/openwrt/openwrt.git
REF=openwrt-25.12
TARGET=x86
SUBTARGET=64
DEVICE=generic
FEED_NAMES=packages luci routing
```

Use this for a snapshot, branch, commit, or release source tree when the complete firmware must be produced from source but there is no reason to build unrelated distribution packages.

The `packages` file becomes normal OpenWrt `CONFIG_PACKAGE_*=y/n` selections. OpenWrt compiles only the selected firmware package graph and the build/runtime dependencies required by that graph. Merely indexing a feed does not cause all packages in that feed to be compiled.

`FEED_NAMES` is optional. In this mode it means **feeds available for package/dependency resolution**, not “compile every package in these feeds”. Restricting feed indexing can reduce preparation time.

`SDK_URL` or `TOOLCHAIN_URL` may optionally accelerate clean builds. They are mutually exclusive.

### 4. Full source

```text
METHOD=source
BUILD_MODE=full-source
REPOSITORY=https://github.com/openwrt/openwrt.git
REF=main
TARGET=x86
SUBTARGET=64
DEVICE=generic
FEED_NAMES=packages luci routing
```

Use this only when the goal is to produce the broad package/distribution build from source, not merely one firmware image.

The builder enables OpenWrt's full package selections (`CONFIG_ALL`, `CONFIG_ALL_KMODS`, and `CONFIG_ALL_NONSHARED`). `FEED_NAMES` controls which default feeds are fetched and installed before that full build. Core OpenWrt packages are still part of the source tree.

If `FEED_NAMES` is omitted, all default feeds are used. Because this is intentionally the most expensive mode, selecting only the feeds that are actually required is recommended.

## Common source settings

All source modes require:

```text
METHOD=source
BUILD_MODE=selective-source | release-patched | full-source
REPOSITORY=...
REF=...
TARGET=...
SUBTARGET=...
DEVICE=...
```

`BUILD_MODE` defaults to `selective-source` for backward compatibility, but new profiles should set it explicitly.

Optional acceleration settings:

```text
SDK_URL=...
TOOLCHAIN_URL=...
FEED_NAMES=packages luci routing
```

An SDK supplies both host tools and the target toolchain, so `SDK_URL` and `TOOLCHAIN_URL` cannot be combined.

## `packages`

One package per line:

```text
luci
dnsmasq-full
-dnsmasq
```

A leading `-` excludes a package. Inline comments are supported.

The meaning depends on the mode:

- **ImageBuilder:** final binary package selection passed directly to the official ImageBuilder.
- **Release patched:** final binary package selection passed to the generated patched ImageBuilder; unchanged packages come from the release repositories.
- **Selective source:** packages to compile/include from source plus dependencies.
- **Full source:** still describes the packages desired in the produced firmware image, while the full distribution/package build is controlled by the mode and feed scope.

Do not list transitive dependencies manually.

## `FEED_NAMES` and `feeds`

`FEED_NAMES` accepts names separated by spaces or commas. With a value such as:

```text
FEED_NAMES=packages luci routing
```

the builder runs `./scripts/feeds update packages luci routing` instead of `update -a`.

In **selective-source**, this limits feed discovery/indexing while compilation remains package-selective.

In **full-source**, this defines which feed trees participate in the full package build.

A `feeds` file may append custom feed definitions using standard OpenWrt syntax (`src-git`, `src-git-full`, `src-link`, or `src-cpy`). If `git-packages` is used, all feeds are indexed because arbitrary external packages may have dependencies the builder cannot know in advance.

## `git-packages`

Format:

```text
REPOSITORY [REF] [PATH]
```

The selected package source is copied under `package/openwrt-builder/`. Add its package name to `packages` when it should be installed in the firmware.

## `files/`

An optional `files/` directory mirrors the firmware root filesystem. Source modes merge it into OpenWrt's `files/`; ImageBuilder modes pass it through `FILES=...`.

For first-boot configuration changes, prefer `/etc/uci-defaults/` scripts rather than replacing whole `/etc/config/*` files.

## Profile README files

A profile README explains only that profile: why its mode was chosen, what release/device it targets, and any profile-specific package or patch decisions. Generic builder behavior belongs in this document.

## Validation

`python3 scripts/build.py validate` checks every profile. For source profiles it validates `BUILD_MODE`, feed syntax, acceleration options, and the extra requirements of `release-patched` (`RELEASE_VERSION`, `RELEASE_REPOSITORY`, and `PATCH_PACKAGES`).
