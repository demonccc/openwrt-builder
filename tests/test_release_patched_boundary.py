import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("openwrt_builder_boundary", ROOT / "scripts" / "build.py")
BUILDER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BUILDER)


class ReleasePatchedBoundaryTests(unittest.TestCase):
    def test_compile_without_dependencies_sets_no_deps(self):
        source = Path("/tmp/source")
        commands = []

        def fake_run(command, *, cwd=None, check=True):
            commands.append((list(command), cwd))
            return SimpleNamespace(returncode=0)

        with patch.object(BUILDER, "run", side_effect=fake_run):
            BUILDER.compile_without_dependencies(
                source,
                ["package/kernel/mac80211/compile", "package/kernel/linux/compile"],
                4,
            )

        self.assertEqual(len(commands), 1)
        command, cwd = commands[0]
        self.assertEqual(cwd, source)
        self.assertEqual(command[0], "make")
        self.assertIn("package/kernel/mac80211/compile", command)
        self.assertIn("package/kernel/linux/compile", command)
        self.assertIn("NO_DEPS=1", command)
        self.assertIn("-j4", command)

    def test_resolves_only_selected_packages_for_explicit_targets(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        source = Path(temp.name)
        (source / ".config").write_text(
            """CONFIG_PACKAGE_kmod-ath9k=y
CONFIG_PACKAGE_kmod-mac80211=y
CONFIG_PACKAGE_hostapd=n
CONFIG_PACKAGE_batctl-full=y
""",
            encoding="utf-8",
        )
        (source / "tmp").mkdir()
        (source / "tmp" / ".packageinfo").write_text(
            """Source-Makefile: package/kernel/mac80211/Makefile
Package: kmod-ath9k
Package: kmod-mac80211
Source-Makefile: package/network/services/hostapd/Makefile
Package: hostapd
Source-Makefile: package/feeds/routing/batman-adv/Makefile
Package: batctl-full
""",
            encoding="utf-8",
        )

        packages = BUILDER.resolve_selected_packages_for_targets(
            source,
            ["package/kernel/mac80211/compile"],
        )

        self.assertEqual(packages, ["kmod-ath9k", "kmod-mac80211"])

    def test_local_apk_copy_is_allowlisted(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        source = root / "source"
        imagebuilder = root / "imagebuilder"
        package_dir = source / "bin" / "targets" / "ath79" / "generic" / "packages"
        userspace_dir = source / "bin" / "packages" / "mips_24kc" / "base"
        package_dir.mkdir(parents=True)
        userspace_dir.mkdir(parents=True)
        imagebuilder.mkdir()

        for filename in (
            "kernel-6.12.94-r1.apk",
            "kmod-ath9k-6.12.94-r1.apk",
            "kmod-usb-storage-6.12.94-r1.apk",
        ):
            (package_dir / filename).write_text(filename, encoding="utf-8")
        for filename in (
            "base-files-1666-r1.apk",
            "hostapd-2026.01.01-r1.apk",
            "libubox-2026.01.01-r1.apk",
        ):
            (userspace_dir / filename).write_text(filename, encoding="utf-8")

        copied = BUILDER.copy_local_apks(
            source,
            imagebuilder,
            ["base-files", "kernel", "kmod-ath9k", "kmod-usb-storage"],
        )

        self.assertEqual(copied, ["base-files", "kernel", "kmod-ath9k", "kmod-usb-storage"])
        copied_names = sorted(path.name for path in (imagebuilder / "packages").glob("*.apk"))
        self.assertEqual(
            copied_names,
            [
                "base-files-1666-r1.apk",
                "kernel-6.12.94-r1.apk",
                "kmod-ath9k-6.12.94-r1.apk",
                "kmod-usb-storage-6.12.94-r1.apk",
            ],
        )
        self.assertFalse(any(name.startswith("hostapd-") for name in copied_names))
        self.assertFalse(any(name.startswith("libubox-") for name in copied_names))

    def test_local_apk_copy_fails_if_required_package_is_missing(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        source = root / "source"
        imagebuilder = root / "imagebuilder"
        source.mkdir()
        imagebuilder.mkdir()

        with self.assertRaisesRegex(BUILDER.BuilderError, "kmod-ath9k"):
            BUILDER.copy_local_apks(source, imagebuilder, ["kmod-ath9k"])

    def test_official_libc_seed_does_not_match_libc_utils(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        official_ib = root / "official"
        source = root / "source"
        (official_ib / "packages").mkdir(parents=True)
        (official_ib / "packages" / "libc-utils-1.0-r1.apk").write_text("utils", encoding="utf-8")
        (official_ib / "packages" / "libc-1.2.5-r4.apk").write_text("libc", encoding="utf-8")

        result = BUILDER.seed_official_imagebuilder_package(
            official_ib,
            source,
            {"TARGET": "ath79", "SUBTARGET": "generic"},
            "libc",
        )

        self.assertEqual(result.name, "libc-1.2.5-r4.apk")
        self.assertEqual(result.read_text(encoding="utf-8"), "libc")

    def test_kernel_modules_build_uses_modules_stamp_not_target_compile(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        source = Path(temp.name)
        image_dir = source / "target" / "linux" / "demo" / "image"
        image_dir.mkdir(parents=True)
        (image_dir / "Makefile").write_text("", encoding="utf-8")
        linux_dir = source / "build_dir" / "target-demo_musl" / "linux-demo_generic" / "linux-6.12.94"
        modules_stamp = linux_dir / ".modules"
        commands = []

        def fake_run(command, *, cwd=None, check=True):
            command = list(command)
            commands.append(command)
            if "target/linux/prepare" in command:
                linux_dir.mkdir(parents=True, exist_ok=True)
            if str(modules_stamp) in command:
                modules_stamp.touch()
            return SimpleNamespace(returncode=0)

        with patch.object(BUILDER, "run", side_effect=fake_run):
            result = BUILDER.compile_kernel_modules(
                source,
                {"TARGET": "demo", "SUBTARGET": "generic"},
                2,
            )

        self.assertEqual(result, modules_stamp)
        self.assertIn("target/linux/prepare", commands[0])
        self.assertIn("NO_DEPS=1", commands[0])
        self.assertIn(str(modules_stamp), commands[1])
        self.assertFalse(any("target/linux/compile" in command for command in commands))


        def test_resolves_only_external_kmod_prerequisites_for_explicit_roots(self):
            temp = tempfile.TemporaryDirectory()
            self.addCleanup(temp.cleanup)
            source = Path(temp.name)
            (source / ".config").write_text(
                """CONFIG_PACKAGE_kmod-ath9k=y
    CONFIG_PACKAGE_kmod-ath9k-common=y
    CONFIG_PACKAGE_kmod-ath=y
    CONFIG_PACKAGE_kmod-mac80211=y
    CONFIG_PACKAGE_kmod-random-core=y
    CONFIG_PACKAGE_kmod-usb-core=y
    """,
                encoding="utf-8",
            )
            (source / "tmp").mkdir()
            (source / "tmp" / ".packageinfo").write_text(
                """Source-Makefile: package/kernel/mac80211/Makefile
    Package: kmod-ath9k
    Depends: +kmod-ath9k-common
    Package: kmod-ath9k-common
    Depends: +kmod-ath +kmod-random-core
    Package: kmod-ath
    Depends: +kmod-mac80211
    Package: kmod-mac80211
    Source-Makefile: package/kernel/linux/Makefile
    Package: kmod-random-core
    Package: kmod-usb-core
    """,
                encoding="utf-8",
            )
            prerequisites = BUILDER.resolve_external_kmod_prerequisites(
                source,
                ["kmod-ath9k", "kmod-ath9k-common", "kmod-ath", "kmod-mac80211"],
                ["package/kernel/mac80211/compile"],
            )
            self.assertEqual(
                prerequisites,
                {"package/kernel/linux/compile": ["kmod-random-core"]},
            )

        def test_prerequisite_compile_disables_unrelated_selected_packages(self):
            temp = tempfile.TemporaryDirectory()
            self.addCleanup(temp.cleanup)
            source = Path(temp.name)
            (source / ".config").write_text(
                """CONFIG_PACKAGE_kmod-random-core=y
    CONFIG_PACKAGE_kmod-usb-core=y
    """,
                encoding="utf-8",
            )
            (source / "tmp").mkdir()
            (source / "tmp" / ".packageinfo").write_text(
                """Source-Makefile: package/kernel/linux/Makefile
    Package: kmod-random-core
    Package: kmod-usb-core
    """,
                encoding="utf-8",
            )
            commands = []

            def fake_run(command, *, cwd=None, check=True):
                commands.append((list(command), cwd))
                return SimpleNamespace(returncode=0)

            with patch.object(BUILDER, "run", side_effect=fake_run):
                BUILDER.compile_package_prerequisites(
                    source,
                    {"package/kernel/linux/compile": ["kmod-random-core"]},
                    4,
                )

            self.assertEqual(len(commands), 1)
            command, cwd = commands[0]
            self.assertEqual(cwd, source)
            self.assertIn("package/kernel/linux/compile", command)
            self.assertIn("CONFIG_PACKAGE_kmod-random-core=y", command)
            self.assertIn("CONFIG_PACKAGE_kmod-usb-core=n", command)
            self.assertIn("NO_DEPS=1", command)
            self.assertNotIn("package/feeds/routing/batman-adv/compile", command)


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


if __name__ == "__main__":
    unittest.main()
