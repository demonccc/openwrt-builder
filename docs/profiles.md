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

### ImageBuilder behavior

For an ImageBuilder build, the same include/exclude list is passed through the native ImageBuilder `PACKAGES` argument.

## `feeds`

For `METHOD=source`, `feeds` uses standard OpenWrt feed syntax. Each non-comment line is appended to `feeds.conf.default` before the builder runs:

```text
./scripts/feeds update -a
./scripts/feeds install -a
```

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

For source profiles it also validates `feeds` and `git-packages` syntax. For ImageBuilder profiles those two files are intentionally ignored.

The optional `README.md` and `files/` directory are not required for a valid profile.
