#!/usr/bin/env python3
"""Simple OpenWrt profile builder used locally and by GitHub Actions."""

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

SOURCE_KEYS = ("METHOD", "REPOSITORY", "REF", "TARGET", "SUBTARGET", "DEVICE")
SOURCE_OPTIONAL_KEYS = ("TOOLCHAIN_URL", "FEED_NAMES")
IMAGEBUILDER_KEYS = ("METHOD", "IMAGEBUILDER_URL", "DEVICE")


class BuilderError(RuntimeError):
    """Raised for user-facing builder configuration errors."""


def run(
    command: list[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess:
    print("+", shlex.join(command), flush=True)
    return subprocess.run(command, cwd=cwd, check=check)


def strip_comment(line: str) -> str:
    return line.split("#", 1)[0].strip()


def has_entries(path: Path) -> bool:
    return any(strip_comment(line) for line in path.read_text(encoding="utf-8").splitlines())


def resolve_profile(name: str) -> Path:
    path = PROFILES_DIR / name
    if not path.is_dir():
        raise BuilderError(f"Profile '{name}' does not exist: {path}")
    return path


def parse_settings(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}

    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = strip_comment(raw)
        if not line:
            continue
        if "=" not in line:
            raise BuilderError(f"{path}:{number}: expected KEY=value")

        key, value = (part.strip() for part in line.split("=", 1))
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            raise BuilderError(f"{path}:{number}: invalid key '{key}'")
        if not value:
            raise BuilderError(f"{path}:{number}: '{key}' cannot be empty")
        if key in values:
            raise BuilderError(f"{path}:{number}: duplicate key '{key}'")
        values[key] = value

    method = values.get("METHOD")
    if method not in ("source", "imagebuilder"):
        raise BuilderError(f"{path}: METHOD must be 'source' or 'imagebuilder'")

    required = SOURCE_KEYS if method == "source" else IMAGEBUILDER_KEYS
    allowed = set(required)
    if method == "source":
        allowed.update(SOURCE_OPTIONAL_KEYS)

    unknown = set(values) - allowed
    if unknown:
        raise BuilderError(f"{path}: unsupported keys for {method}: {', '.join(sorted(unknown))}")

    missing = [key for key in required if key not in values]
    if missing:
        raise BuilderError(f"{path}: missing required keys: {', '.join(missing)}")

    return values


def parse_feed_names(value: str | None) -> list[str]:
    if not value:
        return []

    names = [name for name in re.split(r"[\s,]+", value) if name]
    for name in names:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
            raise BuilderError(f"Invalid feed name in FEED_NAMES: '{name}'")

    return list(dict.fromkeys(names))


def parse_packages(path: Path) -> tuple[list[str], list[str]]:
    include: list[str] = []
    exclude: list[str] = []
    seen: dict[str, str] = {}

    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = strip_comment(raw)
        if not line:
            continue

        excluded = line.startswith("-")
        package = line[1:].strip() if excluded else line
        if not package or any(char.isspace() for char in package):
            raise BuilderError(f"{path}:{number}: invalid package entry '{line}'")

        mode = "exclude" if excluded else "include"
        if package in seen:
            raise BuilderError(
                f"{path}:{number}: package '{package}' is already listed as {seen[package]}"
            )
        seen[package] = mode
        (exclude if excluded else include).append(package)

    return include, exclude


def parse_feeds(path: Path) -> list[str]:
    feeds: list[str] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = strip_comment(raw)
        if not line:
            continue
        if not line.startswith(("src-git ", "src-git-full ", "src-link ", "src-cpy ")):
            raise BuilderError(
                f"{path}:{number}: unsupported feed line. Use standard OpenWrt feed syntax."
            )
        feeds.append(line)
    return feeds


def parse_git_packages(path: Path) -> list[tuple[str, str | None, str]]:
    packages: list[tuple[str, str | None, str]] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = strip_comment(raw)
        if not line:
            continue

        parts = shlex.split(line)
        if not 1 <= len(parts) <= 3:
            raise BuilderError(f"{path}:{number}: expected REPOSITORY [REF] [PATH]")

        repository = parts[0]
        ref = None if len(parts) < 2 or parts[1] == "-" else parts[1]
        package_path = "." if len(parts) < 3 else parts[2]

        if "://" not in repository and not repository.startswith("git@"):
            raise BuilderError(f"{path}:{number}: invalid Git repository '{repository}'")
        if package_path.startswith("/") or ".." in Path(package_path).parts:
            raise BuilderError(f"{path}:{number}: PATH must stay inside the repository")

        packages.append((repository, ref, package_path))
    return packages


def validate_profile_dir(profile_dir: Path) -> None:
    missing = [name for name in PROFILE_FILES if not (profile_dir / name).is_file()]
    if missing:
        raise BuilderError(f"{profile_dir}: missing required files: {', '.join(missing)}")

    files_dir = profile_dir / "files"
    if files_dir.exists() and not files_dir.is_dir():
        raise BuilderError(f"{files_dir}: optional files entry must be a directory")

    settings = parse_settings(profile_dir / "settings")
    parse_packages(profile_dir / "packages")

    if settings["METHOD"] == "source":
        parse_feed_names(settings.get("FEED_NAMES"))
        parse_feeds(profile_dir / "feeds")
        parse_git_packages(profile_dir / "git-packages")


def validate_all() -> None:
    profiles = sorted(path for path in PROFILES_DIR.iterdir() if path.is_dir())
    if not profiles:
        raise BuilderError("No profiles found")

    for profile_dir in profiles:
        validate_profile_dir(profile_dir)
        print(f"OK: {profile_dir.name}")


def repository_name(repository: str) -> str:
    path = urlparse(repository).path if "://" in repository else repository
    name = Path(path.rstrip("/")).name
    return name[:-4] if name.endswith(".git") else name


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
    if not feeds:
        return

    feeds_file = source_dir / "feeds.conf.default"
    with feeds_file.open("a", encoding="utf-8") as handle:
        handle.write("\n# Added by openwrt-builder\n")
        for feed in feeds:
            handle.write(feed + "\n")


def update_feeds(source_dir: Path, feed_names: list[str]) -> None:
    if feed_names:
        print(f"Updating only selected feeds: {' '.join(feed_names)}", flush=True)
        run(["./scripts/feeds", "update", *feed_names], cwd=source_dir)
        return

    run(["./scripts/feeds", "update", "-a"], cwd=source_dir)


def install_feed_packages(
    source_dir: Path,
    include: list[str],
    git_packages: list[tuple[str, str | None, str]],
) -> None:
    if git_packages:
        print(
            "Git packages configured; installing all indexed feed packages so external package "
            "dependencies are available.",
            flush=True,
        )
        run(["./scripts/feeds", "install", "-a"], cwd=source_dir)
        return

    if not include:
        return

    print("Installing only requested feed packages and their dependencies.", flush=True)
    run(["./scripts/feeds", "install", *include], cwd=source_dir)


def install_git_packages(
    source_dir: Path,
    entries: list[tuple[str, str | None, str]],
) -> None:
    if not entries:
        return

    destination_root = source_dir / "package" / "openwrt-builder"
    destination_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="openwrt-builder-") as temp_dir:
        temp_root = Path(temp_dir)

        for index, (repository, ref, package_path) in enumerate(entries):
            checkout = temp_root / f"repo-{index}"
            clone_ref(repository, ref, checkout)

            source = (checkout / package_path).resolve()
            checkout_root = checkout.resolve()
            if source != checkout_root and checkout_root not in source.parents:
                raise BuilderError(f"Package path escapes repository: {package_path}")
            if not source.is_dir():
                raise BuilderError(f"Git package directory does not exist: {repository} {package_path}")

            name = source.name if package_path != "." else repository_name(repository)
            destination = destination_root / name
            if destination.exists():
                raise BuilderError(f"Multiple Git package entries resolve to '{name}'")

            shutil.copytree(source, destination, ignore=shutil.ignore_patterns(".git"))


def download_external_toolchain(
    url: str,
    destination: Path,
) -> tuple[Path, str, str]:
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)

    archive = destination / "toolchain.tar.zst"
    print(f"Downloading external toolchain: {url}")
    with urllib.request.urlopen(url) as response, archive.open("wb") as handle:
        shutil.copyfileobj(response, handle)

    extract_dir = destination / "extract"
    extract_dir.mkdir()
    run(["tar", "--zstd", "-xf", str(archive), "-C", str(extract_dir)])

    compilers = sorted(
        path
        for path in extract_dir.rglob("*-gcc")
        if path.is_file() and path.parent.name == "bin"
    )
    musl_compilers = [path for path in compilers if path.name.endswith("-musl-gcc")]
    if len(musl_compilers) == 1:
        compiler = musl_compilers[0]
    elif len(compilers) == 1:
        compiler = compilers[0]
    else:
        candidates = ", ".join(str(path.relative_to(extract_dir)) for path in compilers)
        raise BuilderError(
            "Could not uniquely identify the external musl toolchain compiler "
            f"(candidates: {candidates or 'none'})"
        )

    toolchain_root = compiler.parent.parent.resolve()
    prefix = compiler.name.removesuffix("gcc")
    if not prefix.endswith("-"):
        raise BuilderError(f"Could not determine toolchain prefix from {compiler.name}")

    gcc_version = subprocess.check_output(
        [str(compiler), "-dumpfullversion"],
        text=True,
    ).strip()
    if not gcc_version:
        raise BuilderError("External toolchain compiler did not report a GCC version")

    print(f"External toolchain root: {toolchain_root}")
    print(f"External toolchain prefix: {prefix}")
    print(f"External toolchain GCC: {gcc_version}")
    return toolchain_root, prefix, gcc_version


