#!/usr/bin/env python3
"""Validate the public OpenWrt Builder profile catalog and version contract."""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

PROFILE_ID_RE = re.compile(
    r"^(?P<device>[a-z0-9]+(?:-[a-z0-9]+)*)-(?P<version>\d+\.\d+\.\d+|\d+\.\d+|snapshot)$"
)
RELEASE_REF_RE = re.compile(r"^v?(\d+\.\d+\.\d+)$")
STABLE_REF_RE = re.compile(r"^openwrt-(\d+\.\d+)(?:$|[-.].*)")
RELEASE_URL_RE = re.compile(r"/releases/(\d+\.\d+\.\d+)/")
REQUIRED_FILES = {"README.md", "settings", "packages", "feeds", "git-packages"}
OPTIONAL_ENTRIES = {"source-build-targets", "files"}


def fail(message: str) -> None:
    raise ValueError(message)


def load_builder(root: Path):
    spec = importlib.util.spec_from_file_location("openwrt_builder_profile_catalog", root / "scripts" / "build.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def parse_profile_id(profile_id: str) -> tuple[str, str, str]:
    match = PROFILE_ID_RE.fullmatch(profile_id)
    if not match:
        fail(
            "profile ID must be <device>-<X.Y.Z|X.Y|snapshot> using lowercase letters, digits and hyphens"
        )
    device = match.group("device")
    version = match.group("version")
    source = "snapshot" if version == "snapshot" else ("release" if version.count(".") == 2 else "stable")
    return device, version, source


def release_from_ref(ref: str) -> str | None:
    match = RELEASE_REF_RE.fullmatch(ref)
    return match.group(1) if match else None


def release_from_url(value: str) -> str | None:
    match = RELEASE_URL_RE.search(urlparse(value).path)
    return match.group(1) if match else None


def validate_profile_layout(profile_dir: Path, settings: dict[str, str]) -> None:
    entries = {entry.name: entry for entry in profile_dir.iterdir()}
    missing = sorted(REQUIRED_FILES - entries.keys())
    if missing:
        fail(f"{profile_dir}: missing catalog files: {', '.join(missing)}")
    unknown = sorted(set(entries) - REQUIRED_FILES - OPTIONAL_ENTRIES)
    if unknown:
        fail(f"{profile_dir}: unsupported profile entries: {', '.join(unknown)}")
    for name in REQUIRED_FILES | {"source-build-targets"}:
        entry = entries.get(name)
        if entry is not None and (entry.is_symlink() or not entry.is_file()):
            fail(f"{entry}: must be a regular file")
    files_dir = entries.get("files")
    if files_dir is not None:
        if files_dir.is_symlink() or not files_dir.is_dir():
            fail(f"{files_dir}: must be a regular directory")
        for child in files_dir.rglob("*"):
            if child.is_symlink():
                fail(f"{child}: symlinks are not allowed in profile files/")
    targets = entries.get("source-build-targets")
    release_patched = settings.get("METHOD") == "source" and settings.get("BUILD_MODE") == "release-patched"
    if release_patched and targets is None:
        fail(f"{profile_dir}: release-patched requires source-build-targets")
    if not release_patched and targets is not None:
        fail(f"{profile_dir}: source-build-targets is only valid for release-patched")


def validate_version_contract(profile_dir: Path, settings: dict[str, str]) -> None:
    _, version, source = parse_profile_id(profile_dir.name)
    method = settings["METHOD"]

    if source == "release":
        if method == "imagebuilder":
            actual = release_from_url(settings["IMAGEBUILDER_URL"])
            if actual != version:
                fail(f"{profile_dir}: profile version {version} does not match ImageBuilder release {actual or 'unknown'}")
            return

        if settings["BUILD_MODE"] == "release-patched":
            actual = release_from_ref(settings.get("BASE_REF", ""))
            field = "BASE_REF"
        else:
            actual = release_from_ref(settings["REF"])
            field = "REF"
        if actual != version:
            fail(f"{profile_dir}: profile version {version} does not match {field} release {actual or 'unknown'}")
        sdk_url = settings.get("SDK_URL")
        if sdk_url:
            sdk_version = release_from_url(sdk_url)
            if sdk_version != version:
                fail(f"{profile_dir}: SDK_URL release {sdk_version or 'unknown'} does not match profile version {version}")
        return

    if source == "stable":
        if method != "source":
            fail(f"{profile_dir}: X.Y profiles must build from the moving stable source branch")
        if settings["BUILD_MODE"] == "release-patched":
            fail(f"{profile_dir}: X.Y profiles cannot use release-patched; use an exact X.Y.Z profile")
        match = STABLE_REF_RE.fullmatch(settings["REF"])
        actual = match.group(1) if match else None
        if actual != version:
            fail(f"{profile_dir}: profile stable line {version} does not match REF {settings['REF']}")
        if settings.get("SDK_URL"):
            fail(f"{profile_dir}: moving X.Y profiles cannot pin a point-release SDK_URL")
        return

    if method == "imagebuilder":
        if "/snapshots/" not in urlparse(settings["IMAGEBUILDER_URL"]).path:
            fail(f"{profile_dir}: snapshot ImageBuilder profiles must use a /snapshots/ URL")
    elif settings["REF"] != "main":
        fail(f"{profile_dir}: snapshot source profiles must use REF=main")


def validate_catalog(root: Path) -> list[str]:
    profiles_dir = root / "profiles"
    if profiles_dir.is_symlink() or not profiles_dir.is_dir():
        fail("profiles must be a regular directory")
    builder = load_builder(root)
    profiles: list[str] = []
    for entry in sorted(profiles_dir.iterdir()):
        if entry.name == "README.md":
            if entry.is_symlink() or not entry.is_file():
                fail("profiles/README.md must be a regular file")
            continue
        if entry.is_symlink() or not entry.is_dir():
            fail(f"{entry}: only versioned profile directories and README.md are allowed")
        parse_profile_id(entry.name)
        builder.validate_profile_dir(entry)
        settings = builder.parse_settings(entry / "settings")
        validate_profile_layout(entry, settings)
        builder.parse_feeds(entry / "feeds")
        builder.parse_git_packages(entry / "git-packages")
        validate_version_contract(entry, settings)
        profiles.append(entry.name)
    if not profiles:
        fail("at least one valid profile is required")
    return profiles


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        profiles = validate_catalog(args.root)
        print(f"Validated {len(profiles)} profiles: {', '.join(profiles)}")
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
