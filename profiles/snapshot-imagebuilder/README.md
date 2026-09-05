# Snapshot ImageBuilder build

Builds a current OpenWrt snapshot image using the official prebuilt ImageBuilder instead of compiling OpenWrt from source.

- Method: `imagebuilder`
- Target: `x86/64`
- Device: `generic`
- Source: official OpenWrt snapshot ImageBuilder

Use this profile when you want a fast snapshot firmware build and all required packages are already published by OpenWrt.

`feeds` and `git-packages` are ignored in this mode. The optional profile `files/` directory is supported and can embed predefined files or configuration into the firmware.

This is a useful base profile to copy for other snapshot ImageBuilder builds.
