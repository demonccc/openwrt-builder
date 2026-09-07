# OpenWrt 25.12 ImageBuilder example

This profile demonstrates **mode 1: ImageBuilder**, the fastest build path.

Use it when the device is already supported by the official release and no source patch is required. The builder downloads the official OpenWrt 25.12.5 ImageBuilder and assembles the image from already-built packages selected in `packages`.

Nothing in the OpenWrt source tree is compiled locally: no kernel, toolchain, host tools, or userspace packages. This should be the default choice whenever an official ImageBuilder can produce the required firmware.

When copying the profile for another device, change the ImageBuilder URL to the correct target/subtarget and set `DEVICE` to a profile supported by that ImageBuilder.

See the [profile reference](../../docs/profiles.md) for ImageBuilder behavior.
