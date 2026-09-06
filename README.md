# OpenWrt Builder

Reusable OpenWrt firmware builder powered by GitHub Actions.

The goal of this repository is to make it simple to create reproducible OpenWrt builds without mixing build automation with the OpenWrt source tree itself.

You can fork this repository, keep only the profiles you need, create your own profiles from the included bases, and build firmware from official OpenWrt sources, official ImageBuilders, or custom OpenWrt forks.

## Source build modes

Source-build acceleration is completely optional and is controlled by each profile.

A profile with only the normal source settings performs a full OpenWrt source build:

```text
METHOD=source
REPOSITORY=https://github.com/openwrt/openwrt.git
REF=openwrt-25.12
TARGET=x86
SUBTARGET=64
DEVICE=generic
```

With no optional acceleration settings, OpenWrt builds its host tools and target toolchain from source, updates all default feeds, then builds the selected target, packages, dependencies, and firmware image.

Optional profile settings can reduce clean-build time:

```text
SDK_URL=...        # reuse SDK host tools + target toolchain
TOOLCHAIN_URL=...  # reuse only a target toolchain
FEED_NAMES=...     # update/index only selected feeds
```

`SDK_URL` and `TOOLCHAIN_URL` are mutually exclusive because an OpenWrt SDK already contains its target toolchain. `FEED_NAMES` is independent and may be used with either acceleration mode or by itself.

Removing `SDK_URL`, `TOOLCHAIN_URL`, and `FEED_NAMES` always returns to the normal full source-build behavior. This is useful for self-hosted runners where the user wants OpenWrt to build the complete build environment itself.

"Full source build" does **not** mean compiling every package published in every OpenWrt feed. OpenWrt still compiles only the selected firmware packages plus the build/runtime dependencies required by the resolved configuration.

## Included profiles

| Profile | Method | Target | Purpose |
| --- | --- | --- | --- |
| [`snapshot-full-source`](profiles/snapshot-full-source/README.md) | Full source | x86/64 generic | Explicit current snapshot build with host tools, toolchain, and target built from source |
| [`openwrt-25.12-full-source`](profiles/openwrt-25.12-full-source/README.md) | Full source | x86/64 generic | Explicit OpenWrt 25.12 build with host tools, toolchain, and target built from source |
| [`snapshot-source`](profiles/snapshot-source/README.md) | Source | x86/64 generic | Current OpenWrt snapshot source-build base |
| [`snapshot-imagebuilder`](profiles/snapshot-imagebuilder/README.md) | ImageBuilder | x86/64 generic | Current OpenWrt snapshot assembled with the official ImageBuilder |
| [`openwrt-25.12-source`](profiles/openwrt-25.12-source/README.md) | Source | x86/64 generic | Stable OpenWrt 25.12 source-build base |
| [`openwrt-25.12-imagebuilder`](profiles/openwrt-25.12-imagebuilder/README.md) | ImageBuilder | x86/64 generic | Stable OpenWrt 25.12 assembled with the official ImageBuilder |
| [`openwrt-24.10-source`](profiles/openwrt-24.10-source/README.md) | Source | x86/64 generic | OpenWrt 24.10 built from source |
| [`archer-a9-v6`](profiles/archer-a9-v6/README.md) | Source + SDK | TP-Link Archer A9 v6 | Custom QCN5502 source build reusing official SDK host tools/toolchain and selected feeds |
| [`velop-whw03-v2-imagebuilder`](profiles/velop-whw03-v2-imagebuilder/README.md) | ImageBuilder | Linksys Velop WHW03 V2 | Device-specific package selection using the official OpenWrt ImageBuilder |

The two `*-full-source` profiles are intentionally explicit reference examples showing how to opt out of all build acceleration. The bundled profiles are starting points; a fork can delete any profiles it does not use.

## Documentation

The canonical documentation for how the builder works lives under [`docs/`](docs/):

- [Using OpenWrt Builder](docs/usage.md) — forking the repository, creating builds, GitHub Actions, runners, local builds, and validation.
- [Profile reference](docs/profiles.md) — profile structure, source and ImageBuilder methods, optional SDK/toolchain/feed acceleration, package selection, feeds, Git packages, and embedded files/configuration.

Keeping operational documentation under `docs/` means a fork can replace or customize this root README without losing the builder reference documentation.

## License

MIT
