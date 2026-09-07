#!/usr/bin/env python3
"""Reusable OpenWrt profile builder used locally and by GitHub Actions."""

from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
PROFILES_DIR = ROOT / "profiles"
WORK_DIR = ROOT / ".work"
PROFILE_FILES = ("settings", "packages", "feeds", "git-packages")
SOURCE_KEYS = ("METHOD", "BUILD_MODE", "REPOSITORY", "REF", "TARGET", "SUBTARGET", "DEVICE")
SOURCE_OPTIONAL_KEYS = ("SDK_URL", "TOOLCHAIN_URL", "FEED_NAMES")
IMAGEBUILDER_KEYS = ("METHOD", "IMAGEBUILDER_URL", "DEVICE")
BUILD_MODES = ("release-patched", "selective-source", "full-source")


class BuilderError(RuntimeError):
    pass


def run(command: list[str], *, cwd: Path | None = None, check: bool = True):
    print("+", shlex.join(command), flush=True)
    return subprocess.run(command, cwd=cwd, check=check)


def strip_comment(line: str) -> str:
    return line.split("#", 1)[0].strip()


def has_entries(path: Path) -> bool:
    return path.is_file() and any(strip_comment(x) for x in path.read_text().splitlines())


def resolve_profile(name: str) -> Path:
    path = PROFILES_DIR / name
    if not path.is_dir():
        raise BuilderError(f"Profile '{name}' does not exist: {path}")
    return path


def parse_settings(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, raw in enumerate(path.read_text().splitlines(), 1):
        line = strip_comment(raw)
        if not line:
            continue
        if "=" not in line:
            raise BuilderError(f"{path}:{number}: expected KEY=value")
        key, value = (x.strip() for x in line.split("=", 1))
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key) or not value:
            raise BuilderError(f"{path}:{number}: invalid setting")
        if key in values:
            raise BuilderError(f"{path}:{number}: duplicate key '{key}'")
        values[key] = value

    method = values.get("METHOD")
    if method not in ("source", "imagebuilder"):
        raise BuilderError(f"{path}: METHOD must be source or imagebuilder")
    required = SOURCE_KEYS if method == "source" else IMAGEBUILDER_KEYS
    allowed = set(required) | (set(SOURCE_OPTIONAL_KEYS) if method == "source" else set())
    unknown = set(values) - allowed
    missing = [x for x in required if x not in values]
    if unknown:
        raise BuilderError(f"{path}: unsupported keys: {', '.join(sorted(unknown))}")
    if missing:
        raise BuilderError(f"{path}: missing required keys: {', '.join(missing)}")
    if method == "source":
        if values["BUILD_MODE"] not in BUILD_MODES:
            raise BuilderError(f"{path}: BUILD_MODE must be one of {', '.join(BUILD_MODES)}")
        if values.get("SDK_URL") and values.get("TOOLCHAIN_URL"):
            raise BuilderError(f"{path}: SDK_URL and TOOLCHAIN_URL are mutually exclusive")
        if values["BUILD_MODE"] == "release-patched" and not values.get("SDK_URL"):
            raise BuilderError(f"{path}: release-patched requires the matching release SDK_URL")
    return values


def parse_feed_names(value: str | None) -> list[str]:
    names = [x for x in re.split(r"[\s,]+", value or "") if x]
    for name in names:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
            raise BuilderError(f"Invalid feed name: {name}")
    return list(dict.fromkeys(names))


def parse_packages(path: Path) -> tuple[list[str], list[str]]:
    include, exclude = [], []
    seen = set()
    for number, raw in enumerate(path.read_text().splitlines(), 1):
        line = strip_comment(raw)
        if not line:
            continue
        is_exclude = line.startswith("-")
        package = line[1:].strip() if is_exclude else line
        if not package or any(x.isspace() for x in package) or package in seen:
            raise BuilderError(f"{path}:{number}: invalid or duplicate package '{line}'")
        seen.add(package)
        (exclude if is_exclude else include).append(package)
    return include, exclude


def parse_simple_list(path: Path) -> list[str]:
    if not path.is_file():
        return []
    result = []
    for number, raw in enumerate(path.read_text().splitlines(), 1):
        line = strip_comment(raw)
        if not line:
            continue
        if any(x.isspace() for x in line):
            raise BuilderError(f"{path}:{number}: expected one OpenWrt make target per line")
        result.append(line)
    return list(dict.fromkeys(result))


