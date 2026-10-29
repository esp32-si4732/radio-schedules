"""Command-line entry point for radio schedules."""

import argparse


def main(argv=None):
    parser = argparse.ArgumentParser(prog="rsked")
    parser.parse_args(argv)
    return 0
