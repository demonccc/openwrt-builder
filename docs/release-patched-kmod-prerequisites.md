# release-patched kernel package prerequisites

`release-patched` keeps firmware package selection separate from source compilation.

Packages selected for the final firmware do not automatically become source build roots. The only patched source roots are those declared in `source-build-targets`.

Kernel package validation is stricter: a patched external kernel module can depend on an in-tree kernel module whose `.ko` provider must already be staged before the patched package is created. The builder therefore resolves the transitive `kmod-*` dependency closure of the explicitly patched package outputs and prepares only external prerequisite subpackages from their source roots.

For example, `kmod-ath9k-common` depends on `kmod-random-core`. The builder may run the `package/kernel/linux/compile` source root with package overrides that enable only `kmod-random-core` and disable unrelated selected subpackages from that source root. The resulting prerequisite APK is not copied into the custom ImageBuilder; the final firmware continues to use the official `BASE_REF` package for unchanged prerequisites.

This preserves the intended boundary:

- explicit patched package roots are compiled locally;
- required kernel-module prerequisites are staged narrowly for dependency validation;
- unrelated selected packages such as `batman-adv` are not compiled;
- unchanged packages remain official `BASE_REF` binaries in the final image.


## How to read dependency expansion

A dependency appearing in an SDK or kmod preparation log is not automatically a custom package in the final firmware. The builder distinguishes:

- SDK build dependencies needed to compile an explicit source root;
- narrow external kmod prerequisites needed to validate a custom module against the kernel ABI;
- official runtime dependencies resolved by the exact `BASE_REF` repositories;
- custom APKs explicitly allowed by the profile.

For AudioWRT, adding a package can therefore expand the build when its `DEPENDS` or `PKG_BUILD_DEPENDS` pulls more of the package graph into the SDK. That is expected if the expansion stays inside SDK preparation and the final `CUSTOM_APK_PACKAGES` list remains within the declared boundary. If unrelated userspace is compiled as custom output, inspect the package metadata and `source-build-targets`; do not add the entire dependency closure there.

See [the usage troubleshooting guide](usage.md#dependency-expansion-and-troubleshooting) for the commands and the expected/suspicious cases.
