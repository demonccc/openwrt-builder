#!/usr/bin/env python3
"""Four-mode OpenWrt builder layered on the original ImageBuilder/source implementation."""
from __future__ import annotations

import argparse, os, re, shutil, subprocess, sys
from pathlib import Path
import legacy_builder as legacy

SOURCE_MODES = ("selective-source", "release-patched", "full-source")
SOURCE_EXTRA_KEYS = {"BUILD_MODE", "RELEASE_VERSION", "RELEASE_REPOSITORY", "PATCH_PACKAGES"}


def parse_names(value: str | None, label: str) -> list[str]:
    if not value:
        return []
    names = [x for x in re.split(r"[\s,]+", value) if x]
    for name in names:
        if not re.fullmatch(r"[A-Za-z0-9_.+-]+", name):
            raise legacy.BuilderError(f"Invalid name in {label}: '{name}'")
    return list(dict.fromkeys(names))


def parse_settings(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = legacy.strip_comment(raw)
        if not line:
            continue
        if "=" not in line:
            raise legacy.BuilderError(f"{path}:{number}: expected KEY=value")
        key, value = (part.strip() for part in line.split("=", 1))
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key) or not value:
            raise legacy.BuilderError(f"{path}:{number}: invalid setting '{line}'")
        if key in values:
            raise legacy.BuilderError(f"{path}:{number}: duplicate key '{key}'")
        values[key] = value

    method = values.get("METHOD")
    if method == "imagebuilder":
        allowed = set(legacy.IMAGEBUILDER_KEYS)
        required = legacy.IMAGEBUILDER_KEYS
    elif method == "source":
        allowed = set(legacy.SOURCE_KEYS) | set(legacy.SOURCE_OPTIONAL_KEYS) | SOURCE_EXTRA_KEYS
        required = legacy.SOURCE_KEYS
    else:
        raise legacy.BuilderError(f"{path}: METHOD must be 'source' or 'imagebuilder'")
    unknown = set(values) - allowed
    if unknown:
        raise legacy.BuilderError(f"{path}: unsupported keys: {', '.join(sorted(unknown))}")
    missing = [key for key in required if key not in values]
    if missing:
        raise legacy.BuilderError(f"{path}: missing required keys: {', '.join(missing)}")

    if method == "source":
        mode = values.setdefault("BUILD_MODE", "selective-source")
        if mode not in SOURCE_MODES:
            raise legacy.BuilderError(f"{path}: invalid BUILD_MODE '{mode}'")
        if values.get("SDK_URL") and values.get("TOOLCHAIN_URL"):
            raise legacy.BuilderError(f"{path}: SDK_URL and TOOLCHAIN_URL are mutually exclusive")
        if mode == "release-patched":
            for key in ("RELEASE_VERSION", "RELEASE_REPOSITORY", "PATCH_PACKAGES"):
                if not values.get(key):
                    raise legacy.BuilderError(f"{path}: {key} is required for release-patched")
            parse_names(values["PATCH_PACKAGES"], "PATCH_PACKAGES")
    return values


def validate_profile_dir(profile_dir: Path) -> None:
    missing = [name for name in legacy.PROFILE_FILES if not (profile_dir / name).is_file()]
    if missing:
        raise legacy.BuilderError(f"{profile_dir}: missing required files: {', '.join(missing)}")
    files_dir = profile_dir / "files"
    if files_dir.exists() and not files_dir.is_dir():
        raise legacy.BuilderError(f"{files_dir}: optional files entry must be a directory")
    settings = parse_settings(profile_dir / "settings")
    legacy.parse_packages(profile_dir / "packages")
    if settings["METHOD"] == "source":
        legacy.parse_feed_names(settings.get("FEED_NAMES"))
        legacy.parse_feeds(profile_dir / "feeds")
        legacy.parse_git_packages(profile_dir / "git-packages")


def legacy_source_settings(settings: dict[str, str]) -> dict[str, str]:
    return {k: v for k, v in settings.items() if k not in SOURCE_EXTRA_KEYS}


