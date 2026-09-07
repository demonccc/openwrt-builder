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
  docker.io/demonccc/openwrt-builder:latest validate
```

Build a profile:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD:/workspace" \
  docker.io/demonccc/openwrt-builder:latest build \
  --profile archer-a9-v6 \
  --output artifact \
  --jobs "$(nproc)"
```

The repository checkout is mounted at `/workspace`. The Docker image contains the build environment, not a baked copy of the builder code, so the current checkout always controls `scripts/build.py`, profiles, and documentation.

The bind mount keeps `.work/` and `artifact/` in the working directory. OpenWrt must not build as root; the image has a non-root default user and the examples map to the host UID/GID.

The canonical environment definition is the repository [Dockerfile](https://github.com/demonccc/openwrt-builder/blob/main/Dockerfile).

## Builder image publication

The [Build builder image workflow](https://github.com/demonccc/openwrt-builder/blob/main/.github/workflows/docker-image.yml) validates Dockerfile changes in pull requests and publishes the image from `main` to Docker Hub.

Published tags:

- `docker.io/demonccc/openwrt-builder:latest`
- `docker.io/demonccc/openwrt-builder:sha-<commit>`

Publishing requires these GitHub Actions secrets:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

The Docker Hub token should be a scoped access token with permission to push `demonccc/openwrt-builder`.

The workflow uses Buildx and GitHub Actions layer caching, so rebuilding the environment after a Dockerfile change can reuse unchanged layers.

## GitHub Actions firmware builds

Run **Build OpenWrt firmware** and choose a profile directory. The canonical [firmware build workflow](https://github.com/demonccc/openwrt-builder/blob/main/.github/workflows/build.yml) pulls `docker.io/demonccc/openwrt-builder:latest` and executes the current checkout inside it.

If the published image is temporarily unavailable, the workflow falls back to building the repository Dockerfile locally instead of failing only because Docker Hub cannot be reached.

Successful builds upload `artifact/` and create a GitHub Release containing the firmware and `BUILD_INFO`.

## Validation workflow

The canonical [profile validation workflow](https://github.com/demonccc/openwrt-builder/blob/main/.github/workflows/validate.yml) uses the same published builder image. It also retains the local Dockerfile fallback until the published image is available.

## Direct Python execution

Still supported when the host already has the dependencies:

```bash
python3 scripts/build.py validate
python3 scripts/build.py build --profile openwrt-25.12-source
```

Docker is the recommended portable path because it keeps the build environment consistent with GitHub Actions.

## Source override

`--source-ref` can temporarily override `REF`. When a profile uses explicit `SDK_URL`, the caller remains responsible for compatibility between that SDK and the overridden source.

See the canonical [`openwrt-25.12-source` settings](https://github.com/demonccc/openwrt-builder/blob/main/profiles/openwrt-25.12-source/settings) for an explicit `SDK_URL` example.
