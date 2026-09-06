# OpenWrt 24.10.6 — ImageBuilder example

This profile demonstrates **build mode 1: ImageBuilder** using the official OpenWrt 24.10.6 `x86/64` ImageBuilder.

It exists alongside the 25.12 example to show that the same fast path works for older supported release families: pin the matching official ImageBuilder and select the final firmware packages without compiling OpenWrt source.

Use this pattern whenever all required kernel and userspace components already exist as published binaries for the chosen release.
