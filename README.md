# OpenWrt Builder

Reusable OpenWrt firmware builder powered by GitHub Actions.

This root README is intentionally an index. The canonical explanation of how builds work lives under [`docs/`](docs/), while each profile README explains only why that profile exists and its profile-specific choices.

## Build modes

| Mode | What it compiles |
| --- | --- |
| **1. ImageBuilder** | Nothing from source; assembles firmware from prebuilt OpenWrt artifacts |
| **2. `release-patched`** | Only target/kernel/package components affected by a patch; unchanged packages come from the exact base release |
| **3. `selective-source`** | Only packages selected for the firmware plus their dependencies |
| **4. `full-source`** | The broad package universe from source, optionally limited to selected feeds |

`SDK` is independent from the build mode. It controls build acceleration, not package scope. See [Profile reference](docs/profiles.md).

## Reference profiles

Only these profiles are kept intentionally:

| Profile | Mode | Example |
| --- | --- | --- |
| [`velop-whw03-v2-imagebuilder`](https://github.com/demonccc/openwrt-builder/blob/main/profiles/velop-whw03-v2-imagebuilder/README.md) | ImageBuilder | Real device profile using OpenWrt 25.12 ImageBuilder |
| [`openwrt-24.10-imagebuilder`](https://github.com/demonccc/openwrt-builder/blob/main/profiles/openwrt-24.10-imagebuilder/README.md) | ImageBuilder | Generic x86/64 ImageBuilder profile for OpenWrt 24.10 |
| [`archer-a9-v6`](https://github.com/demonccc/openwrt-builder/blob/main/profiles/archer-a9-v6/README.md) | `release-patched` | QCN5502/ath9k patch with unchanged packages from OpenWrt 25.12.5 |
| [`openwrt-25.12-source`](https://github.com/demonccc/openwrt-builder/blob/main/profiles/openwrt-25.12-source/README.md) | `selective-source` | Selective source build for OpenWrt 25.12 |
| [`snapshot-full-source`](https://github.com/demonccc/openwrt-builder/blob/main/profiles/snapshot-full-source/README.md) | `full-source` | Full source build from the current OpenWrt snapshot |

## Documentation

- [Using OpenWrt Builder](docs/usage.md)
- [Profile reference and build modes](docs/profiles.md)

## License

MIT