def write_mode_config(source_dir: Path, settings: dict[str, str], include: list[str], exclude: list[str], external_toolchain) -> None:
    target, subtarget, device = settings["TARGET"], settings["SUBTARGET"], settings["DEVICE"]
    mode = settings["BUILD_MODE"]
    lines = [f"CONFIG_TARGET_{target}=y", f"CONFIG_TARGET_{target}_{subtarget}=y"]
    if mode != "release-patched":
        lines.append(f"CONFIG_TARGET_{target}_{subtarget}_DEVICE_{device}=y")
    if mode == "full-source":
        lines += ["CONFIG_ALL=y", "CONFIG_ALL_KMODS=y", "CONFIG_ALL_NONSHARED=y"]
    elif mode == "release-patched":
        lines += [
            "CONFIG_IB=y",
            f'CONFIG_VERSION_NUMBER="{settings["RELEASE_VERSION"]}"',
            f'CONFIG_VERSION_REPO="{settings["RELEASE_REPOSITORY"]}"',
        ]
        lines += [f"CONFIG_PACKAGE_{p}=y" for p in parse_names(settings["PATCH_PACKAGES"], "PATCH_PACKAGES")]
    else:
        lines += [f"CONFIG_PACKAGE_{p}=y" for p in include]
        lines += [f"CONFIG_PACKAGE_{p}=n" for p in exclude]
    if external_toolchain:
        root, prefix, gcc = external_toolchain
        lines += [
            "CONFIG_DEVEL=y", "CONFIG_EXTERNAL_TOOLCHAIN=y",
            f'CONFIG_TARGET_NAME="{prefix.removesuffix("-")}"', f'CONFIG_TOOLCHAIN_PREFIX="{prefix}"',
            f'CONFIG_TOOLCHAIN_ROOT="{root}"', "CONFIG_EXTERNAL_TOOLCHAIN_LIBC_USE_MUSL=y",
            f'CONFIG_EXTERNAL_GCC_VERSION="{gcc}"',
        ]
    (source_dir / ".config").write_text("\n".join(lines) + "\n", encoding="utf-8")


def resolve_patch_targets(source_dir: Path, packages: list[str]) -> list[str]:
    metadata = source_dir / "tmp" / ".packageinfo"
    if not metadata.is_file():
        raise legacy.BuilderError(f"OpenWrt package metadata not generated: {metadata}")
    current = None
    mapping: dict[str, str] = {}
    for line in metadata.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("Source-Makefile: "):
            current = line.split(":", 1)[1].strip().removesuffix("/Makefile")
        elif current and line.startswith("Package: "):
            mapping[line.split(":", 1)[1].strip()] = current
    missing = [p for p in packages if p not in mapping]
    if missing:
        raise legacy.BuilderError("Could not resolve PATCH_PACKAGES: " + ", ".join(missing))
    return list(dict.fromkeys(f"{mapping[p]}/compile" for p in packages))


def generated_imagebuilder(source_dir: Path, settings: dict[str, str]) -> Path:
    target_dir = source_dir / "bin" / "targets" / settings["TARGET"] / settings["SUBTARGET"]
    matches = sorted(target_dir.glob("*imagebuilder*.tar.zst"))
    if len(matches) != 1:
        raise legacy.BuilderError(f"Expected one generated ImageBuilder, found {len(matches)} in {target_dir}")
    return matches[0]


