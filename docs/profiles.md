# Profile reference

A profile is a directory under `profiles/` that describes one OpenWrt firmware build.

For the workflow used to fork the repository, copy profiles, run builds, and use runners, see [Using OpenWrt Builder](usage.md).

## Profile structure

Required files:

```text
profiles/my-router/
  settings
  packages
  feeds
  git-packages
```

Optional files and directories:

```text
profiles/my-router/
  README.md
  files/
```

The four required files are deliberately plain text. Blank lines and comments starting with `#` are ignored where applicable.

`README.md` is human documentation for that specific profile. It is not parsed by the builder.

`files/` contains files that should be embedded into the generated OpenWrt filesystem. It is optional and works with both build methods.

## Build methods

Profiles support two methods:

- `source`: clone an OpenWrt Git repository and compile the selected target, packages, and dependencies;
- `imagebuilder`: download an existing OpenWrt ImageBuilder and assemble firmware from already-built packages.

The method is selected in `settings` with `METHOD=source` or `METHOD=imagebuilder`.

## `settings`

### Source build

A source profile requires:

```text
METHOD=source
REPOSITORY=https://github.com/openwrt/openwrt.git
REF=openwrt-25.12
TARGET=ath79
SUBTARGET=generic
DEVICE=vendor_device-name
```

- `REPOSITORY`: Git repository containing the OpenWrt source tree.
- `REF`: branch, tag, or commit to build.
- `TARGET`: OpenWrt target.
- `SUBTARGET`: OpenWrt subtarget.
- `DEVICE`: OpenWrt device profile.

The repository can be the official `openwrt/openwrt` repository or any compatible custom fork. This allows a profile to build OpenWrt trees containing device support, kernel changes, driver patches, or other source modifications that are not present upstream.

Source builds use `packages`, `feeds`, `git-packages`, and optional `files/`.

### Source-build acceleration is optional

A source profile may optionally define any of these settings:

```text
TOOLS_IMAGE=ghcr.io/openwrt/tools:openwrt-25.12
TOOLCHAIN_URL=https://downloads.openwrt.org/.../openwrt-toolchain-....tar.zst
FEED_NAMES=packages luci routing
```

They are independent and never required. If none are present, the builder follows the normal OpenWrt clean source-build path: OpenWrt builds its host tools and target toolchain from source, indexes all default feeds, then builds the selected target, packages, dependencies, and firmware image.

The bundled `openwrt-25.12-full-source` and `snapshot-full-source` profiles intentionally omit all three options as explicit full-source examples.

A full source build does **not** compile every package available from every feed. Feed indexing makes package definitions available to OpenWrt; actual compilation is still driven by the resolved OpenWrt configuration and dependency graph.

#### Optional prebuilt host tools

A source profile may define `TOOLS_IMAGE`:

```text
TOOLS_IMAGE=ghcr.io/openwrt/tools:openwrt-25.12
```

The container must contain the native OpenWrt prebuilt-tools layout:

```text
/prebuilt_tools/staging_dir/host
/prebuilt_tools/build_dir/host
```

The builder pulls the image with Docker, extracts `/prebuilt_tools`, links both host-tool trees into the temporary OpenWrt source checkout, and runs:

```text
./scripts/ext-tools.sh --refresh
```

This is the same mechanism used by OpenWrt's own CI. Both `staging_dir/host` and `build_dir/host` are necessary: the installed binaries alone are not sufficient for a normal source `world` build to consider `tools/compile` satisfied.

When `TOOLS_IMAGE` is set, the runner must have Docker available. GitHub-hosted Linux runners provide Docker. A self-hosted runner that does not want or cannot use prebuilt host tools should simply omit `TOOLS_IMAGE`.

The tools image must be compatible with the source revision and host OS/architecture. OpenWrt publishes branch-specific tools images for its CI; for the 25.12 branch, `ghcr.io/openwrt/tools:openwrt-25.12` is the matching upstream image.

The builder skips `tools/download` when prebuilt host tools are configured because those tool sources are not used.

#### Why the OpenWrt SDK is not used for host-tool acceleration

Official OpenWrt SDK archives include `staging_dir/host` and a target toolchain, but the SDK packaging process excludes `*/stamp` and does not include `build_dir/host`. That is sufficient for compiling packages *inside the SDK*, but not for transplanting the SDK into a normal source tree and skipping `tools/compile` during `make world`.

For source-build acceleration, use `TOOLS_IMAGE` for host tools and `TOOLCHAIN_URL` for the target toolchain. The builder intentionally does not expose `SDK_URL` as a source-build acceleration setting.

#### Optional prebuilt toolchain

