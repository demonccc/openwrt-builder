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