def assemble_patched(profile_name: str, profile_dir: Path, settings: dict[str, str], source_dir: Path, output: Path) -> None:
    include, exclude = legacy.parse_packages(profile_dir / "packages")
    package_args = include + [f"-{p}" for p in exclude]
    work = legacy.WORK_DIR / profile_name / "generated-imagebuilder"
    if work.exists():
        shutil.rmtree(work)
    extract = work / "extract"
    extract.mkdir(parents=True)
    legacy.run(["tar", "--zstd", "-xf", str(generated_imagebuilder(source_dir, settings)), "-C", str(extract)])
    roots = [p for p in extract.iterdir() if p.is_dir()]
    if len(roots) != 1:
        raise legacy.BuilderError("Could not determine generated ImageBuilder directory")
    ib = roots[0]
    local = ib / "packages"
    local.mkdir(exist_ok=True)
    target_packages = source_dir / "bin" / "targets" / settings["TARGET"] / settings["SUBTARGET"] / "packages"
    if target_packages.is_dir():
        for package in target_packages.glob("*.apk"):
            shutil.copy2(package, local / package.name)
    output = legacy.prepare_output(output)
    command = ["make", "image", f"PROFILE={settings['DEVICE']}", f"PACKAGES={' '.join(package_args)}", f"BIN_DIR={output}"]
    files_dir = profile_dir / "files"
    if files_dir.is_dir():
        command.append(f"FILES={files_dir.resolve()}")
    legacy.run(command, cwd=ib)


def build_full_or_patched(profile_name: str, profile_dir: Path, settings: dict[str, str], source_ref: str | None, output: Path, jobs: int) -> None:
    include, exclude = legacy.parse_packages(profile_dir / "packages")
    feeds = legacy.parse_feeds(profile_dir / "feeds")
    git_packages = legacy.parse_git_packages(profile_dir / "git-packages")
    feed_names = legacy.parse_feed_names(settings.get("FEED_NAMES"))
    mode = settings["BUILD_MODE"]
    ref = source_ref or settings["REF"]
    source_dir = legacy.WORK_DIR / profile_name / "openwrt"
    print(f"Method:  source\nMode:    {mode}\nSource:  {settings['REPOSITORY']} @ {ref}\nTarget:  {settings['TARGET']}/{settings['SUBTARGET']}/{settings['DEVICE']}")
    legacy.clone_ref(settings["REPOSITORY"], ref, source_dir)
    legacy.add_feeds(source_dir, feeds)
    if git_packages and feed_names:
        print("NOTE: FEED_NAMES ignored because git-packages requires all feeds.")
        feed_names = []
    legacy.update_feeds(source_dir, feed_names)
    if mode == "full-source" or git_packages:
        legacy.run(["./scripts/feeds", "install", "-a"], cwd=source_dir)
    legacy.install_git_packages(source_dir, git_packages)

    sdk = legacy.download_sdk(settings["SDK_URL"], legacy.WORK_DIR / profile_name / "sdk") if settings.get("SDK_URL") else None
    external = legacy.download_external_toolchain(settings["TOOLCHAIN_URL"], legacy.WORK_DIR / profile_name / "toolchain") if settings.get("TOOLCHAIN_URL") else None
    files_included = legacy.copy_profile_files(profile_dir, source_dir / "files")
    write_mode_config(source_dir, settings, include, exclude, external)
    legacy.run(["make", "defconfig"], cwd=source_dir)
    if sdk:
        legacy.install_sdk_build_state(source_dir, sdk)
    if sdk:
        legacy.run(["make", "package/download", "target/download", f"-j{jobs}"], cwd=source_dir)
    elif external:
        legacy.run(["make", "tools/download", "package/download", "target/download", f"-j{jobs}"], cwd=source_dir)
    else:
        legacy.run(["make", "download", f"-j{jobs}"], cwd=source_dir)

    if mode == "full-source":
        legacy.run(["make", f"-j{jobs}"], cwd=source_dir)
        target_dir = source_dir / "bin" / "targets" / settings["TARGET"] / settings["SUBTARGET"]
        output = legacy.prepare_output(output)
        for item in target_dir.iterdir():
            if item.name == "packages":
                continue
            dest = output / item.name
            shutil.copytree(item, dest) if item.is_dir() else shutil.copy2(item, dest)
    else:
        patch_packages = parse_names(settings["PATCH_PACKAGES"], "PATCH_PACKAGES")
        patch_targets = resolve_patch_targets(source_dir, patch_packages)
        print("Patched packages:", " ".join(patch_packages))
        print("Patched source targets:", " ".join(patch_targets))
        legacy.run(["make", "target/linux/install", f"-j{jobs}"], cwd=source_dir)
        minimal = list(dict.fromkeys(["package/base-files/compile", "package/libs/toolchain/compile", "package/kernel/linux/compile", *patch_targets]))
        legacy.run(["make", *minimal, f"-j{jobs}"], cwd=source_dir)
        legacy.run(["make", "package/index"], cwd=source_dir)
        legacy.run(["make", "target/imagebuilder/compile", f"-j{jobs}"], cwd=source_dir)
        assemble_patched(profile_name, profile_dir, settings, source_dir, output)

    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source_dir, text=True).strip()
    info = [f"PROFILE={profile_name}", "METHOD=source", f"BUILD_MODE={mode}", f"SOURCE_COMMIT={commit}",
            f"TARGET={settings['TARGET']}", f"SUBTARGET={settings['SUBTARGET']}", f"DEVICE={settings['DEVICE']}",
            f"FEED_NAMES={' '.join(feed_names) if feed_names else 'all'}", f"FILES={'included' if files_included else 'none'}"]
    if mode == "release-patched":
        info += [f"RELEASE_VERSION={settings['RELEASE_VERSION']}", f"RELEASE_REPOSITORY={settings['RELEASE_REPOSITORY']}",
                 f"PATCH_PACKAGES={settings['PATCH_PACKAGES']}", "USER_PACKAGES=official-release-binaries"]
    (Path(output).resolve() / "BUILD_INFO").write_text("\n".join(info) + "\n", encoding="utf-8")


