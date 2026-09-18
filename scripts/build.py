#!/usr/bin/env python3
"""OpenWrt Builder CLI with the release-patched flow layered over the implementation.

release-patched follows the same boundary used by AudioWRT:
- compile explicitly patched package roots in the exact-release official SDK;
- keep unchanged runtime packages from the exact-release official repositories;
- assemble with the exact-release official ImageBuilder.

The only target-side work kept outside the SDK is creation of a per-device
kernel artifact when the custom checkout changes the DTS. That artifact reuses
the official release vmlinux and runs only the OpenWrt image/DTS pipeline; it
does not rebuild the kernel.
"""

from pathlib import Path
import shutil

_IMPL_PATH = Path(__file__).with_name("build_impl.py")
_ORIGINAL_NAME = __name__

# Execute the implementation in this module namespace so tests and monkeypatches
# continue to see the same globals/functions as before. Suppress its __main__
# block until the release-patched overrides below have been installed.
globals()["__name__"] = "openwrt_builder_impl"
exec(compile(_IMPL_PATH.read_text(encoding="utf-8"), str(_IMPL_PATH), "exec"), globals())
globals()["__name__"] = _ORIGINAL_NAME

