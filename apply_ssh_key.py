#!/usr/bin/env python3
"""Copy an SSH public key to a remote host's authorized_keys file.

Examples:
  python apply_ssh_key.py -i ~/.ssh/id_ed25519.pub user@my-server
  python apply_ssh_key.py -H my-server -u ubuntu -k ~/.ssh/id_ed25519 -p 22
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ssh_config_gui.ssh_askpass import is_askpass_subprocess, prompt_password_cli, run_askpass_subprocess
from ssh_config_gui.ssh_keys import apply_public_key, find_key_pair


def _parse_target(value: str) -> tuple[str, str]:
    if "@" not in value:
        raise argparse.ArgumentTypeError("target must be user@host")
    user, host = value.rsplit("@", 1)
    if not user or not host:
        raise argparse.ArgumentTypeError("target must be user@host")
    return user, host


def main(argv: list[str] | None = None) -> int:
    if is_askpass_subprocess(argv):
        return run_askpass_subprocess()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "target",
        nargs="?",
        help="Remote login as user@hostname",
    )
    parser.add_argument("-H", "--hostname", help="Remote hostname or IP")
    parser.add_argument("-u", "--user", help="Remote SSH username")
    parser.add_argument("-p", "--port", type=int, default=0, help="SSH port")
    parser.add_argument(
        "-k",
        "--key",
        type=Path,
        help="Private or public key path (uses .pub for authorized_keys)",
    )
    parser.add_argument(
        "-i",
        "--identity",
        type=Path,
        help="Existing private key used to log in (optional)",
    )
    parser.add_argument("-J", "--proxy-jump", default="", help="ProxyJump bastion host")
    args = parser.parse_args(argv)

    if args.target:
        user, hostname = _parse_target(args.target)
    else:
        if not args.hostname or not args.user:
            parser.error("Provide user@host or both --user and --hostname")
        user, hostname = args.user, args.hostname

    if not args.key:
        parser.error("--key / -k is required")

    key_path = args.key.expanduser()
    pair = find_key_pair(key_path)
    if pair:
        public = pair.public
        login_identity = args.identity.expanduser() if args.identity else pair.private
    else:
        public = key_path if key_path.suffix == ".pub" else Path(str(key_path) + ".pub")
        login_identity = args.identity.expanduser() if args.identity else None

    if not public.is_file():
        print(f"Public key not found: {public}", file=sys.stderr)
        return 1

    try:
        message = apply_public_key(
            public,
            hostname=hostname,
            user=user,
            port=args.port or None,
            login_identity=login_identity,
            proxy_jump=args.proxy_jump or None,
            password_prompt=prompt_password_cli,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