def parse_feeds(path: Path) -> list[str]:
    result = []
    for number, raw in enumerate(path.read_text().splitlines(), 1):
        line = strip_comment(raw)
        if not line:
            continue
        if not line.startswith(("src-git ", "src-git-full ", "src-link ", "src-cpy ")):
            raise BuilderError(f"{path}:{number}: unsupported feed line")
        result.append(line)
    return result


def parse_git_packages(path: Path) -> list[tuple[str, str | None, str]]:
    result = []
    for number, raw in enumerate(path.read_text().splitlines(), 1):
        line = strip_comment(raw)
        if not line:
            continue
        parts = shlex.split(line)
        if not 1 <= len(parts) <= 3:
            raise BuilderError(f"{path}:{number}: expected REPOSITORY [REF] [PATH]")
        repo = parts[0]
        ref = None if len(parts) < 2 or parts[1] == "-" else parts[1]
        subpath = "." if len(parts) < 3 else parts[2]
        result.append((repo, ref, subpath))
    return result


def validate_profile_dir(profile_dir: Path) -> None:
    missing = [x for x in PROFILE_FILES if not (profile_dir / x).is_file()]
    if missing:
        raise BuilderError(f"{profile_dir}: missing files: {', '.join(missing)}")
    settings = parse_settings(profile_dir / "settings")
    parse_packages(profile_dir / "packages")
    if settings["METHOD"] == "source":
        parse_feed_names(settings.get("FEED_NAMES"))
        parse_feeds(profile_dir / "feeds")
        parse_git_packages(profile_dir / "git-packages")
        if settings["BUILD_MODE"] == "release-patched" and not parse_simple_list(profile_dir / "source-build-targets"):
            raise BuilderError(f"{profile_dir}: release-patched requires source-build-targets")


def validate_all() -> None:
    for profile in sorted(x for x in PROFILES_DIR.iterdir() if x.is_dir()):
        validate_profile_dir(profile)
        print(f"OK: {profile.name}")


def clone_ref(repository: str, ref: str | None, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not ref:
        run(["git", "clone", "--depth", "1", repository, str(destination)])
        return
    run(["git", "clone", "--filter=blob:none", "--no-checkout", repository, str(destination)])
    run(["git", "fetch", "--depth", "1", "origin", ref], cwd=destination)
    run(["git", "checkout", "--detach", "FETCH_HEAD"], cwd=destination)


def add_feeds(source_dir: Path, feeds: list[str]) -> None:
    if feeds:
        with (source_dir / "feeds.conf.default").open("a") as handle:
            handle.write("\n# Added by openwrt-builder\n" + "\n".join(feeds) + "\n")


def update_feeds(source_dir: Path, names: list[str]) -> None:
    run(["./scripts/feeds", "update", *(names or ["-a"])], cwd=source_dir)


def install_feed_packages(source_dir: Path, include: list[str], git_packages, *, full: bool, feed_names: list[str]) -> None:
    if full:
        if feed_names:
            for feed in feed_names:
                run(["./scripts/feeds", "install", "-a", "-p", feed], cwd=source_dir)
        else:
            run(["./scripts/feeds", "install", "-a"], cwd=source_dir)
    elif git_packages:
        run(["./scripts/feeds", "install", "-a"], cwd=source_dir)
    elif include:
        run(["./scripts/feeds", "install", *include], cwd=source_dir)


def install_git_packages(source_dir: Path, entries) -> None:
    if not entries:
        return
    root = source_dir / "package" / "openwrt-builder"
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        for index, (repo, ref, subpath) in enumerate(entries):
            checkout = Path(td) / str(index)
            clone_ref(repo, ref, checkout)
            src = (checkout / subpath).resolve()
            if not src.is_dir():
                raise BuilderError(f"Git package directory does not exist: {repo} {subpath}")
            name = src.name if subpath != "." else Path(urlparse(repo).path.rstrip("/")).stem
            shutil.copytree(src, root / name, ignore=shutil.ignore_patterns(".git"))


def download_archive(url: str, destination: Path, filename: str, label: str) -> Path:
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    archive = destination / filename
    print(f"Downloading {label}: {url}")
    with urllib.request.urlopen(url) as response, archive.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    extracted = destination / "extract"
    extracted.mkdir()
    run(["tar", "--zstd", "-xf", str(archive), "-C", str(extracted)])
    return extracted


def download_sdk(url: str, destination: Path) -> Path:
    extracted = download_archive(url, destination, "sdk.tar.zst", "OpenWrt SDK")
    roots = [x for x in extracted.iterdir() if x.is_dir()]
    if len(roots) != 1:
        raise BuilderError("Could not determine extracted SDK directory")
    return roots[0]


def download_external_toolchain(url: str, destination: Path):
    extracted = download_archive(url, destination, "toolchain.tar.zst", "external toolchain")
    compilers = [x for x in extracted.rglob("*-musl-gcc") if x.is_file()]
    if len(compilers) != 1:
        raise BuilderError("Could not determine external musl compiler")
    compiler = compilers[0]
    return compiler.parent.parent.resolve(), compiler.name.removesuffix("gcc"), subprocess.check_output([str(compiler), "-dumpfullversion"], text=True).strip()


def build_state(source_dir: Path):
    helper = source_dir / ".owb.mk"
    helper.write_text("owb:\n\t@printf 'HOST=%s\\n' '$(STAGING_DIR_HOST)'\n\t@printf 'TOOLCHAIN=%s\\n' '$(TOOLCHAIN_DIR)'\n\t@printf 'TOOLS_STAMP=%s\\n' '$(tools/stamp-compile)'\n\t@printf 'TOOLCHAIN_STAMP=%s\\n' '$(toolchain/stamp-compile)'\n")
    try:
        output = subprocess.check_output(["make", "-s", "OPENWRT_BUILD=1", "-f", "Makefile", "-f", helper.name, "owb"], cwd=source_dir, text=True)
    finally:
        helper.unlink(missing_ok=True)
    values = dict(x.split("=", 1) for x in output.splitlines() if "=" in x)
    return tuple(Path(values[x]).resolve() for x in ("HOST", "TOOLCHAIN", "TOOLS_STAMP", "TOOLCHAIN_STAMP"))


def replace_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst, symlinks=True)


