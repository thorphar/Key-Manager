"""Read and write OpenSSH client config files (~/.ssh/config)."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

_HOST_RE = re.compile(r"^Host\s+(.+)$", re.IGNORECASE)
_MATCH_RE = re.compile(r"^Match\s+(.+)$", re.IGNORECASE)
_KV_RE = re.compile(r"^(\S+)(?:\s+(.*))?$")


@dataclass
class HostEntry:
    """One `Host` block and its indented options."""

    names: list[str]
    options: dict[str, list[str]] = field(default_factory=dict)

    @property
    def label(self) -> str:
        return self.names[0] if self.names else "(unnamed)"

    def get(self, key: str, default: str = "") -> str:
        values = self.options.get(key, [])
        return values[0] if values else default

    def set(self, key: str, value: str) -> None:
        value = value.strip()
        if value:
            self.options[key] = [value]
        elif key in self.options:
            del self.options[key]


@dataclass
class SshConfigFile:
    """Parsed config: preamble lines plus editable host blocks."""

    preamble: list[str] = field(default_factory=list)
    hosts: list[HostEntry] = field(default_factory=list)
    tail: list[str] = field(default_factory=list)


def default_config_path() -> Path:
    return Path.home() / ".ssh" / "config"


def _split_host_names(raw: str) -> list[str]:
    return [part for part in raw.split() if part and part != "*"]


def _parse_option_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    match = _KV_RE.match(stripped)
    if not match:
        return None
    key, value = match.group(1), (match.group(2) or "").strip()
    return key, value


def _canonical_key(key: str) -> str:
    aliases = {
        "hostname": "HostName",
        "user": "User",
        "port": "Port",
        "identityfile": "IdentityFile",
        "identitiesonly": "IdentitiesOnly",
        "proxyjump": "ProxyJump",
        "forwardagent": "ForwardAgent",
    }
    lower = key.lower()
    return aliases.get(lower, key if key[:1].isupper() else key.capitalize())


def load_config(path: Path | None = None) -> SshConfigFile:
    path = path or default_config_path()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        return SshConfigFile()

    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    result = SshConfigFile()
    preamble: list[str] = []
    current: HostEntry | None = None
    in_host = False
    tail_started = False

    for line in lines:
        host_match = _HOST_RE.match(line.strip())
        match_match = _MATCH_RE.match(line.strip())

        if host_match:
            if current is not None:
                result.hosts.append(current)
            elif preamble and not tail_started:
                result.preamble = preamble
                preamble = []
            current = HostEntry(names=_split_host_names(host_match.group(1)))
            in_host = True
            tail_started = False
            continue

        if match_match:
            if current is not None:
                result.hosts.append(current)
                current = None
            if in_host or result.hosts:
                tail_started = True
                result.tail.append(line)
            else:
                preamble.append(line)
            in_host = False
            continue

        if current is not None:
            parsed = _parse_option_line(line)
            if parsed:
                key, value = parsed
                canon = _canonical_key(key)
                current.options.setdefault(canon, []).append(value)
            continue

        if tail_started or result.hosts:
            result.tail.append(line)
        else:
            preamble.append(line)

    if current is not None:
        result.hosts.append(current)
    elif preamble and not result.preamble:
        result.preamble = preamble

    return result


def _format_option(key: str, value: str) -> str:
    if " " in value and not (value.startswith('"') and value.endswith('"')):
        return f'    {key} "{value}"'
    return f"    {key} {value}"


def format_config(config: SshConfigFile) -> str:
    parts: list[str] = []

    if config.preamble:
        parts.extend(config.preamble)

    for index, host in enumerate(config.hosts):
        if parts and parts[-1].strip():
            parts.append("")
        names = " ".join(host.names) if host.names else "unnamed"
        parts.append(f"Host {names}")
        preferred_order = [
            "HostName",
            "User",
            "Port",
            "IdentityFile",
            "IdentitiesOnly",
            "ProxyJump",
            "ForwardAgent",
        ]
        written: set[str] = set()
        for key in preferred_order:
            if key in host.options:
                for value in host.options[key]:
                    parts.append(_format_option(key, value))
                written.add(key)
        for key in sorted(host.options):
            if key in written:
                continue
            for value in host.options[key]:
                parts.append(_format_option(key, value))

    if config.tail:
        if parts and parts[-1].strip():
            parts.append("")
        parts.extend(config.tail)

    body = "\n".join(parts)
    return body + ("\n" if body else "")


def save_config(config: SshConfigFile, path: Path | None = None, *, backup: bool = True) -> Path:
    path = path or default_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if backup and path.exists() and path.stat().st_size > 0:
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
    path.write_text(format_config(config), encoding="utf-8")
    return path
