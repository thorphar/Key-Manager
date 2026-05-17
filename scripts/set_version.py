#!/usr/bin/env python3
"""Write version metadata for builds.

Usage:
  python scripts/set_version.py 1.2.3
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _parse_version(raw: str) -> tuple[int, int, int, int]:
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?", raw.strip())
    if not match:
        raise SystemExit(f"Invalid version {raw!r}. Expected format like 1.2.3 or v1.2.3")
    major, minor, patch = (int(match.group(i)) for i in range(1, 4))
    return major, minor, patch, 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("Usage: python scripts/set_version.py <version>", file=sys.stderr)
        return 2

    version = args[0].lstrip("v")
    major, minor, patch, build = _parse_version(version)
    version_tuple = f"{major}.{minor}.{patch}"

    (ROOT / "ssh_config_gui" / "_version.py").write_text(
        f'"""Application version."""\n\n__version__ = "{version_tuple}"\n',
        encoding="utf-8",
    )

    file_version = f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {patch}, {build}),
    prodvers=({major}, {minor}, {patch}, {build}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [StringStruct('CompanyName', 'Key Manager'),
        StringStruct('FileDescription', 'Key Manager'),
        StringStruct('FileVersion', '{version_tuple}'),
        StringStruct('InternalName', 'KeyManager'),
        StringStruct('LegalCopyright', ''),
        StringStruct('OriginalFilename', 'KeyManager-{version_tuple}.exe'),
        StringStruct('ProductName', 'Key Manager'),
        StringStruct('ProductVersion', '{version_tuple}')]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""

    build_dir = ROOT / "build"
    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "file_version_info.txt").write_text(file_version, encoding="utf-8")
    (build_dir / "version.txt").write_text(version_tuple + "\n", encoding="utf-8")

    print(f"Version set to {version_tuple}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
