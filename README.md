# OpenWRT Builder

Reusable OpenWrt firmware builder powered by GitHub Actions.

The goal of this repository is to make it simple to create reproducible and customized OpenWrt firmware builds without mixing build automation with the OpenWrt source tree itself.

You fork this repository, choose or create a profile, and build firmware from either the official OpenWrt repository or any custom OpenWrt fork. A profile describes how OpenWrt should be built, which device to target, which packages to include or exclude, and optionally which files or default configuration should be embedded in the firmware.

There is no custom YAML, TOML, or JSON profile format to learn.

## How to use this repository

### 1. Fork the repository

Fork `demonccc/openwrt-builder` to your own GitHub account or organization.

Your fork contains the build workflow, the build engine, and a set of reusable profiles. In normal use, most customization happens under `profiles/`.

The bundled profiles are examples and starting points, not required configuration. You can delete any profiles you do not plan to use and keep only the ones relevant to your builds.

### 2. Choose a base profile

The repository includes profiles that show both supported build methods:

| Profile | Method | Source | Target | Purpose |
| --- | --- | --- | --- | --- |
| `snapshot-source` | Source | `openwrt/openwrt:main` | x86/64 generic | Build current OpenWrt snapshot directly from source |
| `snapshot-imagebuilder` | ImageBuilder | official snapshot ImageBuilder | x86/64 generic | Fast snapshot image assembly using prebuilt packages |
| `openwrt-25.12-source` | Source | `openwrt/openwrt:openwrt-25.12` | x86/64 generic | Build OpenWrt 25.12 directly from source |
| `openwrt-25.12-imagebuilder` | ImageBuilder | official 25.12.5 ImageBuilder | x86/64 generic | Fast 25.12 image assembly using prebuilt packages |
| `openwrt-24.10-source` | Source | `openwrt/openwrt:openwrt-24.10` | x86/64 generic | Build OpenWrt 24.10 directly from source |
| `archer-a9-v6` | Source | `demonccc/openwrt:openwrt-25.12-archerA9v6` | TP-Link Archer A9 v6 | Custom OpenWrt 25.12 build with QCN5502 support |
| `velop-whw03-v2-imagebuilder` | ImageBuilder | official 25.12.5 ImageBuilder | Linksys Velop WHW03 V2 | WHW03 V2 firmware with selected Wi-Fi, mesh, roaming, management and diagnostic packages |

Each bundled profile also contains its own `README.md` explaining what that profile demonstrates and why it exists.

To create your own profile, copy an entire directory together with all of its contents. For example, for a normal source build based on OpenWrt 25.12:

```bash
cp -r profiles/openwrt-25.12-source profiles/my-router
```

Or, if you only need to customize an image with packages already published by OpenWrt:

```bash
cp -r profiles/openwrt-25.12-imagebuilder profiles/my-router
```

Then edit the files inside `profiles/my-router/`.

After creating your own profiles, you can delete the bundled profiles you do not need.

## Build methods

### Source builds

`METHOD=source` clones an OpenWrt Git repository and performs a normal OpenWrt source build.

Use source builds when you need:

- a custom OpenWrt fork;
- kernel or driver patches;
- experimental device support;
- custom feeds containing source packages;
- packages loaded directly from Git repositories;
- any change that requires compiling OpenWrt itself.

A source profile uses settings like:

```text
METHOD=source
REPOSITORY=https://github.com/openwrt/openwrt.git
REF=openwrt-25.12
TARGET=ath79
SUBTARGET=generic
DEVICE=vendor_device-name
```

`REF` can be a branch, tag, or commit.

The bundled `archer-a9-v6` profile is an example of a custom source build. It points to a custom OpenWrt fork containing the QCN5502 patches required by the TP-Link Archer A9 v6:

```text
METHOD=source
REPOSITORY=https://github.com/demonccc/openwrt.git
REF=openwrt-25.12-archerA9v6
TARGET=ath79
SUBTARGET=generic
DEVICE=tplink_archer-a9-v6
```

The builder does not care whether the source repository is official OpenWrt or a custom fork.

### ImageBuilder builds

`METHOD=imagebuilder` downloads an already-built OpenWrt ImageBuilder and assembles a firmware image without compiling the full OpenWrt source tree.

This is normally much faster than a source build and is useful when all packages you need are already available as compiled packages for that OpenWrt build.

An ImageBuilder profile uses settings like:

```text
METHOD=imagebuilder
IMAGEBUILDER_URL=https://downloads.openwrt.org/releases/25.12.5/targets/x86/64/openwrt-imagebuilder-25.12.5-x86-64.Linux-x86_64.tar.zst
DEVICE=generic
```

The `packages` file works in both methods.

Important: in `imagebuilder` mode, the `feeds` and `git-packages` files are ignored completely. They may contain entries and do not need to be emptied or deleted; those entries simply do not participate in the ImageBuilder build. ImageBuilder can only use packages that are already available in the prebuilt package repositories associated with that ImageBuilder.

## Profile structure

Every profile contains four required files:

```text
profiles/my-router/
  settings
  packages
  feeds
  git-packages
```

A profile may also contain:

```text
  README.md
  files/
```

`README.md` is documentation for people using the profile. It is not interpreted by the builder.

`files/` is optional and is used to embed files or predefined OpenWrt configuration into the generated firmware.

