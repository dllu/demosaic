"""Fixed-profile comparisons preserve coefficients without silently refitting."""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from demosaic.io import RawMetadata

spec = importlib.util.spec_from_file_location(
    "raw_pair_profile", Path(__file__).resolve().parents[1] / "scripts/report_raw_pair.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.mark.parametrize("wrapped", [False, True])
def test_fixed_profile_skips_estimator_and_preserves_diagnostics(tmp_path, monkeypatch, wrapped):
    estimate = {
        "reliable": True,
        "shot": 0.00146,
        "read": 0.00000107,
        "accepted_patches": 645,
        "reason": "fit",
    }
    document = (
        {
            "estimate": estimate,
            "raw_metadata": {"camera": "GFX100S", "iso": 6400},
            "method": "archived-Haar",
        }
        if wrapped
        else estimate
    )
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(document))

    def forbidden(*args, **kwargs):
        raise AssertionError("A supplied profile must not fit noise")

    monkeypatch.setattr(module, "estimate_noise", forbidden)
    profile = module.read_noise_profile(path)
    diagnostic, conditioning = module.noise_conditioning(
        object(), SimpleNamespace(camera="GFX100S", iso=6400), profile
    )
    assert diagnostic == estimate
    assert conditioning == {
        "shot": estimate["shot"],
        "read": estimate["read"],
        "source": "input Haar fit",
    }
    assert json.loads(path.read_text()) == document


@pytest.mark.parametrize("reliable", [True, False])
def test_default_estimation_and_nominal_fallback_remain_identical(monkeypatch, reliable):
    raw = object()
    meta = SimpleNamespace(iso=6400)
    diagnostic = {"reliable": reliable, "shot": 0.0015, "read": 0.000001}
    estimate = SimpleNamespace(**diagnostic, to_dict=lambda: diagnostic)
    calls = []

    def fit(value, *, metadata):
        calls.append((value, metadata))
        return estimate

    monkeypatch.setattr(module, "estimate_noise", fit)
    measured, conditioning = module.noise_conditioning(raw, meta)
    shot, read = (
        (estimate.shot, estimate.read) if reliable else module.Sensor(iso=6400).coefficients()
    )
    assert measured == diagnostic
    assert conditioning == {
        "shot": shot,
        "read": read,
        "source": "input Haar fit" if reliable else "nominal ISO prior (not calibrated)",
    }
    assert calls == [(raw, meta)]


@pytest.mark.parametrize(
    "field,value",
    [
        (field, value)
        for field in ("shot", "read")
        for value in (None, True, False, "0.01", -1, float("nan"), float("inf"), -float("inf"))
    ],
)
def test_invalid_coefficients_rejected_before_model_loading(tmp_path, field, value):
    profile = {"reliable": True, "shot": 0.01, "read": 0.001, field: value}
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps({"estimate": profile}))
    with pytest.raises(ValueError, match=field):
        module.read_noise_profile(path)


@pytest.mark.parametrize(
    "profile",
    [
        [],
        None,
        {"estimate": []},
        {"shot": 0.01, "read": 0.001},
        {"reliable": 1, "shot": 0.01, "read": 0.001},
        {"reliable": False, "shot": 0.01, "read": 0.001},
        {"reliable": True, "shot": 0.01},
        {"reliable": True, "read": 0.001},
        {"reliable": True, "shot": 0.01, "read": 0.001, "raw_metadata": []},
        {"reliable": True, "shot": 0.01, "read": 0.001, "conditioning_source": ""},
    ],
)
def test_invalid_profile_rejected(tmp_path, profile):
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(profile))
    with pytest.raises((TypeError, ValueError)):
        module.read_noise_profile(path)


@pytest.mark.parametrize("metadata", [{"camera": "Other camera"}, {"iso": 100}])
def test_camera_or_iso_mismatch_rejected_before_forward(metadata):
    profile = {
        "estimate": {"reliable": True, "shot": 0.01, "read": 0.001},
        "raw_metadata": metadata,
    }
    with pytest.raises(ValueError, match="does not match"):
        module.noise_conditioning(object(), SimpleNamespace(camera="GFX100S", iso=6400), profile)