A source profile may define `TOOLCHAIN_URL`:

```text
TOOLCHAIN_URL=https://downloads.openwrt.org/releases/25.12.5/targets/ath79/generic/openwrt-toolchain-25.12.5-ath79-generic_gcc-14.3.0_musl.Linux-x86_64.tar.zst
```

When this setting is present, the builder downloads and extracts the toolchain archive, detects the compiler prefix and GCC version, and configures OpenWrt with `CONFIG_EXTERNAL_TOOLCHAIN=y`.

This skips rebuilding the target compiler toolchain, including GCC, binutils, libc, kernel headers, fortify headers, and GDB. The target kernel, kernel modules, selected packages, package build dependencies, and firmware image are still compiled from the configured source tree.

If `TOOLCHAIN_URL` is omitted, the normal OpenWrt internal target toolchain is built from source.

#### Optional feed selection

By default, a source build updates and indexes every feed listed in the OpenWrt source tree's `feeds.conf.default`.

A source profile may restrict that work with `FEED_NAMES`:

```text
FEED_NAMES=packages luci routing
```

Feed names may be separated by spaces or commas. When set, the builder runs:

```text
./scripts/feeds update packages luci routing
```

instead of:

```text
./scripts/feeds update -a
```

Use this only when all explicitly selected packages and their feed dependencies are available from the listed feeds. Packages from the OpenWrt core tree are unaffected.

If `git-packages` contains entries, `FEED_NAMES` is ignored and all feeds are updated and indexed. External source packages may have feed dependencies that the builder cannot determine safely before installation.

#### Acceleration combinations

| Profile settings | Host tools | Target toolchain | Feed indexing |
| --- | --- | --- | --- |
| none | built from source | built from source | all default feeds |
| `FEED_NAMES` | built from source | built from source | selected feeds |
| `TOOLS_IMAGE` | prebuilt OpenWrt tools | built from source | all default feeds |
| `TOOLCHAIN_URL` | built from source | prebuilt external toolchain | all default feeds |
| `TOOLS_IMAGE` + `TOOLCHAIN_URL` | prebuilt OpenWrt tools | prebuilt external toolchain | all default feeds |
| `TOOLS_IMAGE` + `TOOLCHAIN_URL` + `FEED_NAMES` | prebuilt OpenWrt tools | prebuilt external toolchain | selected feeds |

The options are intentionally independent. Remove any option to restore the corresponding native OpenWrt work.

The source download phase is also scoped accordingly:

| Acceleration | Source download targets |
| --- | --- |
| none | normal `make download` |
| `TOOLS_IMAGE` only | `toolchain/download package/download target/download` |
| `TOOLCHAIN_URL` only | `tools/download package/download target/download` |
| both | `package/download target/download` |

### ImageBuilder build

An ImageBuilder profile requires:

```text
METHOD=imagebuilder
IMAGEBUILDER_URL=https://downloads.openwrt.org/releases/25.12.5/targets/x86/64/openwrt-imagebuilder-25.12.5-x86-64.Linux-x86_64.tar.zst
DEVICE=generic
```

- `IMAGEBUILDER_URL`: URL of the OpenWrt ImageBuilder archive.
- `DEVICE`: ImageBuilder profile passed to `make image PROFILE=...`.

ImageBuilder uses precompiled OpenWrt packages and avoids compiling the full source tree.

It uses `packages` and optional `files/`.

`feeds` and `git-packages` are ignored completely in ImageBuilder mode. They may contain entries; the builder does not parse or validate them for an ImageBuilder profile.

## `packages`

Use one package per line:

```text
luci
dnsmasq-full
-dnsmasq
```

A normal package name means the package must be included. A leading `-` means it must be excluded.

Inline comments are also supported:

```text
luci                 # include LuCI
-wpad-basic-mbedtls  # remove the default basic wpad variant
wpad-mbedtls         # use the full variant instead
```

Do not list every transitive dependency from a generated `.config` or package manifest. List the packages that are intentionally part of the firmware and let OpenWrt resolve their dependencies.

### Source behavior

For a source build, package entries are translated to OpenWrt `.config` symbols:

```text
package-name  -> CONFIG_PACKAGE_package-name=y
-package-name -> CONFIG_PACKAGE_package-name=n
```

After `make defconfig`, the builder verifies that requested packages were selected and explicitly excluded packages were not enabled.

The source build compiles the selected firmware packages and the dependencies required by OpenWrt. Packages merely present in a feed are not compiled unless they are selected or required as dependencies.

A failed parallel `make` fails the build immediately. The builder does not automatically retry the complete OpenWrt build serially.