def install_sdk_state(source_dir: Path, sdk_root: Path) -> None:
    host, toolchain, tools_stamp, toolchain_stamp = build_state(source_dir)
    sdk_toolchains = list((sdk_root / "staging_dir").glob("toolchain-*"))
    if len(sdk_toolchains) != 1 or sdk_toolchains[0].name != toolchain.name:
        raise BuilderError("SDK toolchain does not match the source build")
    replace_tree(sdk_root / "staging_dir" / "host", host)
    replace_tree(sdk_toolchains[0], toolchain)
    (toolchain / "stamp").mkdir(parents=True, exist_ok=True)
    (toolchain / "stamp" / ".gcc_final_installed").touch()
    tools_stamp.parent.mkdir(parents=True, exist_ok=True); tools_stamp.touch()
    toolchain_stamp.parent.mkdir(parents=True, exist_ok=True); toolchain_stamp.touch()


def write_config(source_dir: Path, settings: dict[str, str], include: list[str], exclude: list[str], external, *, full=False, ib=False) -> None:
    target, subtarget, device = settings["TARGET"], settings["SUBTARGET"], settings["DEVICE"]
    lines = [f"CONFIG_TARGET_{target}=y", f"CONFIG_TARGET_{target}_{subtarget}=y", f"CONFIG_TARGET_{target}_{subtarget}_DEVICE_{device}=y"]
    if full:
        lines += ["CONFIG_ALL=y", "CONFIG_ALL_KMODS=y", "CONFIG_ALL_NONSHARED=y"]
    if ib:
        lines += ["CONFIG_IB=y"]
    if external:
        root, prefix, gcc = external
        lines += ["CONFIG_DEVEL=y", "CONFIG_EXTERNAL_TOOLCHAIN=y", f'CONFIG_TARGET_NAME="{prefix.removesuffix("-")}"', f'CONFIG_TOOLCHAIN_PREFIX="{prefix}"', f'CONFIG_TOOLCHAIN_ROOT="{root}"', "CONFIG_EXTERNAL_TOOLCHAIN_LIBC_USE_MUSL=y", f'CONFIG_EXTERNAL_GCC_VERSION="{gcc}"']
    lines += [f"CONFIG_PACKAGE_{x}=y" for x in include]
    lines += [f"CONFIG_PACKAGE_{x}=n" for x in exclude]
    (source_dir / ".config").write_text("\n".join(lines) + "\n")


def prepare_source(profile_name: str, profile_dir: Path, settings: dict[str, str], source_ref: str | None, include: list[str], *, full=False):
    ref = source_ref or settings["REF"]
    source_dir = WORK_DIR / profile_name / "openwrt"
    clone_ref(settings["REPOSITORY"], ref, source_dir)
    add_feeds(source_dir, parse_feeds(profile_dir / "feeds"))
    feed_names = parse_feed_names(settings.get("FEED_NAMES"))
    git_packages = parse_git_packages(profile_dir / "git-packages")
    if git_packages and feed_names and not full:
        print("NOTE: FEED_NAMES ignored because git-packages needs full feed indexing")
        feed_names = []
    update_feeds(source_dir, feed_names)
    install_feed_packages(source_dir, include, git_packages, full=full, feed_names=feed_names)
    install_git_packages(source_dir, git_packages)
    return source_dir, ref, feed_names