def build(profile_name: str, source_ref: str | None, output: Path, jobs: int) -> None:
    profile_dir = legacy.resolve_profile(profile_name)
    validate_profile_dir(profile_dir)
    settings = parse_settings(profile_dir / "settings")
    print(f"Profile: {profile_name}")
    if settings["METHOD"] == "imagebuilder":
        if source_ref:
            print("NOTE: --source-ref is ignored in imagebuilder mode.")
        legacy.build_with_imagebuilder(profile_name, profile_dir, settings, output)
    elif settings["BUILD_MODE"] == "selective-source":
        legacy.build_from_source(profile_name, profile_dir, legacy_source_settings(settings), source_ref, output, jobs)
        info = Path(output).resolve() / "BUILD_INFO"
        if info.exists():
            text = info.read_text(encoding="utf-8").replace("METHOD=source\n", "METHOD=source\nBUILD_MODE=selective-source\n", 1)
            info.write_text(text, encoding="utf-8")
    else:
        build_full_or_patched(profile_name, profile_dir, settings, source_ref, output, jobs)


def validate_all() -> None:
    profiles = sorted(p for p in legacy.PROFILES_DIR.iterdir() if p.is_dir())
    for profile in profiles:
        validate_profile_dir(profile)
        print(f"OK: {profile.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build OpenWrt firmware using four explicit build modes.")
    subs = parser.add_subparsers(dest="command", required=True)
    vp = subs.add_parser("validate"); vp.add_argument("--profile")
    bp = subs.add_parser("build"); bp.add_argument("--profile", required=True); bp.add_argument("--source-ref"); bp.add_argument("--output", default="artifact"); bp.add_argument("--jobs", type=int, default=max(os.cpu_count() or 1, 1))
    args = parser.parse_args()
    try:
        if args.command == "validate":
            if args.profile:
                validate_profile_dir(legacy.resolve_profile(args.profile)); print(f"OK: {args.profile}")
            else:
                validate_all()
        else:
            if args.jobs < 1: raise legacy.BuilderError("--jobs must be at least 1")
            build(args.profile, args.source_ref, Path(args.output), args.jobs)
    except (legacy.BuilderError, subprocess.CalledProcessError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr); return 1
    return 0
