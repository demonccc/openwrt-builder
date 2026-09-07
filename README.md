# OpenWrt Builder

Reusable OpenWrt firmware builder powered by GitHub Actions.

This root README is intentionally an index. The canonical explanation of how builds work lives under [`docs/`](https://github.com/demonccc/openwrt-builder/tree/main/docs), while each profile README explains only why that profile exists and its profile-specific choices.

## Build modes

| Mode | What it compiles |
| --- | --- |
| **1. ImageBuilder** | Nothing from source; assembles firmware from prebuilt OpenWrt artifacts |
| **2. `release-patched`** | Only target/kernel/package components affected by a patch; unchanged packages come from the exact base release |
| **3. `selective-source`** | Only packages selected for the firmware plus their dependencies |
| **4. `full-source`** | The broad package universe from source, optionally limited to selected feeds |

`SDK` is independent from the build mode. It controls build acceleration, not package scope. See the canonical [Profile reference](https://github.com/demonccc/openwrt-builder/blob/main/docs/profiles.md).

## Reference profiles

Only these profiles are kept intentionally:

| Profile | Mode | Purpose |
| --- | --- | --- |
| [`velop-whw03-v2-imagebuilder`](https://github.com/demonccc/openwrt-builder/blob/main/profiles/velop-whw03-v2-imagebuilder/README.md) | ImageBuilder | Real device profile using OpenWrt 25.12 ImageBuilder |
| [`openwrt-24.10-imagebuilder`](https://github.com/demonccc/openwrt-builder/blob/main/profiles/openwrt-24.10-imagebuilder/README.md) | ImageBuilder | Generic x86/64 ImageBuilder profile for OpenWrt 24.10 |
| [`archer-a9-v6`](https://github.com/demonccc/openwrt-builder/blob/main/profiles/archer-a9-v6/README.md) | `release-patched` | QCN5502/ath9k patch with unchanged 25.12.5 release packages |
| [`openwrt-25.12-source`](https://github.com/demonccc/openwrt-builder/blob/main/profiles/openwrt-25.12-source/README.md) | `selective-source` | Selective source build on OpenWrt 25.12.5 |
| [`snapshot-full-source`](https://github.com/demonccc/openwrt-builder/blob/main/profiles/snapshot-full-source/README.md) | `full-source` | Full source build from current OpenWrt main |

## Builder image

The canonical OpenWrt build environment is published as:

```text
docker.io/demonccc/openwrt-builder:latest
```

The image contains the host-side dependencies required by the supported OpenWrt build modes. Builder code and profiles are not baked into the image; the current repository checkout is mounted into `/workspace` at runtime.

See [Using OpenWrt Builder](https://github.com/demonccc/openwrt-builder/blob/main/docs/usage.md) for local execution, Docker Hub publication, and GitHub Actions usage.

## Documentation

- [Using OpenWrt Builder](https://github.com/demonccc/openwrt-builder/blob/main/docs/usage.md)
- [Profile reference and build modes](https://github.com/demonccc/openwrt-builder/blob/main/docs/profiles.md)

## License

MIT
