"""Fetch a small, verified RawNIND paired-RAW evaluation subset under CC BY-SA 4.0."""

import argparse
from pathlib import Path

from demosaic.paired import fetch_paired


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path("/mnt/external/demosaic/references/rawnind-dataset")
    )
    parser.add_argument("--split", choices=("development", "test", "both"), default="development")
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    for split in ("development", "test") if args.split == "both" else (args.split,):
        fetch_paired(args.output, split=split, workers=args.workers)


if __name__ == "__main__":
    main()
