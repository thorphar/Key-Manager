#!/usr/bin/env python3
"""Rotate SSH keys on a remote host (install new, remove old from authorized_keys).

Example:
  python swap_ssh_key.py -H my-server -u ubuntu -o ~/.ssh/id_ed25519 -n ~/.ssh/id_ed25519_new
"""

from __future__ import annotations

import argparse
import sys

from ssh_config_gui.ssh_askpass import is_askpass_subprocess, prompt_password_cli, run_askpass_subprocess
from ssh_config_gui.ssh_keys import SshTarget, find_key_pair, swap_host_keys


def main(argv: list[str] | None = None) -> int:
    if is_askpass_subprocess(argv):
        return run_askpass_subprocess()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-H", "--hostname", required=True)
    parser.add_argument("-u", "--user", required=True)
    parser.add_argument("-p", "--port", type=int, default=0)
    parser.add_argument("-J", "--proxy-jump", default="")
    parser.add_argument("-o", "--old-key", type=str, default="", help="Current private key path")
    parser.add_argument("-n", "--new-key", type=str, required=True, help="New private key path")
    parser.add_argument("--keep-old-on-server", action="store_true")
    parser.add_argument("--skip-verify", action="store_true")
    args = parser.parse_args(argv)

    new_key = find_key_pair(args.new_key)
    if new_key is None:
        print(f"New key not found: {args.new_key}", file=sys.stderr)
        return 1

    old_key = find_key_pair(args.old_key) if args.old_key else None
    target = SshTarget(
        hostname=args.hostname,
        user=args.user,
        port=args.port or None,
        proxy_jump=args.proxy_jump or None,
    )

    try:
        message = swap_host_keys(
            target=target,
            new_key=new_key,
            old_key=old_key,
            login_identity=old_key.private if old_key else None,
            remove_old_from_server=not args.keep_old_on_server,
            verify_new_key=not args.skip_verify,
            password_prompt=prompt_password_cli,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
