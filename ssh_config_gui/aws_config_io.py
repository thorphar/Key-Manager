"""Read and write AWS CLI config and credentials INI files."""

from __future__ import annotations

import shutil
from configparser import ConfigParser, RawConfigParser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

AwsFileKind = Literal["config", "credentials"]

# Keys surfaced in the GUI (remaining keys are preserved per profile).
CONFIG_KNOWN_KEYS = (
    "region",
    "output",
    "role_arn",
    "source_profile",
    "mfa_serial",
    "external_id",
    "sso_start_url",
    "sso_region",
    "sso_account_id",
    "sso_role_name",
    "credential_process",
)

CREDENTIALS_KNOWN_KEYS = (
    "aws_access_key_id",
    "aws_secret_access_key",
    "aws_session_token",
)


@dataclass
class AwsProfile:
    name: str
    options: dict[str, str] = field(default_factory=dict)

    def get(self, key: str, default: str = "") -> str:
        return self.options.get(key, default)

    def set(self, key: str, value: str) -> None:
        value = value.strip()
        if value:
            self.options[key] = value
        elif key in self.options:
            del self.options[key]


@dataclass
class AwsIniFile:
    """Parsed AWS INI file with profile blocks and other sections preserved."""

    profiles: list[AwsProfile] = field(default_factory=list)
    other_sections: list[tuple[str, dict[str, str]]] = field(default_factory=list)


def default_aws_config_path() -> Path:
    return Path.home() / ".aws" / "config"


def default_aws_credentials_path() -> Path:
    return Path.home() / ".aws" / "credentials"


def _parser() -> ConfigParser:
    return ConfigParser(interpolation=None)


def _profile_name_from_section(section: str, kind: AwsFileKind) -> str | None:
    if kind == "credentials":
        return section
    if section == "default":
        return "default"
    if section.lower().startswith("profile "):
        return section.split(" ", 1)[1].strip()
    return None


def _section_name_from_profile(name: str, kind: AwsFileKind) -> str:
    if kind == "credentials":
        return name
    if name == "default":
        return "default"
    return f"profile {name}"


def load_aws_ini(path: Path, kind: AwsFileKind) -> AwsIniFile:
    path = path or (default_aws_config_path() if kind == "config" else default_aws_credentials_path())
    result = AwsIniFile()

    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        return result

    parser = _parser()
    parser.read(path, encoding="utf-8")

    for section in parser.sections():
        options = {key: parser.get(section, key, fallback="") for key in parser.options(section)}
        profile_name = _profile_name_from_section(section, kind)
        if profile_name is not None:
            result.profiles.append(AwsProfile(name=profile_name, options=options))
        else:
            result.other_sections.append((section, options))

    return result


def save_aws_ini(
    data: AwsIniFile,
    path: Path,
    kind: AwsFileKind,
    *,
    backup: bool = True,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if backup and path.exists() and path.stat().st_size > 0:
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))

    parser = RawConfigParser(interpolation=None)
    parser.optionxform = str  # preserve key casing

    for profile in data.profiles:
        section = _section_name_from_profile(profile.name, kind)
        parser.add_section(section)
        for key, value in profile.options.items():
            parser.set(section, key, value)

    for section, options in data.other_sections:
        if not parser.has_section(section):
            parser.add_section(section)
        for key, value in options.items():
            parser.set(section, key, value)

    with path.open("w", encoding="utf-8") as handle:
        parser.write(handle, space_around_delimiters=False)

    return path


def known_keys(kind: AwsFileKind) -> tuple[str, ...]:
    return CONFIG_KNOWN_KEYS if kind == "config" else CREDENTIALS_KNOWN_KEYS
