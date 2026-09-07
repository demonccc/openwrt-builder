# Using OpenWrt Builder

This guide covers execution. See [Profile reference](profiles.md) for build-mode and profile semantics.

## Recommended local execution: Docker

`scripts/build.py` performs the real OpenWrt build, including the final `make`; it is not only a configuration generator. Running it directly therefore requires all OpenWrt host dependencies.

Build the repository image:

```bash
docker build -t openwrt-builder .
```

Validate profiles:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD:/workspace" \
  openwrt-builder validate
```

Build a profile:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD:/workspace" \
  openwrt-builder build \
  --profile archer-a9-v6 \
  --output artifact \
  --jobs "$(nproc)"
```

The bind mount keeps `.work/` and `artifact/` in the working directory, while the container supplies the Ubuntu/OpenWrt build dependencies. OpenWrt must not build as root; the image has a non-root default user and the examples map to the host UID/GID.

## Direct Python execution

Still supported when the host already has the dependencies:

```bash
python3 scripts/build.py validate
python3 scripts/build.py build --profile openwrt-25.12-source
```

Docker is the recommended portable path.

## GitHub Actions

Run **Build OpenWrt firmware** and choose a profile directory. The workflow builds this same `Dockerfile` and executes `scripts/build.py` inside it, so local and CI builds share the same environment.

Successful builds upload `artifact/` and create a GitHub Release containing the firmware and `BUILD_INFO`.

## Source override

`--source-ref` can temporarily override `REF`. When a profile uses explicit `SDK_URL`, the caller remains responsible for compatibility between that SDK and the overridden source.

## Validation workflow

`Validate profiles` builds the Docker image and runs profile validation inside it on feature branches and pull requests.
