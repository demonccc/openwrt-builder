import importlib.util
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("openwrt_builder_explicit_boundary", ROOT / "scripts" / "build.py")
BUILDER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BUILDER)


class ReleasePatchedExplicitBoundaryTests(unittest.TestCase):
    def test_release_patched_uses_official_sdk_and_imagebuilder(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        source, sdk, official_ib = (root / name for name in ("source", "sdk", "imagebuilder"))
        profile = root / "profile"
        device_kernel = source / "build_dir" / "target-demo" / "linux-demo" / "device-kernel.bin"
        injected_kernel = official_ib / "build_dir" / "target-demo" / "linux-demo" / device_kernel.name
        settings = {"BASE_REF": "v1.2.3", "DEVICE": "device"}
        declared_target = "package/kernel/radio/compile"
        package = "kmod-radio"
        with ExitStack() as stack:
            def stub(name, **kwargs):
                return stack.enter_context(patch.object(BUILDER, name, **kwargs))

            stub("parse_packages", return_value=(["base-files", package], []))
            stub("parse_simple_list", return_value=[declared_target])
            stub("prepare_source", return_value=(source, "patch-ref", [], "base-commit"))
            feed_install = stub("install_feed_packages")
            stub("prepare_sdk", return_value=(sdk, "sdk-url", "auto"))
            stub("copy_files", return_value=False)
            stub("write_config")
            run = stub("run")
            stub("resolve_selected_packages_for_targets", return_value=[package])
            stub("install_sdk_state")
            stub("download_sources")
            sdk_targets = stub("prepare_sdk_source_targets", return_value=([declared_target], [declared_target]))
            sdk_compile = stub("compile_sdk_source_targets")
            stub("prepare_official_base_imagebuilder", return_value=official_ib)
            copied_apks = stub("copy_local_apks", return_value=[package])
            stub("prepare_device_kernel_artifact", return_value=device_kernel)
            inject_kernel = stub("inject_device_kernel_into_official_imagebuilder", return_value=injected_kernel)
            stub("prepare_output")
            write_info = stub("write_info")
            generated = stub("generated_imagebuilder")
            compile_source = stub("compile_without_dependencies")

            BUILDER.build_release_patched("sample", profile, settings, None, root / "out", 2)

        sdk_targets.assert_called_once_with(source, sdk, [declared_target], [package])
        feed_install.assert_called_once_with(
            source, ["base-files", package], [], full=False, feed_names=[]
        )
        sdk_compile.assert_called_once_with(sdk, [declared_target], 2)
        copied_apks.assert_called_once_with(sdk, official_ib, [package])
        inject_kernel.assert_called_once_with(device_kernel, source, official_ib)
        self.assertEqual(run.call_args_list[-1].kwargs["cwd"], official_ib)
        self.assertEqual(run.call_args_list[-1].args[0][:2], ["make", "image"])
        generated.assert_not_called()
        compile_source.assert_not_called()
        info = write_info.call_args.args[1]
        self.assertIn("IMAGE_ASSEMBLY_ENV=official-imagebuilder", info)
        self.assertIn(f"CUSTOM_APK_PACKAGES={package}", info)


if __name__ == "__main__":
    unittest.main()
