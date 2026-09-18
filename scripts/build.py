#!/usr/bin/env python3
"""OpenWrt Builder CLI with the release-patched flow layered over the implementation.

release-patched follows the same boundary used by AudioWRT:
- compile explicitly patched package roots in the exact-release official SDK;
- keep unchanged runtime packages from the exact-release official repositories;
- assemble with the exact-release official ImageBuilder.

The only target-side work kept outside the SDK is creation of a per-device
kernel artifact when the custom checkout changes the DTS. That artifact reuses
the official release vmlinux and runs only the OpenWrt image/DTS pipeline; it
does not rebuild the kernel.
"""

from pathlib import Path
import shutil

_IMPL_PATH = Path(__file__).with_name("build_impl.py")
_ORIGINAL_NAME = __name__

# Execute the implementation in this module namespace so tests and monkeypatches
# continue to see the same globals/functions as before. Suppress its __main__
# block until the release-patched overrides below have been installed.
globals()["__name__"] = "openwrt_builder_impl"
exec(compile(_IMPL_PATH.read_text(encoding="utf-8"), str(_IMPL_PATH), "exec"), globals())
globals()["__name__"] = _ORIGINAL_NAME


def _relative_to_build_dir(path, tree_root):
    build_dir = Path(tree_root) / "build_dir"
    try:
        return Path(path).resolve().relative_to(build_dir.resolve())
    except ValueError as exc:
        raise BuilderError(f"Path is outside OpenWrt build_dir: {path}") from exc


def _official_build_dir_peer(official_ib, source_path, source_dir, marker):
    """Resolve the exact-release ImageBuilder peer for an OpenWrt build_dir path."""
    relative = _relative_to_build_dir(source_path, source_dir)
    exact = Path(official_ib) / "build_dir" / relative
    if (exact / marker).is_file():
        return exact

    # Normally exact release source and ImageBuilder use the same target triplet.
    # Keep one deterministic fallback for extracted archives whose target prefix
    # differs while the remaining build_dir layout is identical.
    relative_parts = relative.parts
    suffix = Path(*relative_parts[1:]) if len(relative_parts) > 1 else Path(source_path).name
    candidates = [
        path
        for path in (Path(official_ib) / "build_dir").glob(f"target-*/{suffix}")
        if (path / marker).is_file()
    ]
    if len(candidates) != 1:
        raise BuilderError(
            "Could not resolve one official ImageBuilder peer for "
            f"{source_path} containing {marker}; found {len(candidates)}"
        )
    return candidates[0]