def copy_profile_files(profile_dir: Path, destination: Path) -> bool:
    source = profile_dir / "files"
    if not source.is_dir():
        return False

    shutil.copytree(source, destination, dirs_exist_ok=True)
    return True


def write_source_config(
    source_dir: Path,
    settings: dict[str, str],
    include: list[str],
    exclude: list[str],
    external_toolchain: tuple[Path, str, str] | None,
) -> None:
    target = settings["TARGET"]
    subtarget = settings["SUBTARGET"]
    device = settings["DEVICE"]

    lines = [
        f"CONFIG_TARGET_{target}=y",
        f"CONFIG_TARGET_{target}_{subtarget}=y",
        f"CONFIG_TARGET_{target}_{subtarget}_DEVICE_{device}=y",
    ]

    if external_toolchain:
        toolchain_root, prefix, gcc_version = external_toolchain
        target_name = prefix.removesuffix("-")
        lines.extend(
            [
                "CONFIG_DEVEL=y",
                "CONFIG_EXTERNAL_TOOLCHAIN=y",
                f'CONFIG_TARGET_NAME="{target_name}"',
                f'CONFIG_TOOLCHAIN_PREFIX="{prefix}"',
                f'CONFIG_TOOLCHAIN_ROOT="{toolchain_root}"',
                "CONFIG_EXTERNAL_TOOLCHAIN_LIBC_USE_MUSL=y",
                f'CONFIG_EXTERNAL_GCC_VERSION="{gcc_version}"',
            ]
        )

    lines.extend(f"CONFIG_PACKAGE_{package}=y" for package in include)
    lines.extend(f"CONFIG_PACKAGE_{package}=n" for package in exclude)
    (source_dir / ".config").write_text("\n".join(lines) + "\n", encoding="utf-8")


