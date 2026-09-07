# Docker architecture

OpenWrt Builder always runs inside Docker, both locally and in GitHub Actions.

This is intentional: Docker is the portable execution boundary of the project. Windows, macOS, Linux, and GitHub Actions all run the same Linux build environment, with the same dependencies and the same builder behavior.

The upstream project publishes its canonical build environment as:

```text
demonccc/openwrt-builder:latest
```

For day-to-day commands, see [Using OpenWrt Builder](https://github.com/demonccc/openwrt-builder/blob/main/docs/usage.md).

## Builder image responsibility

The image is a reusable Linux build host for OpenWrt. It contains Ubuntu and the host-side dependencies required by the supported build modes.

It intentionally does not contain:

- the `openwrt-builder` repository;
- OpenWrt source;
- a fixed OpenWrt SDK;
- a fixed OpenWrt ImageBuilder;
- profiles.

The current repository checkout is mounted into `/workspace` at runtime. Therefore the checked-out `scripts/` and `profiles/` are always used without rebuilding the Docker image.

The image intentionally has no `ENTRYPOINT`. The caller explicitly runs the builder from the mounted checkout:

```bash
python3 scripts/build.py ...
```

That command is always executed inside the container. Running `scripts/build.py` directly on the host is not a supported execution path.

## Why Docker is mandatory

OpenWrt builds depend on a large and specific Linux host environment. Running the builder directly on the host would create different dependency sets and behavior across Linux distributions, macOS, Windows, and GitHub Actions.

Using Docker makes the execution model consistent:

```text
Windows / macOS / Linux / GitHub Actions
                  |
                  v
         openwrt-builder image
                  |
                  v
        scripts/build.py
                  |
                  v
            OpenWrt build
```

Only Docker is required on the host. The host does not need the OpenWrt build dependencies installed directly.

## What is baked into the image

The canonical definition is the repository [Dockerfile](https://github.com/demonccc/openwrt-builder/blob/main/Dockerfile).

It contains the operating-system prerequisites needed to start an OpenWrt build without installing packages first: compilers, build utilities, compression tools, Python, Perl, Git, and related libraries.

It also contains:

```text
skopeo
umoci
```

These utilities allow `scripts/build.py` to consume OpenWrt's official prebuilt host-tools OCI images directly from GHCR without requiring access to the host Docker socket.

OpenWrt source, SDKs and ImageBuilders remain runtime inputs because their version depends on the selected profile.

## Building the builder image locally

From the repository root:

```bash
docker build \
  --platform linux/amd64 \
  -t openwrt-builder:local \
  .
```

The project currently publishes `linux/amd64`, matching the Ubuntu x86_64 GitHub Actions runner used by the workflows.

The local image still runs the builder from the mounted checkout:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD:/workspace" \
  openwrt-builder:local \
  python3 scripts/build.py validate
```

Rebuild the Docker image only when the build environment changes, normally when the Dockerfile changes. Changes to `scripts/`, `profiles/`, or documentation do not require rebuilding it.

## OpenWrt prebuilt host tools

The builder image provides the operating-system prerequisites, but OpenWrt normally builds another layer of host tools under:

```text
build_dir/host
staging_dir/host
```

For source builds that are not already using an SDK, `scripts/build.py` automatically tries to reuse OpenWrt's official prebuilt host-tools image:

```text
ghcr.io/openwrt/tools:<family>
```

This resolution and pull are performed by `scripts/build.py` itself, inside the builder container. GitHub Actions does not implement a separate OpenWrt-tools code path. Therefore a local Docker run and a GitHub Actions firmware build execute the same builder logic.

Typical family mapping is:

```text
v25.12.1       -> ghcr.io/openwrt/tools:openwrt-25.12
v25.12.5       -> ghcr.io/openwrt/tools:openwrt-25.12
openwrt-25.12  -> ghcr.io/openwrt/tools:openwrt-25.12
main           -> ghcr.io/openwrt/tools:latest
```

The OpenWrt tools image is an acceleration artifact only. It never replaces the main `openwrt-builder` container.

`scripts/build.py` uses `skopeo` to pull the OCI image and `umoci` to unpack `/prebuilt_tools`. It then exposes the official `build_dir/host` and `staging_dir/host` trees to the OpenWrt checkout and invokes OpenWrt's own `scripts/ext-tools.sh --refresh` mechanism.

### Compatibility rules

The builder is conservative about reuse:

- If an SDK is in use, host tools come from the SDK and no separate tools image is downloaded.
- Official stable OpenWrt refs use their `openwrt-X.Y` tools family.
- Official OpenWrt `main` uses `ghcr.io/openwrt/tools:latest`.
- `release-patched` forks compare the custom source against `BASE_REF`. If host-tools inputs such as `tools/`, `toolchain/`, `include/cmake.mk`, or the external-tools/stamp mechanism changed, official prebuilt tools are not reused.
- Custom repositories without a `BASE_REF` do not assume compatibility and build host tools from source.
- If the official tools image cannot be pulled or unpacked, the optimization is skipped and OpenWrt builds the host tools normally.

`BUILD_INFO` records:

```text
HOST_TOOLS_MODE
HOST_TOOLS_IMAGE
HOST_TOOLS_REASON
```

so every source build shows whether host tools came from the SDK, the official prebuilt image, or source.

## Builder image consumption

The firmware workflow exposes an explicit `builder_image` input. The upstream default is:

```text
demonccc/openwrt-builder:latest
```

This input is independent from Docker Hub publishing credentials. A fork can keep using the upstream image, or explicitly point a manual build at its own compatible image:

```text
mydockeruser/openwrt-builder:latest
```

The validation workflow uses the upstream image by default for push and pull-request validation. Manual validation exposes the same `builder_image` input.

## Builder image publication

The canonical [Build builder image workflow](https://github.com/demonccc/openwrt-builder/blob/main/.github/workflows/docker-image.yml) builds and publishes the environment image.

Its behavior is:

- Pull requests that change `Dockerfile` or `.github/workflows/docker-image.yml` build and validate the image without pushing it.
- Pushes to `main` that change either file build and publish the image to Docker Hub.
- `workflow_dispatch` can publish the image manually.

The publication target is resolved from the explicit Docker Hub username:

```text
docker.io/<DOCKERHUB_USERNAME>/openwrt-builder
```

and publishes:

```text
docker.io/<DOCKERHUB_USERNAME>/openwrt-builder:latest
docker.io/<DOCKERHUB_USERNAME>/openwrt-builder:sha-<commit>
```

`DOCKERHUB_USERNAME` controls only where images are published. It does not implicitly change the builder image used by firmware or validation workflows.

The workflow uses Docker Buildx and GitHub Actions layer caching for the Docker image itself.

## Docker Hub configuration

Publishing to Docker Hub requires explicit repository configuration:

```text
DOCKERHUB_USERNAME  GitHub Actions variable
DOCKERHUB_TOKEN     GitHub Actions secret
```

There is intentionally no automatic fallback from the GitHub repository owner to a Docker Hub username. GitHub and Docker Hub are independent namespaces, and silently assuming they match can target an unrelated Docker Hub account and make failures difficult to diagnose.

### Username variable

`DOCKERHUB_USERNAME` is the Docker Hub account or organization that owns the `openwrt-builder` repository.

Configure it under:

```text
Settings
  -> Secrets and variables
  -> Actions
  -> Variables
  -> New repository variable
```

Use:

```text
Name:  DOCKERHUB_USERNAME
Value: <your Docker Hub username or organization>
```

For this repository:

```text
DOCKERHUB_USERNAME=demonccc
```

### Token secret

Create a Docker Hub access token with permission to push `<DOCKERHUB_USERNAME>/openwrt-builder`, then add it under:

```text
Settings
  -> Secrets and variables
  -> Actions
  -> Secrets
  -> New repository secret
```

Use:

```text
Name:  DOCKERHUB_TOKEN
Value: <Docker Hub access token>
```

The token is only needed for publishing. Pull-request image validation does not log in to Docker Hub.
