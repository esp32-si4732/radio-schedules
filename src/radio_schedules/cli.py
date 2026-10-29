"""Command-line entry point for radio schedules."""

import argparse
import sys

from . import itu


def main(argv=None):
    parser = argparse.ArgumentParser(prog="rsked")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="check source definitions")
    checks = check.add_subparsers(dest="source", required=True)
    checks.add_parser(
        "itu", help="compare bundled ITU names with the current online table"
    )
    parser.parse_args(argv)
    try:
        changes = itu.check()
        print(
            "\n".join(changes)
            if changes
            else f"ITU: no differences ({len(itu.AREAS)} entries)"
        )
        return int(bool(changes))
    except (OSError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1
