import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("openwrt_builder_output_paths", ROOT / "scripts" / "build.py")
BUILDER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BUILDER)


class OutputPathTests(unittest.TestCase):
    def test_build_resolves_relative_output_from_workspace(self):
        profile_dir = ROOT / "profiles" / "demo"

        with patch.object(BUILDER, "resolve_profile", return_value=profile_dir), patch.object(
            BUILDER, "validate_profile_dir"
        ), patch.object(
            BUILDER, "parse_settings", return_value={"METHOD": "imagebuilder"}
        ), patch.object(
            BUILDER, "build_imagebuilder"
        ) as imagebuilder:
            BUILDER.build("demo", None, Path("artifact"), 1)

        imagebuilder.assert_called_once_with(
            "demo",
            profile_dir,
            {"METHOD": "imagebuilder"},
            (BUILDER.ROOT / "artifact").resolve(),
        )


if __name__ == "__main__":
    unittest.main()
