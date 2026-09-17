#!/usr/bin/env python3
"""OpenWrt Builder CLI with release-patched staging fixes layered over the implementation."""

from pathlib import Path
import subprocess

_IMPL_PATH = Path(__file__).with_name("build_impl.py")
_ORIGINAL_NAME = __name__

# Execute the implementation in this module namespace so tests and monkeypatches
# continue to see the same globals/functions as before. Suppress its __main__
# block until the fixes below have been installed.
globals()["__name__"] = "openwrt_builder_impl"
exec(compile(_IMPL_PATH.read_text(encoding="utf-8"), str(_IMPL_PATH), "exec"), globals())
globals()["__name__"] = _ORIGINAL_NAME

# Keep references to implementation functions that are wrapped below.
_seed_official_kernel_abi_impl = seed_official_kernel_abi


def resolve_target_staging_root(source_dir):
    """Resolve STAGING_DIR_ROOT from OpenWrt make metadata and create it if needed."""
    source_dir = Path(source_dir).resolve()
    helper = source_dir / ".owb-staging.mk"
    helper.write_text(
        "owb-staging:\n\t@printf '%s\\n' '$(STAGING_DIR_ROOT)'\n",
        encoding="utf-8",
    )
    try:
        output = subprocess.check_output(
            [
                "make",
                "-s",
                "OPENWRT_BUILD=1",
                "-f",
                "Makefile",
                "-f",
                helper.name,
                "owb-staging",
            ],
            cwd=source_dir,
            text=True,
        ).strip()
    finally:
        helper.unlink(missing_ok=True)

    if not output:
        raise BuilderError("OpenWrt did not resolve STAGING_DIR_ROOT")
    root = Path(output)
    if not root.is_absolute():
        root = source_dir / root
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def clear_official_initramfs_source(linux_dir):
    """Remove absolute build-host initramfs paths inherited from the official ImageBuilder."""
    config = Path(linux_dir) / ".config"
    if not config.is_file():
        raise BuilderError(f"Kernel config is missing: {config}")

    lines = config.read_text(encoding="utf-8").splitlines()
    replaced = False
    rewritten = []
    for line in lines:
        if line.startswith("CONFIG_INITRAMFS_SOURCE="):
            rewritten.append('CONFIG_INITRAMFS_SOURCE=""')
            replaced = True
        else:
            rewritten.append(line)

    if not replaced:
        rewritten.append('CONFIG_INITRAMFS_SOURCE=""')

    config.write_text("\n".join(rewritten) + "\n", encoding="utf-8")
    print("Cleared stale CONFIG_INITRAMFS_SOURCE from official kernel config", flush=True)


def refresh_kernel_atomic_headers(linux_dir):
    """Regenerate checksum-protected atomic headers with the kernel's generator."""
    linux_dir = Path(linux_dir).resolve()
    generator = linux_dir / "scripts" / "atomic" / "gen-atomics.sh"
    if not generator.is_file():
        raise BuilderError(f"Kernel atomic header generator is missing: {generator}")

    print("Regenerating kernel atomic headers and embedded SHA1 checksums", flush=True)
    run(["/bin/sh", str(generator.relative_to(linux_dir))], cwd=linux_dir)

    for name in (
        "atomic-arch-fallback.h",
        "atomic-instrumented.h",
        "atomic-long.h",
    ):
        header = linux_dir / "include" / "linux" / "atomic" / name
        if not header.is_file():
            raise BuilderError(f"Kernel atomic header was not generated: {header}")

        lines = header.read_text(encoding="utf-8").splitlines()
        if not lines or not re.fullmatch(r"// [0-9a-f]{40}", lines[-1]):
            raise BuilderError(f"Kernel atomic header is missing its SHA1 footer: {header}")


def seed_official_kernel_abi(official_ib, source_dir, settings):
    """Seed the release ABI while removing build-host-only state from the official config."""
    vermagic = _seed_official_kernel_abi_impl(official_ib, source_dir, settings)
    linux_dir = resolve_linux_source_directory(source_dir, settings)
    clear_official_initramfs_source(linux_dir)
    refresh_kernel_atomic_headers(linux_dir)
    return vermagic


def seed_official_imagebuilder_keys(official_ib, source_dir, settings):
    source = official_ib / "keys"
    if not source.is_dir():
        raise BuilderError("Official base ImageBuilder does not contain APK signing keys")

    target_root = resolve_target_staging_root(source_dir)
    destination = target_root / "etc" / "apk" / "keys"
    destination.mkdir(parents=True, exist_ok=True)
    copied = 0
    for key in source.iterdir():
        if key.is_file():
            shutil.copy2(key, destination / key.name)
            copied += 1
    if copied == 0:
        raise BuilderError("Official base ImageBuilder APK signing keys are empty")
    return destination


def seed_official_imagebuilder_versions(official_ib, source_dir, settings):
    version_mk = official_ib / "include" / "version.mk"
    if not version_mk.is_file():
        raise BuilderError("Official base ImageBuilder does not contain include/version.mk")

    wanted = {
        "BASE_FILES_VERSION": "base-files.version",
        "LIBC_VERSION": "libc.version",
        "KERNEL_VERSION": "kernel.version",
    }
    values = {}
    for raw in version_mk.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(
            r"(BASE_FILES_VERSION|LIBC_VERSION|KERNEL_VERSION):=(.+)",
            raw.strip(),
        )
        if match:
            values[match.group(1)] = match.group(2).strip()

    missing = [name for name in wanted if not values.get(name)]
    if missing:
        raise BuilderError(
            "Official base ImageBuilder is missing version metadata: "
            + ", ".join(missing)
        )

    staging_dir = resolve_target_staging_root(source_dir).parent
    written = {}
    for variable, filename in wanted.items():
        destination = staging_dir / filename
        destination.write_text(values[variable] + "\n", encoding="utf-8")
        written[variable] = values[variable]
    return written


if _ORIGINAL_NAME == "__main__":
    raise SystemExit(main())
