import importlib.util
import inspect
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("openwrt_builder_explicit_boundary", ROOT / "scripts" / "build.py")
BUILDER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BUILDER)


class ReleasePatchedExplicitBoundaryTests(unittest.TestCase):
    def test_release_patched_does_not_expand_all_selected_kmods(self):
        source = inspect.getsource(BUILDER.build_release_patched)
        self.assertNotIn("resolve_kernel_build_targets", source)
        self.assertNotIn("kernel_targets", source)
        self.assertIn("resolve_selected_packages_for_targets", source)

    def test_release_patched_does_not_compile_base_files(self):
        source = inspect.getsource(BUILDER.build_release_patched)
        self.assertNotIn('package/base-files/compile', source)
        self.assertIn('seed_official_imagebuilder_package', source)
        self.assertIn('"base-files"', source)

    def test_release_patched_compiles_only_declared_package_roots(self):
        source = inspect.getsource(BUILDER.build_release_patched)
        self.assertNotIn("CONFIG_ALL_KMODS=y", source)
        self.assertIn("compile_without_dependencies(source_dir, targets, jobs)", source)
        self.assertIn("official_ib=official_ib", source)
        self.assertIn("package_build_root = sdk if sdk else source_dir", source)

    def test_release_patched_never_names_unrelated_package_targets(self):
        source = inspect.getsource(BUILDER.build_release_patched)
        self.assertNotIn("batman-adv/compile", source)
        self.assertNotIn("gpio-button-hotplug/compile", source)
        self.assertNotIn("package/kernel/linux/compile", source)

    def test_sdk_source_compile_keeps_dependencies_enabled(self):
        source = inspect.getsource(BUILDER.compile_sdk_source_targets)
        self.assertNotIn("NO_DEPS=1", source)
        self.assertIn("source_target_root", source)

    def test_release_patched_uses_sdk_for_explicit_packages(self):
        source = inspect.getsource(BUILDER.build_release_patched)
        self.assertIn("prepare_sdk_source_targets", source)
        self.assertIn("compile_sdk_source_targets", source)
        self.assertIn("package_build_root = sdk if sdk else source_dir", source)
        self.assertIn('["base-files", "libc", "kernel"]', source)



if __name__ == "__main__":
    unittest.main()
