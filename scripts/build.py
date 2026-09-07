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
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parents[1]
PROFILES_DIR = ROOT / "profiles"
WORK_DIR = ROOT / ".work"
PROFILE_FILES = ("settings", "packages", "feeds", "git-packages")
SOURCE_KEYS = ("METHOD", "BUILD_MODE", "REPOSITORY", "REF", "TARGET", "SUBTARGET", "DEVICE")
SOURCE_OPTIONAL_KEYS = ("BASE_REF", "SDK", "SDK_URL", "FEED_NAMES")
IMAGEBUILDER_KEYS = ("METHOD", "IMAGEBUILDER_URL", "DEVICE")
BUILD_MODES = ("release-patched", "selective-source", "full-source")
SDK_MODES = ("auto", "none")
RELEASE_REF_RE = re.compile(r"^v?(\d+\.\d+\.\d+)$")
STABLE_BRANCH_RE = re.compile(r"^openwrt-(\d+\.\d+)(?:$|[-.].*)")
OPENWRT_DOWNLOADS = "https://downloads.openwrt.org/releases"
OPENWRT_GIT = "https://github.com/openwrt/openwrt.git"
OPENWRT_TOOLS_IMAGE = "ghcr.io/openwrt/tools"
HOST_TOOLS_COMPAT_PATHS = (
    "tools",
    "toolchain",
    "include/version.mk",
    "include/cmake.mk",
    "include/subdir.mk",
    "scripts/ext-tools.sh",
    "scripts/timestamp.pl",
)


class BuilderError(RuntimeError):
    pass


def run(command, *, cwd=None, check=True):
    print("+", shlex.join(command), flush=True)
    return subprocess.run(command, cwd=cwd, check=check)


def strip_comment(line):
    return line.split("#", 1)[0].strip()


def resolve_profile(name):
    path = PROFILES_DIR / name
    if not path.is_dir():
        raise BuilderError(f"Profile '{name}' does not exist: {path}")
    return path


def parse_settings(path):
    values = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = strip_comment(raw)
        if not line:
            continue
        if "=" not in line:
            raise BuilderError(f"{path}:{number}: expected KEY=value")
        key, value = (part.strip() for part in line.split("=", 1))
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key) or not value:
            raise BuilderError(f"{path}:{number}: invalid setting")
        if key in values:
            raise BuilderError(f"{path}:{number}: duplicate key '{key}'")
        values[key] = value

    method = values.get("METHOD")
    if method not in ("source", "imagebuilder"):
        raise BuilderError(f"{path}: METHOD must be source or imagebuilder")

    required = SOURCE_KEYS if method == "source" else IMAGEBUILDER_KEYS
    allowed = set(required)
    if method == "source":
        allowed.update(SOURCE_OPTIONAL_KEYS)
    unknown = set(values) - allowed
    missing = [key for key in required if key not in values]
    if unknown:
        raise BuilderError(f"{path}: unsupported keys: {', '.join(sorted(unknown))}")
    if missing:
        raise BuilderError(f"{path}: missing required keys: {', '.join(missing)}")

    if method == "source":
        mode = values["BUILD_MODE"]
        if mode not in BUILD_MODES:
            raise BuilderError(f"{path}: BUILD_MODE must be one of {', '.join(BUILD_MODES)}")
        sdk = values.get("SDK")
        if sdk and sdk not in SDK_MODES:
            raise BuilderError(f"{path}: SDK must be auto or none")
        if sdk and values.get("SDK_URL"):
            raise BuilderError(f"{path}: SDK and SDK_URL are mutually exclusive")
        if mode == "release-patched":
            base_ref = values.get("BASE_REF")
            if not base_ref:
                raise BuilderError(f"{path}: release-patched requires BASE_REF")
            if not RELEASE_REF_RE.fullmatch(base_ref):
                raise BuilderError(f"{path}: BASE_REF must be an exact release tag such as v25.12.5")
        elif values.get("BASE_REF"):
            raise BuilderError(f"{path}: BASE_REF is only valid for release-patched")
    return values


def parse_feed_names(value):
    names = [name for name in re.split(r"[\s,]+", value or "") if name]
    for name in names:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
            raise BuilderError(f"Invalid feed name: {name}")
    return list(dict.fromkeys(names))


