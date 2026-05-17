# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Key Manager (Windows)."""

from __future__ import annotations

import os
from pathlib import Path

block_cipher = None
root = Path(SPECPATH).parent
version = os.environ.get("APP_VERSION", "0.0.0-dev")
app_name = f"KeyManager-{version}"
version_file = root / "build" / "file_version_info.txt"
icon_file = root / "assets" / "icon.ico"
assets = [(str(root / "assets" / "icon.png"), "assets")]

a = Analysis(
    [str(root / "main.py")],
    pathex=[str(root)],
    binaries=[],
    datas=assets,
    hiddenimports=[
        "ssh_config_gui",
        "ssh_config_gui.app",
        "ssh_config_gui.main_window",
        "ssh_config_gui.ssh_panel",
        "ssh_config_gui.aws_panel",
        "ssh_config_gui.aws_config_io",
        "ssh_config_gui.config_io",
        "ssh_config_gui.theme",
        "ssh_config_gui.tray_app",
        "ssh_config_gui.ssh_keys",
        "ssh_config_gui.ssh_askpass",
        "ssh_config_gui.terminal",
        "ssh_config_gui.ui_helpers",
        "ssh_config_gui.keygen_dialog",
        "ssh_config_gui.key_swap_dialog",
        "ssh_config_gui._version",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(version_file) if version_file.is_file() else None,
    icon=str(icon_file) if icon_file.is_file() else None,
)
