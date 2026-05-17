"""SSH key pair discovery, generation, and authorized_keys deployment."""

from __future__ import annotations

import os
import shlex
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ssh_config_gui.ssh_askpass import _auth_failure, _run_ssh, run_ssh_with_askpass


@dataclass(frozen=True)
class KeyPair:
    name: str
    private: Path
    public: Path

    @property
    def label(self) -> str:
        return self.name


@dataclass(frozen=True)
class SshTarget:
    hostname: str
    user: str
    port: int | None = None
    proxy_jump: str | None = None

    @property
    def label(self) -> str:
        return f"{self.user}@{self.hostname}"


def default_ssh_dir() -> Path:
    return Path.home() / ".ssh"


def list_key_pairs(ssh_dir: Path | None = None) -> list[KeyPair]:
    directory = ssh_dir or default_ssh_dir()
    if not directory.is_dir():
        return []

    pairs: list[KeyPair] = []
    for public in sorted(directory.glob("*.pub")):
        private = public.with_suffix("")
        if private.is_file():
            pairs.append(KeyPair(name=private.name, private=private, public=public))
    return pairs


def find_key_pair(private_path: Path | str, ssh_dir: Path | None = None) -> KeyPair | None:
    private = Path(private_path).expanduser()
    for pair in list_key_pairs(ssh_dir):
        if pair.private.resolve() == private.resolve():
            return pair
    if private.is_file() and private.suffix != ".pub":
        public = Path(str(private) + ".pub")
        if public.is_file():
            return KeyPair(name=private.name, private=private, public=public)
    return None


def read_public_key(public_key: Path) -> str:
    pubkey = public_key.expanduser().read_text(encoding="utf-8").strip()
    if not pubkey:
        raise ValueError(f"Public key file is empty: {public_key}")
    return pubkey


def generate_key_pair(
    name: str,
    *,
    key_type: str = "ed25519",
    comment: str = "",
    passphrase: str = "",
    ssh_dir: Path | None = None,
    force: bool = False,
) -> KeyPair:
    directory = ssh_dir or default_ssh_dir()
    directory.mkdir(parents=True, exist_ok=True)

    safe_name = name.strip()
    if not safe_name or "/" in safe_name or "\\" in safe_name:
        raise ValueError("Key name must be a simple filename (no path separators).")

    private = directory / safe_name
    public = Path(str(private) + ".pub")
    if private.exists() or public.exists():
        if not force:
            raise FileExistsError(f"Key already exists: {private}")
        private.unlink(missing_ok=True)
        public.unlink(missing_ok=True)

    cmd = ["ssh-keygen", "-f", str(private), "-C", comment or f"{safe_name} key", "-N", passphrase]
    if key_type == "rsa":
        cmd[1:1] = ["-t", "rsa", "-b", "4096"]
    else:
        cmd[1:1] = ["-t", key_type]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ssh-keygen failed")

    if not private.is_file() or not public.is_file():
        raise RuntimeError("ssh-keygen finished but key files were not created")

    return KeyPair(name=private.name, private=private, public=public)


def _build_ssh_args(
    *,
    port: int | None = None,
    identity_file: Path | None = None,
    proxy_jump: str | None = None,
    batch_mode: bool = False,
) -> list[str]:
    args = ["ssh", "-o", "StrictHostKeyChecking=accept-new"]
    if batch_mode:
        args.append("-o")
        args.append("BatchMode=yes")
    if port and port > 0:
        args.extend(["-p", str(port)])
    if identity_file and identity_file.is_file():
        args.extend(["-i", str(identity_file)])
    if proxy_jump:
        args.extend(["-J", proxy_jump.strip()])
    return args


def _validate_target(target: SshTarget) -> str:
    host = target.hostname.strip()
    username = target.user.strip()
    if not host:
        raise ValueError("HostName is required.")
    if not username:
        raise ValueError("User is required.")
    return f"{username}@{host}"


def run_remote_command(
    remote_shell: str,
    target: SshTarget,
    *,
    login_identity: Path | None = None,
    password: str | None = None,
    password_prompt: Callable[[str], str | None] | None = None,
) -> None:
    """Run a remote shell command over SSH, with key-then-password authentication."""
    ssh_target = _validate_target(target)
    cmd = _build_ssh_args(
        port=target.port,
        identity_file=login_identity,
        proxy_jump=target.proxy_jump,
        batch_mode=False,
    ) + [ssh_target, remote_shell]

    env = os.environ.copy()
    key_only_cmd = _build_ssh_args(
        port=target.port,
        identity_file=login_identity,
        proxy_jump=target.proxy_jump,
        batch_mode=True,
    ) + [ssh_target, remote_shell]

    result = _run_ssh(key_only_cmd, env)
    if result.returncode == 0:
        return

    if not _auth_failure(result.stderr, result.stdout):
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(detail or f"ssh exited with code {result.returncode}")

    if password is None and password_prompt is not None:
        password = password_prompt(ssh_target)
    if not password:
        raise RuntimeError("SSH authentication failed. Password is required.")

    result = run_ssh_with_askpass(cmd, password)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(detail or f"ssh exited with code {result.returncode}")


