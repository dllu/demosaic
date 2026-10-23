"""Keep explicit encoder comparisons strict without changing legacy study checks."""

import copy

import pytest
from evaluate_v43_quality_trial import check_joint_model_config
from frozen_backbone_identity import (
    CONVNEXT_TINY_SHA256,
    backbone_identity,
    validate_backbone_identity,
    verify_backbone_identity,
)
from queue_quality_recipe_evaluation import checkpoints
from train_directional_bank_trial import ref, save

TINY = {
    "model": "facebook/dinov3-convnext-tiny-pretrain-lvd1689m",
    "revision": "10d30274b4d445111e2d5bf75ac93bbd94db274b",
    "sha256": CONVNEXT_TINY_SHA256,
}
SMALL = {
    "model": "facebook/dinov3-convnext-small-pretrain-lvd1689m",
    "revision": "421020015aa4266363db803b6049a529999afb1e",
    "sha256": "691963f0f796aac860d818d59d9d14287a4675612829fbe9467c7f5df8ce5b14",
}


def config(identity):
    return {
        "dino_model": identity["model"],
        "dino_revision": identity["revision"],
        "dino_feature_fusion": "convnext-pyramid",
        "width": 64,
        "physical_fp32": True,
        "adc_cfa_projection": False,
    }


def test_legacy_shared_hash_and_exact_config_checks_remain_strict():
    assert verify_backbone_identity({}, "a" * 64, {}, legacy_sha256="a" * 64) == "a" * 64
    with pytest.raises(ValueError, match="parameters differ"):
        verify_backbone_identity({}, "b" * 64, {}, legacy_sha256="a" * 64)
    check_joint_model_config(config(TINY), config(TINY))
    with pytest.raises(AssertionError):
        check_joint_model_config(config(SMALL), config(TINY))


@pytest.mark.parametrize("damage", ["model", "revision", "sha256", "missing", "extra"])
def test_malformed_or_mutable_encoder_identity_is_rejected(damage):
    identity = copy.deepcopy(SMALL)
    if damage == "model":
        identity["model"] = " "
    elif damage == "revision":
        identity["revision"] = "main"
    elif damage == "sha256":
        identity["sha256"] = identity["sha256"][:16]
    elif damage == "missing":
        identity.pop("revision")
    else:
        identity["allow_any_hash"] = True
    with pytest.raises(ValueError):
        validate_backbone_identity(identity)


@pytest.mark.parametrize("damage", [None, "model", "revision", "sha256"])
def test_each_loaded_encoder_must_match_its_own_pinned_identity(damage):
    actual = config(SMALL)
    digest = SMALL["sha256"]
    if damage in ("model", "revision"):
        actual["dino_" + damage] = TINY[damage]
    elif damage == "sha256":
        digest = TINY["sha256"]
    if damage:
        with pytest.raises(ValueError):
            verify_backbone_identity(
                actual, digest, {"expected_backbone": SMALL}, legacy_sha256=TINY["sha256"]
            )
    else:
        assert backbone_identity(actual, digest) == SMALL
        assert (
            verify_backbone_identity(
                actual, digest, {"expected_backbone": SMALL}, legacy_sha256=TINY["sha256"]
            )
            == SMALL["sha256"]
        )


@pytest.mark.parametrize("damage", [None, "width", "physical_fp32", "dino_feature_fusion"])
def test_declared_encoder_change_does_not_relax_restoration_configuration(damage):
    actual, reference = config(SMALL), config(TINY)
    if damage:
        actual[damage] = {"width": 32, "physical_fp32": False, "dino_feature_fusion": "other"}[
            damage
        ]
        with pytest.raises(AssertionError):
            check_joint_model_config(actual, reference, expected_backbone=SMALL)
    else:
        check_joint_model_config(actual, reference, expected_backbone=SMALL)
        actual["adc_cfa_projection"] = True
        with pytest.raises(AssertionError):
            check_joint_model_config(actual, reference, expected_backbone=SMALL)
        check_joint_model_config(
            actual, reference, expected_backbone=SMALL, adc_projection=True
        )


@pytest.mark.parametrize("damage", [None, "wrong-small-hash", "incomplete-identities"])
def test_training_receipts_and_evaluation_records_bind_each_encoder(tmp_path, monkeypatch, damage):
    monkeypatch.setattr("queue_quality_recipe_evaluation.live", lambda _: False)
    parent = {"path": "/immutable/Tiny-zero.pt", "sha256": "e" * 64}
    training = {
        "parent": parent,
        "parent_step": 20000,
        "parent_backbone": TINY,
        "backbones": {"V105": TINY, "V106": SMALL},
        "smoke_updates": 8,
        "train_updates": 20000,
        "arms": {"V105": {}, "V106": {}},
    }
    state = {"completed": {}}
    for arm, identity in training["backbones"].items():
        checkpoint, result = tmp_path / f"{arm}.pt", tmp_path / f"{arm}.json"
        checkpoint.write_bytes(arm.encode())
        save(
            result,
            {
                "status": "completed-quality-training-phase",
                "phase": "CPU",
                "arm": arm,
                "updates": 8,
                "initialization": {
                    "initial_EMA_exact": True,
                    "DINO_sha256": TINY["sha256"]
                    if damage == "wrong-small-hash"
                    else identity["sha256"],
                },
                "owner": {"pid": 1, "created": 2},
                "checkpoint": ref(checkpoint),
                "source_sha256": "f" * 64,
            },
        )
        state["completed"][f"CPU-{arm}"] = ref(result)
    if damage == "incomplete-identities":
        training["backbones"].pop("V106")
    if damage:
        with pytest.raises(AssertionError):
            checkpoints(state, training, cpu_smoke=True, parent_label="V102")
    else:
        records, _ = checkpoints(state, training, cpu_smoke=True, parent_label="V102")
        assert [r["expected_backbone"] for r in records] == [TINY, TINY, SMALL]
        assert all(
            r["expected_lineage"]["initialized_from"] == {**parent, "step": 20000}
            for r in records[1:]
        )
