"""Known-target response must separate real signal, false structure and DC."""

import numpy as np
import pytest
from diagnose_crossed_line_raw_evidence import template_fit
from diagnose_crossed_line_response import mesh_metrics


def signals():
    y, x = np.mgrid[:256, :256]
    wave = 0.0001 * np.cos(2 * np.pi * (x + 2 * y) / 16)
    empty = np.broadcast_to((0.02 + 0.00001 * x)[None, None], (1, 3, 256, 256)).copy()
    present = empty + wave[None, None]
    return empty, present, wave


def test_known_present_and_absent_response_and_plane_bias():
    empty, present, _ = signals()
    a = mesh_metrics(present, present, present, empty)
    b = mesh_metrics(empty, empty, present, empty)
    assert a["known_mesh_gain"] == pytest.approx(1)
    assert b["known_mesh_gain"] == pytest.approx(0, abs=1e-12)
    biased = mesh_metrics(present + 0.001, present, present, empty)
    assert biased["known_mesh_gain"] == pytest.approx(1)
    assert biased["error"]["DC_MSE"] == pytest.approx(1e-6)
    assert biased["error"]["spatial_MSE"] < 1e-30


def test_false_mesh_on_empty_and_unrelated_detail_are_measured_separately():
    empty, present, wave = signals()
    false = mesh_metrics(present, empty, present, empty)
    assert false["known_mesh_gain"] == pytest.approx(1)
    assert false["error"]["spatial_MSE"] > 0
    shifted = mesh_metrics(empty + np.roll(wave, 4, axis=1)[None, None], empty, present, empty)
    assert abs(shifted["known_mesh_gain"]) < 0.001
    assert shifted["detrended_nonmesh_RMS"] > 0.00005


def test_RAW_template_fit_removes_phase_planes_and_scales_uncertainty():
    y, x = np.mgrid[:16, :16]
    empty = np.full((4, 16, 16), 0.02)
    present = empty + np.cos(2 * np.pi * (x + 2 * y) / 8)[None] * 0.001
    planes = np.arange(4)[:, None, None] * 0.0001 + x[None] * 0.00001 + y[None] * 0.00002
    variance = np.full_like(empty, 1e-5)
    a = template_fit(present + planes, present, empty, variance)
    b = template_fit(present + planes, present, empty, 4 * variance)
    assert a["oracle_template_gain"] == pytest.approx(1)
    assert b["oracle_template_gain"] == pytest.approx(1)
    assert b["gain_std_approx"] == pytest.approx(2 * a["gain_std_approx"])
    assert template_fit(empty + planes, present, empty, variance)[
        "oracle_template_gain"
    ] == pytest.approx(0, abs=1e-12)
