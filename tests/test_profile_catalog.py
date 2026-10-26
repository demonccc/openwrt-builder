import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("profile_catalog", ROOT / "scripts" / "validate-profile-catalog.py")
CATALOG = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(CATALOG)


class ProfileCatalogTests(unittest.TestCase):
    def test_versioned_profile_id_forms(self):
        self.assertEqual(CATALOG.parse_profile_id("tplink-archer_a9_v6-25.12.5"), ("archer-a9-v6", "25.12.5", "release"))
        self.assertEqual(CATALOG.parse_profile_id("tplink-archer_a9_v6-25.12"), ("archer-a9-v6", "25.12", "stable"))
        self.assertEqual(CATALOG.parse_profile_id("generic-x86_64-snapshot"), ("x86-64", "snapshot", "snapshot"))

    def test_rejects_profile_without_version(self):
        with self.assertRaisesRegex(ValueError, "X.Y.Z"):
            CATALOG.parse_profile_id("archer-a9-v6")

    def test_rejects_legacy_device_only_name(self):
        with self.assertRaisesRegex(ValueError, "vendor"):
            CATALOG.parse_profile_id("archer-a9-v6-25.12.5")

    def test_current_catalog_is_valid(self):
        catalog = CATALOG.validate_catalog(ROOT)
        self.assertTrue(catalog)
        self.assertEqual(catalog, sorted(catalog))


if __name__ == "__main__":
    unittest.main()
