# OpenWrt Builder

Reusable OpenWrt firmware builder powered by GitHub Actions.

The goal of this repository is to make it simple to create reproducible OpenWrt builds without mixing build automation with the OpenWrt source tree itself.

You can fork this repository, keep only the profiles you need, create your own profiles from the included bases, and build firmware from official OpenWrt sources, official ImageBuilders, or custom OpenWrt forks.

## Included profiles

| Profile | Method | Target | Purpose |
| --- | --- | --- | --- |
| [`snapshot-source`](profiles/snapshot-source/README.md) | Source | x86/64 generic | Current OpenWrt snapshot built from source |
| [`snapshot-imagebuilder`](profiles/snapshot-imagebuilder/README.md) | ImageBuilder | x86/64 generic | Current OpenWrt snapshot assembled with the official ImageBuilder |
| [`openwrt-25.12-source`](profiles/openwrt-25.12-source/README.md) | Source | x86/64 generic | Stable OpenWrt 25.12 built from source |
| [`openwrt-25.12-imagebuilder`](profiles/openwrt-25.12-imagebuilder/README.md) | ImageBuilder | x86/64 generic | Stable OpenWrt 25.12 assembled with the official ImageBuilder |
| [`openwrt-24.10-source`](profiles/openwrt-24.10-source/README.md) | Source | x86/64 generic | OpenWrt 24.10 built from source |
| [`archer-a9-v6`](profiles/archer-a9-v6/README.md) | Source | TP-Link Archer A9 v6 | Custom OpenWrt fork with QCN5502 support |
| [`velop-whw03-v2-imagebuilder`](profiles/velop-whw03-v2-imagebuilder/README.md) | ImageBuilder | Linksys Velop WHW03 V2 | Device-specific package selection using the official OpenWrt ImageBuilder |

The bundled profiles are starting points. A fork can delete any profiles it does not use.

## Documentation

The canonical documentation for how the builder works lives under [`docs/`](docs/):

- [Using OpenWrt Builder](docs/usage.md) — forking the repository, creating builds, GitHub Actions, runners, local builds, and validation.
- [Profile reference](docs/profiles.md) — profile structure, source and ImageBuilder methods, package selection, feeds, Git packages, and embedded files/configuration.

Keeping operational documentation under `docs/` means a fork can replace or customize this root README without losing the builder reference documentation.

## License

MIT
