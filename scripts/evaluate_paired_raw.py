"""Compare restoration methods on registered, calibrated real-RAW crops."""

import argparse
from pathlib import Path

from demosaic.real_suite import evaluate_pairs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path, nargs="+")
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rawnind", type=Path)
    parser.add_argument(
        "--precision", choices=("bfloat16", "float16", "float32"), default="float16"
    )
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--gallery", action="store_true")
    args = parser.parse_args()
    evaluate_pairs(
        args.checkpoint,
        args.prepared,
        args.output,
        rawnind=args.rawnind,
        precision=args.precision,
        batch_size=args.batch_size,
        gallery=args.gallery,
    )


if __name__ == "__main__":
    main()