### ImageBuilder behavior

For an ImageBuilder build, the same include/exclude list is passed through the native ImageBuilder `PACKAGES` argument.

## `feeds`

For `METHOD=source`, `feeds` uses standard OpenWrt feed syntax. Each non-comment line is appended to `feeds.conf.default` before feed metadata is updated.

Without `FEED_NAMES`, the builder runs:

```text
./scripts/feeds update -a
```

With `FEED_NAMES`, only those named feeds are updated and indexed.

The builder then installs only the packages listed for inclusion in the profile:

```text
./scripts/feeds install <requested-package> ...
```

OpenWrt resolves the required feed dependencies recursively. Package names that belong to the OpenWrt core tree do not need to come from a feed.

If `git-packages` contains entries, the builder updates all feeds and intentionally falls back to:

```text
./scripts/feeds install -a
```

This makes feed packages available to externally loaded Git packages whose dependencies are not known to the builder in advance. `feeds install -a` registers packages in the OpenWrt source tree; it does not by itself compile every package.

Example:

```text
src-git myfeed https://github.com/example/openwrt-feed.git
```

Supported feed entry prefixes are:

```text
src-git
src-git-full
src-link
src-cpy
```

For `METHOD=imagebuilder`, this file is ignored even when it contains entries.

## `git-packages`

For `METHOD=source`, this file makes OpenWrt packages available directly from Git repositories without defining a feed.

Format:

```text
REPOSITORY [REF] [PATH]
```

- `REPOSITORY`: required Git repository URL;
- `REF`: optional branch, tag, or commit;
- `PATH`: optional package directory inside the repository.

Use `-` as `REF` when a path is required but the repository default branch should be used.

Examples:

```text
https://github.com/example/luci-app-example.git
https://github.com/example/luci-app-example.git v1.2.0
https://github.com/example/openwrt-apps.git main luci-app-example
https://github.com/example/openwrt-apps.git - luci-app-example
```

The selected package directory is copied into the temporary OpenWrt source tree under `package/openwrt-builder/`.

Adding a Git package only makes it available to OpenWrt. Add its OpenWrt package name to `packages` when it should be installed in the firmware.

Because external Git packages can have dependencies that are not known before their source is loaded, source profiles with `git-packages` update and install all configured feeds before the external package is copied into the build tree.

For `METHOD=imagebuilder`, this file is ignored even when it contains entries.

## Embedded files and configuration

A profile may contain an optional `files/` directory.

The directory mirrors the root filesystem of the generated OpenWrt image. For example:

```text
profiles/my-router/files/etc/banner
profiles/my-router/files/etc/uci-defaults/99-custom-settings
profiles/my-router/files/usr/bin/custom-script
```

becomes:

```text
/etc/banner
/etc/uci-defaults/99-custom-settings
/usr/bin/custom-script
```

### Source builds

For `METHOD=source`, the profile `files/` tree is merged into the native OpenWrt source-tree `files/` directory before the build. Profile files override files at the same relative path.

### ImageBuilder builds

For `METHOD=imagebuilder`, the builder passes the profile directory through the native ImageBuilder `FILES=...` argument.

### Configuration strategy

Use direct files when the entire file should be part of the image exactly as stored in the profile.

For configuration changes that should be applied on first boot, prefer `/etc/uci-defaults/` scripts instead of replacing complete `/etc/config/*` files. This lets OpenWrt create the normal device defaults first and then apply only the intended changes.

Example:

```sh
#!/bin/sh

uci set irqbalance.irqbalance.enabled='1'
uci commit irqbalance

exit 0
```

A successful `uci-defaults` script is normally removed after it runs on first boot.

The builder does not automatically generate network, wireless, firewall, or topology configuration. Only files explicitly placed in the profile `files/` directory are embedded.

## `README.md`

A profile may include `README.md` to explain only the purpose and profile-specific decisions for that build, such as:

- hardware or OpenWrt version;
- source repository or ImageBuilder release;
- intentional package replacements;
- device-specific patches or constraints.

Generic builder behavior should not be duplicated in profile README files. Link to this reference instead when generic behavior needs to be mentioned.

## Validation

The builder validates all four required files for every profile.

For source profiles it also validates `TOOLS_IMAGE`, `TOOLCHAIN_URL`, `FEED_NAMES`, `feeds`, and `git-packages` syntax. `TOOLS_IMAGE` is accepted as a container image reference; its runtime layout and Docker availability are checked when a build actually uses it.

For ImageBuilder profiles, source-only settings and source-only files are intentionally ignored.

The optional `README.md` and `files/` directory are not required for a valid profile.
