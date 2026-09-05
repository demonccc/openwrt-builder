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

The workflow accepts:

- `profile`: directory name under `profiles/`;
- `runner`: `github-hosted` or `self-hosted`;
- `source_ref`: optional branch, tag, or commit override for source builds;
- `create_release`: whether the generated firmware should also be published as a GitHub Release.

The source ref override is ignored for ImageBuilder profiles.

### GitHub-hosted runners

The workflow uses Ubuntu 24.04.

For source builds it frees additional disk space and installs the full set of OpenWrt build dependencies before compiling.

For ImageBuilder builds it skips the large disk-cleanup step and the source-build toolchain installation, because ImageBuilder only needs the tools required to download, extract, and assemble the image.

### Self-hosted runners

A self-hosted runner can be selected when you want to use your own CPU, RAM, storage, cache, or build environment.

The current workflow expects an Ubuntu/Debian-compatible runner with `sudo` available.

For source builds it installs the OpenWrt source-build dependencies. For ImageBuilder builds it installs only the smaller set of tools required for ImageBuilder operation.

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
