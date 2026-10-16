"""Sweep real mixed-domain training throughput in isolated, short-lived runs.

This measures performance, not image quality or large-batch convergence. Every
case starts from the same checkpoint; manifests, model, LR and data proportions
stay fixed. Run after sourcing scripts/env.sh, without another owned GPU job.
"""

import argparse
import hashlib
import json
import random
import subprocess
import time
from pathlib import Path

import psutil
import yaml

from demosaic.safety import writable_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--initialize", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--batch-sizes", type=int, nargs="+", default=[4, 8, 16, 32, 64])
    parser.add_argument("--warmup", type=int, default=15)
    parser.add_argument("--measure", type=int, default=45)
    parser.add_argument("--repeats", type=int, default=2)
    args = parser.parse_args()
    if min(args.batch_sizes + [args.warmup, args.measure, args.repeats]) < 1:
        parser.error("Batch sizes, warmup, measurement steps and repeats must be positive")
    output = writable_path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    source = args.config.read_bytes()
    initial_hash = hashlib.sha256(args.initialize.read_bytes()).hexdigest()
    config = yaml.safe_load(source)
    cases = [(repeat, batch) for repeat in range(args.repeats) for batch in args.batch_sizes]
    random.Random(20261015).shuffle(cases)
    plan = {
        "kind": "training throughput; not quality/convergence evidence",
        "config": str(args.config.resolve()),
        "config_sha256": hashlib.sha256(source).hexdigest(),
        "initialize": str(args.initialize.resolve()),
        "initialization_sha256": initial_hash,
        "warmup_steps_excluded": args.warmup,
        "measured_steps": args.measure,
        "cases": cases,
        "timing": "Difference of cumulative training wall times; includes selected-domain loading/degradation, DINO, forward/backward, AdamW and EMA. Excludes startup/warmup, validation and checkpoint serialization.",
        "shared_machine": True,
        "results": [],
    }
    summary = output / "summary.json"
    if summary.exists():
        raise ValueError("Choose a new benchmark output directory")
    summary.write_text(json.dumps(plan, indent=2) + "\n")
    for repeat, batch in cases:
        if psutil.virtual_memory().available / 1e9 < config.get("min_available_gb", 12) + 12:
            raise RuntimeError("Insufficient system RAM headroom before next case")
        case = output / f"batch{batch}-repeat{repeat}"
        case.mkdir()
        modified = {
            **config,
            "run": str(case / "run"),
            "batch_size": batch,
            "log_every": 1,
            "trace_observations": False,
            "steps": 5000,
            "checkpoint_every": 5000,
            "validation_protocol": None,
        }
        path = case / "config.yaml"
        path.write_text(yaml.safe_dump(modified, sort_keys=False))
        command = [
            "uv",
            "run",
            "--no-sync",
            "demosaic",
            "train",
            str(path),
            "--initialize",
            str(args.initialize.resolve()),
            "--stop-after",
            str(args.warmup + args.measure),
        ]
        before = {
            "available_gb": psutil.virtual_memory().available / 1e9,
            "load_average": list(psutil.getloadavg()),
        }
        start = time.monotonic()
        with (case / "console.log").open("w") as stream:
            completed = subprocess.run(
                command, stdout=stream, stderr=subprocess.STDOUT, check=False
            )
        if completed.returncode:
            plan["results"].append(
                {
                    "batch": batch,
                    "repeat": repeat,
                    "returncode": completed.returncode,
                    "case": str(case),
                    "before": before,
                }
            )
            summary.write_text(json.dumps(plan, indent=2) + "\n")
            raise RuntimeError(f"Benchmark case failed; inspect {case}/console.log")
        rows = [json.loads(line) for line in (case / "run/metrics.jsonl").read_text().splitlines()]
        rows = [r for r in rows if r.get("event") == "train"]
        first = next(r for r in rows if r["step"] == args.warmup)
        last = next(r for r in rows if r["step"] == args.warmup + args.measure)
        elapsed = (
            last["seconds_per_step"] * last["step"] - first["seconds_per_step"] * first["step"]
        )
        assert elapsed > 0
        domains = {}
        for row in rows:
            if row["step"] > args.warmup:
                domains[row["domain"]] = domains.get(row["domain"], 0) + 1
        runtime = yaml.safe_load((case / "run/config.yaml").read_text())
        result = {
            "batch": batch,
            "repeat": repeat,
            "images_per_second": batch * args.measure / elapsed,
            "seconds_per_step": elapsed / args.measure,
            "measured_seconds": elapsed,
            "peak_cuda_gb": last["cuda_gb"],
            "domains": domains,
            "whole_process_seconds": time.monotonic() - start,
            "case": str(case),
            "source_sha256": runtime["source_sha256"],
            "before": before,
            "available_gb_after": psutil.virtual_memory().available / 1e9,
        }
        plan["results"].append(result)
        summary.write_text(json.dumps(plan, indent=2) + "\n")
        print(json.dumps(result), flush=True)
    plan["status"] = "complete"
    summary.write_text(json.dumps(plan, indent=2) + "\n")


if __name__ == "__main__":
    main()