def config_value(config: str, symbol: str) -> str | None:
    enabled = f"{symbol}="
    disabled = f"# {symbol} is not set"
    for line in config.splitlines():
        if line.startswith(enabled):
            return line[len(enabled) :]
        if line == disabled:
            return "n"
    return None


def validate_resolved_config(
    source_dir: Path,
    settings: dict[str, str],
    include: list[str],
    exclude: list[str],
) -> None:
    config = (source_dir / ".config").read_text(encoding="utf-8")
    target_symbols = [
        f"CONFIG_TARGET_{settings['TARGET']}",
        f"CONFIG_TARGET_{settings['TARGET']}_{settings['SUBTARGET']}",
        f"CONFIG_TARGET_{settings['TARGET']}_{settings['SUBTARGET']}_DEVICE_{settings['DEVICE']}",
    ]
    for symbol in target_symbols:
        if config_value(config, symbol) != "y":
            raise BuilderError(f"OpenWrt did not select required target symbol: {symbol}")

    if settings.get("TOOLCHAIN_URL"):
        if config_value(config, "CONFIG_EXTERNAL_TOOLCHAIN") != "y":
            raise BuilderError("OpenWrt did not enable the requested external toolchain")

    errors: list[str] = []
    for package in include:
        if config_value(config, f"CONFIG_PACKAGE_{package}") != "y":
            errors.append(f"{package}: requested but not selected")
    for package in exclude:
        value = config_value(config, f"CONFIG_PACKAGE_{package}")
        if value not in (None, "n"):
            errors.append(f"{package}: explicitly excluded but resolved to {value}")
    if errors:
        raise BuilderError("Package validation failed:\n  - " + "\n  - ".join(errors))


