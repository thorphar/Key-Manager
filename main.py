#!/usr/bin/env python3
"""Entry point: python main.py"""

from __future__ import annotations

import sys

from ssh_config_gui.ssh_askpass import is_askpass_subprocess, run_askpass_subprocess


def main(argv: list[str] | None = None) -> int:
    if is_askpass_subprocess(argv):
        return run_askpass_subprocess()

    from ssh_config_gui.app import run_app

    return run_app(argv)


if __name__ == "__main__":
    raise SystemExit(main())
