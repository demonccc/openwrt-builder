#!/usr/bin/env python3
"""Reusable OpenWrt profile builder used locally and by GitHub Actions.

`build_core.py` contains shared builder helpers and the generic source/imagebuilder
flows. `release-patched` intentionally lives here because it has a stricter
source boundary: only the profile's explicit `source-build-targets` are compiled
from the patched tree. Selecting a firmware package or kmod never promotes its
source tree into the local build set.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path as _Path

_CORE_PATH = _Path(__file__).with_name("build_core.py")
_SPEC = importlib.util.spec_from_file_location("openwrt_builder_core", _CORE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Could not load builder core: {_CORE_PATH}")
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)

for _name in dir(_CORE):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_CORE, _name)


def _sync_core(*names):
    for name in names:
        if name in globals():
            setattr(_CORE, name, globals()[name])


def compile_without_dependencies(source_dir, targets, jobs):
    _sync_core("run")
    return _CORE.compile_without_dependencies(source_dir, targets, jobs)


def compile_kernel_modules(source_dir, settings, jobs):
    _sync_core("run", "resolve_linux_source_directory", "target_linux_directory")
    return _CORE.compile_kernel_modules(source_dir, settings, jobs)


def prepare_device_kernel_artifact(source_dir, settings, jobs):
    _sync_core(
        "run",
        "target_image_directory",
        "parse_device_kernel_target",
        "resolve_kernel_image_stamp",
    )
    return _CORE.prepare_device_kernel_artifact(source_dir, settings, jobs)


def build_release_patched(profile_name, profile_dir, settings, source_ref, output, jobs):
    """Build only the explicitly patched source boundary.

    Firmware package selection is intentionally separate from source compilation:
    packages selected in .config (including unrelated kmod-* packages) remain
    official BASE_REF binaries unless their source root is listed in
    source-build-targets. The custom kernel package itself is always local.
    """
    include, exclude = parse_packages(profile_dir / "packages")
    targets = parse_simple_list(profile_dir / "source-build-targets")
    source_dir, ref, feeds, base_commit = prepare_source(
        profile_name, profile_dir, settings, source_ref, [], full=False
    )

    install_feed_packages(source_dir, [], [], full=True, feed_names=feeds)
    sdk, sdk_url, sdk_mode = prepare_sdk(profile_name, settings)
    tools_image, tools_reason = (None, "sdk-provides-host-tools")
    if not sdk:
        tools_image, tools_reason = prepare_prebuilt_tools(
            profile_name, settings, source_dir, ref, base_commit
        )

    files = copy_files(profile_dir, source_dir / "files")
    write_config(source_dir, settings, include, exclude, imagebuilder=True)
    run(["make", "defconfig"], cwd=source_dir)

    # This is the complete local package-source boundary for release-patched.
    # Do not derive additional build roots from CONFIG_PACKAGE_kmod-* selections.
    explicit_packages = resolve_selected_packages_for_targets(source_dir, targets)

    if sdk:
        install_sdk_state(source_dir, sdk)
    else:
        run(["make", "tools/install", "toolchain/install", f"-j{jobs}"], cwd=source_dir)
    download_sources(source_dir, jobs, sdk)

    # The target kernel/module state is required for the patched package roots,
    # but unrelated selected kmods are never compiled as package source roots.
    compile_kernel_modules(source_dir, settings, jobs)
    compile_without_dependencies(source_dir, targets, jobs)

    # base-files and libc are unchanged userspace. Seed the exact official
    # BASE_REF APKs instead of rebuilding them from the patched tree.
    official_ib = prepare_official_base_imagebuilder(settings, profile_name)
    official_base_files = seed_official_imagebuilder_package(
        official_ib, source_dir, settings, "base-files"
    )
    official_libc = seed_official_imagebuilder_package(
        official_ib, source_dir, settings, "libc"
    )

    device_kernel = prepare_device_kernel_artifact(source_dir, settings, jobs)
    compile_without_dependencies(source_dir, ["target/imagebuilder/compile"], jobs)

    imagebuilder_dir = generated_imagebuilder(source_dir, settings)
    pin_release_repositories(settings, imagebuilder_dir, profile_name, official_ib=official_ib)

    custom_packages = list(dict.fromkeys(["kernel", *explicit_packages]))
    copied_custom_packages = copy_local_apks(source_dir, imagebuilder_dir, custom_packages)
    copied_official_packages = copy_local_apks(
        source_dir, imagebuilder_dir, ["base-files", "libc"]
    )

    prepare_output(output)
    package_args = include + [f"-{package}" for package in exclude]
    command = [
        "make",
        "image",
        f"PROFILE={settings['DEVICE']}",
        f"PACKAGES={' '.join(package_args)}",
        f"BIN_DIR={output}",
    ]
    if files:
        command.append(f"FILES={(source_dir / 'files').resolve()}")
    run(command, cwd=imagebuilder_dir)

    host_tools_mode = "sdk" if sdk else ("official-prebuilt" if tools_image else "source")
    write_info(output, [
        f"PROFILE={profile_name}",
        "METHOD=source",
        "BUILD_MODE=release-patched",
        f"REF={ref}",
        f"BASE_REF={settings['BASE_REF']}",
        f"SDK_MODE={sdk_mode}",
        f"SDK_URL={sdk_url or 'none'}",
        f"HOST_TOOLS_MODE={host_tools_mode}",
        f"HOST_TOOLS_IMAGE={tools_image or 'none'}",
        f"HOST_TOOLS_REASON={tools_reason}",
        f"SOURCE_BUILD_TARGETS={' '.join(targets)}",
        f"SOURCE_BUILD_PACKAGES={' '.join(explicit_packages)}",
        "KMOD_POLICY=official-base-unless-explicit-source-target",
        f"CUSTOM_APK_PACKAGES={' '.join(copied_custom_packages)}",
        f"OFFICIAL_SEEDED_PACKAGES={' '.join(copied_official_packages)}",
        f"DEVICE_KERNEL_ARTIFACT={device_kernel.name}",
        f"OFFICIAL_BASE_FILES_APK={official_base_files.name}",
        f"OFFICIAL_LIBC_APK={official_libc.name}",
        f"INCLUDE_PACKAGES={' '.join(include)}",
        f"EXCLUDE_PACKAGES={' '.join(exclude)}",
        f"FEED_NAMES={' '.join(feeds) if feeds else 'all'}",
        "UNCHANGED_PACKAGES=official-base-release",
    ])


def _bind_release_patched_dispatch():
    """Bind the core dispatcher to the canonical release-patched implementation."""
    _CORE.build_release_patched = build_release_patched


def build(profile_name, source_ref, output, jobs):
    _sync_core(
        "workspace_path",
        "resolve_profile",
        "validate_profile_dir",
        "parse_settings",
        "build_imagebuilder",
        "build_source",
    )
    _bind_release_patched_dispatch()
    return _CORE.build(profile_name, source_ref, output, jobs)


# Keep imports and direct calls deterministic too, not only CLI execution.
_bind_release_patched_dispatch()


if __name__ == "__main__":
    _bind_release_patched_dispatch()
    raise SystemExit(_CORE.main())
