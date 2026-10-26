import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("openwrt_builder", ROOT / "scripts" / "build.py")
BUILDER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BUILDER)


class FeedDiscoveryTests(unittest.TestCase):
    def test_omitted_feed_names_uses_all_configured_feeds_for_selected_packages(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            profile = root / "profile"
            profile.mkdir()
            source_checkout = root / "example" / "openwrt"
            source_checkout.mkdir(parents=True)
            (source_checkout / "feeds.conf.default").write_text("", encoding="utf-8")
            (profile / "feeds").write_text(
                "src-git custom https://example.com/feed.git\\n", encoding="utf-8"
            )
            settings = {
                "BUILD_MODE": "selective-source",
                "REPOSITORY": "https://example.com/openwrt.git",
                "REF": "v1.2.3",
            }
            with (
                patch.object(BUILDER, "WORK_DIR", root),
                patch.object(BUILDER, "clone_ref"),
                patch.object(BUILDER, "configure_download_cache"),
                patch.object(BUILDER, "update_feeds") as update,
                patch.object(BUILDER, "install_feed_packages") as install,
                patch.object(BUILDER, "install_git_packages"),
            ):
                source, ref, feeds, base = BUILDER.prepare_source(
                    "example", profile, settings, None, ["example-package"], full=False
                )

            self.assertEqual((ref, feeds, base), ("v1.2.3", [], None))
            self.assertIn("src-git custom", (source / "feeds.conf.default").read_text())
            update.assert_called_once_with(source, [])
            install.assert_called_once_with(
                source, ["example-package"], [], full=False, feed_names=[]
            )


class DeviceKernelResolutionTests(unittest.TestCase):
    def test_parses_selected_device_kernel_from_install_target(self):
        database = """install: /tmp/build_dir/target-mips/linux-ath79_generic/tplink_archer-a9-v6-kernel.bin other-target
other: value
"""

        target = BUILDER.parse_device_kernel_target(database, "tplink_archer-a9-v6")

        self.assertEqual(
            target,
            Path("/tmp/build_dir/target-mips/linux-ath79_generic/tplink_archer-a9-v6-kernel.bin"),
        )

    def test_respects_custom_kernel_suffix(self):
        database = """install: /tmp/build_dir/target-aarch64/linux-example/vendor_device-fit-uImage.itb
"""

        target = BUILDER.parse_device_kernel_target(database, "vendor_device")

        self.assertEqual(
            target,
            Path("/tmp/build_dir/target-aarch64/linux-example/vendor_device-fit-uImage.itb"),
        )

    def test_fails_when_device_kernel_is_missing(self):
        with self.assertRaisesRegex(BUILDER.BuilderError, "found 0"):
            BUILDER.parse_device_kernel_target("install: unrelated-target\n", "tplink_archer-a9-v6")

    def test_fails_when_device_kernel_is_ambiguous(self):
        database = """install: /tmp/build_dir/x/tplink_archer-a9-v6-kernel.bin /tmp/build_dir/x/tplink_archer-a9-v6-kernel-debug.bin
"""

        with self.assertRaisesRegex(BUILDER.BuilderError, "found 2"):
            BUILDER.parse_device_kernel_target(database, "tplink_archer-a9-v6")

    def test_target_image_directory_prefers_feed_target(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        source = Path(temp.name)
        core = source / "target" / "linux" / "demo" / "image"
        feed = source / "target" / "linux" / "feeds" / "demo" / "image"
        core.mkdir(parents=True)
        feed.mkdir(parents=True)
        (core / "Makefile").write_text("", encoding="utf-8")
        (feed / "Makefile").write_text("", encoding="utf-8")

        resolved = BUILDER.target_image_directory(source, {"TARGET": "demo"})

        self.assertEqual(resolved, feed)

    def test_target_image_directory_falls_back_to_core_target(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        source = Path(temp.name)
        core = source / "target" / "linux" / "demo" / "image"
        core.mkdir(parents=True)
        (core / "Makefile").write_text("", encoding="utf-8")

        resolved = BUILDER.target_image_directory(source, {"TARGET": "demo"})

        self.assertEqual(resolved, core)

    def test_resolves_configured_linux_image_stamp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        kernel_target = root / "linux-demo" / "vendor_device-kernel.bin"
        linux_dir = kernel_target.parent / "linux-6.12.94"
        linux_dir.mkdir(parents=True)
        (linux_dir / ".config").write_text("CONFIG_TEST=y\n", encoding="utf-8")

        stamp = BUILDER.resolve_kernel_image_stamp(kernel_target)

        self.assertEqual(stamp, linux_dir / ".image")

    def test_builds_device_artifact_from_official_kernel_without_kernel_compile(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        source = Path(temp.name)
        image_dir = source / "target" / "linux" / "demo" / "image"
        image_dir.mkdir(parents=True)
        (image_dir / "Makefile").write_text("", encoding="utf-8")
        kernel_target = source / "build_dir" / "target-demo" / "linux-demo_generic" / "vendor_device-kernel.bin"
        linux_dir = kernel_target.parent / "linux-6.12.94"
        linux_dir.mkdir(parents=True)
        (linux_dir / ".config").write_text("CONFIG_TEST=y\n", encoding="utf-8")
        official_ib = source / "official"
        official_kernel = official_ib / "build_dir" / "target-demo" / "linux-demo_generic"
        official_linux = official_kernel / "linux-6.12.94"
        official_linux.joinpath("scripts", "dtc").mkdir(parents=True)
        (official_linux / "scripts" / "dtc" / "dtc").write_text("dtc", encoding="utf-8")
        (official_kernel / "vmlinux").write_text("official kernel", encoding="utf-8")
        (official_ib / "staging_dir" / "host" / "lib").mkdir(parents=True)
        database = SimpleNamespace(
            returncode=0,
            stdout=f"install: {kernel_target}\n",
            stderr="",
        )
        commands = []

        def fake_run(command, *, cwd=None, check=True):
            commands.append(list(command))
            if str(kernel_target) in command:
                kernel_target.parent.mkdir(parents=True, exist_ok=True)
                kernel_target.touch()
            return SimpleNamespace(returncode=0)

        with patch.object(BUILDER.subprocess, "run", return_value=database), patch.object(
            BUILDER, "run", side_effect=fake_run
        ):
            result = BUILDER.prepare_device_kernel_artifact(
                source,
                {"TARGET": "demo", "SUBTARGET": "generic", "DEVICE": "vendor_device"},
                1,
                official_ib=official_ib,
            )

        self.assertEqual(result, kernel_target)
        self.assertIn("target/linux/prepare", commands[0])
        self.assertIn("kernel_prepare", commands[1])
        self.assertIn(str(kernel_target), commands[2])
        self.assertEqual((kernel_target.parent / "vmlinux").read_text(encoding="utf-8"), "official kernel")
        self.assertFalse(any("target/linux/compile" in command for command in commands))
        self.assertFalse(any(".image" in " ".join(command) for command in commands))


if __name__ == "__main__":
    unittest.main()