def parse_packages(path):
    include, exclude, seen = [], [], set()
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = strip_comment(raw)
        if not line:
            continue
        excluded = line.startswith("-")
        package = line[1:].strip() if excluded else line
        if not package or any(char.isspace() for char in package) or package in seen:
            raise BuilderError(f"{path}:{number}: invalid or duplicate package '{line}'")
        seen.add(package)
        (exclude if excluded else include).append(package)
    return include, exclude


def parse_simple_list(path):
    if not path.is_file():
        return []
    result = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = strip_comment(raw)
        if not line:
            continue
        if any(char.isspace() for char in line):
            raise BuilderError(f"{path}:{number}: expected one make target per line")
        result.append(line)
    return list(dict.fromkeys(result))


def parse_feeds(path):
    result = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = strip_comment(raw)
        if not line:
            continue
        if not line.startswith(("src-git ", "src-git-full ", "src-link ", "src-cpy ")):
            raise BuilderError(f"{path}:{number}: unsupported feed line")
        result.append(line)
    return result


def parse_git_packages(path):
    result = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = strip_comment(raw)
        if not line:
            continue
        parts = shlex.split(line)
        if not 1 <= len(parts) <= 3:
            raise BuilderError(f"{path}:{number}: expected REPOSITORY [REF] [PATH]")
        repo = parts[0]
        ref = None if len(parts) < 2 or parts[1] == "-" else parts[1]
        subpath = "." if len(parts) < 3 else parts[2]
        if "://" not in repo and not repo.startswith("git@"):
            raise BuilderError(f"{path}:{number}: invalid Git repository '{repo}'")
        if subpath.startswith("/") or ".." in Path(subpath).parts:
            raise BuilderError(f"{path}:{number}: PATH must stay inside the repository")
        result.append((repo, ref, subpath))
    return result


def validate_profile_dir(profile_dir):
    missing = [name for name in PROFILE_FILES if not (profile_dir / name).is_file()]
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


def validate_all():
    profiles = sorted(path for path in PROFILES_DIR.iterdir() if path.is_dir())
    if not profiles:
        raise BuilderError("No profiles found")
    for profile in profiles:
        validate_profile_dir(profile)
        print(f"OK: {profile.name}")


def clone_ref(repository, ref, destination, *, preserve_history=False):
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "clone", "--filter=blob:none", "--no-checkout", repository, str(destination)])
    fetch = ["git", "fetch"]
    if not preserve_history:
        fetch += ["--depth", "1"]
    fetch += ["origin", ref]
    run(fetch, cwd=destination)
    run(["git", "checkout", "--detach", "FETCH_HEAD"], cwd=destination)


def validate_release_base(source_dir, base_ref):
    run(["git", "fetch", "--filter=blob:none", OPENWRT_GIT, base_ref], cwd=source_dir)
    base_commit = subprocess.check_output(["git", "rev-parse", "FETCH_HEAD"], cwd=source_dir, text=True).strip()
    result = run(["git", "merge-base", "--is-ancestor", base_commit, "HEAD"], cwd=source_dir, check=False)
    if result.returncode:
        raise BuilderError(f"Custom REF is not based on official OpenWrt BASE_REF={base_ref}")
    return base_commit


def add_feeds(source_dir, feeds):
    if feeds:
        with (source_dir / "feeds.conf.default").open("a", encoding="utf-8") as handle:
            handle.write("\n# Added by openwrt-builder\n" + "\n".join(feeds) + "\n")


def update_feeds(source_dir, names):
    run(["./scripts/feeds", "update", *(names or ["-a"])], cwd=source_dir)


def install_feed_packages(source_dir, include, git_packages, *, full, feed_names):
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


def repository_name(repository):
    path = urlparse(repository).path if "://" in repository else repository
    name = Path(path.rstrip("/")).name
    return name[:-4] if name.endswith(".git") else name


def install_git_packages(source_dir, entries):
    if not entries:
        return
    root = source_dir / "package" / "openwrt-builder"
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="openwrt-builder-") as temp_dir:
        for index, (repo, ref, subpath) in enumerate(entries):
            checkout = Path(temp_dir) / str(index)
            clone_ref(repo, ref or "HEAD", checkout)
            source = (checkout / subpath).resolve()
            if not source.is_dir():
                raise BuilderError(f"Git package directory does not exist: {repo} {subpath}")
            name = source.name if subpath != "." else repository_name(repo)
            shutil.copytree(source, root / name, ignore=shutil.ignore_patterns(".git"))


