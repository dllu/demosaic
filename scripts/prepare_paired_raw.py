"""Align paired RAW captures and prepare fixed-grid, calibrated validation crops."""

import os

os.environ.setdefault("OMP_NUM_THREADS", "4")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "4")

import argparse
from pathlib import Path

from demosaic.realdata import prepare_pairs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument("--grid", type=int, default=3)
    args = parser.parse_args()
    prepare_pairs(args.manifest, args.output, size=args.size, grid=args.grid)


if __name__ == "__main__":
    main()
