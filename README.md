# OpenWrt Builder

Reusable OpenWrt firmware builder powered by Docker and GitHub Actions.

The canonical explanation of build modes lives under [`docs/`](docs/). Public build profiles live under [`profiles/`](profiles/) and are selected by versioned profile ID.

## Profile IDs

Profile names follow:

```text
<device>-<X.Y.Z|X.Y|snapshot>
```

Examples:

```text
archer-a9-v6-25.12.5   # exact OpenWrt release
archer-a9-v6-25.12     # moving OpenWrt 25.12 stable branch
x86-64-snapshot        # OpenWrt main/snapshot
```

Build implementation is not part of the public profile name. `imagebuilder`, `release-patched`, `selective-source`, and `full-source` remain settings inside each profile.

The profile catalog is validated in CI. The validator checks required files, settings/package/feed syntax, and consistency between the version encoded in the profile ID and `REF`, `BASE_REF`, SDK/ImageBuilder release URLs. See [`profiles/README.md`](profiles/README.md).

## Build modes

| Mode | What it compiles |
| --- | --- |
| **ImageBuilder** | Nothing from source; assembles firmware from prebuilt OpenWrt artifacts |
| **`release-patched`** | Only the custom kernel/target layer, selected kmods and explicitly affected package roots; unchanged userspace comes from the exact base release |
| **`selective-source`** | Only packages selected for the firmware plus their dependencies |
| **`full-source`** | The broad package universe from source, optionally limited by selected feeds |

`release-patched` enforces that boundary: local package roots are built with `NO_DEPS=1`, the generated ImageBuilder receives an explicit local-APK allowlist, and unchanged runtime userspace is resolved from the repositories pinned to `BASE_REF`. `BUILD_INFO` records the exact locally injected package set.

`SDK` is independent from build mode. It controls build acceleration, not package scope. See [`docs/profiles.md`](docs/profiles.md).

## Reference profiles

| Profile | Mode | Purpose |
| --- | --- | --- |
| [`archer-a9-v6-25.12.5`](profiles/archer-a9-v6-25.12.5/) | `release-patched` | Archer A9 v6 on exact `v25.12.5 + QCN5502` |
| [`archer-a9-v6-25.12`](profiles/archer-a9-v6-25.12/) | `selective-source` | Archer A9 v6 following the custom OpenWrt 25.12 stable-derived branch |
| [`linksys-velop-whw03-v2-25.12.5`](profiles/linksys-velop-whw03-v2-25.12.5/) | ImageBuilder | Linksys Velop WHW03 v2 on OpenWrt 25.12.5 |
| [`x86-64-24.10.5`](profiles/x86-64-24.10.5/) | ImageBuilder | Generic x86/64 on OpenWrt 24.10.5 |
| [`x86-64-25.12.5`](profiles/x86-64-25.12.5/) | `selective-source` | Generic x86/64 on exact OpenWrt 25.12.5 source |
| [`x86-64-snapshot`](profiles/x86-64-snapshot/) | `full-source` | Generic x86/64 following OpenWrt main |

## Docker execution

OpenWrt Builder always runs inside Docker, locally and in GitHub Actions. Running `scripts/build.py` directly on the host is not a supported firmware-build path. Docker is the portable execution boundary so Windows, macOS, Linux and CI use the same Linux build environment and builder implementation.

The upstream image is:

```text
docker.io/demonccc/openwrt-builder:latest
```

The repository checkout is mounted into `/workspace`; builder code and profiles are not baked into the image.

For commands, see [`docs/usage.md`](docs/usage.md). For image architecture and Docker Hub publishing, see [`docs/docker.md`](docs/docker.md).

## GitHub Actions profile selector

The build workflow exposes a choice dropdown generated from the validated profile catalog. `scripts/sync-profile-workflow.py` keeps it synchronized, and `.github/workflows/sync-profile-options.yml` publishes catalog changes after they land on `main`.

## License

MIT
