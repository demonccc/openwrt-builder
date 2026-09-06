# Using OpenWrt Builder

This guide explains how to use the repository. For the exact profile format and the four build modes, see [Profile reference](profiles.md).

## Fork the repository

Fork `demonccc/openwrt-builder` to your own GitHub account or organization. The included profiles are examples and starting points; keep, copy, or delete them as needed.

## Choose the closest profile

Choose the example that matches how much source you actually need to compile:

- `openwrt-25.12-imagebuilder` or `openwrt-24.10-imagebuilder` when published binaries are enough;
- `archer-a9-v6` when a released version needs a small source patch but unchanged packages should remain binary;
- `openwrt-25.12-source` or `snapshot-source` for a selective source build;
- `snapshot-full-source` for a full distribution/package build.

Copy the complete profile directory and edit it according to the [profile reference](profiles.md).

For example:

```bash
cp -r profiles/openwrt-25.12-source profiles/my-router
```

The source repository may be official OpenWrt or a compatible custom fork. The Archer A9 example points to `demonccc/openwrt` because the QCN5502/ath9k change is not in the release source used by the normal ImageBuilder.

## Build with GitHub Actions

Open **Actions** and run **Build OpenWrt firmware**. The workflow input is the profile directory name under `profiles/`. The profile is the complete build recipe.

Every successful workflow run uploads the generated firmware as an Actions artifact and creates a GitHub Release containing the firmware files. Source builds also install the OpenWrt build dependencies and free additional runner disk space; ImageBuilder builds skip that source-build preparation.

## Build locally

Validate every profile:

```bash
python3 scripts/build.py validate
```

Validate one profile:

```bash
python3 scripts/build.py validate --profile archer-a9-v6
```

Build a profile:

```bash
python3 scripts/build.py build --profile archer-a9-v6
```

The generated files are copied to `artifact/` by default. `BUILD_INFO` records the selected build mode and relevant source/ImageBuilder/package information.

## Embedded files and configuration

Profiles may contain a `files/` root filesystem overlay. See [Embedded files and configuration](profiles.md#embedded-files-and-configuration) for exact behavior and the recommended use of `/etc/uci-defaults/`.

## Validation in GitHub Actions

The **Validate profiles** workflow checks Python syntax and validates all profiles on `main`, feature branches matching `feat/**`, and pull requests.
