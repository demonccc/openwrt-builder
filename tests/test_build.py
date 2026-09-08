import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("openwrt_builder", ROOT / "scripts" / "build.py")
BUILDER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BUILDER)


class KernelTargetResolutionTests(unittest.TestCase):
    def make_source(self, config, packageinfo):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / ".config").write_text(config, encoding="utf-8")
        (root / "tmp").mkdir()
        (root / "tmp" / ".packageinfo").write_text(packageinfo, encoding="utf-8")
        return temp, root

    def test_resolves_selected_kmods_to_unique_source_targets(self):
        temp, source = self.make_source(
            """CONFIG_PACKAGE_iptables-nft=y
CONFIG_PACKAGE_kmod-ath9k=y
CONFIG_PACKAGE_kmod-ath10k=y
CONFIG_PACKAGE_kmod-usb-core=y
CONFIG_PACKAGE_kmod-batman-adv=y
CONFIG_PACKAGE_kmod-ath10k-ct=n
""",
            """Source-Makefile: package/kernel/mac80211/Makefile
Package: kmod-ath9k
Package: kmod-ath10k
Source-Makefile: package/kernel/linux/Makefile
Package: kmod-usb-core
Source-Makefile: package/feeds/routing/batman-adv/Makefile
Package: kmod-batman-adv
""",
        )
        self.addCleanup(temp.cleanup)

        packages, targets = BUILDER.resolve_kernel_build_targets(source)

        self.assertEqual(
            packages,
            ["kmod-ath9k", "kmod-ath10k", "kmod-usb-core", "kmod-batman-adv"],
        )
        self.assertEqual(
            targets,
            [
                "package/kernel/mac80211/compile",
                "package/kernel/linux/compile",
                "package/feeds/routing/batman-adv/compile",
            ],
        )

    def test_fails_when_selected_kmod_has_no_source_mapping(self):
        temp, source = self.make_source(
            "CONFIG_PACKAGE_kmod-missing=y\n",
            """Source-Makefile: package/kernel/linux/Makefile
Package: kmod-usb-core
""",
        )
        self.addCleanup(temp.cleanup)

        with self.assertRaisesRegex(BUILDER.BuilderError, "kmod-missing"):
            BUILDER.resolve_kernel_build_targets(source)


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


if __name__ == "__main__":
    unittest.main()