def download_archive(url, destination, filename, label):
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    archive = destination / filename
    print(f"Downloading {label}: {url}", flush=True)
    with urllib.request.urlopen(url) as response, archive.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    extracted = destination / "extract"
    extracted.mkdir()
    run(["tar", "--zstd", "-xf", str(archive), "-C", str(extracted)])
    return extracted


def exact_release(ref):
    match = RELEASE_REF_RE.fullmatch(ref)
    return match.group(1) if match else None


def openwrt_tools_tag(ref):
    release = exact_release(ref)
    if release:
        major_minor = ".".join(release.split(".")[:2])
        return f"openwrt-{major_minor}"
    match = STABLE_BRANCH_RE.fullmatch(ref)
    if match:
        return f"openwrt-{match.group(1)}"
    if ref in ("main", "master", "HEAD"):
        return "latest"
    return None


def is_official_openwrt_repository(repository):
    path = urlparse(repository).path if "://" in repository else repository
    normalized = path.rstrip("/")
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    return normalized.lower().endswith("/openwrt/openwrt")


def changed_host_tools_inputs(source_dir, base_commit):
    output = subprocess.check_output(
        ["git", "diff", "--name-only", f"{base_commit}..HEAD", "--", *HOST_TOOLS_COMPAT_PATHS],
        cwd=source_dir,
        text=True,
    )
    return [line for line in output.splitlines() if line]


def resolve_prebuilt_tools(settings, source_dir, ref, base_commit):
    if settings["BUILD_MODE"] == "release-patched":
        tag = openwrt_tools_tag(settings["BASE_REF"])
        if not tag:
            return None, "base-ref-has-no-official-tools-family"
        changed = changed_host_tools_inputs(source_dir, base_commit)
        if changed:
            print(
                "OpenWrt prebuilt host tools disabled because the custom source changes "
                + ", ".join(changed),
                flush=True,
            )
            return None, "custom-source-modifies-host-tools"
        return f"{OPENWRT_TOOLS_IMAGE}:{tag}", "compatible-with-base-ref"

    if not is_official_openwrt_repository(settings["REPOSITORY"]):
        return None, "custom-repository-without-base-ref"
    tag = openwrt_tools_tag(ref)
    if not tag:
        return None, "ref-has-no-official-tools-family"
    return f"{OPENWRT_TOOLS_IMAGE}:{tag}", "official-ref"


def unpack_prebuilt_tools(profile_name, image):
    destination = WORK_DIR / profile_name / "prebuilt-tools"
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    oci_dir = destination / "oci"
    bundle_dir = destination / "bundle"

    copy_result = run(
        [
            "skopeo",
            "copy",
            "--override-os",
            "linux",
            "--override-arch",
            "amd64",
            f"docker://{image}",
            f"oci:{oci_dir}:tools",
        ],
        check=False,
    )
    if copy_result.returncode:
        print(f"NOTE: could not pull {image}; OpenWrt will build host tools from source.", flush=True)
        shutil.rmtree(destination, ignore_errors=True)
        return None

    unpack_result = run(
        ["umoci", "unpack", "--rootless", "--image", f"{oci_dir}:tools", str(bundle_dir)],
        check=False,
    )
    if unpack_result.returncode:
        print(f"NOTE: could not unpack {image}; OpenWrt will build host tools from source.", flush=True)
        shutil.rmtree(destination, ignore_errors=True)
        return None

    prebuilt = bundle_dir / "rootfs" / "prebuilt_tools"
    if not (prebuilt / "staging_dir" / "host").is_dir() or not (prebuilt / "build_dir" / "host").is_dir():
        print(f"NOTE: {image} does not contain the expected /prebuilt_tools tree; using source host tools.", flush=True)
        shutil.rmtree(destination, ignore_errors=True)
        return None
    return prebuilt


def install_prebuilt_tools(source_dir, prebuilt_root):
    staging_dir = source_dir / "staging_dir"
    build_dir = source_dir / "build_dir"
    staging_dir.mkdir(exist_ok=True)
    build_dir.mkdir(exist_ok=True)
    for destination, target in (
        (staging_dir / "host", prebuilt_root / "staging_dir" / "host"),
        (build_dir / "host", prebuilt_root / "build_dir" / "host"),
    ):
        if destination.is_symlink() or destination.is_file():
            destination.unlink()
        elif destination.exists():
            shutil.rmtree(destination)
        destination.symlink_to(target, target_is_directory=True)
    run(["./scripts/ext-tools.sh", "--refresh"], cwd=source_dir)


