from pathlib import Path
from textwrap import dedent

build_path = Path("scripts/build.py")
tests_path = Path("tests/test_release_patched_boundary.py")
build = build_path.read_text(encoding="utf-8")
tests = tests_path.read_text(encoding="utf-8")

anchor = "def copy_local_apks(source_dir, imagebuilder_dir, allowed_packages):\n"
helper = dedent('''
def seed_official_imagebuilder_keys(official_ib, source_dir, settings):
    source = official_ib / "keys"
    if not source.is_dir():
        raise BuilderError("Official base ImageBuilder does not contain APK signing keys")
    target_roots = [
        root
        for root in source_dir.glob("staging_dir/target-*/root-*")
        if root.name == f"root-{settings['TARGET']}"
    ]
    if len(target_roots) != 1:
        raise BuilderError(
            f"Expected one staging root for target {settings['TARGET']}, found {len(target_roots)}"
        )
    destination = target_roots[0] / "etc" / "apk" / "keys"
    destination.mkdir(parents=True, exist_ok=True)
    copied = 0
    for key in source.iterdir():
        if key.is_file():
            shutil.copy2(key, destination / key.name)
            copied += 1
    if copied == 0:
        raise BuilderError("Official base ImageBuilder APK signing keys are empty")
    return destination


''').lstrip()
if "def seed_official_imagebuilder_keys(" not in build:
    build = build.replace(anchor, helper + anchor, 1)

old = '''    official_libc = seed_official_imagebuilder_package(
        official_ib, source_dir, settings, "libc"
    )

    device_kernel = prepare_device_kernel_artifact(source_dir, settings, jobs)
'''
new = '''    official_libc = seed_official_imagebuilder_package(
        official_ib, source_dir, settings, "libc"
    )
    official_keys = seed_official_imagebuilder_keys(
        official_ib, source_dir, settings
    )

    device_kernel = prepare_device_kernel_artifact(source_dir, settings, jobs)
'''
if old not in build:
    raise SystemExit("Could not find official package seeding block")
build = build.replace(old, new, 1)

old = '''        f"OFFICIAL_LIBC_APK={official_libc.name}",
        f"INCLUDE_PACKAGES={' '.join(include)}",
'''
new = '''        f"OFFICIAL_LIBC_APK={official_libc.name}",
        f"OFFICIAL_APK_KEYS={official_keys}",
        f"INCLUDE_PACKAGES={' '.join(include)}",
'''
if old not in build:
    raise SystemExit("Could not find BUILD_INFO keys insertion point")
build = build.replace(old, new, 1)

test_anchor = '\n\nif __name__ == "__main__":\n'
test_method = dedent('''
    def test_seeds_official_apk_keys_into_target_staging_root(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        official_ib = root / "official"
        source = root / "source"
        (official_ib / "keys").mkdir(parents=True)
        (official_ib / "keys" / "openwrt-key.pem").write_text("key", encoding="utf-8")
        staging = source / "staging_dir" / "target-mips_24kc_musl" / "root-ath79"
        staging.mkdir(parents=True)

        result = BUILDER.seed_official_imagebuilder_keys(
            official_ib,
            source,
            {"TARGET": "ath79"},
        )

        self.assertEqual(result, staging / "etc" / "apk" / "keys")
        self.assertEqual(
            (result / "openwrt-key.pem").read_text(encoding="utf-8"),
            "key",
        )
''').rstrip() + "\n"
test_method = "\n".join("    " + line if line else "" for line in test_method.splitlines()) + "\n"
if "test_seeds_official_apk_keys_into_target_staging_root" not in tests:
    tests = tests.replace(test_anchor, "\n" + test_method + test_anchor, 1)

build_path.write_text(build, encoding="utf-8")
tests_path.write_text(tests, encoding="utf-8")