def prepare_output(output: Path) -> Path:
    output = output.resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    return output


def build_from_source(
    profile_name: str,
    profile_dir: Path,
    settings: dict[str, str],
    source_ref: str | None,
    output: Path,
    jobs: int,
) -> None:
    include, exclude = parse_packages(profile_dir / "packages")
    feeds = parse_feeds(profile_dir / "feeds")
    git_packages = parse_git_packages(profile_dir / "git-packages")
    feed_names = parse_feed_names(settings.get("FEED_NAMES"))

    ref = source_ref or settings["REF"]
    source_dir = WORK_DIR / profile_name / "openwrt"

    print("Method:  source")
    print(f"Source:  {settings['REPOSITORY']} @ {ref}")
    print(f"Target:  {settings['TARGET']}/{settings['SUBTARGET']}/{settings['DEVICE']}")

    clone_ref(settings["REPOSITORY"], ref, source_dir)
    add_feeds(source_dir, feeds)

    if git_packages and feed_names:
        print(
            "NOTE: FEED_NAMES is ignored because git-packages requires all feeds to be indexed.",
            flush=True,
        )
        feed_names = []

    update_feeds(source_dir, feed_names)
    install_feed_packages(source_dir, include, git_packages)
    install_git_packages(source_dir, git_packages)

    external_toolchain = None
    toolchain_url = settings.get("TOOLCHAIN_URL")
    if toolchain_url:
        external_toolchain = download_external_toolchain(
            toolchain_url,
            WORK_DIR / profile_name / "toolchain",
        )

    files_included = copy_profile_files(profile_dir, source_dir / "files")
    write_source_config(source_dir, settings, include, exclude, external_toolchain)

    run(["make", "defconfig"], cwd=source_dir)
    validate_resolved_config(source_dir, settings, include, exclude)
    run(["make", "download", f"-j{jobs}"], cwd=source_dir)
    run(["make", f"-j{jobs}"], cwd=source_dir)

    target_dir = source_dir / "bin" / "targets" / settings["TARGET"] / settings["SUBTARGET"]
    if not target_dir.is_dir():
        raise BuilderError(f"Expected firmware directory was not created: {target_dir}")

    output = prepare_output(output)
    for item in target_dir.iterdir():
        if item.name == "packages":
            continue
        destination = output / item.name
        if item.is_dir():
            shutil.copytree(item, destination)
        else:
            shutil.copy2(item, destination)

    source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=source_dir, text=True
    ).strip()
    info = [
        f"PROFILE={profile_name}",
        "METHOD=source",
        f"REPOSITORY={settings['REPOSITORY']}",
        f"REF={ref}",
        f"SOURCE_COMMIT={source_commit}",
        f"TARGET={settings['TARGET']}",
        f"SUBTARGET={settings['SUBTARGET']}",
        f"DEVICE={settings['DEVICE']}",
        f"INCLUDE_PACKAGES={' '.join(include)}",
        f"EXCLUDE_PACKAGES={' '.join(exclude)}",
        f"FEED_NAMES={' '.join(feed_names) if feed_names else 'all'}",
        f"FILES={'included' if files_included else 'none'}",
    ]

    if external_toolchain:
        _, prefix, gcc_version = external_toolchain
        info.extend(
            [
                "TOOLCHAIN=external",
                f"TOOLCHAIN_URL={toolchain_url}",
                f"TOOLCHAIN_PREFIX={prefix}",
                f"TOOLCHAIN_GCC_VERSION={gcc_version}",
            ]
        )
    else:
        info.append("TOOLCHAIN=internal")

    (output / "BUILD_INFO").write_text("\n".join(info) + "\n", encoding="utf-8")