def prepare_device_kernel_artifact(source_dir, settings, jobs, official_ib=None):
    """Build only the patched device image artifact using the official kernel.

    AudioWRT deliberately does not rebuild the release kernel. release-patched
    follows the same rule. OpenWrt's ath79 per-device kernel image is the
    official generic kernel plus the device DTB/image pipeline, so seed the
    exact-release vmlinux from the official ImageBuilder and build only that
    device artifact from the custom checkout.
    """
    if official_ib is None:
        raise BuilderError("release-patched device artifacts require the official ImageBuilder")

    # Prepare source/DTS state, not a kernel image. This must never request the
    # linux .image target: doing so recompiles the whole kernel and defeats the
    # exact-release ABI boundary.
    run(["make", "target/linux/prepare", "NO_DEPS=1", f"-j{jobs}"], cwd=source_dir)

    image_dir = target_image_directory(source_dir, settings)
    topdir = Path(source_dir).resolve()
    relative_image_dir = str(image_dir.relative_to(source_dir))
    make_base = [
        "make", "-s", "-C", relative_image_dir, "--no-print-directory",
        f"TOPDIR={topdir}", "TARGET_BUILD=",
    ]
    database = subprocess.run(
        [*make_base, "-pn", "install"],
        cwd=source_dir,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if database.returncode:
        detail = database.stderr.strip().splitlines()
        suffix = f": {detail[-1]}" if detail else ""
        raise BuilderError(f"Could not inspect OpenWrt image make database{suffix}")

    kernel_target = parse_device_kernel_target(database.stdout, settings["DEVICE"])

    # OpenWrt deliberately keeps these as two different directories:
    # KERNEL_BUILD_DIR (e.g. linux-ath79_generic) contains vmlinux and device
    # artifacts, while LINUX_DIR (e.g. linux-ath79_generic/linux-6.12.94)
    # contains the prepared kernel source tree and scripts/dtc/dtc. ImageBuilder
    # preserves the same split, so resolve each peer independently.
    source_kernel_dir = kernel_target.parent
    source_linux_dir = resolve_linux_source_directory(source_dir, settings)

    official_kernel_dir = _official_build_dir_peer(
        official_ib, source_kernel_dir, source_dir, "vmlinux"
    )
    official_linux_dir = _official_build_dir_peer(
        official_ib, source_linux_dir, source_dir, "scripts/dtc/dtc"
    )

    official_vmlinux = official_kernel_dir / "vmlinux"
    seeded_vmlinux = source_kernel_dir / "vmlinux"
    seeded_vmlinux.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(official_vmlinux, seeded_vmlinux)

    # target/linux/prepare lays out the source tree but does not build dtc.
    # ImageBuilder ships dtc as a bundled host-tool wrapper: "dtc" executes a
    # sibling ".dtc.bin" through libraries under staging_dir/host/lib. Copy the
    # complete bundled tool and its exact-release runtime instead of copying only
    # the wrapper script.
    official_dtc_dir = official_linux_dir / "scripts" / "dtc"
    seeded_dtc_dir = source_linux_dir / "scripts" / "dtc"
    if not (official_dtc_dir / "dtc").is_file():
        raise BuilderError(
            f"Official ImageBuilder kernel tree is missing dtc: {official_dtc_dir / 'dtc'}"
        )
    shutil.copytree(
        official_dtc_dir,
        seeded_dtc_dir,
        dirs_exist_ok=True,
        symlinks=True,
    )

    official_host_lib = Path(official_ib) / "staging_dir" / "host" / "lib"
    seeded_host_lib = Path(source_dir) / "staging_dir" / "host" / "lib"
    if not official_host_lib.is_dir():
        raise BuilderError(
            f"Official ImageBuilder is missing bundled host libraries: {official_host_lib}"
        )
    seeded_host_lib.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        official_host_lib,
        seeded_host_lib,
        dirs_exist_ok=True,
        symlinks=True,
    )

    print(
        f"Seeded exact-release vmlinux from official ImageBuilder: {official_vmlinux}",
        flush=True,
    )
    print(
        f"Seeded exact-release bundled dtc from official ImageBuilder: {official_dtc_dir}",
        flush=True,
    )

    # Build the custom DTB/per-device kernel wrapper only. The generic kernel
    # itself is the prebuilt official release kernel copied above.
    run(
        [
            "make", "-C", relative_image_dir,
            f"TOPDIR={topdir}", "TARGET_BUILD=", "kernel_prepare", f"-j{jobs}",
        ],
        cwd=source_dir,
    )
    run(
        [
            "make", "-C", relative_image_dir,
            f"TOPDIR={topdir}", "TARGET_BUILD=", str(kernel_target), f"-j{jobs}",
        ],
        cwd=source_dir,
    )
    if not kernel_target.is_file():
        raise BuilderError(f"Device kernel artifact was not generated: {kernel_target}")

    print(
        f"Device kernel artifact built from official kernel + patched DTS: {kernel_target}",
        flush=True,
    )
    return kernel_target


def inject_device_kernel_into_official_imagebuilder(
    device_kernel, source_dir, official_ib
):
    """Replace only the device kernel artifact inside the official ImageBuilder."""
    relative = _relative_to_build_dir(device_kernel, source_dir)
    destination = Path(official_ib) / "build_dir" / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(device_kernel, destination)
    print(
        f"Injected patched device kernel artifact into official ImageBuilder: {destination}",
        flush=True,
    )
    return destination


