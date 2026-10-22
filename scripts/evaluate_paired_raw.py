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
    parser.add_argument("--gaussian-reference", type=Path)
    parser.add_argument("--nonlocal-reference", type=Path)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument(
        "--precision", choices=("bfloat16", "float16", "float32"), default="float16"
    )
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--refinement-precision", choices=("float32", "float16"), default="float32")
    parser.add_argument("--gallery", action="store_true")
    parser.add_argument(
        "--noise-multiplier",
        type=float,
        default=1.0,
        help="Diagnostic multiplier on learned-restorer variance inputs",
    )
    parser.add_argument("--prior-window", type=int, help="Diagnostic learned-model prior override")
    args = parser.parse_args()
    if args.device == "cpu" and (
        args.precision != "float32" or args.refinement_precision != "float32"
    ):
        parser.error("CPU evaluation requires float32 precision for both network and refinement")
    evaluate_pairs(
        args.checkpoint,
        args.prepared,
        args.output,
        rawnind=args.rawnind,
        device=args.device,
        precision=args.precision,
        batch_size=args.batch_size,
        gallery=args.gallery,
        noise_multiplier=args.noise_multiplier,
        prior_window=args.prior_window,
        refinement_precision=args.refinement_precision,
        gaussian_reference=args.gaussian_reference,
        nonlocal_reference=args.nonlocal_reference,
    )


if __name__ == "__main__":
    main()
