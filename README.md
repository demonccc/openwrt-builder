# OpenWrt Builder

Reusable OpenWrt firmware builder powered by GitHub Actions.

This root README is intentionally an index. The canonical explanation of builder behavior, settings, package selection, feed handling, acceleration, and the four build modes lives in [`docs/`](docs/).

## Build modes

| Mode | Purpose | Typical speed |
| --- | --- | --- |
| **1. ImageBuilder** | Assemble firmware entirely from official prebuilt artifacts | Fastest |
| **2. release-patched** | Compile only patched target/package components and reuse unchanged release binaries | Fast |
| **3. selective-source** | Build from source only the firmware-selected packages and dependencies | Medium |
| **4. full-source** | Build the broad package universe from source, optionally restricted by feeds | Slowest |

See [Profile reference](docs/profiles.md) for the exact behavior and configuration of each mode, and [Using OpenWrt Builder](docs/usage.md) for running builds locally or through GitHub Actions.

## Reference profiles

The bundled profiles are examples meant to be copied and adapted:

| Profile | Mode | Why it exists |
| --- | --- | --- |
| [`openwrt-25.12-imagebuilder`](profiles/openwrt-25.12-imagebuilder/README.md) | ImageBuilder | Official stable release with no source compilation |
| [`openwrt-24.10-imagebuilder`](profiles/openwrt-24.10-imagebuilder/README.md) | ImageBuilder | Same fast path demonstrated on the previous stable series |
| [`archer-a9-v6`](profiles/archer-a9-v6/README.md) | release-patched | Compile QCN5502/ath9k support for the Archer A9 while reusing unchanged 25.12 binaries |
| [`openwrt-25.12-source`](profiles/openwrt-25.12-source/README.md) | selective-source | Stable source build that compiles only firmware-selected packages and dependencies |
| [`snapshot-source`](profiles/snapshot-source/README.md) | selective-source | Snapshot/arbitrary-source equivalent where release binaries are not assumed reusable |
| [`snapshot-full-source`](profiles/snapshot-full-source/README.md) | full-source | Full distribution/package build example from current OpenWrt source |

Additional profiles remain as compatibility or device-specific examples.

## Documentation

- [Using OpenWrt Builder](docs/usage.md)
- [Profile reference and build modes](docs/profiles.md)

## License

MIT