def prepare_prebuilt_tools(profile_name, settings, source_dir, ref, base_commit):
    image, reason = resolve_prebuilt_tools(settings, source_dir, ref, base_commit)
    if not image:
        print(f"OpenWrt prebuilt host tools: unavailable ({reason}); using source host tools.", flush=True)
        return None, reason
    print(f"OpenWrt prebuilt host tools: {image} ({reason})", flush=True)
    prebuilt = unpack_prebuilt_tools(profile_name, image)
    if not prebuilt:
        return None, "image-unavailable"
    install_prebuilt_tools(source_dir, prebuilt)
    return image, reason


def resolve_official_artifact(release, target, subtarget, artifact):
    base_url = f"{OPENWRT_DOWNLOADS}/{release}/targets/{target}/{subtarget}/"
    print(f"Resolving official OpenWrt {artifact}: {base_url}", flush=True)
    try:
        with urllib.request.urlopen(base_url) as response:
            listing = response.read().decode("utf-8")
    except OSError as exc:
        raise BuilderError(f"Could not read OpenWrt downloads directory: {base_url}") from exc

    release_re, target_re, subtarget_re = map(re.escape, (release, target, subtarget))
    if artifact == "sdk":
        pattern = rf'href="([^"]*openwrt-sdk-{release_re}-{target_re}-{subtarget_re}_[^"]+\.Linux-x86_64\.tar\.zst)"'
    elif artifact == "imagebuilder":
        pattern = rf'href="([^"]*openwrt-imagebuilder-{release_re}-{target_re}-{subtarget_re}\.Linux-x86_64\.tar\.zst)"'
    else:
        raise BuilderError(f"Unsupported official artifact: {artifact}")
    matches = list(dict.fromkeys(unescape(value) for value in re.findall(pattern, listing)))
    if len(matches) != 1:
        raise BuilderError(f"Expected one {artifact} for {release}/{target}/{subtarget}, found {len(matches)}")
    return urljoin(base_url, matches[0])


def resolve_sdk(settings):
    if settings.get("SDK_URL"):
        return settings["SDK_URL"], "url"
    sdk_mode = settings.get("SDK", "auto")
    if sdk_mode == "none":
        return None, "none"
    release_ref = settings["BASE_REF"] if settings["BUILD_MODE"] == "release-patched" else settings["REF"]
    release = exact_release(release_ref)
    if not release:
        print(f"SDK=auto: '{release_ref}' is not an exact release tag; using source toolchain.", flush=True)
        return None, "auto-unavailable"
    return resolve_official_artifact(release, settings["TARGET"], settings["SUBTARGET"], "sdk"), "auto"


def download_sdk(url, destination):
    extracted = download_archive(url, destination, "sdk.tar.zst", "OpenWrt SDK")
    roots = [path for path in extracted.iterdir() if path.is_dir()]
    if len(roots) != 1:
        raise BuilderError("Could not determine SDK directory")
    return roots[0]


def build_state(source_dir):
    helper = source_dir / ".owb.mk"
    helper.write_text("owb:\n\t@printf 'HOST=%s\\n' '$(STAGING_DIR_HOST)'\n\t@printf 'TOOLCHAIN=%s\\n' '$(TOOLCHAIN_DIR)'\n\t@printf 'TOOLS_STAMP=%s\\n' '$(tools/stamp-compile)'\n\t@printf 'TOOLCHAIN_STAMP=%s\\n' '$(toolchain/stamp-compile)'\n", encoding="utf-8")
    try:
        output = subprocess.check_output(["make", "-s", "OPENWRT_BUILD=1", "-f", "Makefile", "-f", helper.name, "owb"], cwd=source_dir, text=True)
    finally:
        helper.unlink(missing_ok=True)
    values = dict(line.split("=", 1) for line in output.splitlines() if "=" in line)
    return tuple(Path(values[key]).resolve() for key in ("HOST", "TOOLCHAIN", "TOOLS_STAMP", "TOOLCHAIN_STAMP"))


def replace_tree(source, destination):
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, symlinks=True)


