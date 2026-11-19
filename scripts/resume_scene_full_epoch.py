"""Run a frozen full-epoch plan with durable restart points inside each milestone."""

import argparse
import shutil
import subprocess
import time
from itertools import pairwise
from pathlib import Path

from run_scene_full_epoch import phase_audit, run_worker

from demosaic.experiments.artifacts import checked, read_json, reference, verify_plan, write_json
from demosaic.experiments.runtime import exclusive_run, owner_live


def completed_segment(root, plan, folder, mode, stop, resume):
    folder.mkdir(parents=True, exist_ok=True)
    while True:
        for attempt in sorted(folder.glob("attempt-*"), reverse=True):
            launch = attempt / "launch.json"
            if launch.exists():
                owner = read_json(launch)["child"]
                while owner_live(owner):
                    time.sleep(10)
            receipt = attempt / "work" / "completed.json"
            if receipt.exists():
                return receipt

        arguments = ["train", "--mode", mode, "--stop-step", str(stop)]
        if resume is not None:
            arguments += ["--resume-receipt", str(checked(resume))]
        try:
            output = run_worker(root, plan, folder, arguments)
        except subprocess.CalledProcessError:
            attempt = Path(read_json(folder / "launch.json")["attempt"])
            log = (attempt / "worker.log").read_text()
            if "RuntimeError: Training RAM reserve unavailable" not in log:
                raise
            continue
        return output / "completed.json"


def combine_segments(folder, binding, plan, mode, first, stop, segments):
    """Preserve the worker receipts and produce the original milestone format."""
    records = [read_json(checked(segment["receipt"])) for segment in segments]
    for before, after in pairwise(records):
        if after["resume"] != before["checkpoints"][-1]:
            raise ValueError("Scene segment is missing its predecessor checkpoint")
    if (
        not records
        or any(row["script"] != plan["training_script"] for row in records)
        or (records[0]["start_step_exclusive"], records[-1]["steps"]) != (first, stop)
    ):
        raise ValueError("Scene segments do not cover the requested frozen phase")

    folder.mkdir(exist_ok=True)
    trace = folder / "observations.jsonl"
    building = trace.with_suffix(".incomplete")
    with building.open("wb") as output:
        for record in records:
            with checked(record["observations"]).open("rb") as source:
                shutil.copyfileobj(source, output)
    building.replace(trace)

    result = folder / "completed.json"
    receipt = {
        "plan": binding,
        "mode": mode,
        "start_step_exclusive": first,
        "steps": stop,
        "schedule_steps": plan["steps"],
        "resume": records[0]["resume"],
        "seconds": sum(row["seconds"] for row in records),
        "data_seconds": sum(row["data_seconds"] for row in records),
        "checkpoint_seconds": sum(row["checkpoint_seconds"] for row in records),
        "checkpoints": [checkpoint for row in records for checkpoint in row["checkpoints"]],
        "observations": reference(trace),
        "script": plan["training_script"],
        "DINO_unchanged": all(row["DINO_unchanged"] for row in records),
        "segments": [row["receipt"] for row in segments],
        "scope": "Original milestone aggregated from validated frozen-worker segments.",
    }
    if result.exists():
        if receipt != read_json(result):
            raise ValueError(f"Combined scene receipt changed for {mode} at {stop}")
    else:
        write_json(result, receipt)
    return result


def resume_phase(root, binding, plan, dataset, mode, first, stop, resume, interval):
    phase = root / f"{mode}-{stop:06d}"
    phase.mkdir(exist_ok=True)
    verified = phase / "verified.json"
    if verified.exists():
        summary = read_json(verified)
        checked(summary["checkpoint"])
        return summary

    segments = phase / "segments"
    segments.mkdir(exist_ok=True)
    states = []
    starts = range(first, stop, interval)
    for start in starts:
        end = min(start + interval, stop)
        part = segments / f"through-{end:06d}"
        known = part / "verified.json"
        if known.exists():
            accepted = read_json(known)
            receipt = checked(accepted["receipt"])
        else:
            receipt = completed_segment(root, plan, part, mode, end, resume)
            accepted = phase_audit(receipt, binding, mode, start, end, dataset)
            write_json(known, accepted)
        data = read_json(receipt)
        predecessor = read_json(checked(resume))["checkpoints"][-1] if resume else None
        if data["resume"] != predecessor:
            raise ValueError(f"Unexpected predecessor for {mode} at {end}")
        resume = accepted["receipt"]
        states.append(accepted)

    receipt = combine_segments(phase / "combined", binding, plan, mode, first, stop, states)
    summary = phase_audit(receipt, binding, mode, first, stop, dataset)
    write_json(verified, summary)
    return summary


def run(root, interval):
    from train_scene_context import training_dataset

    if interval < 1:
        raise ValueError("Segment interval must be positive")
    with exclusive_run(root):
        binding = reference(root / "plan.json")
        plan = read_json(checked(binding))
        verify_plan(plan)
        qualified = read_json(root / "qualified.json")
        if qualified["plan"] != binding:
            raise ValueError("Run requires a qualification for the original plan")
        checked(qualified["preflight"])

        identity = root / "segmentation.json"
        policy = {
            "plan": binding,
            "maximum_segment_updates": interval,
            "controller": reference(__file__),
        }
        if identity.exists():
            recorded = read_json(identity)
            if recorded["plan"] != binding or recorded["maximum_segment_updates"] != interval:
                raise ValueError("Resume with the original plan and segment interval")
        else:
            write_json(identity, policy)

        dataset = training_dataset(plan)
        latest = dict.fromkeys(plan["modes"])
        first = 0
        for stop in plan["phase_stops"]:
            marker = root / f"matched-{stop:06d}.json"
            if marker.exists():
                prior = read_json(marker)
                if prior["plan"] != binding or prior["through_update"] != stop:
                    raise ValueError(f"Unexpected existing scene milestone at {stop}")
                for mode, summary in prior["arms"].items():
                    latest[mode] = summary["receipt"]
                first = stop
                continue
            summaries = {
                mode: resume_phase(
                    root, binding, plan, dataset, mode, first, stop, latest[mode], interval
                )
                for mode in plan["modes"]
            }
            if len({row["observations"]["sha256"] for row in summaries.values()}) != 1:
                raise ValueError(f"Unmatched scene inputs through update {stop}")
            for mode, summary in summaries.items():
                latest[mode] = summary["receipt"]
            write_json(
                marker,
                {
                    "plan": binding,
                    "matched_input_traces": True,
                    "first_step_exclusive": first,
                    "through_update": stop,
                    "arms": summaries,
                    "training_complete": stop == plan["steps"],
                    "numerical_review_complete": False,
                    "native_review_complete": False,
                },
            )
            first = stop
        write_json(
            root / "status.json", {"training_complete": True, "through_update": first}, replace=True
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--segment-updates", type=int, default=500)
    args = parser.parse_args()
    run(args.root.resolve(), args.segment_updates)
