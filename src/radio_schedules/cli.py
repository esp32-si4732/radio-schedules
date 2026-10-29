"""Command-line entry point for radio schedules."""

import argparse
import sys

from . import itu
from .format import read


def main(argv=None):
    parser = argparse.ArgumentParser(prog="rsked")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="check source definitions")
    checks = check.add_subparsers(dest="source", required=True)
    checks.add_parser(
        "itu", help="compare bundled ITU names with the current online table"
    )
    validate = commands.add_parser("validate", help="validate a schedule CSV file")
    validate.add_argument("file")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            rows = read(args.file)
            print(f"{args.file}: valid ({len(rows)} rows)")
            return 0
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
