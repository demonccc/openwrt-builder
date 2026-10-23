# release-patched SDK dependencies

`release-patched` keeps firmware package selection separate from source compilation.

Packages selected for the final firmware do not automatically become source build roots. The only patched source roots are those declared in `source-build-targets`.

The exact-release SDK may compile dependencies of a declared patched root, including kernel module prerequisites. This does not cause those dependencies to be injected into the final firmware. Only APKs explicitly selected from `source-build-targets` are copied into the official ImageBuilder.

This preserves the intended boundary:

- explicit patched package roots are compiled in the official SDK;
- genuine build dependencies may be prepared by the SDK;
- unrelated selected packages such as `batman-adv` are not copied as custom APKs;
- unchanged packages remain official `BASE_REF` binaries in the final image.


## How to read dependency expansion

A dependency appearing in an SDK or kmod preparation log is not automatically a custom package in the final firmware. The builder distinguishes:

- SDK build dependencies needed to compile an explicit source root;
- SDK dependencies needed to compile a custom module;
- official runtime dependencies resolved by the exact `BASE_REF` repositories;
- custom APKs explicitly allowed by the profile.

Adding a package can therefore expand the build when its `DEPENDS` or `PKG_BUILD_DEPENDS` pulls more of the package graph into the SDK. That is expected if the final `CUSTOM_APK_PACKAGES` list remains within the declared boundary. If unrelated userspace is copied as custom output, inspect the package metadata and `source-build-targets`; do not add the entire dependency closure there.

See [the usage troubleshooting guide](usage.md#dependency-expansion-and-troubleshooting) for the commands and the expected/suspicious cases.
