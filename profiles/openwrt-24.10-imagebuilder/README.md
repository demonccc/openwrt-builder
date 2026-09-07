# OpenWrt 24.10 ImageBuilder example

This profile demonstrates **mode 1: ImageBuilder**, the fastest build path.

Use it when the target device is already supported by an official OpenWrt release and no source patch is required. The builder downloads the official ImageBuilder and asks it to assemble a firmware image with the packages listed in `packages`. No kernel, toolchain, or userspace package is compiled locally.

This example uses OpenWrt 24.10.5 on x86/64. When copying the profile for another target or release, change `IMAGEBUILDER_URL` and `DEVICE`; keep package customization in `packages`.

`feeds` and `git-packages` are intentionally unused in this mode because the official ImageBuilder consumes already-built OpenWrt package repositories.