def prepare_acceleration(profile_name: str, settings: dict[str, str]):
    sdk = download_sdk(settings["SDK_URL"], WORK_DIR / profile_name / "sdk") if settings.get("SDK_URL") else None
    external = download_external_toolchain(settings["TOOLCHAIN_URL"], WORK_DIR / profile_name / "toolchain") if settings.get("TOOLCHAIN_URL") else None
    return sdk, external


def copy_files(profile_dir: Path, destination: Path) -> bool:
    src = profile_dir / "files"
    if not src.is_dir():
        return False
    shutil.copytree(src, destination, dirs_exist_ok=True)
    return True


def download_sources(source_dir: Path, jobs: int, sdk, external) -> None:
    if sdk:
        run(["make", "package/download", "target/download", f"-j{jobs}"], cwd=source_dir)
    elif external:
        run(["make", "tools/download", "package/download", "target/download", f"-j{jobs}"], cwd=source_dir)
    else:
        run(["make", "download", f"-j{jobs}"], cwd=source_dir)


def prepare_output(output: Path) -> Path:
    output = output.resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    return output


def copy_firmware(source_dir: Path, settings: dict[str, str], output: Path) -> None:
    src = source_dir / "bin" / "targets" / settings["TARGET"] / settings["SUBTARGET"]
    if not src.is_dir():
        raise BuilderError(f"Expected firmware directory missing: {src}")
    prepare_output(output)
    for item in src.iterdir():
        if item.name == "packages":
            continue
        shutil.copytree(item, output / item.name) if item.is_dir() else shutil.copy2(item, output / item.name)


def info(output: Path, lines: list[str]) -> None:
    (output / "BUILD_INFO").write_text("\n".join(lines) + "\n")


def build_source(profile_name: str, profile_dir: Path, settings: dict[str, str], source_ref: str | None, output: Path, jobs: int) -> None:
    include, exclude = parse_packages(profile_dir / "packages")
    full = settings["BUILD_MODE"] == "full-source"
    source_dir, ref, feeds = prepare_source(profile_name, profile_dir, settings, source_ref, include, full=full)
    sdk, external = prepare_acceleration(profile_name, settings)
    files = copy_files(profile_dir, source_dir / "files")
    write_config(source_dir, settings, include, exclude, external, full=full)
    run(["make", "defconfig"], cwd=source_dir)
    if sdk: install_sdk_state(source_dir, sdk)
    download_sources(source_dir, jobs, sdk, external)
    run(["make", f"-j{jobs}"], cwd=source_dir)
    copy_firmware(source_dir, settings, output)
    info(output, [f"PROFILE={profile_name}", "METHOD=source", f"BUILD_MODE={settings['BUILD_MODE']}", f"REF={ref}", f"FEED_NAMES={' '.join(feeds) if feeds else 'all'}", f"INCLUDE_PACKAGES={' '.join(include)}", f"EXCLUDE_PACKAGES={' '.join(exclude)}", f"FILES={'included' if files else 'none'}"])


def generated_imagebuilder(source_dir: Path, settings: dict[str, str]) -> Path:
    target_dir = source_dir / "bin" / "targets" / settings["TARGET"] / settings["SUBTARGET"]
    archives = list(target_dir.glob("*imagebuilder*.tar.zst"))
    if len(archives) != 1:
        raise BuilderError(f"Expected one generated ImageBuilder, found {len(archives)}")
    dest = WORK_DIR / "generated-imagebuilder"
    if dest.exists(): shutil.rmtree(dest)
    dest.mkdir(parents=True)
    run(["tar", "--zstd", "-xf", str(archives[0]), "-C", str(dest)])
    roots = [x for x in dest.iterdir() if x.is_dir()]
    if len(roots) != 1: raise BuilderError("Could not identify generated ImageBuilder")
    return roots[0]


def copy_local_apks(source_dir: Path, ib: Path) -> int:
    dst = ib / "packages"; dst.mkdir(exist_ok=True)
    count = 0
    for root in (source_dir / "bin" / "packages", source_dir / "bin" / "targets"):
        if not root.exists(): continue
        for apk in root.rglob("*.apk"):
            shutil.copy2(apk, dst / apk.name); count += 1
    return count