def install_sdk_state(source_dir, sdk_root):
    host, toolchain, tools_stamp, toolchain_stamp = build_state(source_dir)
    sdk_toolchains = list((sdk_root / "staging_dir").glob("toolchain-*"))
    if len(sdk_toolchains) != 1 or sdk_toolchains[0].name != toolchain.name:
        raise BuilderError("SDK toolchain does not match the source build")
    replace_tree(sdk_root / "staging_dir" / "host", host)
    replace_tree(sdk_toolchains[0], toolchain)
    (toolchain / "stamp").mkdir(parents=True, exist_ok=True)
    (toolchain / "stamp" / ".gcc_final_installed").touch()
    tools_stamp.parent.mkdir(parents=True, exist_ok=True)
    tools_stamp.touch()
    toolchain_stamp.parent.mkdir(parents=True, exist_ok=True)
    toolchain_stamp.touch()


def write_config(source_dir, settings, include, exclude, *, full=False, imagebuilder=False):
    target, subtarget, device = settings["TARGET"], settings["SUBTARGET"], settings["DEVICE"]
    lines = [f"CONFIG_TARGET_{target}=y", f"CONFIG_TARGET_{target}_{subtarget}=y", f"CONFIG_TARGET_{target}_{subtarget}_DEVICE_{device}=y"]
    if full:
        lines += ["CONFIG_ALL=y", "CONFIG_ALL_KMODS=y", "CONFIG_ALL_NONSHARED=y"]
    if imagebuilder:
        lines.append("CONFIG_IB=y")
    lines += [f"CONFIG_PACKAGE_{package}=y" for package in include]
    lines += [f"CONFIG_PACKAGE_{package}=n" for package in exclude]
    (source_dir / ".config").write_text("\n".join(lines) + "\n", encoding="utf-8")


def prepare_source(profile_name, profile_dir, settings, source_ref, include, *, full):
    ref = source_ref or settings["REF"]
    source_dir = WORK_DIR / profile_name / "openwrt"
    clone_ref(settings["REPOSITORY"], ref, source_dir, preserve_history=settings["BUILD_MODE"] == "release-patched")
    base_commit = None
    if settings["BUILD_MODE"] == "release-patched":
        base_commit = validate_release_base(source_dir, settings["BASE_REF"])
    add_feeds(source_dir, parse_feeds(profile_dir / "feeds"))
    feed_names = parse_feed_names(settings.get("FEED_NAMES"))
    git_packages = parse_git_packages(profile_dir / "git-packages")
    if git_packages and feed_names and not full:
        print("NOTE: FEED_NAMES ignored because git-packages requires all feeds.", flush=True)
        feed_names = []
    update_feeds(source_dir, feed_names)
    install_feed_packages(source_dir, include, git_packages, full=full, feed_names=feed_names)
    install_git_packages(source_dir, git_packages)
    return source_dir, ref, feed_names, base_commit


def prepare_sdk(profile_name, settings):
    url, mode = resolve_sdk(settings)
    return (download_sdk(url, WORK_DIR / profile_name / "sdk") if url else None), url, mode


def copy_files(profile_dir, destination):
    source = profile_dir / "files"
    if not source.is_dir():
        return False
    shutil.copytree(source, destination, dirs_exist_ok=True)
    return True


def download_sources(source_dir, jobs, sdk):
    if sdk:
        run(["make", "package/download", "target/download", f"-j{jobs}"], cwd=source_dir)
    else:
        run(["make", "download", f"-j{jobs}"], cwd=source_dir)


def prepare_output(output):
    output = output.resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    return output


def copy_firmware(source_dir, settings, output):
    source = source_dir / "bin" / "targets" / settings["TARGET"] / settings["SUBTARGET"]
    if not source.is_dir():
        raise BuilderError(f"Expected firmware directory missing: {source}")
    prepare_output(output)
    for item in source.iterdir():
        if item.name == "packages":
            continue
        destination = output / item.name
        shutil.copytree(item, destination) if item.is_dir() else shutil.copy2(item, destination)


