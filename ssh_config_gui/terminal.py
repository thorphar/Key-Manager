"""Open the system default terminal with an SSH session to a host."""

from __future__ import annotations

import shlex
import shutil
import subprocess
import sys
from pathlib import Path


def _default_ssh_config() -> Path:
    return Path.home() / ".ssh" / "config"


def build_ssh_command(host_alias: str, config_path: Path) -> list[str]:
    cmd = ["ssh"]
    try:
        use_custom = config_path.expanduser().resolve() != _default_ssh_config().resolve()
    except OSError:
        use_custom = True
    if use_custom:
        cmd.extend(["-F", str(config_path.expanduser())])
    cmd.append(host_alias)
    return cmd


def open_ssh_in_terminal(host_alias: str, config_path: Path) -> None:
    """Launch *host_alias* in a new terminal window using the system SSH client."""
    alias = host_alias.strip()
    if not alias:
        raise ValueError("Host alias is required.")

    ssh_cmd = build_ssh_command(alias, config_path)

    if sys.platform == "win32":
        _open_windows_terminal(ssh_cmd, alias)
        return
    if sys.platform == "darwin":
        _open_macos_terminal(ssh_cmd)
        return
    _open_unix_terminal(ssh_cmd)


def _open_windows_terminal(ssh_cmd: list[str], title: str) -> None:
    wt = shutil.which("wt") or shutil.which("wt.exe")
    if wt:
        subprocess.Popen([wt, "-w", "0", "new-tab", "--title", title, *ssh_cmd])
        return

    subprocess.Popen(
        ssh_cmd,
        creationflags=subprocess.CREATE_NEW_CONSOLE,  # type: ignore[attr-defined]
    )


def _open_macos_terminal(ssh_cmd: list[str]) -> None:
    command = " ".join(shlex.quote(part) for part in ssh_cmd)
    script = f'tell application "Terminal" to do script "{command}"'
    subprocess.Popen(["osascript", "-e", script])


def _open_unix_terminal(ssh_cmd: list[str]) -> None:
    ssh_line = " ".join(shlex.quote(part) for part in ssh_cmd)

    if shutil.which("xdg-terminal-exec"):
        subprocess.Popen(["xdg-terminal-exec", *ssh_cmd])
        return

    if shutil.which("gnome-terminal"):
        subprocess.Popen(["gnome-terminal", "--", *ssh_cmd])
        return

    if shutil.which("konsole"):
        subprocess.Popen(["konsole", "-e", *ssh_cmd])
        return

    if shutil.which("xterm"):
        subprocess.Popen(["xterm", "-e", *ssh_cmd])
        return

    raise RuntimeError("No supported terminal emulator found on this system.")
