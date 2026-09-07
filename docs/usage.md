# Using OpenWrt Builder

This guide covers execution. See the canonical [Profile reference](https://github.com/demonccc/openwrt-builder/blob/main/docs/profiles.md) for build-mode and profile semantics.

## Recommended local execution: published Docker image

`scripts/build.py` performs the real OpenWrt build, including the final `make`; it is not only a configuration generator. The published builder image contains the OpenWrt host build dependencies so local and CI builds do not need to reinstall them for every run.

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

The repository checkout is mounted at `/workspace`. The Docker image contains the build environment, not a baked copy of the builder code, so the current checkout always controls `scripts/build.py`, profiles, and documentation.

The image intentionally has no `ENTRYPOINT`. It is a reusable build host; the caller explicitly chooses which command from the mounted checkout to execute.

The bind mount keeps `.work/` and `artifact/` in the working directory. OpenWrt must not build as root; the image has a non-root default user and the examples map to the host UID/GID.

The canonical environment definition is the repository [Dockerfile](https://github.com/demonccc/openwrt-builder/blob/main/Dockerfile).

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

## Builder image publication

The [Build builder image workflow](https://github.com/demonccc/openwrt-builder/blob/main/.github/workflows/docker-image.yml) validates Dockerfile changes in pull requests and publishes the image from `main` to Docker Hub.

The image is intentionally an environment image. Builder code and profiles are mounted from the checkout and are not copied into the image. Therefore changes to `scripts/`, `profiles/`, or documentation do not require rebuilding the Docker image; changes to the Dockerfile do.

Published tags:

- `docker.io/demonccc/openwrt-builder:latest`
- `docker.io/demonccc/openwrt-builder:sha-<commit>`

Publishing requires the GitHub Actions secret `DOCKERHUB_TOKEN`. The Docker Hub username and image namespace are intentionally fixed to `demonccc`, so there is no separate username setting to keep in sync.

The token should be a scoped Docker Hub access token with permission to push `demonccc/openwrt-builder`.

The workflow uses Buildx and GitHub Actions layer caching, so rebuilding the environment after a Dockerfile change can reuse unchanged layers.

## GitHub Actions firmware builds

Run **Build OpenWrt firmware** and choose a profile directory. The canonical [firmware build workflow](https://github.com/demonccc/openwrt-builder/blob/main/.github/workflows/build.yml) pulls `docker.io/demonccc/openwrt-builder:latest` and executes the current checkout inside it.

If the published image is temporarily unavailable, the workflow falls back to building the repository Dockerfile locally instead of failing only because Docker Hub cannot be reached.

Successful builds upload `artifact/` and create a GitHub Release containing the firmware and `BUILD_INFO`.

## Validation workflow

The canonical [profile validation workflow](https://github.com/demonccc/openwrt-builder/blob/main/.github/workflows/validate.yml) uses the same published builder image. It also retains the local Dockerfile fallback until the published image is available.

## Direct Python execution

Still supported when the host already has the dependencies. To get the same automatic prebuilt-host-tools optimization outside Docker, the host also needs `skopeo` and `umoci`.

```bash
python3 scripts/build.py validate
python3 scripts/build.py build --profile openwrt-25.12-source
```

Docker is the recommended portable path because it keeps the build environment consistent with GitHub Actions.

## Source override

`--source-ref` can temporarily override `REF`. When a profile uses explicit `SDK_URL`, the caller remains responsible for compatibility between that SDK and the overridden source.

See the canonical [`openwrt-25.12-source` settings](https://github.com/demonccc/openwrt-builder/blob/main/profiles/openwrt-25.12-source/settings) for an explicit `SDK_URL` example.