def apply_public_key(
    public_key: Path,
    *,
    hostname: str,
    user: str,
    port: int | None = None,
    login_identity: Path | None = None,
    proxy_jump: str | None = None,
    password: str | None = None,
    password_prompt: Callable[[str], str | None] | None = None,
) -> str:
    """Append *public_key* to the remote user's authorized_keys (idempotent)."""
    target = SshTarget(hostname=hostname, user=user, port=port, proxy_jump=proxy_jump)
    ssh_target = _validate_target(target)
    pubkey = read_public_key(public_key)
    remote_shell = (
        "umask 077; "
        "mkdir -p ~/.ssh; "
        "chmod 700 ~/.ssh; "
        "touch ~/.ssh/authorized_keys; "
        "chmod 600 ~/.ssh/authorized_keys; "
        f"grep -qxF {shlex.quote(pubkey)} ~/.ssh/authorized_keys "
        f"|| echo {shlex.quote(pubkey)} >> ~/.ssh/authorized_keys"
    )
    run_remote_command(
        remote_shell,
        target,
        login_identity=login_identity,
        password=password,
        password_prompt=password_prompt,
    )
    return f"Public key installed on {ssh_target}"


def remove_public_key(
    public_key: Path,
    target: SshTarget,
    *,
    login_identity: Path | None = None,
    password: str | None = None,
    password_prompt: Callable[[str], str | None] | None = None,
) -> None:
    """Remove *public_key* from the remote authorized_keys file if present."""
    pubkey = read_public_key(public_key)
    remote_shell = (
        "umask 077; "
        "test -f ~/.ssh/authorized_keys || exit 0; "
        f"grep -vxF {shlex.quote(pubkey)} ~/.ssh/authorized_keys > ~/.ssh/authorized_keys.tmp "
        "&& mv ~/.ssh/authorized_keys.tmp ~/.ssh/authorized_keys; "
        "chmod 600 ~/.ssh/authorized_keys"
    )
    run_remote_command(
        remote_shell,
        target,
        login_identity=login_identity,
        password=password,
        password_prompt=password_prompt,
    )


def verify_key_login(
    target: SshTarget,
    *,
    identity_file: Path,
) -> None:
    """Confirm that *identity_file* can authenticate to *target* (BatchMode)."""
    ssh_target = _validate_target(target)
    remote_shell = "echo key-swap-ok"
    cmd = _build_ssh_args(
        port=target.port,
        identity_file=identity_file,
        proxy_jump=target.proxy_jump,
        batch_mode=True,
    ) + [ssh_target, remote_shell]
    result = _run_ssh(cmd, os.environ.copy())
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(detail or "Login check with the new key failed")


def swap_host_keys(
    *,
    target: SshTarget,
    new_key: KeyPair,
    old_key: KeyPair | None,
    login_identity: Path | None = None,
    remove_old_from_server: bool = True,
    verify_new_key: bool = True,
    password: str | None = None,
    password_prompt: Callable[[str], str | None] | None = None,
) -> str:
    """Install *new_key* on the server, optionally remove *old_key*, verify login."""
    if old_key and old_key.public.resolve() == new_key.public.resolve():
        raise ValueError("Old and new keys must be different.")

    ssh_target = _validate_target(target)
    connect_key = login_identity
    if connect_key is None and old_key is not None:
        connect_key = old_key.private
    if connect_key is None:
        connect_key = new_key.private

    # 1. Add new key while old login still works.
    apply_public_key(
        new_key.public,
        hostname=target.hostname,
        user=target.user,
        port=target.port,
        proxy_jump=target.proxy_jump,
        login_identity=connect_key,
        password=password,
        password_prompt=password_prompt,
    )

    # 2. Remove old key from server.
    if remove_old_from_server and old_key is not None:
        remove_public_key(
            old_key.public,
            target,
            login_identity=connect_key,
            password=password,
            password_prompt=None,
        )

    # 3. Verify new key works before updating local config.
    if verify_new_key:
        verify_key_login(target, identity_file=new_key.private)

    parts = [f"Swapped keys on {ssh_target}: now using {new_key.name}"]
    if remove_old_from_server and old_key is not None:
        parts.append(f"removed {old_key.name} from authorized_keys")
    return ". ".join(parts)
