# Using OpenWrt Builder

OpenWrt Builder always runs inside Docker. The same containerized execution model is used locally and by GitHub Actions so Windows, macOS, Linux and CI use the same Linux build environment and the same `scripts/build.py` behavior.

Public profiles use `<vendor>-<model>-<openwrt_version>` as their folder and build ID; model parts use underscores. Existing release tags retain their old names. See [`profiles/README.md`](../profiles/README.md) and [`docs/profiles.md`](profiles.md).

## Prerequisite

Install Docker. On Windows and macOS, Docker Desktop is the simplest supported environment; on Linux, use Docker Engine or Docker Desktop.

Clone the repository and run commands from its root so the checkout can be mounted at `/workspace`. The Docker image contains the build environment, while `scripts/` and `profiles/` come from the mounted checkout. Script-only changes do not require rebuilding the Docker image.

Pull the canonical builder image:

```bash
docker pull demonccc/openwrt-builder:latest
```

## Validate profiles

Linux / macOS:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD:/workspace" \
  demonccc/openwrt-builder:latest \
  python3 scripts/build.py validate
```

Windows PowerShell:

```powershell
docker run --rm `
  -e HOME=/tmp `
  -v "${PWD}:/workspace" `
  demonccc/openwrt-builder:latest `
  python3 scripts/build.py validate
```

Catalog/version validation is stricter than the builder's per-profile parser and is also available directly:

```bash
python3 scripts/validate-profile-catalog.py
```

CI runs both forms.

## Build a profile

The exact-release Archer A9 v6 profile is `tplink-archer_a9_v6-25.12.5`.

Linux / macOS:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD:/workspace" \
  demonccc/openwrt-builder:latest \
  python3 scripts/build.py build \
  --profile tplink-archer_a9_v6-25.12.5 \
  --output artifact
```

Windows PowerShell:

```powershell
docker run --rm `
  -e HOME=/tmp `
  -v "${PWD}:/workspace" `
  demonccc/openwrt-builder:latest `
  python3 scripts/build.py build `
  --profile tplink-archer_a9_v6-25.12.5 `
  --output artifact
```

`--jobs` is optional. When omitted, the builder uses the CPU count visible inside the container. Docker Desktop handles the bind mount on Windows, so the Windows command does not use Linux UID/GID mapping.

## Persistent local download cache

Local builds can opt into a persistent cache with:

```text
--cache-dir <path>
```

Recommended location:

```text
.cache/openwrt-builder
```

The cache keeps reusable downloaded inputs: OpenWrt `dl/` source archives and downloaded SDK/ImageBuilder archives. The source checkout, `build_dir/`, target staging state and compilation outputs are recreated.

Example:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD:/workspace" \
  demonccc/openwrt-builder:latest \
  python3 scripts/build.py build \
  --profile tplink-archer_a9_v6-25.12.5 \
  --output artifact \
  --cache-dir .cache/openwrt-builder
```

Windows PowerShell uses the same arguments with PowerShell line continuations.

GitHub Actions intentionally does not pass `--cache-dir`; CI remains clean and ephemeral by default.

## Diagnostics

The `build` command exposes:

```text
--verbosity normal|verbose|debug
--log-file <path>
--jobs <count>
```

Verbosity maps to OpenWrt make behavior internally:

```text
normal  -> default OpenWrt behavior
verbose -> V=s
debug   -> V=sc
```

The builder passes the native make variable directly; callers should not set `V` or `MAKEFLAGS` themselves.

Recommended Archer diagnostic build on Linux/macOS:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD:/workspace" \
  demonccc/openwrt-builder:latest \
  python3 scripts/build.py build \
  --profile tplink-archer_a9_v6-25.12.5 \
  --output artifact \
  --cache-dir .cache/openwrt-builder \
  --jobs 1 \
  --verbosity debug \
  --log-file logs/tplink-archer_a9_v6-25.12.5.log
```

Windows PowerShell:

