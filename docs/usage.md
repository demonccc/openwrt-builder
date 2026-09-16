# Using OpenWrt Builder

OpenWrt Builder always runs inside Docker. The same containerized execution model is used locally and by GitHub Actions so Windows, macOS, Linux and CI use the same Linux build environment and the same `scripts/build.py` behavior.

Public profiles are versioned. See [`profiles/README.md`](../profiles/README.md) and [`docs/profiles.md`](profiles.md).

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

The exact-release Archer A9 v6 profile is `archer-a9-v6-25.12.5`.

Linux / macOS:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD:/workspace" \
  demonccc/openwrt-builder:latest \
  python3 scripts/build.py build \
  --profile archer-a9-v6-25.12.5 \
  --output artifact
```

Windows PowerShell:

```powershell
docker run --rm `
  -e HOME=/tmp `
  -v "${PWD}:/workspace" `
  demonccc/openwrt-builder:latest `
  python3 scripts/build.py build `
  --profile archer-a9-v6-25.12.5 `
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

The cache keeps reusable downloaded inputs: OpenWrt `dl/` source archives and downloaded SDK/ImageBuilder archives. The source checkout, `build_dir/`, target staging state, generated ImageBuilder and compilation outputs are recreated.

Example:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD:/workspace" \
  demonccc/openwrt-builder:latest \
  python3 scripts/build.py build \
  --profile archer-a9-v6-25.12.5 \
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
  --profile archer-a9-v6-25.12.5 \
  --output artifact \
  --cache-dir .cache/openwrt-builder \
  --jobs 1 \
  --verbosity debug \
  --log-file logs/archer-a9-v6-25.12.5.log
```

Windows PowerShell:

```powershell
docker run --rm `
  -e HOME=/tmp `
  -v "${PWD}:/workspace" `
  demonccc/openwrt-builder:latest `
  python3 scripts/build.py build `
  --profile archer-a9-v6-25.12.5 `
  --output artifact `
  --cache-dir .cache/openwrt-builder `
  --jobs 1 `
  --verbosity debug `
  --log-file logs/archer-a9-v6-25.12.5.log
```

`--log-file` is overwritten on each invocation and must stay outside `--output`, because the firmware output directory is recreated.

## GitHub Actions firmware build

Run **Build OpenWrt firmware**. The `profile` input is a choice dropdown generated from the validated catalog under `profiles/`.

The workflow also exposes `builder_image` and `verbosity`. The default builder image is:

```text
demonccc/openwrt-builder:latest
```

Successful builds upload `artifact/` and create a GitHub Release containing the firmware and `BUILD_INFO`.

When a profile is added, removed or renamed, contributors only change the profile catalog. `scripts/sync-profile-workflow.py` derives the dropdown. After the change lands on `main`, `Sync build profile options` publishes the generated workflow update.

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
  --profile x86-64-25.12.5 \
  --source-ref v25.12.5 \
  --output artifact
```

When a profile uses an explicit `SDK_URL`, the caller remains responsible for compatibility between that SDK and a temporary overridden source ref.
