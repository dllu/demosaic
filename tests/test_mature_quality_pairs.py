"""Strict quality comparisons and actual native-panel metadata contracts."""

import json
from types import SimpleNamespace

import pytest
import torch
from build_native_crop_board import build
from mature_quality_pairs import case_gates, native_pair, physical_rows


@pytest.mark.parametrize(
    "kind,field,limit",
    [
        ("photo", "srgb_psnr", 0.05),
        ("photo", "linear_psnr", 0.05),
        ("synthetic", "srgb_ssim", 0.0001),
        ("camera", "sensor_psnr", 0.05),
        ("camera", "ahd_srgb_ssim", 0.0001),
    ],
)
def test_any_individual_failure_remains_a_failure(kind, field, limit):
    baseline = {
        k: 0.9 if "ssim" in k else 40.0
        for k in [
            "srgb_psnr",
            "srgb_ssim",
            "linear_psnr",
            "sensor_psnr",
            "ahd_srgb_psnr",
            "ahd_srgb_ssim",
        ]
    }
    candidate = dict(baseline)
    candidate[field] -= limit + 1e-6
    assert case_gates(kind, baseline, candidate)[field] is False
    assert all(case_gates(kind, baseline, baseline).values())


def test_missing_camera_support_cannot_pass():
    data = {"sensor_psnr": None, "ahd_srgb_psnr": 40.0, "ahd_srgb_ssim": 0.99}
    with pytest.raises(ValueError, match="Missing"):
        case_gates("camera", data, data)


def test_flat_and_carrier_failures_cannot_be_hidden_by_group_means():
    assert not all(case_gates("carrier", {"in_phase_gain": 0.8}, {"in_phase_gain": 0.749}).values())
    assert not all(
        case_gates("flat", {"spatial_luma_rms": 0.01}, {"spatial_luma_rms": 0.01251}).values()
    )
    assert not all(
        case_gates("flat", {"spatial_luma_rms": 0.0}, {"spatial_luma_rms": 1e-12}).values()
    )


def test_color_bias_and_spatial_variation_are_separate():
    base = {"camera_RGB_mean_error": [0.001, 0, 0], "spatially_centered_camera_RGB_RMS": 0.001}
    bad_mean = {**base, "camera_RGB_mean_error": [0.001 + 2 / 65535, 0, 0]}
    bad_texture = {**base, "spatially_centered_camera_RGB_RMS": 0.001251}
    assert not all(case_gates("hue", base, bad_mean).values())
    assert not all(case_gates("hue", base, bad_texture).values())
    assert all(case_gates("hue", base, base).values())


def test_unclipped_difference_retains_sub_code_and_over_range_values():
    baseline = torch.tensor([[[[-0.1, 1.1]]]]).expand(1, 3, 1, 2).double()
    diff = physical_rows(baseline, baseline + 0.5 / 65535)[0]
    assert diff["RGB_values"] == 6
    assert abs(diff["max_abs_DN16"] - 0.5) < 1e-10
    assert abs(diff["RMS_DN16"] - 0.5) < 1e-10


def test_native_metadata_keeps_model_specific_paths_out_of_shared_settings(tmp_path):
    # Unit PNG fixture only; no neural model, historical checkpoint or GPU receipt.
    target = torch.full((1, 3, 256, 256), 0.18)
    host = {
        "packed": torch.full((1, 4, 128, 128), 0.18),
        "variance": torch.zeros(1, 4, 128, 128),
        "colors": torch.tensor([[0, 1, 1, 2]]),
        "wb": torch.ones(1, 3),
        "matrix": torch.eye(3)[None],
        "target": target,
    }
    predictions = {"fp32": target, "fp16-hidden": target + 1e-7}
    crops = []
    for label, sha in [("unit-A", "a" * 64), ("unit-B", "b" * 64)]:
        runner = SimpleNamespace(
            checkpoint={"sha256": sha},
            metadata=lambda policy, label=label, sha=sha: {
                "label": label + ":" + policy,
                "sha256": sha,
            },
        )
        crops += native_pair(
            runner,
            tmp_path,
            "unit-source",
            predictions,
            host,
            {
                "source_id": "unit-source",
                "source": {"kind": "unit-fixture"},
                "condition": {"shot": 0, "read": 0},
                "evaluation_tile_xywh": [48, 48, 160, 160],
                "reference": "Exact unit analytic target",
            },
            roi=[48, 48, 160, 160],
            model_metadata={"observation": label + ".npz"},
        )
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"native_crops": crops}))
    board = build([report], tmp_path / "native.png", "synthetic")
    assert board["native_cells_exact"] == 6 and len(board["models"]) == 4