def write_info(output, lines):
    (output / "BUILD_INFO").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_source(profile_name, profile_dir, settings, source_ref, output, jobs):
    include, exclude = parse_packages(profile_dir / "packages")
    full = settings["BUILD_MODE"] == "full-source"
    source_dir, ref, feeds, base_commit = prepare_source(profile_name, profile_dir, settings, source_ref, include, full=full)
    sdk, sdk_url, sdk_mode = prepare_sdk(profile_name, settings)
    tools_image, tools_reason = (None, "sdk-provides-host-tools")
    if not sdk:
        tools_image, tools_reason = prepare_prebuilt_tools(profile_name, settings, source_dir, ref, base_commit)
    files = copy_files(profile_dir, source_dir / "files")
    write_config(source_dir, settings, include, exclude, full=full)
    run(["make", "defconfig"], cwd=source_dir)
    if sdk:
        install_sdk_state(source_dir, sdk)
    download_sources(source_dir, jobs, sdk)
    run(["make", f"-j{jobs}"], cwd=source_dir)
    copy_firmware(source_dir, settings, output)
    host_tools_mode = "sdk" if sdk else ("official-prebuilt" if tools_image else "source")
    write_info(output, [f"PROFILE={profile_name}", "METHOD=source", f"BUILD_MODE={settings['BUILD_MODE']}", f"REF={ref}", f"SDK_MODE={sdk_mode}", f"SDK_URL={sdk_url or 'none'}", f"HOST_TOOLS_MODE={host_tools_mode}", f"HOST_TOOLS_IMAGE={tools_image or 'none'}", f"HOST_TOOLS_REASON={tools_reason}", f"FEED_NAMES={' '.join(feeds) if feeds else 'all'}", f"INCLUDE_PACKAGES={' '.join(include)}", f"EXCLUDE_PACKAGES={' '.join(exclude)}", f"FILES={'included' if files else 'none'}"])


def generated_imagebuilder(source_dir, settings):
    target_dir = source_dir / "bin" / "targets" / settings["TARGET"] / settings["SUBTARGET"]
    archives = list(target_dir.glob("*imagebuilder*.tar.zst"))
    if len(archives) != 1:
        raise BuilderError(f"Expected one generated ImageBuilder, found {len(archives)}")
    destination = WORK_DIR / "generated-imagebuilder"
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    run(["tar", "--zstd", "-xf", str(archives[0]), "-C", str(destination)])
    roots = [path for path in destination.iterdir() if path.is_dir()]
    if len(roots) != 1:
        raise BuilderError("Could not identify generated ImageBuilder")
    return roots[0]


def download_imagebuilder(url, destination):
    extracted = download_archive(url, destination, "imagebuilder.tar.zst", "ImageBuilder")
    roots = [path for path in extracted.iterdir() if path.is_dir()]
    if len(roots) != 1:
        raise BuilderError("Could not determine ImageBuilder directory")
    return roots[0]


def pin_release_repositories(settings, custom_ib, profile_name):
    release = exact_release(settings["BASE_REF"])
    url = resolve_official_artifact(release, settings["TARGET"], settings["SUBTARGET"], "imagebuilder")
    official_ib = download_imagebuilder(url, WORK_DIR / profile_name / "base-imagebuilder")
    copied = []
    for name in ("repositories", "repositories.conf"):
        source = official_ib / name
        if source.is_file():
            shutil.copy2(source, custom_ib / name)
            copied.append(name)
    if not copied:
        raise BuilderError("Could not find repository configuration in the official base ImageBuilder")
    print(f"Pinned custom ImageBuilder repositories to {settings['BASE_REF']}: {', '.join(copied)}", flush=True)


def copy_local_apks(source_dir, imagebuilder_dir):
    destination = imagebuilder_dir / "packages"
    destination.mkdir(exist_ok=True)
    count = 0
    for root in (source_dir / "bin" / "packages", source_dir / "bin" / "targets"):
        if root.exists():
            for apk in root.rglob("*.apk"):
                shutil.copy2(apk, destination / apk.name)
                count += 1
    return count


