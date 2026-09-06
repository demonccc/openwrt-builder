# Using OpenWrt Builder

This guide explains how to use the repository. For the profile file format and build-method details, see [Profile reference](profiles.md).

## Fork the repository

Fork `demonccc/openwrt-builder` to your own GitHub account or organization.

The fork contains the build workflows, the builder script, and a set of reusable profiles. The included profiles are examples and starting points; they are not required configuration.

You can delete any profiles you do not plan to use and keep only the profiles relevant to your builds.

## Create or customize a profile

Choose the included profile that is closest to the OpenWrt version and build method you need, then copy the complete directory.

For example, to create a source build based on OpenWrt 25.12:

```bash
cp -r profiles/openwrt-25.12-source profiles/my-router
```

For an ImageBuilder-based profile:

```bash
cp -r profiles/openwrt-25.12-imagebuilder profiles/my-router
```

Edit the copied profile according to the [profile reference](profiles.md).

A source profile can point to the official OpenWrt repository or to any compatible custom OpenWrt fork. The `archer-a9-v6` profile is an example: it builds from `demonccc/openwrt` because that fork contains the QCN5502 support required by that device.

An ImageBuilder profile points to an official or otherwise compatible OpenWrt ImageBuilder archive and assembles firmware from packages already built for that target.

## Build with GitHub Actions

Open **Actions** in your fork and run **Build OpenWrt firmware**.

The workflow has a single input:

- `profile`: directory name under `profiles/`.

The selected profile is the complete build recipe. Source repository, source ref, target, device, package selection, feeds, optional external toolchain, and other build behavior come from the profile itself.

The workflow runs on GitHub-hosted Ubuntu 24.04 runners.

Every successful workflow run:

1. uploads the generated firmware as a GitHub Actions artifact;
2. creates a GitHub Release containing the generated firmware files.

Release creation is the default behavior for all profiles so users can find firmware from the repository Releases page without browsing individual workflow runs.

For source builds the workflow frees additional disk space and installs the OpenWrt source-build dependencies before compiling.

For ImageBuilder builds it skips the source-build disk cleanup and toolchain dependency installation because ImageBuilder assembles firmware from already-built packages.

## Build locally

The same builder can be used outside GitHub Actions when the required tools are installed.

Validate all profiles:

```bash
python3 scripts/build.py validate
```

Validate one profile:

```bash
python3 scripts/build.py validate --profile archer-a9-v6
```

Build a source profile:

```bash
python3 scripts/build.py build --profile archer-a9-v6
```

Build an ImageBuilder profile:

```bash
python3 scripts/build.py build --profile velop-whw03-v2-imagebuilder
```

The generated files are copied to `artifact/` by default. The output also contains `BUILD_INFO`, which records the selected profile, build method, source or ImageBuilder reference, and explicit package selections.

## Embedded files and configuration

Profiles can optionally contain a `files/` directory to embed files directly into the generated firmware, including OpenWrt configuration or first-boot scripts.

This works with both source and ImageBuilder profiles. See [Embedded files and configuration](profiles.md#embedded-files-and-configuration) in the profile reference for the exact behavior and recommended use of `/etc/uci-defaults/`.

## Validation in GitHub Actions

The `Validate profiles` workflow checks Python syntax and validates all profiles on `main`, feature branches matching `feat/**`, and pull requests.
