"""Evaluate a completed checkpoint with an explicitly sealed evaluator overlay.

The controller supplies the original training package with only its evaluator
replaced. Avoid the normal CLI's deliberate re-exec into the unmodified training
snapshot; loading, model code, weights and deterministic runtime remain original.
"""

import argparse
from pathlib import Path

from demosaic.experiments.artifacts import reference
from demosaic.experiments.evaluation.runner import evaluate_cases
from demosaic.experiments.outputs import load_endpoint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("cases", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--state", choices=["raw", "ema"], required=True)
    parser.add_argument("--verify-anchor-scores", type=Path, required=True)
    parser.add_argument("--verify-anchor-method", required=True)
    args = parser.parse_args()
    model, plan, checkpoint, _ = load_endpoint(args.run, state=args.state)
    print(
        evaluate_cases(
            model,
            args.cases,
            args.output,
            checkpoint=checkpoint,
            method=plan["recipe"]["name"] + "-" + args.state,
            device=plan["recipe"]["runtime"]["device"],
            anchor_reference={
                "scores": reference(args.verify_anchor_scores),
                "method": args.verify_anchor_method,
            },
        )
    )


if __name__ == "__main__":
    main()