```powershell
docker run --rm `
  -e HOME=/tmp `
  -v "${PWD}:/workspace" `
  demonccc/openwrt-builder:latest `
  python3 scripts/build.py build `
  --profile tplink-archer_a9_v6-25.12.5 `
  --output artifact `
  --cache-dir .cache/openwrt-builder `
  --jobs 1 `
  --verbosity debug `
  --log-file logs/tplink-archer_a9_v6-25.12.5.log
```

`--log-file` is overwritten on each invocation and must stay outside `--output`, because the firmware output directory is recreated.

## Dependency expansion and troubleshooting

`release-patched` has two different dependency behaviors:

1. The SDK can resolve build-time and ABI dependencies needed to compile an explicitly declared source root. Seeing additional targets in this part of the log is normal.
2. The official ImageBuilder receives only the custom APK allowlist and the patched device artifact. Extra SDK targets should not silently become custom userspace packages.

After a build, inspect the boundary:

```bash
grep -E '^(SOURCE_BUILD|SDK_REGISTERED|SDK_BUILD|PACKAGE_BUILD_ENV|IMAGE_ASSEMBLY_ENV|KMOD_POLICY|CUSTOM_APK_PACKAGES|DEVICE_KERNEL_BASE|DEVICE_KERNEL_ARTIFACT|DEVICE_KERNEL_IN_IMAGEBUILDER|INCLUDE_PACKAGES|EXCLUDE_PACKAGES|FEED_NAMES|UNCHANGED_PACKAGES)=' artifact/BUILD_INFO
```

Use the log together with `BUILD_INFO`:

- If only SDK targets needed by the declared roots appear, the expansion is normally expected.
- If unrelated userspace packages are compiled and copied as custom APKs, inspect `source-build-targets` first. Do not add every package from the dependency log there.
- If a new AudioWRT package causes more work, check its `DEPENDS` and `PKG_BUILD_DEPENDS`. Keep unchanged runtime dependencies supplied by the official release; declare a source root only when the dependency is itself patched or required to produce the custom ABI.
- If `CONFIG_ALL=y`, `CONFIG_ALL_KMODS=y` or a full kernel target appears in a `release-patched` build, the build has crossed into the wrong mode or target path.

The practical fix is to classify the extra package: official runtime dependency, SDK build dependency, or genuinely patched source root. The first two do not automatically belong in `source-build-targets`.

## GitHub Actions firmware build

Run **Build OpenWrt firmware**. The job runs inside the selected builder Docker image and invokes `python3 scripts/build.py` directly. It does not run Docker-in-Docker; the generated `artifact/` directory stays in the Actions workspace for upload and release creation.

The `profile` input is a choice dropdown maintained in `.github/workflows/build.yml`.

The workflow also exposes `builder_image` and `verbosity`. The default builder image is:

```text
demonccc/openwrt-builder:latest
```

Successful builds upload `artifact/` and create a GitHub Release containing the firmware and `BUILD_INFO`.

When adding, removing, or renaming a profile, edit the `profile` options in `.github/workflows/build.yml` in the same pull request. Use the profile directory name as the option value. If the default profile is removed, update `default` too. The catalog validator checks profiles themselves; it does not synchronize the dropdown.

## Locally built builder image

If the Docker environment itself changes, build the image locally as documented in [`docs/docker.md`](docker.md), then replace the image name in the commands above with:

```text
openwrt-builder:local
```

## Source override

`--source-ref` can temporarily override `REF` while using the normal Docker execution path. This is a diagnostic/development override; it does not change the profile catalog identity or its declared version contract.

For example:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD:/workspace" \
  demonccc/openwrt-builder:latest \
  python3 scripts/build.py build \
  --profile generic-x86_64-25.12.5 \
  --source-ref v25.12.5 \
  --output artifact
```

When a profile uses an explicit `SDK_URL`, the caller remains responsible for compatibility between that SDK and a temporary overridden source ref.
