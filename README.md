# OpenWrt Builder

Reusable OpenWrt firmware builder powered by GitHub Actions.

This root README is intentionally an index. The canonical explanation of how builds work lives under [`docs/`](docs/), while each profile README explains only why that profile exists and what it demonstrates.

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
| [`velop-whw03-v2-imagebuilder`](profiles/velop-whw03-v2-imagebuilder/README.md) | ImageBuilder | Real device profile using OpenWrt 25.12 ImageBuilder |
| [`openwrt-24.10-imagebuilder`](profiles/openwrt-24.10-imagebuilder/README.md) | ImageBuilder | Generic x86/64 ImageBuilder example for OpenWrt 24.10 |
| [`archer-a9-v6`](profiles/archer-a9-v6/README.md) | `release-patched` | QCN5502/ath9k patch + unchanged 25.12.5 binaries; demonstrates `SDK=auto` |
| [`openwrt-25.12-source`](profiles/openwrt-25.12-source/README.md) | `selective-source` | Selective source build; demonstrates explicit `SDK_URL` |
| [`snapshot-full-source`](profiles/snapshot-full-source/README.md) | `full-source` | Full snapshot build; demonstrates `SDK=none` and feed scope |

## Documentation

- [Using OpenWrt Builder](docs/usage.md)
- [Profile reference and build modes](docs/profiles.md)

## License

MIT