def download_imagebuilder(url: str, destination: Path) -> Path:
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)

    archive = destination / "imagebuilder.tar.zst"
    print(f"Downloading ImageBuilder: {url}")
    with urllib.request.urlopen(url) as response, archive.open("wb") as handle:
        shutil.copyfileobj(response, handle)

    extract_dir = destination / "extract"
    extract_dir.mkdir()
    run(["tar", "--zstd", "-xf", str(archive), "-C", str(extract_dir)])

    roots = [path for path in extract_dir.iterdir() if path.is_dir()]
    if len(roots) != 1:
        raise BuilderError("Could not determine extracted ImageBuilder directory")
    return roots[0]


def build_with_imagebuilder(
    profile_name: str,
    profile_dir: Path,
    settings: dict[str, str],
    output: Path,
) -> None:
    include, exclude = parse_packages(profile_dir / "packages")
    package_args = include + [f"-{package}" for package in exclude]
    files_dir = profile_dir / "files"

    print("Method:  imagebuilder")
    print(f"ImageBuilder: {settings['IMAGEBUILDER_URL']}")
    print(f"Profile: {settings['DEVICE']}")
    print("NOTE: feeds and git-packages are ignored in imagebuilder mode.")
    if has_entries(profile_dir / "feeds"):
        print("NOTE: ignoring entries from feeds")
    if has_entries(profile_dir / "git-packages"):
        print("NOTE: ignoring entries from git-packages")

    work_dir = WORK_DIR / profile_name / "imagebuilder"
    imagebuilder_dir = download_imagebuilder(settings["IMAGEBUILDER_URL"], work_dir)
    output = prepare_output(output)

    command = [
        "make",
        "image",
        f"PROFILE={settings['DEVICE']}",
        f"PACKAGES={' '.join(package_args)}",
        f"BIN_DIR={output}",
    ]
    if files_dir.is_dir():
        command.append(f"FILES={files_dir.resolve()}")

    run(command, cwd=imagebuilder_dir)

    info = [
        f"PROFILE={profile_name}",
        "METHOD=imagebuilder",
        f"IMAGEBUILDER_URL={settings['IMAGEBUILDER_URL']}",
        f"DEVICE={settings['DEVICE']}",
        f"INCLUDE_PACKAGES={' '.join(include)}",
        f"EXCLUDE_PACKAGES={' '.join(exclude)}",
        "FEEDS=ignored",
        "GIT_PACKAGES=ignored",
        f"FILES={'included' if files_dir.is_dir() else 'none'}",
    ]
    (output / "BUILD_INFO").write_text("\n".join(info) + "\n", encoding="utf-8")


def build(profile_name: str, source_ref: str | None, output: Path, jobs: int) -> None:
    profile_dir = resolve_profile(profile_name)
    validate_profile_dir(profile_dir)
    settings = parse_settings(profile_dir / "settings")

    print(f"Profile: {profile_name}")
    if settings["METHOD"] == "source":
        build_from_source(profile_name, profile_dir, settings, source_ref, output, jobs)
    else:
        if source_ref:
            print("NOTE: --source-ref is ignored in imagebuilder mode.")
        build_with_imagebuilder(profile_name, profile_dir, settings, output)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build OpenWrt firmware from simple profiles.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate profile files.")
    validate_parser.add_argument(
        "--profile", help="Validate one profile. If omitted, all profiles are validated."
    )

    build_parser = subparsers.add_parser("build", help="Build one firmware profile.")
    build_parser.add_argument("--profile", required=True)
    build_parser.add_argument(
        "--source-ref", help="Override REF for source builds. Ignored by ImageBuilder builds."
    )
    build_parser.add_argument(
        "--output", default="artifact", help="Directory where firmware artifacts are copied."
    )
    build_parser.add_argument(
        "--jobs",
        type=int,
        default=max(os.cpu_count() or 1, 1),
        help="Parallel make jobs for source builds.",
    )

    args = parser.parse_args()
    try:
        if args.command == "validate":
            if args.profile:
                profile_dir = resolve_profile(args.profile)
                validate_profile_dir(profile_dir)
                print(f"OK: {args.profile}")
            else:
                validate_all()
        elif args.command == "build":
            if args.jobs < 1:
                raise BuilderError("--jobs must be at least 1")
            build(args.profile, args.source_ref, Path(args.output), args.jobs)
    except (BuilderError, subprocess.CalledProcessError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
