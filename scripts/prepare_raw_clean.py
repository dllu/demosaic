"""Prepare camera-linear 16-bit training targets from licensed low-ISO RAWs."""

import argparse
from pathlib import Path

from demosaic.raw_clean import prepare_raw_clean


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--factor", type=int, default=8)
    parser.add_argument("--min-size", type=int, default=256)
    args = parser.parse_args()
    result = prepare_raw_clean(
        args.manifest, args.output, factor=args.factor, min_size=args.min_size
    )
    print(f"Prepared {len(result['rows'])} images; rejected {len(result['rejected'])}")


if __name__ == "__main__":
    main()
