# OpenWrt 25.12.5 — ImageBuilder example

This profile demonstrates **build mode 1: ImageBuilder** using the official OpenWrt 25.12.5 `x86/64` ImageBuilder.

Use it when no OpenWrt source or kernel change is required. Nothing is compiled: the firmware is assembled from packages already published for the release, making this the fastest build path.

The `packages` file is the only package selection for the image. This profile is a template for released OpenWrt targets that can be customized entirely with published binaries and filesystem overlays.
