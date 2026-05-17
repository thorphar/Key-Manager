"""GUI / subprocess helper so OpenSSH can obtain passwords without a terminal."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

_PASSWORD_FILE_ENV = "SSH_ASKPASS_PASSWORD_FILE"
_ASKPASS_MARKER = "--ssh-askpass"


def is_askpass_subprocess(argv: list[str] | None = None) -> bool:
    return _ASKPASS_MARKER in (argv if argv is not None else sys.argv)


def run_askpass_subprocess() -> int:
    """Print password for SSH_ASKPASS (no newline). Called as a child process by ssh."""
    path = os.environ.get(_PASSWORD_FILE_ENV, "")
    if not path:
        return 1
    try:
        password = Path(path).read_text(encoding="utf-8")
    except OSError:
        return 1
    sys.stdout.write(password)
    sys.stdout.flush()
    return 0


def prompt_password_gui(parent, target: str) -> str | None:
    from PySide6.QtWidgets import QInputDialog, QLineEdit

    password, ok = QInputDialog.getText(
        parent,
        "SSH password",
        f"Enter the login password for:\n{target}",
        QLineEdit.EchoMode.Password,
    )
    if not ok:
        return None
    return password


def prompt_password_cli(target: str) -> str | None:
    try:
        import getpass

        return getpass.getpass(f"Password for {target}: ")
    except (EOFError, KeyboardInterrupt):
        return None


def _askpass_wrapper_script() -> Path:
    """Build a launcher script because SSH_ASKPASS must be a single executable path."""
    if getattr(sys, "frozen", False):
        command = f'"{sys.executable}" {_ASKPASS_MARKER}'
    else:
        command = f'"{sys.executable}" -m ssh_config_gui.ssh_askpass'

    fd, raw_path = tempfile.mkstemp(prefix="ssh_gui_askpass_", suffix=".cmd" if sys.platform == "win32" else ".sh")
    os.close(fd)
    path = Path(raw_path)
    if sys.platform == "win32":
        path.write_text(f"@echo off\r\n{command}\r\n", encoding="utf-8")
    else:
        path.write_text(f"#!/bin/sh\nexec {command}\n", encoding="utf-8")
        path.chmod(0o700)
    return path


def _auth_failure(stderr: str, stdout: str) -> bool:
    text = f"{stderr}\n{stdout}".lower()
    needles = (
        "permission denied",
        "authentication failed",
        "please try again",
        "password:",
        "no supported authentication methods",
    )
    return any(n in text for n in needles)


def _run_ssh(cmd: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    kwargs: dict = {
        "capture_output": True,
        "text": True,
        "stdin": subprocess.DEVNULL,
        "env": env,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.run(cmd, **kwargs)


def run_ssh_with_askpass(
    cmd: list[str],
    password: str,
) -> subprocess.CompletedProcess[str]:
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        delete=False,
        prefix="ssh_gui_pw_",
    ) as handle:
        handle.write(password)
        password_file = handle.name

    wrapper = _askpass_wrapper_script()
    env = os.environ.copy()
    env[_PASSWORD_FILE_ENV] = password_file
    env["SSH_ASKPASS"] = str(wrapper)
    env["SSH_ASKPASS_REQUIRE"] = "force"
    env.setdefault("DISPLAY", "1")

    try:
        return _run_ssh(cmd, env)
    finally:
        Path(password_file).unlink(missing_ok=True)
        wrapper.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(run_askpass_subprocess())