def build_release_patched(profile_name, profile_dir, settings, source_ref, output, jobs):
    include, exclude = parse_packages(profile_dir / "packages")
    targets = parse_simple_list(profile_dir / "source-build-targets")
    source_dir, ref, feeds, base_commit = prepare_source(profile_name, profile_dir, settings, source_ref, [], full=False)
    sdk, sdk_url, sdk_mode = prepare_sdk(profile_name, settings)
    tools_image, tools_reason = (None, "sdk-provides-host-tools")
    if not sdk:
        tools_image, tools_reason = prepare_prebuilt_tools(profile_name, settings, source_dir, ref, base_commit)
    files = copy_files(profile_dir, source_dir / "files")
    write_config(source_dir, settings, [], [], imagebuilder=True)
    run(["make", "defconfig"], cwd=source_dir)
    if sdk:
        install_sdk_state(source_dir, sdk)
    download_sources(source_dir, jobs, sdk)
    run(["make", "target/linux/compile", f"-j{jobs}"], cwd=source_dir)
    for target in targets:
        run(["make", target, f"-j{jobs}"], cwd=source_dir)
    run(["make", "package/base-files/compile", f"-j{jobs}"], cwd=source_dir)
    run(["make", "target/imagebuilder/compile", f"-j{jobs}"], cwd=source_dir)
    imagebuilder_dir = generated_imagebuilder(source_dir, settings)
    pin_release_repositories(settings, imagebuilder_dir, profile_name)
    local_apks = copy_local_apks(source_dir, imagebuilder_dir)
    prepare_output(output)
    package_args = include + [f"-{package}" for package in exclude]
    command = ["make", "image", f"PROFILE={settings['DEVICE']}", f"PACKAGES={' '.join(package_args)}", f"BIN_DIR={output}"]
    if files:
        command.append(f"FILES={(source_dir / 'files').resolve()}")
    run(command, cwd=imagebuilder_dir)
    host_tools_mode = "sdk" if sdk else ("official-prebuilt" if tools_image else "source")
    write_info(output, [f"PROFILE={profile_name}", "METHOD=source", "BUILD_MODE=release-patched", f"REF={ref}", f"BASE_REF={settings['BASE_REF']}", f"SDK_MODE={sdk_mode}", f"SDK_URL={sdk_url or 'none'}", f"HOST_TOOLS_MODE={host_tools_mode}", f"HOST_TOOLS_IMAGE={tools_image or 'none'}", f"HOST_TOOLS_REASON={tools_reason}", f"SOURCE_BUILD_TARGETS={' '.join(targets)}", f"LOCAL_APKS={local_apks}", f"INCLUDE_PACKAGES={' '.join(include)}", f"EXCLUDE_PACKAGES={' '.join(exclude)}", f"FEED_NAMES={' '.join(feeds) if feeds else 'all'}", "UNCHANGED_PACKAGES=official-base-release-repositories"])


def build_imagebuilder(profile_name, profile_dir, settings, output):
    include, exclude = parse_packages(profile_dir / "packages")
    imagebuilder_dir = download_imagebuilder(settings["IMAGEBUILDER_URL"], WORK_DIR / profile_name / "imagebuilder")
    prepare_output(output)
    package_args = include + [f"-{package}" for package in exclude]
    command = ["make", "image", f"PROFILE={settings['DEVICE']}", f"PACKAGES={' '.join(package_args)}", f"BIN_DIR={output}"]
    if (profile_dir / "files").is_dir():
        command.append(f"FILES={(profile_dir / 'files').resolve()}")
    run(command, cwd=imagebuilder_dir)
    write_info(output, [f"PROFILE={profile_name}", "METHOD=imagebuilder", "BUILD_MODE=imagebuilder", f"IMAGEBUILDER_URL={settings['IMAGEBUILDER_URL']}", f"DEVICE={settings['DEVICE']}"])


def build(profile_name, source_ref, output, jobs):
    profile_dir = resolve_profile(profile_name)
    validate_profile_dir(profile_dir)
    settings = parse_settings(profile_dir / "settings")
    if settings["METHOD"] == "imagebuilder":
        build_imagebuilder(profile_name, profile_dir, settings, output)
    elif settings["BUILD_MODE"] == "release-patched":
        build_release_patched(profile_name, profile_dir, settings, source_ref, output, jobs)
    else:
        build_source(profile_name, profile_dir, settings, source_ref, output, jobs)


def main():
    parser = argparse.ArgumentParser(description="Build OpenWrt firmware from reusable profiles.")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("--profile")
    build_cmd = commands.add_parser("build")
    build_cmd.add_argument("--profile", required=True)
    build_cmd.add_argument("--source-ref")
    build_cmd.add_argument("--output", default="artifact")
    build_cmd.add_argument("--jobs", type=int, default=max(os.cpu_count() or 1, 1))
    args = parser.parse_args()
    try:
        if args.command == "validate":
            if args.profile:
                validate_profile_dir(resolve_profile(args.profile))
                print(f"OK: {args.profile}")
            else:
                validate_all()
        else:
            if args.jobs < 1:
                raise BuilderError("--jobs must be at least 1")
            build(args.profile, args.source_ref, Path(args.output), args.jobs)
    except (BuilderError, subprocess.CalledProcessError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
