"""Command line entry point.

    python -m orders --input A=samples/source_a.jsonl --input B=samples/source_b.jsonl --out-dir output
"""
import argparse
import logging
import os
import sys

from .adapters import ADAPTERS
from .pipeline import JsonLinesSink, OrderProcessor, read_records


def parse_input(value):
    if "=" not in value:
        raise argparse.ArgumentTypeError("expected SOURCE=PATH, e.g. A=samples/source_a.jsonl")
    source, path = value.split("=", 1)
    source = source.strip().upper()
    if source not in ADAPTERS:
        raise argparse.ArgumentTypeError(f"unknown source '{source}', expected one of {sorted(ADAPTERS)}")
    return source, path


def main(argv=None):
    parser = argparse.ArgumentParser(prog="orders", description="Process orders from source systems A and B.")
    parser.add_argument("--input", action="append", type=parse_input, required=True,
                        metavar="SOURCE=PATH", help="input file for a source (repeatable)")
    parser.add_argument("--out-dir", default="output", help="where to write target and rejected files")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO if args.verbose else logging.ERROR,
                        format="%(levelname)s %(name)s: %(message)s")

    os.makedirs(args.out_dir, exist_ok=True)
    target_path = os.path.join(args.out_dir, "target_orders.jsonl")
    rejected_path = os.path.join(args.out_dir, "rejected_orders.jsonl")

    with JsonLinesSink(target_path) as target, JsonLinesSink(rejected_path) as rejected:
        processor = OrderProcessor(target, rejected)
        for source, path in args.input:
            for record in read_records(path):
                processor.process(source, record)

    s = processor.stats
    print(f"delivered: {s.delivered} {s.by_source}")
    print(f"rejected:  {s.rejected}")
    print(f"duplicates skipped: {s.duplicates}")
    print(f"output:   {target_path}")
    print(f"rejected: {rejected_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())