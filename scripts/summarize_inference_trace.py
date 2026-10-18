"""Read-only Kineto operator attribution; no torch import or model execution."""

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from demosaic.safety import writable_path


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def interval(event):
    start, duration = event.get("ts"), event.get("dur")
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (start, duration)):
        raise ValueError("Nonfinite or missing event timestamp/duration")
    if duration < 0:
        raise ValueError("Negative event duration")
    return start, start + duration


def contains(outer, inner):
    return (
        (outer.get("pid"), outer.get("tid")) == (inner.get("pid"), inner.get("tid"))
        and interval(outer)[0] <= interval(inner)[0]
        and interval(inner)[1] <= interval(outer)[1]
    )


def summarize_events(events, *, range_prefix=None):
    cpu = [
        e for e in events if e.get("ph") == "X" and e.get("cat") in ["cpu_op", "user_annotation"]
    ]
    ids = {}
    for event in cpu:
        external = event.get("args", {}).get("External id")
        if external is not None:
            if external in ids:
                raise ValueError("Ambiguous CPU external id")
            ids[external] = event
    ranges = [
        e
        for e in cpu
        if e["cat"] == "user_annotation"
        and (range_prefix is None or e["name"].startswith(range_prefix))
    ]
    for event in cpu:
        interval(event)

    def enclosing(event):
        if event is None:
            return []
        # Contain the whole CPU launch operator, on its own process/thread.
        return sorted(
            [r for r in ranges if contains(r, event)],
            key=lambda r: r["dur"],
        )

    gpu = [
        e
        for e in events
        if e.get("ph") == "X" and e.get("cat") in ["kernel", "gpu_memcpy", "gpu_memset"]
    ]
    runtime = defaultdict(list)
    for event in events:
        if (
            event.get("ph") == "X"
            and event.get("cat") in ["cuda_runtime", "cuda_driver"]
            and "correlation" in event.get("args", {})
        ):
            interval(event)
            runtime[event["args"]["correlation"]].append(event)
    exclusive = defaultdict(list)
    inclusive = defaultdict(list)
    operators = defaultdict(list)
    cross = Counter()
    unknown = []
    for event in gpu:
        interval(event)
        args = event.get("args", {})
        op = ids.get(args.get("External id"))
        containing = enclosing(op)
        branch = containing[0]["name"] if containing else "<outside named ranges>"
        exclusive[branch].append(event["dur"])
        for name in {r["name"] for r in containing}:
            inclusive[name].append(event["dur"])
        operators[(branch, op["name"] if op is not None else "<unmapped CPU operator>")].append(
            event["dur"]
        )
        launches = runtime.get(args.get("correlation"), [])
        if len(launches) == 1:
            external = launches[0]["args"].get("External id")
            if external is not None and op is not None and external == args.get("External id"):
                cross["GPU_external_id_independently_matches_unique_runtime_correlation"] += 1
                if contains(op, launches[0]):
                    cross["runtime_launch_inside_matched_CPU_operator_on_same_thread"] += 1
                else:
                    cross["runtime_launch_outside_matched_CPU_operator_or_thread"] += 1
            else:
                cross["runtime_external_id_mismatch_or_unmapped"] += 1
        else:
            cross["runtime_correlation_missing_or_ambiguous"] += 1
        if op is None:
            unknown.append(
                {
                    "name": event["name"],
                    "external_id": args.get("External id"),
                    "correlation": args.get("correlation"),
                    "duration_us": event["dur"],
                }
            )

    def totals(groups):
        return sorted(
            [
                {
                    "name": name,
                    "events": len(values),
                    "summed_GPU_activity_ms": math.fsum(values) / 1000,
                }
                for name, values in groups.items()
            ],
            key=lambda x: -x["summed_GPU_activity_ms"],
        )

    all_gpu = math.fsum(e["dur"] for e in gpu)
    assert math.isclose(
        math.fsum(math.fsum(v) for v in exclusive.values()), all_gpu, rel_tol=0, abs_tol=1e-8
    )
    operators = [
        {
            "exclusive_branch": branch,
            "CPU_operator": op,
            "events": len(v),
            "summed_GPU_activity_ms": math.fsum(v) / 1000,
        }
        for (branch, op), v in operators.items()
    ]
    operators.sort(key=lambda x: -x["summed_GPU_activity_ms"])
    cpu_counts = defaultdict(Counter)
    for op in cpu:
        if op["cat"] != "cpu_op":
            continue
        containing = enclosing(op)
        branch = containing[0]["name"] if containing else "<outside named ranges>"
        cpu_counts[branch][op["name"]] += 1
    return {
        "CPU_operator_events": sum(e["cat"] == "cpu_op" for e in cpu),
        "GPU_activity_events": len(gpu),
        "GPU_categories": dict(Counter(e["cat"] for e in gpu)),
        "CPU_named_range_calls": dict(Counter(e["name"] for e in ranges)),
        "all_GPU_activity_ms_sum": all_gpu / 1000,
        "GPU_mapping_cross_checks": dict(cross),
        "contains_positive_duration_GPU_activity": any(e["dur"] > 0 for e in gpu),
        "all_GPU_mappings_verified": bool(gpu)
        and not unknown
        and cross["GPU_external_id_independently_matches_unique_runtime_correlation"]
        == cross["runtime_launch_inside_matched_CPU_operator_on_same_thread"]
        == len(gpu),
        "range_prefix": range_prefix,
        "unmapped_GPU_events": unknown,
        "exclusive_GPU_ranges": totals(exclusive),
        "inclusive_GPU_ranges_do_not_sum_nested_ranges": totals(inclusive),
        "GPU_operator_attribution": operators,
        "CPU_operator_counts_by_exclusive_range": {
            name: dict(counts) for name, counts in cpu_counts.items()
        },
        "scope": "Saved instrumented trace only; CPU operator joined by External id, runtime cross-check joined separately by correlation and checked inside that CPU operator on its own thread. Innermost enclosing CPU annotation assigns each GPU activity exactly once to exclusive totals; inclusive nested ranges overlap. Kernel/memcpy/memset durations are summed, not critical-path wall time or full-frame speed. CPU operator counts are not GPU timing. No model execution or state/output/precision change.",
    }


def summarize(path, *, range_prefix=None):
    path = Path(path)
    before = sha(path)
    trace = json.loads(path.read_text())
    result = summarize_events(trace["traceEvents"], range_prefix=range_prefix)
    assert sha(path) == before, "Input trace changed while being read"
    return {"trace": str(path), "trace_sha256": before, **result}


def require_cuda_mapping(result):
    if not result["contains_positive_duration_GPU_activity"]:
        raise ValueError(
            "Trace has no positive-duration GPU activities; CPU trace is not GPU evidence"
        )
    if not result["all_GPU_mappings_verified"]:
        raise ValueError(
            "GPU activities have unmapped/mismatched/ambiguous CPU or runtime associations"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--range-prefix")
    parser.add_argument("--require-cuda", action="store_true")
    args = parser.parse_args()
    trace, output = args.trace, writable_path(args.output)
    if output.exists():
        raise ValueError("Choose a new output")
    result = summarize(trace, range_prefix=args.range_prefix)
    if args.require_cuda:
        require_cuda_mapping(result)
    result["driver_sha256"] = sha(__file__)
    result["require_CUDA_mapping"] = args.require_cuda
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                k: result[k]
                for k in [
                    "trace",
                    "GPU_activity_events",
                    "GPU_mapping_cross_checks",
                    "exclusive_GPU_ranges",
                ]
            }
        )
    )
