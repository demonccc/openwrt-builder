# Using OpenWrt Builder

This guide covers execution. See the canonical [Profile reference](https://github.com/demonccc/openwrt-builder/blob/main/docs/profiles.md) for build-mode and profile semantics.

## Docker architecture

The project uses two separate Docker/OCI layers with different responsibilities:

- `docker.io/demonccc/openwrt-builder:latest` is the main build environment. It contains Ubuntu and the host-side packages required to run OpenWrt builds.
- `ghcr.io/openwrt/tools:*` is an optional OpenWrt upstream acceleration artifact containing OpenWrt's precompiled host tools.

Firmware builds always execute inside `docker.io/demonccc/openwrt-builder:latest`. The OpenWrt tools image is never used as the main build container.

The builder image intentionally does not contain:

- the `openwrt-builder` repository;
- OpenWrt source;
- a fixed OpenWrt SDK;
- a fixed OpenWrt ImageBuilder;
- profiles.

The current repository checkout is mounted into `/workspace`, so the checked-out `scripts/`, `profiles/`, and documentation are always the source of truth.

The image intentionally has no `ENTRYPOINT`. The caller explicitly runs `python3 scripts/build.py ...` from the mounted checkout.

## Recommended local execution: published Docker image

Pull the canonical image:

```bash
docker pull docker.io/demonccc/openwrt-builder:latest
```

Validate profiles:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD:/workspace" \
  docker.io/demonccc/openwrt-builder:latest \
  python3 scripts/build.py validate
```

Build a profile:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD:/workspace" \
  docker.io/demonccc/openwrt-builder:latest \
  python3 scripts/build.py build \
  --profile archer-a9-v6 \
  --output artifact \
  --jobs "$(nproc)"
```

The bind mount keeps `.work/` and `artifact/` in the local checkout. OpenWrt must not build as root; the image has a non-root default user and the examples map the container process to the current host UID/GID.

## Building the builder image locally

The canonical environment definition is the repository [Dockerfile](https://github.com/demonccc/openwrt-builder/blob/main/Dockerfile).

Build it locally from the repository root:

```bash
docker build \
  --platform linux/amd64 \
  -t openwrt-builder:local \
  .
```

The project currently publishes only `linux/amd64`, matching the GitHub Actions Ubuntu runner used by the build workflows.

Validate the local image with the current checkout:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD:/workspace" \
  openwrt-builder:local \
  python3 scripts/build.py validate
```

Build firmware with the local image:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD:/workspace" \
  openwrt-builder:local \
  python3 scripts/build.py build \
  --profile archer-a9-v6 \
  --output artifact \
  --jobs "$(nproc)"
```

Rebuilding the Docker image is only necessary when the build environment changes, normally when the Dockerfile changes. Changes to `scripts/`, `profiles/`, or documentation do not require rebuilding the image because those files are mounted from the current checkout.

## OpenWrt prebuilt host tools

The builder image contains the operating-system prerequisites required to build OpenWrt. OpenWrt itself normally builds another layer of host tools under `build_dir/host` and `staging_dir/host`.

When a source build does not use an SDK, the builder automatically tries to reuse OpenWrt's official prebuilt host-tools OCI image from `ghcr.io/openwrt/tools` instead of rebuilding that layer.

Stable release tags and branches are mapped to the same family used by OpenWrt upstream:

```text
v25.12.1       -> ghcr.io/openwrt/tools:openwrt-25.12
v25.12.5       -> ghcr.io/openwrt/tools:openwrt-25.12
openwrt-25.12  -> ghcr.io/openwrt/tools:openwrt-25.12
main           -> ghcr.io/openwrt/tools:latest
```

The image is consumed as an OCI artifact; it does not replace `docker.io/demonccc/openwrt-builder:latest`. `skopeo` pulls it from GHCR and `umoci` extracts `/prebuilt_tools` without requiring the host Docker socket. The builder then links the official `build_dir/host` and `staging_dir/host` trees into the OpenWrt checkout and runs OpenWrt's own `scripts/ext-tools.sh --refresh` mechanism.

The rules are deliberately conservative:

- If an SDK is in use, host tools come from the SDK and no separate tools image is downloaded.
- Official OpenWrt stable refs use their `openwrt-X.Y` tools family.
- Official OpenWrt `main` uses `ghcr.io/openwrt/tools:latest`.
- `release-patched` forks compare the custom source against `BASE_REF`. If host-tools inputs such as `tools/`, `toolchain/`, `include/cmake.mk`, or the external-tools/stamp mechanism changed, official prebuilt tools are not reused.
- Custom repositories without a `BASE_REF` do not assume compatibility and build host tools from source.
- If the official tools image cannot be pulled or unpacked, the optimization is skipped and OpenWrt builds the tools normally.

`BUILD_INFO` records `HOST_TOOLS_MODE`, `HOST_TOOLS_IMAGE`, and `HOST_TOOLS_REASON` so every build shows whether its host tools came from the SDK, the official prebuilt image, or source.

## Builder image publication from GitHub Actions

The canonical [Build builder image workflow](https://github.com/demonccc/openwrt-builder/blob/main/.github/workflows/docker-image.yml) builds and publishes the Docker environment.

Its behavior is:

- On a pull request that changes `Dockerfile` or `.github/workflows/docker-image.yml`, the image is built and validated but is not pushed.
- On a push to `main` that changes either of those files, the image is built and pushed to Docker Hub.
- `workflow_dispatch` can also be used to run the workflow manually. Outside a pull request, the workflow publishes the resulting image and therefore requires the Docker Hub secret.

Published tags are:

- `docker.io/demonccc/openwrt-builder:latest`
- `docker.io/demonccc/openwrt-builder:sha-<commit>`

The Docker Hub username and namespace are intentionally fixed to `demonccc`; no username secret or repository variable is required.

The workflow uses Docker Buildx and GitHub Actions layer caching for the Docker image itself. This cache is independent from OpenWrt firmware build caching.

## Configuring the Docker Hub secret

Docker Hub publication requires one GitHub Actions repository secret:

```text
DOCKERHUB_TOKEN
```

Create a Docker Hub access token with permission to push to `demonccc/openwrt-builder`. Use an access token rather than the Docker Hub account password.

Then add it to the GitHub repository:

1. Open `demonccc/openwrt-builder` on GitHub.
2. Open **Settings**.
3. Open **Secrets and variables** -> **Actions**.
4. Select **New repository secret**.
5. Set the name to `DOCKERHUB_TOKEN`.
6. Paste the Docker Hub access token as the value and save it.

No `DOCKERHUB_USERNAME` secret is required. The workflow already uses `demonccc` as the Docker Hub username.

The secret is used only for Docker Hub login on publishing runs. Pull-request Docker builds do not log in and do not require the secret.

## GitHub Actions firmware builds

Run **Build OpenWrt firmware** and choose a profile directory. The canonical [firmware build workflow](https://github.com/demonccc/openwrt-builder/blob/main/.github/workflows/build.yml) pulls `docker.io/demonccc/openwrt-builder:latest` and executes the current checkout inside it.

The effective command inside the container is equivalent to:

```bash
python3 scripts/build.py build \
  --profile "$PROFILE" \
  --output artifact \
  --jobs "$(nproc)"
```

If the published image is temporarily unavailable, the workflow falls back to building the repository Dockerfile locally instead of failing only because Docker Hub cannot be reached.

Successful builds upload `artifact/` and create a GitHub Release containing the firmware and `BUILD_INFO`.

## Validation workflow

The canonical [profile validation workflow](https://github.com/demonccc/openwrt-builder/blob/main/.github/workflows/validate.yml) uses the same published builder image. It validates the Python builder and the profiles, and retains the local Dockerfile fallback until the published image is available.

## Direct Python execution

Direct Python execution remains supported when the host already has all required build dependencies. To get the same automatic prebuilt-host-tools optimization outside Docker, the host also needs `skopeo` and `umoci`.

```bash
python3 scripts/build.py validate
python3 scripts/build.py build --profile openwrt-25.12-source
```

Docker is the recommended portable path because it keeps the build environment consistent with GitHub Actions.

## Source override

`--source-ref` can temporarily override `REF`. When a profile uses explicit `SDK_URL`, the caller remains responsible for compatibility between that SDK and the overridden source.

See the canonical [`openwrt-25.12-source` settings](https://github.com/demonccc/openwrt-builder/blob/main/profiles/openwrt-25.12-source/settings) for an explicit `SDK_URL` example.
