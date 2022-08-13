"""
Run as a CLI
"""

from argparse import ArgumentParser
import argparse
import json
import sys

from jsonmap.parser import JsonMapping

cli = ArgumentParser(
    prog="jsonmap",
    description="A utility to transform JSON documents",
)
cli.add_argument(
    "program",
    type=str,
    help="A file with the jsonmap program to be applied",
)
group = cli.add_mutually_exclusive_group()
group.add_argument(
    "data",
    type=str,
    nargs="?",
    default=None,
    help="A file containing JSON data. If not set, jsonmap will attempt to read from stdin",
)
group.add_argument(
    "infile",
    nargs="?",
    type=argparse.FileType("r"),
    default=sys.stdin,
    help="Read the JSON data from stdin",
)

args = cli.parse_args()

with open(args.program, "r", encoding="utf-8") as f:
    raw = f.read()
    program = JsonMapping(raw)

with open(args.data, "r", encoding="utf-8") if args.data else args.infile as d:
    data = json.load(d)

output = program.apply(data)
print(json.dumps(output))
