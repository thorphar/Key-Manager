#!/usr/bin/env python3
"""Generate assets/icon.ico from assets/icon.png (Windows exe/installer icons)."""

from __future__ import annotations

import struct
import sys
from pathlib import Path

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent.parent
PNG = ROOT / "assets" / "icon.png"
ICO = ROOT / "assets" / "icon.ico"
SIZES = (16, 24, 32, 48, 64, 128, 256)


def _png_bytes(pixmap: QPixmap) -> bytes:
    image = pixmap.toImage()
    buffer = QByteArray()
    io = QBuffer(buffer)
    io.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(io, "PNG"):
        raise RuntimeError("Failed to encode PNG for icon")
    return bytes(buffer.data())


def _write_ico(entries: list[tuple[int, bytes]], dest: Path) -> None:
    count = len(entries)
    header_size = 6 + 16 * count
    offset = header_size
    parts: list[bytes] = []
    directory: list[bytes] = []

    for size, png in entries:
        width_byte = size if size < 256 else 0
        directory.append(
            struct.pack(
                "<BBBBHHII",
                width_byte,
                width_byte,
                0,
                0,
                1,
                32,
                len(png),
                offset,
            )
        )
        parts.append(png)
        offset += len(png)

    with dest.open("wb") as file:
        file.write(struct.pack("<HHH", 0, 1, count))
        for entry in directory:
            file.write(entry)
        for part in parts:
            file.write(part)


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)

    if not PNG.is_file():
        print(f"Missing source image: {PNG}", file=sys.stderr)
        return 1

    source = QPixmap(str(PNG))
    if source.isNull():
        print(f"Could not load image: {PNG}", file=sys.stderr)
        return 1

    entries: list[tuple[int, bytes]] = []
    for size in SIZES:
        scaled = source.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        entries.append((size, _png_bytes(scaled)))

    _write_ico(entries, ICO)
    print(f"Wrote {ICO}")
    app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
