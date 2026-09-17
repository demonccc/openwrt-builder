from pathlib import Path

device_path = Path('tests/test_build.py')
explicit_path = Path('tests/test_release_patched_explicit_boundary.py')

device = device_path.read_text(encoding='utf-8')
explicit = explicit_path.read_text(encoding='utf-8')

device = device.replace(
    '        self.assertIn("Kernel/Configure=$(KERNEL_MAKE) olddefconfig", commands[0])\n',
    '        self.assertNotIn("Kernel/Configure=$(KERNEL_MAKE) olddefconfig", commands[0])\n',
    1,
)
explicit = explicit.replace(
    '        self.assertIn(\'custom_packages = list(dict.fromkeys(["kernel", *explicit_packages]))\', source)\n',
    '        self.assertIn("package_build_root = sdk if sdk else source_dir", source)\n',
    1,
)

device_path.write_text(device, encoding='utf-8')
explicit_path.write_text(explicit, encoding='utf-8')
