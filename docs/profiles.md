# Profile reference

A profile is a directory under `profiles/` that describes one OpenWrt firmware build. The directory name is the public profile ID used locally and by GitHub Actions.

## Profile naming

Every profile ID must end with its OpenWrt source/version contract:

```text
<device>-<X.Y.Z|X.Y|snapshot>
```

The suffix has one meaning only:

- `X.Y.Z`: exact OpenWrt point release, such as `25.12.5`.
- `X.Y`: moving stable branch for that release line, such as `openwrt-25.12`.
- `snapshot`: OpenWrt development snapshot / `main`.

Examples:

```text
archer-a9-v6-25.12.5
archer-a9-v6-25.12
x86-64-snapshot
```

Build mode is deliberately not encoded in the profile ID. A profile can use `imagebuilder`, `release-patched`, `selective-source`, or `full-source` internally without exposing that implementation detail in its public name.

## Profile structure

Every profile contains:

```text
README.md
settings
packages
feeds
git-packages
```

`source-build-targets` is mandatory only for `release-patched`. `files/` is optional and mirrors files into the generated root filesystem.

The catalog validator rejects unknown top-level entries, symlinks, malformed settings, duplicate packages, invalid feed declarations and invalid Git-package declarations.

## Version contract validation

The version encoded in the directory name is checked against `settings`.

For exact `X.Y.Z` profiles:

- ImageBuilder profiles must use a `/releases/X.Y.Z/` ImageBuilder URL.
- `release-patched` profiles must have matching `BASE_REF=vX.Y.Z`.
- other source modes must use an exact matching `REF=vX.Y.Z`.
- an explicit `SDK_URL` must point to the same release.

For moving `X.Y` profiles:

- the profile must build from source;
- `REF` must match `openwrt-X.Y...`;
- `release-patched` is not allowed because that mode requires an exact release base;
- a point-release `SDK_URL` is not allowed.

For `snapshot` profiles:

- source builds must use `REF=main`;
- ImageBuilder builds must use a `/snapshots/` URL.

## 1. ImageBuilder

ImageBuilder downloads an already-built OpenWrt ImageBuilder and assembles firmware from binary packages:

```text
METHOD=imagebuilder
IMAGEBUILDER_URL=https://downloads.openwrt.org/releases/25.12.5/targets/...
DEVICE=vendor_device
```

No OpenWrt source packages compile. `packages` controls final firmware contents.

Examples:

- [`linksys-velop-whw03-v2-25.12.5`](../profiles/linksys-velop-whw03-v2-25.12.5/)
- [`x86-64-24.10.5`](../profiles/x86-64-24.10.5/)

## 2. `release-patched`

Use this when a custom source tree is based on one exact OpenWrt release and only affected components should be rebuilt:

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

The builder first verifies that the exact official `BASE_REF` is an ancestor of the custom source. It updates the feeds declared by OpenWrt (and any additional feeds from the profile), then registers only the selected feed packages from `packages` and their dependencies so `defconfig` can resolve the final firmware and custom-kernel dependency closure; it does not register every package in each feed. That resolution can mention or build dependencies inside the SDK, but it does not turn the whole selected userspace into local final APKs.

The local build boundary is:

- prepare the patched target state and build the device artifact from the official kernel and patched DTS;
- compile package roots explicitly listed in `source-build-targets` only when the patch requires them;
- use the exact-release official SDK to compile those roots with their genuine build dependencies;
- assemble with the official ImageBuilder matching `BASE_REF`, injecting the patched device artifact and only the declared custom APKs.

Only an explicit local APK allowlist is injected into that ImageBuilder:

```text
selected outputs belonging to source-build-targets
```

`base-files`, `libc` and the kernel package already belong to the official ImageBuilder. Everything else in userspace is resolved from repositories pinned to `BASE_REF`. Unchanged packages such as `hostapd`, `netifd`, `uci`, `ubus`, `libubox`, libraries and utilities remain official release binaries unless they are explicitly part of the patched build boundary.

This distinction is what separates `release-patched` from `selective-source`: selecting a package for the final firmware does not automatically make it a source-build target.

### Dependency expansion

A larger dependency closure in the SDK log is not by itself a bug. OpenWrt may need build-time or ABI dependencies to compile one explicit root. The important question is what reaches the final ImageBuilder:

- expected: extra SDK build targets and official packages resolved by the exact-release repositories;
- suspicious: unrelated userspace APKs copied as custom outputs, `CONFIG_ALL*` expansion, or a full kernel compile when the profile only changes a device/kernel-module boundary;
- corrective action: inspect `source-build-targets`, the package's `DEPENDS`/`PKG_BUILD_DEPENDS`, and the generated `BUILD_INFO`; keep runtime-only dependencies in the `packages` file, and add a source root only when that dependency itself is patched or required for the custom ABI.