def build_release_patched(profile_name: str, profile_dir: Path, settings: dict[str, str], source_ref: str | None, output: Path, jobs: int) -> None:
    include, exclude = parse_packages(profile_dir / "packages")
    targets = parse_simple_list(profile_dir / "source-build-targets")
    source_dir, ref, feeds = prepare_source(profile_name, profile_dir, settings, source_ref, [], full=False)
    sdk, external = prepare_acceleration(profile_name, settings)
    files = copy_files(profile_dir, source_dir / "files")
    write_config(source_dir, settings, [], [], external, ib=True)
    run(["make", "defconfig"], cwd=source_dir)
    if sdk: install_sdk_state(source_dir, sdk)
    download_sources(source_dir, jobs, sdk, external)
    run(["make", "target/linux/compile", f"-j{jobs}"], cwd=source_dir)
    for target in targets:
        run(["make", target, f"-j{jobs}"], cwd=source_dir)
    run(["make", "package/base-files/compile", f"-j{jobs}"], cwd=source_dir)
    run(["make", "target/imagebuilder/compile", f"-j{jobs}"], cwd=source_dir)
    ib = generated_imagebuilder(source_dir, settings)
    local_apks = copy_local_apks(source_dir, ib)
    prepare_output(output)
    args = include + [f"-{x}" for x in exclude]
    command = ["make", "image", f"PROFILE={settings['DEVICE']}", f"PACKAGES={' '.join(args)}", f"BIN_DIR={output}"]
    if files: command.append(f"FILES={(source_dir / 'files').resolve()}")
    run(command, cwd=ib)
    info(output, [f"PROFILE={profile_name}", "METHOD=source", "BUILD_MODE=release-patched", f"REF={ref}", f"SOURCE_BUILD_TARGETS={' '.join(targets)}", f"LOCAL_APKS={local_apks}", f"INCLUDE_PACKAGES={' '.join(include)}", f"FEED_NAMES={' '.join(feeds) if feeds else 'all'}", "UNCHANGED_PACKAGES=official-release-repositories"])


def download_imagebuilder(url: str, destination: Path) -> Path:
    extracted = download_archive(url, destination, "imagebuilder.tar.zst", "ImageBuilder")
    roots = [x for x in extracted.iterdir() if x.is_dir()]
    if len(roots) != 1: raise BuilderError("Could not determine ImageBuilder directory")
    return roots[0]


def build_imagebuilder(profile_name: str, profile_dir: Path, settings: dict[str, str], output: Path) -> None:
    include, exclude = parse_packages(profile_dir / "packages")
    ib = download_imagebuilder(settings["IMAGEBUILDER_URL"], WORK_DIR / profile_name / "imagebuilder")
    prepare_output(output)
    command = ["make", "image", f"PROFILE={settings['DEVICE']}", f"PACKAGES={' '.join(include + [f'-{x}' for x in exclude])}", f"BIN_DIR={output}"]
    if (profile_dir / "files").is_dir(): command.append(f"FILES={(profile_dir / 'files').resolve()}")
    run(command, cwd=ib)
    info(output, [f"PROFILE={profile_name}", "METHOD=imagebuilder", "BUILD_MODE=imagebuilder", f"IMAGEBUILDER_URL={settings['IMAGEBUILDER_URL']}", f"DEVICE={settings['DEVICE']}"])


def build(profile_name: str, source_ref: str | None, output: Path, jobs: int) -> None:
    profile_dir = resolve_profile(profile_name)
    validate_profile_dir(profile_dir)
    settings = parse_settings(profile_dir / "settings")
    if settings["METHOD"] == "imagebuilder":
        build_imagebuilder(profile_name, profile_dir, settings, output)
    elif settings["BUILD_MODE"] == "release-patched":
        build_release_patched(profile_name, profile_dir, settings, source_ref, output, jobs)
    else:
        build_source(profile_name, profile_dir, settings, source_ref, output, jobs)


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate"); validate.add_argument("--profile")
    build_cmd = commands.add_parser("build"); build_cmd.add_argument("--profile", required=True); build_cmd.add_argument("--source-ref"); build_cmd.add_argument("--output", default="artifact"); build_cmd.add_argument("--jobs", type=int, default=max(os.cpu_count() or 1, 1))
    args = parser.parse_args()
    try:
        if args.command == "validate":
            if args.profile:
                validate_profile_dir(resolve_profile(args.profile)); print(f"OK: {args.profile}")
            else: validate_all()
        else:
            if args.jobs < 1: raise BuilderError("--jobs must be at least 1")
            build(args.profile, args.source_ref, Path(args.output), args.jobs)
    except (BuilderError, subprocess.CalledProcessError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr); return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
