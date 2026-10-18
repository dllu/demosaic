import copy
import importlib.util
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def script():
    path = Path("scripts/summarize_inference_trace.py")
    spec = importlib.util.spec_from_file_location("trace_reader", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def event(name, category, start, duration, *, thread=1, **args):
    return {
        "ph": "X",
        "name": name,
        "cat": category,
        "pid": 5,
        "tid": thread,
        "ts": start,
        "dur": duration,
        "args": args,
    }


def events():
    result = [
        event("demosaic::core", "user_annotation", 0, 100),
        event("demosaic::nested", "user_annotation", 10, 20),
    ]
    for i, (name, category, start, duration, thread) in enumerate(
        [
            ("aten::convolution", "kernel", 15, 8, 1),
            ("aten::copy_", "gpu_memcpy", 40, 6, 1),
            ("aten::zero_", "gpu_memset", 29, 2, 1),
            ("aten::add", "kernel", 15, 1, 2),
        ]
    ):
        identity, correlation = 20 + i, 40 + i
        result.extend(
            [
                event(name, "cpu_op", start, 5, thread=thread, **{"External id": identity}),
                event(
                    "cudaLaunch",
                    "cuda_runtime",
                    start + 1,
                    1,
                    thread=thread,
                    **{"External id": identity, "correlation": correlation},
                ),
                # Asynchronous device execution is outside CPU launch intervals.
                event(
                    "GPU " + name,
                    category,
                    1000 + 10 * i,
                    duration,
                    thread=8,
                    **{"External id": identity, "correlation": correlation},
                ),
            ]
        )
    return result


def test_async_launch_attribution_partitions_nested_and_other_thread_work(script):
    result = script.summarize_events(events())
    script.require_cuda_mapping(result)
    exclusive = {r["name"]: r for r in result["exclusive_GPU_ranges"]}
    inclusive = {r["name"]: r for r in result["inclusive_GPU_ranges_do_not_sum_nested_ranges"]}
    assert result["GPU_activity_events"] == 4
    assert result["all_GPU_activity_ms_sum"] == 0.017
    assert exclusive["demosaic::nested"]["summed_GPU_activity_ms"] == 0.008
    assert exclusive["demosaic::core"]["summed_GPU_activity_ms"] == 0.008
    assert exclusive["<outside named ranges>"]["summed_GPU_activity_ms"] == 0.001
    assert inclusive["demosaic::core"]["summed_GPU_activity_ms"] == 0.016
    assert sum(r["events"] for r in exclusive.values()) == 4
    assert result["GPU_mapping_cross_checks"] == {
        "GPU_external_id_independently_matches_unique_runtime_correlation": 4,
        "runtime_launch_inside_matched_CPU_operator_on_same_thread": 4,
    }


def test_zero_ids_are_valid_associations(script):
    values = events()
    for value in values:
        if value["args"].get("External id") == 20:
            value["args"]["External id"] = 0
        if value["args"].get("correlation") == 40:
            value["args"]["correlation"] = 0
    script.require_cuda_mapping(script.summarize_events(values))


@pytest.mark.parametrize(
    "problem",
    [
        "missing_cpu",
        "missing_runtime",
        "ambiguous_runtime",
        "wrong_runtime_external",
        "wrong_runtime_thread",
        "runtime_outside_operator",
    ],
)
def test_conflicting_or_missing_associations_cannot_support_gpu_claims(script, problem):
    values = copy.deepcopy(events())
    kernel = next(e for e in values if e["cat"] == "kernel")
    runtime = next(e for e in values if e["cat"] == "cuda_runtime")
    if problem == "missing_cpu":
        kernel["args"]["External id"] = 900
    elif problem == "missing_runtime":
        kernel["args"]["correlation"] = 900
    elif problem == "ambiguous_runtime":
        values.append(copy.deepcopy(runtime))
    elif problem == "wrong_runtime_external":
        runtime["args"]["External id"] = 900
    elif problem == "wrong_runtime_thread":
        runtime["tid"] = 900
    else:
        runtime["ts"] = 500
    result = script.summarize_events(values)
    assert not result["all_GPU_mappings_verified"]
    with pytest.raises(ValueError, match="associations"):
        script.require_cuda_mapping(result)


def test_duplicate_cpu_external_ids_are_ambiguous(script):
    values = events()
    values.append(copy.deepcopy(next(e for e in values if e["cat"] == "cpu_op")))
    with pytest.raises(ValueError, match="Ambiguous CPU external"):
        script.summarize_events(values)


def test_cpu_only_trace_is_not_gpu_evidence(script):
    values = [e for e in events() if e["cat"] in ["cpu_op", "user_annotation"]]
    result = script.summarize_events(values)
    assert result["all_GPU_activity_ms_sum"] == 0 and result["GPU_activity_events"] == 0
    assert not result["contains_positive_duration_GPU_activity"]
    with pytest.raises(ValueError, match="CPU trace is not GPU evidence"):
        script.require_cuda_mapping(result)


def test_optional_prefix_excludes_unrelated_annotations(script):
    values = events() + [event("unrelated innermost", "user_annotation", 15, 5)]
    unfiltered = script.summarize_events(values)
    filtered = script.summarize_events(values, range_prefix="demosaic::")
    assert "unrelated innermost" in unfiltered["CPU_named_range_calls"]
    assert "unrelated innermost" not in filtered["CPU_named_range_calls"]
    assert filtered["all_GPU_activity_ms_sum"] == unfiltered["all_GPU_activity_ms_sum"]
    assert any(r["name"] == "unrelated innermost" for r in unfiltered["exclusive_GPU_ranges"])
    assert all(r["name"] != "unrelated innermost" for r in filtered["exclusive_GPU_ranges"])


@pytest.mark.parametrize("category", ["cpu_op", "user_annotation", "kernel", "cuda_runtime"])
@pytest.mark.parametrize("duration", [-1, float("nan"), float("inf")])
def test_invalid_event_intervals_are_rejected(script, category, duration):
    values = events()
    next(e for e in values if e["cat"] == category)["dur"] = duration
    with pytest.raises(ValueError, match="duration"):
        script.summarize_events(values)
