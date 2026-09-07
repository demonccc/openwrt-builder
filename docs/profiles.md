# Profile reference

A profile is a directory under `profiles/` that describes one OpenWrt firmware build. Generic builder behavior belongs here; a profile's own `README.md` should explain only why that profile exists and its profile-specific choices.

## Profile structure

Every profile contains `settings`, `packages`, `feeds`, and `git-packages`. `README.md` and `files/` are optional. `source-build-targets` is required only by `release-patched`.

The canonical reference profiles live in the upstream repository, so links in this document remain useful even if a clone removes its local `profiles/` directory.

## 1. ImageBuilder

ImageBuilder downloads an already-built OpenWrt ImageBuilder and assembles firmware from binary packages:

```text
METHOD=imagebuilder
IMAGEBUILDER_URL=https://downloads.openwrt.org/releases/.../openwrt-imagebuilder-....tar.zst
DEVICE=generic
```

No OpenWrt source packages compile. `packages` controls final firmware contents. `feeds` and `git-packages` are ignored. This is the fastest mode.

Profiles:
- [Velop WHW03 v2 on OpenWrt 25.12](https://github.com/demonccc/openwrt-builder/tree/main/profiles/velop-whw03-v2-imagebuilder)
- [Generic x86/64 on OpenWrt 24.10](https://github.com/demonccc/openwrt-builder/tree/main/profiles/openwrt-24.10-imagebuilder)

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

`REF` is the custom source ref. `BASE_REF` is the exact official release compatibility contract and must be a tag such as `v25.12.5`. The builder checks that the official base release commit is an ancestor of the custom source.

See the exact `v25.12.5 + QCN5502` example in the [Archer A9 v6 settings](https://github.com/demonccc/openwrt-builder/blob/main/profiles/archer-a9-v6/settings).

The profile declares affected OpenWrt make targets in `source-build-targets`, for example:

```text
package/kernel/mac80211/compile
```

See the [Archer A9 v6 source-build-targets](https://github.com/demonccc/openwrt-builder/blob/main/profiles/archer-a9-v6/source-build-targets).

The builder resolves the complete firmware package selection with OpenWrt `defconfig`, compiles the target/kernel and the explicit `source-build-targets`, and also rebuilds every selected `kmod-*` source package against that custom kernel. This includes kernel modules selected indirectly through dependencies of userspace packages. A patched kernel normally has a different kernel version/ABI hash, so official release kmods cannot safely be mixed with the locally generated kernel even when both come from the same `BASE_REF` release.

After the required source units and kernel modules are built, the builder creates a custom ImageBuilder, injects the locally built APKs, and replaces its repository configuration with the repository configuration from the official ImageBuilder matching `BASE_REF`. Userspace packages that are not rebuilt therefore resolve from the exact base release, while selected kernel modules resolve from the local package set built against the custom kernel.

`BASE_REF` cannot prove arbitrary ABI compatibility. The builder treats kernel modules as kernel-ABI-coupled and rebuilds all selected kmods automatically; the profile author remains responsible for declaring any additional non-kernel source units affected by the patch set in `source-build-targets`.

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

`REF` may be any branch, tag, or commit. Packages selected for the firmware plus their dependencies compile from that same source tree. Unlike `full-source`, this mode does not enable `CONFIG_ALL`, `CONFIG_ALL_KMODS`, or `CONFIG_ALL_NONSHARED`.

`FEED_NAMES` limits which feeds are available for package resolution; it does not compile every package in those feeds.

Examples:
- [Archer A9 v6 on the custom OpenWrt 25.12 stable-derived branch](https://github.com/demonccc/openwrt-builder/blob/main/profiles/archer-a9-v6-selective-source/settings)
- [OpenWrt 25.12.5 selective source](https://github.com/demonccc/openwrt-builder/blob/main/profiles/openwrt-25.12-source/settings)

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

See the current snapshot configuration in [snapshot-full-source settings](https://github.com/demonccc/openwrt-builder/blob/main/profiles/snapshot-full-source/settings).

## SDK acceleration

SDK selection is independent from `BUILD_MODE` and is available to all source modes.

### `SDK=auto`

`SDK=auto` is also the default when neither `SDK` nor `SDK_URL` is set.

For `release-patched`, the release is derived from `BASE_REF`. For `selective-source` and `full-source`, automatic resolution is possible only when `REF` is an exact release tag such as `v25.12.5`.

The builder reads the official target directory under `downloads.openwrt.org` and finds the matching SDK automatically, including its GCC/libc suffix.

For arbitrary refs such as `main`, `openwrt-25.12`, or a custom branch, `SDK=auto` safely falls back to building the target toolchain from source. A profile may use `SDK=none` to state that choice explicitly.

See `SDK=auto` together with `BASE_REF` in the [Archer A9 v6 release-patched settings](https://github.com/demonccc/openwrt-builder/blob/main/profiles/archer-a9-v6/settings).

### `SDK=none`

Disables SDK reuse. OpenWrt builds the target toolchain from source. Host tools may still come from an applicable official OpenWrt prebuilt-tools image when the builder can prove compatibility. It does not change package scope.

See explicit `SDK=none` in the [Archer A9 v6 selective-source settings](https://github.com/demonccc/openwrt-builder/blob/main/profiles/archer-a9-v6-selective-source/settings) and [snapshot-full-source settings](https://github.com/demonccc/openwrt-builder/blob/main/profiles/snapshot-full-source/settings).

### `SDK_URL`

An explicit override:

```text
SDK_URL=https://downloads.openwrt.org/releases/.../openwrt-sdk-....tar.zst
```

Use it to pin a known-compatible SDK. `SDK` and `SDK_URL` are mutually exclusive.

See an explicit SDK pin in the [openwrt-25.12-source settings](https://github.com/demonccc/openwrt-builder/blob/main/profiles/openwrt-25.12-source/settings).

## Source references

`selective-source` and `full-source` accept any branch, tag, or commit in `REF`. `release-patched` additionally requires exact `BASE_REF=vX.Y.Z` because it reuses release binaries.

Examples:
- exact-release custom patch: [Archer A9 v6 release-patched settings](https://github.com/demonccc/openwrt-builder/blob/main/profiles/archer-a9-v6/settings)
- stable-derived custom branch: [Archer A9 v6 selective-source settings](https://github.com/demonccc/openwrt-builder/blob/main/profiles/archer-a9-v6-selective-source/settings)
- exact release `REF`: [OpenWrt 25.12 selective-source settings](https://github.com/demonccc/openwrt-builder/blob/main/profiles/openwrt-25.12-source/settings)
- moving branch `REF=main`: [snapshot full-source settings](https://github.com/demonccc/openwrt-builder/blob/main/profiles/snapshot-full-source/settings)

## Feed selection

`FEED_NAMES=packages luci routing` accepts space- or comma-separated names.

In `selective-source`, feeds are package sources and compilation remains driven by firmware selection and dependencies. In `release-patched`, the configured feeds are installed as package definitions so OpenWrt can resolve the complete firmware dependency graph; compilation remains limited to explicit patched targets plus the source packages that produce selected kernel modules. In `full-source`, selected feeds expose their complete package universe to the `CONFIG_ALL*` build.

If `git-packages` is used in a non-full build, all feeds are indexed because dependencies of external packages cannot be known in advance.

Examples of `FEED_NAMES`:
- [release-patched Archer A9 v6](https://github.com/demonccc/openwrt-builder/blob/main/profiles/archer-a9-v6/settings)
- [selective-source Archer A9 v6](https://github.com/demonccc/openwrt-builder/blob/main/profiles/archer-a9-v6-selective-source/settings)
- [selective OpenWrt 25.12](https://github.com/demonccc/openwrt-builder/blob/main/profiles/openwrt-25.12-source/settings)
- [full snapshot](https://github.com/demonccc/openwrt-builder/blob/main/profiles/snapshot-full-source/settings)

## `packages`

One package per line. A leading `-` excludes a package:

```text
luci
dnsmasq-full
-dnsmasq
```

List deliberate firmware choices and let OpenWrt resolve dependencies.

Real package selections:
- [Archer A9 v6 packages](https://github.com/demonccc/openwrt-builder/blob/main/profiles/archer-a9-v6/packages)
- [OpenWrt 25.12 selective packages](https://github.com/demonccc/openwrt-builder/blob/main/profiles/openwrt-25.12-source/packages)
- [Velop WHW03 v2 packages](https://github.com/demonccc/openwrt-builder/blob/main/profiles/velop-whw03-v2-imagebuilder/packages)

## `feeds`

Source modes accept standard OpenWrt feed entries such as `src-git`, `src-git-full`, `src-link`, and `src-cpy`. ImageBuilder ignores this file.

See the [Archer A9 v6 feeds file](https://github.com/demonccc/openwrt-builder/blob/main/profiles/archer-a9-v6/feeds).

## `git-packages`

Source modes can import OpenWrt package directories directly from Git using `REPOSITORY [REF] [PATH]`. The package must still be selected in `packages` if it should enter the firmware. ImageBuilder ignores this file.

See the [Archer A9 v6 git-packages file](https://github.com/demonccc/openwrt-builder/blob/main/profiles/archer-a9-v6/git-packages).

## Embedded files

An optional `files/` directory mirrors the generated root filesystem. Prefer `/etc/uci-defaults/` scripts for changes that should apply after OpenWrt creates device defaults.

See the [Velop WHW03 v2 profile](https://github.com/demonccc/openwrt-builder/tree/main/profiles/velop-whw03-v2-imagebuilder) for a complete device profile.

## Validation

Use Docker as documented in [Using OpenWrt Builder](https://github.com/demonccc/openwrt-builder/blob/main/docs/usage.md). Running `scripts/build.py` directly on the host is not a supported execution path.
