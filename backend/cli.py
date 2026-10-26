"""Operator command line: `python -m backend.cli <command>` (TRD 15 §4.8, TRD 21 ENV-053).

Commands are added by later features (FEAT-016, FEAT-017, FEAT-038, FEAT-055). Command-specific
refusals exit with code 2 before settings validation; settings failures exit with code 1 (ENV-002).
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from backend.core.config import load_settings_or_exit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m backend.cli", description=__doc__)
    parser.add_subparsers(dest="command", metavar="<command>")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command is None:
        build_parser().print_help()
    else:
        load_settings_or_exit(operator=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
