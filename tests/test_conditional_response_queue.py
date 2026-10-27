import copy

import numpy as np
import pytest
from queue_conditional_noise_response import (
    completed_methods,
    dependency_ready,
    specialized_source,
)
from report_conditional_noise_response import (
    PATTERNS,
    aggregate,
    group_statistics,
    validate_observations,
)


def boundary():
    dependency = {
        "owner": {"pid": 12, "created": 34.0},
        "plan": {"path": "/cache/plan.json", "sha256": "a" * 64},
        "plan_field": "plan",
        "terminal": "completed",
    }
    state = {
        "owner": dependency["owner"],
        "plan": dependency["plan"],
        "status": "completed",
        "child": None,
    }
    return state, dependency


def test_live_dependency_cannot_release_a_terminal_looking_status():
    state, dep = boundary()
    assert not dependency_ready(state, dep, is_live=lambda owner: True)
    assert dependency_ready(state, dep, is_live=lambda owner: False)


@pytest.mark.parametrize("change", ["owner", "plan", "partial", "failed", "orphan"])
def test_changed_failed_or_incomplete_dependency_never_releases(change):
    state, dep = boundary()
    state = copy.deepcopy(state)
    live = lambda owner: owner["pid"] == 99
    if change == "owner":
        state["owner"]["created"] += 1
    elif change == "plan":
        state["plan"]["sha256"] = "b" * 64
    elif change == "partial":
        state["status"] = "waiting"
    elif change == "failed":
        state["status"] = "failed-preserved"
    else:
        state["child"] = {"pid": 99, "created": 1}
    with pytest.raises((ValueError, RuntimeError)):
        dependency_ready(state, dep, is_live=live)


def completed_fixture():
    checkpoints = [
        {
            "arm": name,
            "path": f"/cache/{name}.pt",
            "sha256": str(index + 1) * 64,
            "expected_lineage": {"step": 20000, "initialized_from": {"sha256": "f" * 64}},
            "expected_backbone": {"sha256": "c" * 64},
        }
        for index, name in enumerate(["V124", "V125"])
    ]
    photo = {
        "invariants": [
            {
                "checkpoint": copy.deepcopy(cp),
                "calls": 3108,
                "encoder_calls": 3108,
                "observations": 12404,
                "before": str(index + 4) * 64,
            }
            for index, cp in enumerate(checkpoints)
        ]
    }
    return {"checkpoints": checkpoints}, photo


def test_only_declared_completed_endpoint_metadata_is_selected():
    evaluation, photo = completed_fixture()
    methods = completed_methods(evaluation, photo, ["V125"])
    assert len(methods) == 1 and methods[0]["label"] == "V125"
    assert methods[0]["checkpoint"]["sha256"] == "2" * 64
    assert methods[0]["expected_full_model_sha256"] == "5" * 64


@pytest.mark.parametrize(
    "change", ["missing", "partial", "encoder", "lineage", "different", "duplicate"]
)
def test_partial_or_mismatched_full_endpoint_is_rejected(change):
    evaluation, photo = completed_fixture()
    if change == "missing":
        photo["invariants"].pop()
    elif change == "partial":
        photo["invariants"][0]["calls"] -= 1
    elif change == "encoder":
        photo["invariants"][0]["encoder_calls"] -= 1
    elif change == "lineage":
        evaluation["checkpoints"][0]["expected_lineage"]["step"] = 10000
    elif change == "different":
        photo["invariants"][0]["checkpoint"]["sha256"] = "b" * 64
    else:
        photo["invariants"].append(copy.deepcopy(photo["invariants"][0]))
    with pytest.raises(ValueError):
        completed_methods(evaluation, photo, ["V124", "V125"])


def observations():
    return [
        {"id": f"case-{pattern}-{draw}", "case_id": "case", "pattern": pattern, "draw": draw}
        for pattern in PATTERNS
        for draw in range(8)
    ]


