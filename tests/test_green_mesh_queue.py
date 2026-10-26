import copy

import pytest
from queue_green_mesh_review import (
    REPORT_TERMINAL,
    completed_endpoint_methods,
    endpoint_methods,
    report_ready,
)

DEPENDENCY = {
    "owner": {"pid": 100, "created": 5.0},
    "plan": {"path": "plan.json", "sha256": "a" * 64},
}


def state():
    return {
        "owner": copy.deepcopy(DEPENDENCY["owner"]),
        "plan": copy.deepcopy(DEPENDENCY["plan"]),
        "status": REPORT_TERMINAL,
    }


@pytest.mark.parametrize("alive", [True, False])
def test_mesh_waits_for_the_actual_comparison_owner(alive):
    assert report_ready(state(), DEPENDENCY, is_live=lambda _: alive) is (not alive)


@pytest.mark.parametrize("damage", ["owner", "plan", "failed", "incomplete"])
def test_bad_comparison_boundary_cannot_trigger_mesh_inference(damage):
    current = state()
    if damage == "owner":
        current["owner"]["created"] += 1
    elif damage == "plan":
        current["plan"]["sha256"] = "b" * 64
    elif damage == "failed":
        current["status"] = "failed-comparisons"
    else:
        current["status"] = "joining-rows"
    with pytest.raises((ValueError, RuntimeError)):
        report_ready(current, DEPENDENCY, is_live=lambda _: False)


@pytest.mark.parametrize("suffix", ["", "-profile3879"])
def test_only_new_endpoint_methods_are_declared(suffix):
    checkpoints = {
        arm: {"path": arm + ".pt", "sha256": str(index) * 64}
        for index, arm in enumerate(("V120", "V121"), 1)
    }
    methods = endpoint_methods(checkpoints, ["V120", "V121"], suffix)
    assert [m["label"] for m in methods] == ["V120" + suffix, "V121" + suffix]
    assert all(m["expected_step"] == 20000 and "prediction" not in m for m in methods)
    assert [m["checkpoint"] for m in methods] == list(checkpoints.values())


@pytest.mark.parametrize(
    "checkpoints, arms",
    [
        ({}, []),
        ({"V120": {"sha256": "a"}}, ["V120", "V121"]),
        ({"V120": {"sha256": "a"}}, ["V120", "V120"]),
        ({"V120": {"sha256": "a"}, "V121": {"sha256": "a"}}, ["V120", "V121"]),
    ],
)
def test_missing_or_duplicate_mesh_endpoints_are_rejected(checkpoints, arms):
    with pytest.raises(ValueError):
        endpoint_methods(checkpoints, arms, "")


INPUTS = {"path": "inputs.json", "sha256": "i" * 64}
ARRAYS = {"path": "inputs.npz", "sha256": "n" * 64}
CHECKPOINTS = {
    "V120": {"path": "final-V120.pt", "sha256": "a" * 64},
    "V121": {"path": "final-V121.pt", "sha256": "b" * 64},
}


def completed_mesh(suffix=""):
    return {
        "status": "completed-new-green-mesh-CPU-context-inference-awaiting-actual-native-viewing",
        "inputs": copy.deepcopy(INPUTS),
        "input_arrays": copy.deepcopy(ARRAYS),
        "methods": [
            {
                "label": "V120" + suffix,
                "kind": "checkpoint",
                "checkpoint": {"path": "early-V120.pt", "sha256": "a" * 64},
                "prediction": {"path": "V120.npy", "sha256": "p" * 64},
                "source_inputs_sha256": ARRAYS["sha256"],
                "step": 20000,
                "new_inference": True,
                "actual_root_forwards": 1,
                "actual_encoder_forwards": 1,
            }
        ],
        "new_root_forwards": 1,
        "new_encoder_forwards": 1,
        "new_RAW_decodes": 0,
        "new_noise_observations": 0,
        "optimizer_updates": 0,
        "CUDA_initialized": False,
    }


@pytest.mark.parametrize("suffix", ["", "-profile3879"])
def test_early_completed_endpoint_is_adopted_without_another_forward(suffix):
    adopted = completed_endpoint_methods(
        completed_mesh(suffix), INPUTS, ARRAYS, ["V120", "V121"], suffix
    )
    methods = endpoint_methods(CHECKPOINTS, ["V120", "V121"], suffix, adopted=adopted)
    assert [m["label"] for m in methods] == ["V121" + suffix]
    assert adopted[0]["checkpoint"]["path"] == "early-V120.pt"
    assert adopted[0]["prediction"]["path"] == "V120.npy"


def test_all_completed_endpoints_can_be_reused_without_any_new_forward():
    result = completed_mesh()
    other = copy.deepcopy(result["methods"][0])
    other.update(label="V121", checkpoint=copy.deepcopy(CHECKPOINTS["V121"]))
    result["methods"].append(other)
    result["new_root_forwards"] = result["new_encoder_forwards"] = 2
    adopted = completed_endpoint_methods(result, INPUTS, ARRAYS, ["V120", "V121"], "")
    assert endpoint_methods(CHECKPOINTS, ["V120", "V121"], "", adopted=adopted) == []


@pytest.mark.parametrize(
    "damage",
    [
        "inputs",
        "arrays",
        "profile",
        "step",
        "root",
        "encoder",
        "reused",
        "duplicate",
        "total",
        "RAW",
        "noise",
        "updates",
        "CUDA",
        "incomplete",
        "old-control",
    ],
)
def test_wrong_observation_or_execution_cannot_be_adopted(damage):
    result = completed_mesh()
    method = result["methods"][0]
    if damage == "inputs":
        result["inputs"]["sha256"] = "x" * 64
    elif damage == "arrays":
        result["input_arrays"]["sha256"] = "x" * 64
    elif damage == "profile":
        method["source_inputs_sha256"] = "x" * 64
    elif damage == "step":
        method["step"] = 19999
    elif damage == "root":
        method["actual_root_forwards"] = 2
    elif damage == "encoder":
        method["actual_encoder_forwards"] = 0
    elif damage == "reused":
        method["new_inference"] = False
    elif damage == "duplicate":
        result["methods"].append(copy.deepcopy(method))
    elif damage == "total":
        result["new_root_forwards"] = 2
    elif damage == "RAW":
        result["new_RAW_decodes"] = 1
    elif damage == "noise":
        result["new_noise_observations"] = 1
    elif damage == "updates":
        result["optimizer_updates"] = 1
    elif damage == "CUDA":
        result["CUDA_initialized"] = True
    elif damage == "incomplete":
        result["status"] = "running"
    else:
        method["label"] = "V115"
    with pytest.raises(ValueError):
        completed_endpoint_methods(result, INPUTS, ARRAYS, ["V120", "V121"], "")


@pytest.mark.parametrize("damage", ["checkpoint", "unknown", "duplicate", "prediction"])
def test_adopted_endpoint_must_match_the_final_quality_checkpoint(damage):
    adopted = completed_endpoint_methods(completed_mesh(), INPUTS, ARRAYS, ["V120", "V121"], "")
    if damage == "checkpoint":
        adopted[0]["checkpoint"]["sha256"] = "x" * 64
    elif damage == "unknown":
        adopted[0]["label"] = "V119"
    elif damage == "duplicate":
        adopted.append(copy.deepcopy(adopted[0]))
    else:
        del adopted[0]["prediction"]
    with pytest.raises(ValueError):
        endpoint_methods(CHECKPOINTS, ["V120", "V121"], "", adopted=adopted)
