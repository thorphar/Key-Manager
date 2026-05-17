#!/usr/bin/env python3
"""Create a gzip tarball of the Linux PyInstaller binary."""

from __future__ import annotations

import os
import stat
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    version = os.environ.get("APP_VERSION")
    if not version:
        print("APP_VERSION environment variable is required", file=sys.stderr)
        return 1

    binary = ROOT / "dist" / f"KeyManager-{version}"
    if not binary.is_file():
        print(f"Missing binary: {binary}", file=sys.stderr)
        return 1

    archive = ROOT / "dist" / f"KeyManager-{version}-linux-x64.tar.gz"

    def _ensure_executable(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo:
        if tarinfo.name == binary.name:
            tarinfo.mode |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        return tarinfo

    with tarfile.open(archive, "w:gz") as tar:
        tar.add(binary, arcname=binary.name, filter=_ensure_executable)

    print(f"Wrote {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