The builder intentionally does not guess a universal source boundary from the package graph. The package graph describes what must be available to compile and install; the profile declares which roots are allowed to be rebuilt locally.

`BUILD_INFO` records the boundary after every build, including:

```text
SOURCE_BUILD_TARGETS
SOURCE_BUILD_PACKAGES
SDK_REGISTERED_SOURCE_ROOTS
SDK_BUILD_TARGETS
PACKAGE_BUILD_ENV
KMOD_POLICY
CUSTOM_APK_PACKAGES
IMAGE_ASSEMBLY_ENV=official-imagebuilder
DEVICE_KERNEL_BASE=official-exact-release-vmlinux
DEVICE_KERNEL_ARTIFACT
DEVICE_KERNEL_IN_IMAGEBUILDER
INCLUDE_PACKAGES
EXCLUDE_PACKAGES
FEED_NAMES
UNCHANGED_PACKAGES=official-base-release
```

If an APK required by the local allowlist was not produced, the builder fails instead of silently falling back to an unrelated local package set.

Example: [`archer-a9-v6-25.12.5`](../profiles/archer-a9-v6-25.12.5/).

## 3. `selective-source`

```text
METHOD=source
BUILD_MODE=selective-source
REPOSITORY=https://github.com/openwrt/openwrt.git
REF=v25.12.5
TARGET=x86
SUBTARGET=64
DEVICE=generic
```

Only packages selected for the firmware plus their dependencies compile from the chosen source tree. This mode does not enable the broad `CONFIG_ALL*` package universe.

It may be used with an exact release, as in [`x86-64-25.12.5`](../profiles/x86-64-25.12.5/), or a moving stable branch, as in [`archer-a9-v6-25.12`](../profiles/archer-a9-v6-25.12/).

## 4. `full-source`

`full-source` accepts the same source machinery but enables the broad package universe with `CONFIG_ALL=y`, `CONFIG_ALL_KMODS=y`, and `CONFIG_ALL_NONSHARED=y`.

Example: [`x86-64-snapshot`](../profiles/x86-64-snapshot/), which follows OpenWrt `main`.

## SDK selection

SDK selection does not expand the final package scope. `release-patched` requires an exact-release SDK; other source modes can build without one.

`SDK=auto` resolves an official SDK when compatibility can be proven from an exact release (`BASE_REF` for `release-patched`, or exact `REF` for other source modes). For arbitrary refs it safely falls back to building the target toolchain from source.

`SDK=none` explicitly disables SDK reuse for source modes that support building their own toolchain. `release-patched` requires an exact-release SDK.

`SDK_URL=...` pins an exact SDK and is mutually exclusive with `SDK`. Catalog validation additionally requires a release URL to match an exact `X.Y.Z` profile and rejects point-release SDK URLs for moving `X.Y` profiles.

## `packages`

One package per line. A leading `-` excludes a package:

```text
luci
dnsmasq-full
-dnsmasq
```

The builder validates malformed and duplicate package entries.

## `feeds`

Source profiles accept standard OpenWrt feed declarations such as `src-git`, `src-git-full`, `src-link`, and `src-cpy`. Use this file only for additional feeds; OpenWrt's default feeds require no declaration. The builder updates the configured feeds and resolves selected packages (including their feed dependencies) by name. A profile author does not need to know which feed supplies each package. Feed indexing still scans the whole feed, so an unselected package such as `telegraf` can appear under `Collecting package info` without being registered or included in the firmware. Optional `FEED_NAMES` limits feed updates when the author already knows which feeds are needed; omit it for automatic lookup. ImageBuilder profiles keep the required `feeds` file for a uniform layout, but do not consume it.

## `git-packages`

Source profiles may import package directories directly from Git using:

```text
REPOSITORY [REF] [PATH]
```

The package must still be selected through `packages` to enter the firmware.

## Embedded files

Optional `files/` content is copied into the generated filesystem. Symlinks are rejected by the catalog validator so profile content remains explicit and portable.

## Catalog validation and GitHub Actions

Run:

```bash
python3 scripts/validate-profile-catalog.py
python3 tests/test_profile_catalog.py
```

The normal validation workflow runs these checks automatically. The build workflow has a manually maintained `profile` choice list in `.github/workflows/build.yml`. Add, remove, or rename the corresponding option in the same pull request as a profile change; update the workflow default if needed. Catalog validation checks profile contents and names, but does not enforce which options are exposed in the build workflow.

See [`profiles/README.md`](../profiles/README.md) for the contribution contract and [`docs/usage.md`](usage.md) for Docker commands.