### `settings`

Defines the build method and the settings required by that method.

For `source`, it contains the Git repository, ref, target, subtarget, and device.

For `imagebuilder`, it contains the ImageBuilder URL and device profile.

### `packages`

Use one package per line. Prefix a package with `-` to explicitly exclude it.

```text
luci
dnsmasq-full
wpad-mbedtls

-dnsmasq
-wpad-basic-mbedtls
```

Do not list transitive dependencies just because they appear in a generated `.config`. List the features you intentionally want and let OpenWrt resolve their dependencies.

For source builds, the builder verifies after `make defconfig` that requested packages were selected and excluded packages were not enabled.

For ImageBuilder builds, the same list is passed to OpenWrt ImageBuilder through its `PACKAGES` argument.

### `feeds`

For source builds, use standard OpenWrt `feeds.conf` syntax:

```text
src-git myfeed https://github.com/example/openwrt-feed.git
```

For ImageBuilder builds, this file is ignored, even when it contains entries.

### `git-packages`

For source builds, use this file for OpenWrt packages distributed directly from Git repositories instead of through a feed.

```text
REPOSITORY [REF] [PATH]
```

Examples:

```text
https://github.com/example/luci-app-example.git
https://github.com/example/luci-app-example.git v1.2.0
https://github.com/example/openwrt-apps.git main luci-app-example
https://github.com/example/openwrt-apps.git - luci-app-example
```

Adding a Git repository only makes the package available to OpenWrt. Add the package name to `packages` when it must be installed in the firmware.

For ImageBuilder builds, this file is ignored, even when it contains entries.

## Embedding configuration and files

A profile can optionally contain a `files/` directory. Its contents are copied into the firmware filesystem using normal OpenWrt rootfs paths.

For example:

```text
profiles/my-router/
  files/
    etc/
      banner
      uci-defaults/
        99-custom-settings
    usr/
      bin/
        custom-script
```

The resulting firmware receives those files as:

```text
/etc/banner
/etc/uci-defaults/99-custom-settings
/usr/bin/custom-script
```

This can be used for things such as:

- OpenWrt UCI defaults;
- service defaults;
- sysctl configuration;
- certificates or public keys;
- scripts;
- custom banners;
- other files that should already exist in the generated firmware.

For settings that should be applied through UCI, prefer scripts under `/etc/uci-defaults/` instead of replacing entire generated OpenWrt configuration files. This lets OpenWrt generate the device defaults first and then apply only the intended changes during first boot.

For a source build, the builder merges the profile `files/` directory into the OpenWrt source tree `files/` directory before compilation.

For an ImageBuilder build, the builder passes the profile directory to OpenWrt using the native `FILES=...` ImageBuilder option.

If a profile does not contain `files/`, the firmware keeps the normal OpenWrt defaults.

## Building firmware

Open **Actions** in your fork and run **Build OpenWrt firmware**.

Choose:

- the profile to build;
- the runner type;
- an optional source ref override;
- whether a GitHub Release should be created.

For example:

```text
Profile: archer-a9-v6
Runner: github-hosted
```

The source ref override applies only to source builds. It is ignored by ImageBuilder builds.

### GitHub-hosted runners

Choose `github-hosted` to build on a GitHub Actions runner.

The workflow detects the selected profile method before preparing the runner:

- source builds free additional disk space and install the complete OpenWrt source-build dependency set;
- ImageBuilder builds skip the expensive disk cleanup and source toolchain installation and use the tools already available in the Ubuntu 24.04 GitHub runner.

This keeps ImageBuilder jobs significantly lighter and faster.

### Self-hosted runners

Choose `self-hosted` to build on your own GitHub Actions runner.

This is useful when you want more CPU, RAM, disk space, persistent caches, or full control over the build machine.

The current workflow expects an Ubuntu/Debian-compatible runner with `sudo` available. Source builds install the complete OpenWrt build dependencies. ImageBuilder builds only install the small runtime tool set required to assemble an image (`make`, `python3`, `tar`, and `zstd`).

Register the self-hosted runner in the repository or organization through GitHub, then select `self-hosted` when starting the workflow.

## Local builds

The same build engine can be run directly on a machine with the required build tools installed:

```bash
python3 scripts/build.py validate
python3 scripts/build.py build --profile archer-a9-v6
python3 scripts/build.py build --profile openwrt-25.12-imagebuilder
```

Build output is copied to `artifact/` and includes a `BUILD_INFO` file describing the build method, source or ImageBuilder, target profile, explicit package selections, and whether profile `files/` were included.

## Repository structure

```text
.github/workflows/
  build.yml
  validate.yml
profiles/
  snapshot-source/
  snapshot-imagebuilder/
  openwrt-25.12-source/
  openwrt-25.12-imagebuilder/
  openwrt-24.10-source/
  archer-a9-v6/
  velop-whw03-v2-imagebuilder/
scripts/
  build.py
```

A directory under `profiles/` is a profile. Copy an existing directory when creating a new build configuration, and delete profiles you do not use.

## Validation

Validate every profile:

```bash
python3 scripts/build.py validate
```

Validate one profile:

```bash
python3 scripts/build.py validate --profile archer-a9-v6
```

Pull requests also run profile validation automatically.

See [`docs/profiles.md`](docs/profiles.md) for the complete profile format reference.

## License

MIT