def build_release_patched(profile_name, profile_dir, settings, source_ref, output, jobs):
    """Build patched packages with the official SDK and assemble with official IB."""
    include, exclude = parse_packages(profile_dir / "packages")
    targets = parse_simple_list(profile_dir / "source-build-targets")

    source_dir, ref, feeds, base_commit = prepare_source(
        profile_name, profile_dir, settings, source_ref, [], full=False
    )
    install_feed_packages(source_dir, [], [], full=True, feed_names=feeds)

    sdk, sdk_url, sdk_mode = prepare_sdk(profile_name, settings)
    if not sdk:
        raise BuilderError(
            "release-patched requires an official SDK; use SDK=auto or SDK_URL"
        )

    files = copy_files(profile_dir, source_dir / "files")
    write_config(source_dir, settings, include, exclude, imagebuilder=True)
    run(["make", "defconfig"], cwd=source_dir)

    explicit_packages = resolve_selected_packages_for_targets(source_dir, targets)
    if not explicit_packages:
        raise BuilderError("release-patched source-build-targets selected no packages")

    # Same boundary as AudioWRT: the exact-release SDK is the package compiler.
    # Runtime dependencies stay official; only explicitly patched source roots
    # are registered and compiled from the custom checkout.
    install_sdk_state(source_dir, sdk)
    download_sources(source_dir, jobs, sdk)
    sdk_registered_targets, sdk_build_targets = prepare_sdk_source_targets(
        source_dir, sdk, targets, explicit_packages
    )
    compile_sdk_source_targets(sdk, sdk_build_targets, jobs)

    # Same final assembly model as AudioWRT: start from the official exact-
    # release ImageBuilder and inject only our locally built artifacts.
    official_ib = prepare_official_base_imagebuilder(settings, profile_name)
    copied_custom_packages = copy_local_apks(
        sdk, official_ib, explicit_packages
    )

    device_kernel = prepare_device_kernel_artifact(
        source_dir, settings, jobs, official_ib=official_ib
    )
    injected_device_kernel = inject_device_kernel_into_official_imagebuilder(
        device_kernel, source_dir, official_ib
    )

    prepare_output(output)
    package_args = include + [f"-{package}" for package in exclude]
    command = [
        "make", "image", f"PROFILE={settings['DEVICE']}",
        f"PACKAGES={' '.join(package_args)}", f"BIN_DIR={output}",
    ]
    if files:
        command.append(f"FILES={(source_dir / 'files').resolve()}")
    run(command, cwd=official_ib)

    write_info(output, [
        f"PROFILE={profile_name}",
        "METHOD=source",
        "BUILD_MODE=release-patched",
        f"REF={ref}",
        f"BASE_REF={settings['BASE_REF']}",
        f"SDK_MODE={sdk_mode}",
        f"SDK_URL={sdk_url or 'none'}",
        "PACKAGE_BUILD_ENV=official-sdk",
        "IMAGE_ASSEMBLY_ENV=official-imagebuilder",
        f"SOURCE_BUILD_TARGETS={' '.join(targets)}",
        f"SOURCE_BUILD_PACKAGES={' '.join(explicit_packages)}",
        f"SDK_REGISTERED_SOURCE_ROOTS={' '.join(sdk_registered_targets) if sdk_registered_targets else 'none'}",
        f"SDK_BUILD_TARGETS={' '.join(sdk_build_targets) if sdk_build_targets else 'none'}",
        "KMOD_POLICY=official-base-unless-explicit-source-target",
        f"CUSTOM_APK_PACKAGES={' '.join(copied_custom_packages)}",
        "DEVICE_KERNEL_BASE=official-exact-release-vmlinux",
        f"DEVICE_KERNEL_ARTIFACT={device_kernel.name}",
        f"DEVICE_KERNEL_IN_IMAGEBUILDER={injected_device_kernel}",
        f"INCLUDE_PACKAGES={' '.join(include)}",
        f"EXCLUDE_PACKAGES={' '.join(exclude)}",
        f"FEED_NAMES={' '.join(feeds) if feeds else 'all'}",
        "UNCHANGED_PACKAGES=official-base-release",
    ])


if _ORIGINAL_NAME == "__main__":
    raise SystemExit(main())
