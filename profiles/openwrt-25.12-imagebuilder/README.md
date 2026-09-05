# OpenWrt 25.12 ImageBuilder build

Builds an OpenWrt 25.12.5 image using the official prebuilt ImageBuilder.

- Method: `imagebuilder`
- Target: `x86/64`
- Device: `generic`
- Release: `25.12.5`
- Source: official OpenWrt ImageBuilder

Use this profile when you want a fast stable build and all required packages are already published by OpenWrt.

`feeds` and `git-packages` are ignored in this mode. The optional profile `files/` directory is supported and can embed predefined files or configuration into the firmware.

This is the recommended base profile to copy for other stable 25.12 ImageBuilder builds.