def test_observation_contract_preserves_eight_draws_per_CFA():
    assert validate_observations([{"id": "case"}], observations()) == 32


@pytest.mark.parametrize("change", ["missing", "duplicate", "extra", "same_id"])
def test_wrong_observation_membership_is_rejected(change):
    rows = observations()
    if change == "missing":
        rows.pop()
    elif change == "duplicate":
        rows[-1] = copy.deepcopy(rows[0])
    elif change == "extra":
        rows[-1]["draw"] = 8
    else:
        rows[-1]["id"] = rows[0]["id"]
    with pytest.raises(ValueError):
        validate_observations([{"id": "case"}], rows)


@pytest.mark.parametrize("offset", [0.0, 0.02])
def test_constant_targets_retain_exact_bias_and_allow_perfect_outputs(offset):
    target = np.full((1, 3, 256, 256), 0.2)
    data = {"target": target, "wb": np.ones((1, 3)), "matrix": np.eye(3)[None]}
    result = group_statistics(np.repeat(target + offset, 8, axis=0), data)
    assert result["local_band"] == []
    assert result["camera_RGB_moments"]["unbiased_squared_conditional_bias"] == pytest.approx(
        offset**2, rel=1e-12, abs=1e-30
    )
    assert result["camera_RGB_moments"]["unbiased_output_variance"] < 1e-30
    if not offset:
        assert result["camera_RGB_bias_fraction_estimate"] is None


def test_fine_band_gain_and_four_CFA_averaging_do_not_pool_draws():
    x = np.arange(256)
    signal = np.cos(2 * np.pi * (x + 0.5) / 8)[None, None, None, :]
    target = np.broadcast_to(0.25 + 0.01 * signal, (1, 3, 256, 256)).copy()
    values = np.repeat(0.25 + 0.5 * (target - 0.25), 8, axis=0)
    data = {"target": target, "wb": np.ones((1, 3)), "matrix": np.eye(3)[None]}
    stats = group_statistics(values, data)
    band = next(b for b in stats["local_band"] if b["bin"] == 1)
    assert band["blocks"] == 100 and band["reference_projected_gain_mean"] == pytest.approx(0.5)
    rows = [
        {"method": "test", "case_id": "case", "pattern": pattern, **stats} for pattern in PATTERNS
    ]
    summary = aggregate(rows, [{"id": "case", "reference_role": "synthetic"}], ["test"])[0]
    assert "draws" not in summary["camera_RGB_moments"]
    assert summary["local_band"][0]["unique_reference_blocks"] == 100
    with pytest.raises(ValueError):
        aggregate(rows[:3], [{"id": "case", "reference_role": "synthetic"}], ["test"])


ORIGINAL_OPERATOR = """
class Operator:
    def __init__(self):
        self.scale = 2
    def forward(self, x):
        return x * self.scale
"""

FREQUENCY_EXTENSION = """
class Operator:
    def __init__(self, *, raw_frequency_features=False):
        if type(raw_frequency_features) is not bool:
            raise ValueError("boolean required")
        self.scale = 2
        self.raw_frequency = None
        if raw_frequency_features:
            self.raw_frequency = make_frequency()
    def forward(self, x):
        if self.raw_frequency is not None:
            x = self.raw_frequency(x)
        return x * self.scale
"""


def test_disabled_frequency_extension_preserves_the_original_operator_AST():
    assert specialized_source(ORIGINAL_OPERATOR) == specialized_source(FREQUENCY_EXTENSION)


def test_active_numerical_changes_cannot_be_hidden_by_feature_specialization():
    changed = FREQUENCY_EXTENSION.replace("return x * self.scale", "return x * self.scale + 1")
    assert specialized_source(ORIGINAL_OPERATOR) != specialized_source(changed)


def test_enabled_frequency_default_cannot_claim_the_original_operator():
    changed = FREQUENCY_EXTENSION.replace(
        "raw_frequency_features=False", "raw_frequency_features=True"
    )
    with pytest.raises(ValueError):
        specialized_source(changed)