def test_explicit_conditioning_source_and_zero_coefficients_are_supported(tmp_path):
    profile = {
        "estimate": {"reliable": True, "shot": 0, "read": 0},
        "conditioning_source": "fixed zero-noise test profile",
    }
    path = tmp_path / "zero.json"
    path.write_text(json.dumps(profile))
    _, conditioning = module.noise_conditioning(
        object(), SimpleNamespace(camera="GFX100S", iso=100), module.read_noise_profile(path)
    )
    assert conditioning == {"shot": 0, "read": 0, "source": profile["conditioning_source"]}


@pytest.mark.parametrize("fixed", [False, True])
def test_report_archives_profile_and_keeps_provenance_outside_conditioning(
    tmp_path, monkeypatch, fixed
):
    """Exercise the actual report path with fixture pixels and no learned model."""
    noisy, reference = tmp_path / "noisy.raw", tmp_path / "reference.raw"
    noisy.write_bytes(b"fixture noisy")
    reference.write_bytes(b"fixture reference")
    metadata = RawMetadata(
        str(noisy), "GFX100S", "RGGB", [0.0] * 4, [1.0] * 4, [1.0] * 3, np.eye(3).tolist(), 0, 6400
    )
    raw = np.full((600, 600), 0.01, np.float32)
    rgb = np.repeat(raw[..., None], 3, axis=2)
    estimate = {"reliable": True, "shot": 0.00146, "read": 0.00000107, "reason": "fit"}
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps({"estimate": estimate, "raw_metadata": {"iso": 6400}}))
    selection = tmp_path / "selection.json"
    selection.write_text(
        json.dumps(
            {
                "noisy": str(noisy),
                "reference": str(reference),
                "regions": [
                    {"name": "fixture", "noisy_xy": [260, 260], "reference_xy": [260, 260]}
                ],
            }
        )
    )
    output = tmp_path / "output"
    calls = {"fit": 0, "fixture_render": 0}

    class FixtureRenderer(torch.nn.Module):
        config = SimpleNamespace(to_dict=lambda: {"fixture": True})

        def forward(self, packed, variance, colors, wb, matrix):
            calls["fixture_render"] += 1
            torch.testing.assert_close(
                variance, packed.clamp_min(0) * estimate["shot"] + estimate["read"]
            )
            return module.malvar(packed, colors, wb)

    def fit(*args, **kwargs):
        calls["fit"] += 1
        assert not fixed, "Supplied profile unexpectedly refitted"
        return SimpleNamespace(**estimate, to_dict=lambda: estimate)

    monkeypatch.setattr(module, "estimate_noise", fit)
    monkeypatch.setattr(module, "read_raw", lambda _: (raw, metadata))
    monkeypatch.setattr(module, "read_reference", lambda _: (raw, rgb, metadata, {}))
    monkeypatch.setattr(module, "freeze_checkpoint", lambda path, output: (path, "a" * 64))
    monkeypatch.setattr(
        module,
        "load_checkpoint",
        lambda *args, **kwargs: (FixtureRenderer(), {"step": 1, "config": {"run": "fixture"}}),
    )
    argv = [
        str(module.__file__),
        str(selection),
        str(tmp_path / "fixture.pt"),
        "--output",
        str(output),
        "--device",
        "cpu",
        "--precision",
        "float32",
    ]
    if fixed:
        argv += ["--noise-profile", str(profile)]
    monkeypatch.setattr(sys, "argv", argv)
    module.main()
    receipt = json.loads((output / "report.json").read_text())
    assert receipt["conditioning"] == {
        "shot": estimate["shot"],
        "read": estimate["read"],
        "source": "input Haar fit",
    }
    assert receipt["noise_estimate"] == estimate
    assert calls == {"fit": int(not fixed), "fixture_render": 1}
    if fixed:
        policy = receipt["conditioning_policy"]
        assert policy["estimator_executed"] is False
        assert policy["profile"]["sha256"] == hashlib.sha256(profile.read_bytes()).hexdigest()
        assert (output / policy["archived_profile"]).read_bytes() == profile.read_bytes()
        assert "estimator was skipped" in (output / "report.md").read_text()
    else:
        assert "conditioning_policy" not in receipt
        assert not (output / "source/noise-profile.json").exists()
