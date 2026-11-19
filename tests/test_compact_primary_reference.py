"""Guard score reuse across byte-matched canonical replay cases."""

import pytest
from collect_scene_primary_compact import reuse_variants

from demosaic.experiments.artifacts import reference, write_json


def test_reference_scores_bind_to_original_batch_and_keep_model_identity(tmp_path):
    full = tmp_path / "full"
    full.mkdir()
    plan = {"path": "original-plan.json", "sha256": "original-plan"}
    inputs = {"path": "fixed-bayer.npz", "sha256": "fixed-bayer"}
    replay = {"root": str(tmp_path), "plan": plan, "models": {"prior-repeat": "repeat"}}
    assert reuse_variants(replay, "known", 3, inputs) == ({}, None, None)
    path = full / "known-00003.json"
    row = {"model": "repeat", "id": "case", "metrics": {"sensor_psnr": 54.0}}
    cpu_proof = {"score": "sensor_psnr", "delta_dB": [0.0]}
    write_json(
        path,
        {
            "plan": plan,
            "stage": "known",
            "batch": 3,
            "arrays": inputs,
            "variants": {
                "repeat": {
                    "rows": [row],
                    "output_fingerprint": {"sha256": "fixed-output"},
                    "forward_seconds": 1.25,
                }
            },
            "V120_CPU_check": cpu_proof,
        },
    )
    variants, proof, binding = reuse_variants(replay, "known", 3, inputs)
    assert binding == reference(path) and proof == cpu_proof
    assert variants["prior-repeat"] == {
        "rows": [row | {"model": "prior-repeat"}],
        "output_fingerprint": {"sha256": "fixed-output"},
        "forward_seconds": 0.0,
        "reused_from": {"batch": binding, "model": "repeat"},
    }
    with pytest.raises(AssertionError):
        reuse_variants(replay, "known", 3, inputs | {"sha256": "other-camera"})
    with pytest.raises(AssertionError):
        reuse_variants(replay | {"plan": {"sha256": "other-replay"}}, "known", 3, inputs)
