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

The builder verifies that the exact official base release is an ancestor of the custom source, rebuilds the target/kernel, explicit `source-build-targets`, every selected kmod and its transitive kmod dependencies against the custom kernel, then creates a custom ImageBuilder. Unchanged userspace packages resolve from the exact official base release.

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
FEED_NAMES=packages luci routing
```

Only packages selected for the firmware plus their dependencies compile from the chosen source tree. This mode does not enable the broad `CONFIG_ALL*` package universe.

It may be used with an exact release, as in [`x86-64-25.12.5`](../profiles/x86-64-25.12.5/), or a moving stable branch, as in [`archer-a9-v6-25.12`](../profiles/archer-a9-v6-25.12/).

## 4. `full-source`

`full-source` accepts the same source machinery but enables the broad package universe with `CONFIG_ALL=y`, `CONFIG_ALL_KMODS=y`, and `CONFIG_ALL_NONSHARED=y`.

Example: [`x86-64-snapshot`](../profiles/x86-64-snapshot/), which follows OpenWrt `main`.

## SDK selection

SDK choice is independent from build mode.

`SDK=auto` resolves an official SDK when compatibility can be proven from an exact release (`BASE_REF` for `release-patched`, or exact `REF` for other source modes). For arbitrary refs it safely falls back to building the target toolchain from source.

`SDK=none` explicitly disables SDK reuse.

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

Source profiles accept standard OpenWrt feed declarations such as `src-git`, `src-git-full`, `src-link`, and `src-cpy`. ImageBuilder profiles keep this required file for a uniform profile layout, but it is not consumed by ImageBuilder builds.

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

The normal validation workflow runs these checks automatically. The build workflow profile input is a generated `choice` list. `scripts/sync-profile-workflow.py` derives that list only from validated profiles, and `.github/workflows/sync-profile-options.yml` publishes changes after profile-related updates land on `main`.

See [`profiles/README.md`](../profiles/README.md) for the contribution contract and [`docs/usage.md`](usage.md) for Docker commands.
