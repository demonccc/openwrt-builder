# Using OpenWrt Builder

OpenWrt Builder always runs inside Docker. The same containerized execution model is used locally and by GitHub Actions so Windows, macOS, Linux, and CI use the same Linux build environment and the same `scripts/build.py` behavior.

For build-mode and profile semantics, see the canonical [Profile reference](https://github.com/demonccc/openwrt-builder/blob/main/docs/profiles.md).

For Docker image architecture, local image builds, OpenWrt prebuilt host tools, and Docker Hub publication, see [Docker architecture](https://github.com/demonccc/openwrt-builder/blob/main/docs/docker.md).

## Prerequisite

Install Docker. On Windows and macOS, Docker Desktop is the simplest supported environment; on Linux, use Docker Engine or Docker Desktop.

Clone the repository and run the commands from its root so the checkout can be mounted at `/workspace`.

## Use the upstream published builder image

Pull the canonical upstream image:

```bash
docker pull demonccc/openwrt-builder:latest
```

### Linux / macOS

Validate all profiles:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD:/workspace" \
  demonccc/openwrt-builder:latest \
  python3 scripts/build.py validate
```

Build a profile:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD:/workspace" \
  demonccc/openwrt-builder:latest \
  python3 scripts/build.py build \
  --profile archer-a9-v6 \
  --output artifact
```

`--jobs` is optional. When omitted, `scripts/build.py` uses the CPU count visible inside the container.

### Windows PowerShell

Validate all profiles:

```powershell
docker run --rm `
  -e HOME=/tmp `
  -v "${PWD}:/workspace" `
  demonccc/openwrt-builder:latest `
  python3 scripts/build.py validate
```

Build a profile:

```powershell
docker run --rm `
  -e HOME=/tmp `
  -v "${PWD}:/workspace" `
  demonccc/openwrt-builder:latest `
  python3 scripts/build.py build `
  --profile archer-a9-v6 `
  --output artifact
```

The checkout mount keeps `.work/` and `artifact/` in the local repository directory. Linux/macOS examples map the process to the current host UID/GID so generated files are not owned by root. Docker Desktop handles the bind mount on Windows.

## Use a locally built builder image

If the Docker environment itself is being changed, build the image locally as documented in [Docker architecture](https://github.com/demonccc/openwrt-builder/blob/main/docs/docker.md), then replace the image name in the commands above with:

```text
openwrt-builder:local
```

For example:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD:/workspace" \
  openwrt-builder:local \
  python3 scripts/build.py validate
```

## GitHub Actions firmware build

Run **Build OpenWrt firmware** and choose a profile directory.

The workflow exposes an explicit `builder_image` input. Its default is:

```text
demonccc/openwrt-builder:latest
```

A fork or custom environment can override it with any compatible image, for example:

```text
mydockeruser/openwrt-builder:latest
```

The builder image used to run firmware is intentionally independent from `DOCKERHUB_USERNAME`. `DOCKERHUB_USERNAME` belongs only to the Docker image publication workflow and identifies where that workflow pushes images.

The firmware workflow mounts the current checkout into `/workspace`. Inside the container it executes the same builder used locally:

```bash
python3 scripts/build.py build \
  --profile "$PROFILE" \
  --output artifact \
  --jobs "$(nproc)"
```

There is no separate GitHub Actions implementation for source preparation, SDK selection, or OpenWrt prebuilt host tools. `scripts/build.py` performs that logic itself, including resolving and pulling compatible `ghcr.io/openwrt/tools` artifacts when appropriate. This is why local Docker execution and GitHub Actions follow the same build path.

If the requested builder image is unavailable, the workflow builds the repository Dockerfile locally and then runs the same command inside that image.

Successful builds upload `artifact/` and create a GitHub Release containing the firmware and `BUILD_INFO`.

## Validation workflow

The canonical [profile validation workflow](https://github.com/demonccc/openwrt-builder/blob/main/.github/workflows/validate.yml) also uses:

```text
demonccc/openwrt-builder:latest
```

by default.

Automated push and pull-request validation use that default. Manual `workflow_dispatch` validation exposes the same `builder_image` input so another compatible image can be tested explicitly.

Both Python syntax validation and profile validation run inside Docker; no builder code is executed directly on the GitHub runner.

Inside the container the workflow executes:

```bash
python3 -m py_compile scripts/build.py
python3 scripts/build.py validate
```

## Source override

`--source-ref` can temporarily override `REF` while still using the normal Docker execution path.

Example on Linux/macOS:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD:/workspace" \
  demonccc/openwrt-builder:latest \
  python3 scripts/build.py build \
  --profile openwrt-25.12-source \
  --source-ref v25.12.5 \
  --output artifact
```

When a profile uses an explicit `SDK_URL`, the caller remains responsible for compatibility between that SDK and the overridden source. See the canonical [`openwrt-25.12-source` settings](https://github.com/demonccc/openwrt-builder/blob/main/profiles/openwrt-25.12-source/settings) for an explicit `SDK_URL` example.
