# OpenWrt Builder

Reusable OpenWrt firmware builder powered by GitHub Actions.

This repository keeps build automation and reusable profiles separate from the OpenWrt source tree. Use the profile that matches how much of OpenWrt must actually be compiled.

## Build modes

| Mode | Profile example | When to use it |
| --- | --- | --- |
| **1. ImageBuilder** | [`openwrt-25.12-imagebuilder`](profiles/openwrt-25.12-imagebuilder/README.md), [`openwrt-24.10-imagebuilder`](profiles/openwrt-24.10-imagebuilder/README.md) | Nothing in OpenWrt source needs to change. Assemble firmware entirely from published binaries. |
| **2. Release patched** | [`archer-a9-v6`](profiles/archer-a9-v6/README.md) | A released OpenWrt version needs a small source/kernel patch. Compile only the patched source package(s) and target pieces, then reuse published release packages for the firmware. |
| **3. Selective source** | [`openwrt-25.12-source`](profiles/openwrt-25.12-source/README.md), [`snapshot-source`](profiles/snapshot-source/README.md) | Build from a source tree, but compile only the firmware package selection and its dependency graph. |
| **4. Full source** | [`snapshot-full-source`](profiles/snapshot-full-source/README.md) | Build a distribution/package set from source. Selected feeds define which feed trees participate in the full build. |

Other profiles in `profiles/` are additional examples.

## Documentation

The canonical builder documentation lives under [`docs/`](docs/):

- [Using OpenWrt Builder](docs/usage.md) — running builds locally or in GitHub Actions.
- [Profile reference and build modes](docs/profiles.md) — exact behavior of the four modes, settings, package selection, feeds, patches, and embedded files.

Profile `README.md` files explain only why that particular profile exists and the decisions specific to it.

## License

MIT
