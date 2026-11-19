"""Protect the paired-reduction distinction and single-draw observation replay."""

import random

import numpy as np
import pytest
import torch
from train_local_paired_continuation import (
    CORE,
    PATCH,
    PairedBands,
    gap_projection,
    observations,
    wire_pair,
)

from demosaic.experiments.artifacts import reference


def _paired_sinusoid():
    bands = PairedBands("cpu", [(1 / 32, 1 / 8), (1 / 8, 1 / 3)])
    field = 1e-3 * torch.cos(2 * torch.pi * torch.arange(PATCH) / 9)
    target = torch.full((6, 3, PATCH, PATCH), 0.2)
    target[0] += field
    target[2] = target[0]
    batch = {
        "sensor_target": target,
        "matrix": torch.eye(3).repeat(6, 1, 1),
        "wb": torch.ones(6, 3),
    }
    return bands, field, batch


def test_redraw_mean_cancels_opposing_errors_but_retains_shared_errors():
    bands, field, batch = _paired_sinusoid()
    prediction = batch["sensor_target"].clone()
    prediction[0] += field
    prediction[2] -= field
    loss, valid = bands.redraw_losses(prediction, batch)
    assert valid and loss["mean"].item() < 1e-8 and loss["individual"].item() > 1e-4
    assert loss["repeat"].item() > loss["individual"].item()

    prediction[2] += 2 * field
    prediction.requires_grad_()
    loss, valid = bands.redraw_losses(prediction, batch)
    assert valid and loss["mean"].item() > 1e-4
    torch.testing.assert_close(loss["mean"], loss["individual"])
    assert loss["repeat"].item() == 0
    (gradient,) = torch.autograd.grad(loss["mean"], prediction)
    assert torch.isfinite(gradient).all()
    assert gradient[:4].count_nonzero() > 0
    assert gradient[4:].count_nonzero() == 0
    assert gradient[:, :, : CORE.start].count_nonzero() == 0


def test_redraw_excludes_clipped_cores():
    bands, field, batch = _paired_sinusoid()
    target = batch["sensor_target"]
    prediction = target.clone()
    prediction[0] += field
    target[[0, 2], 0, CORE.start, CORE.start] = 1
    losses, valid = bands.redraw_losses(prediction, batch, align=True)
    assert not valid
    assert all(value.item() == 0 for value in losses.values())


def test_aligned_redraw_term_is_signed_and_retains_orthogonal_variance_penalty():
    bands, _, batch = _paired_sinusoid()
    phase = 2 * torch.pi * (torch.arange(PATCH) - 128) / 8
    clean, same_band = 1e-3 * phase.cos(), 1e-3 * phase.sin()
    target = torch.full_like(batch["sensor_target"], 0.2)
    target[::2][:2] += clean
    batch["sensor_target"] = target
    under = target.clone()
    under[::2][:2] -= clean
    over = target.clone()
    over[::2][:2] += clean
    a, _ = bands.redraw_losses(under.requires_grad_(), batch, align=True)
    b, _ = bands.redraw_losses(over.requires_grad_(), batch, align=True)
    torch.testing.assert_close(a["aligned"], a["mean"])
    torch.testing.assert_close(b["aligned"], a["aligned"])
    (da,) = torch.autograd.grad(a["aligned"], under)
    (db,) = torch.autograd.grad(b["aligned"], over)
    torch.testing.assert_close(da, -db)

    mixed = target.clone()
    mixed[0] += 2 * same_band
    v, _ = bands.redraw_losses(mixed, batch, align=True)
    assert v["aligned"] < 1e-8
    assert v["mean"] > 1e-4 and v["repeat"] > 1e-4


def test_gap_projection_excludes_intact_area_and_the_continuing_direction():
    bands, _, batch = _paired_sinusoid()
    wire = {
        "gap_center": (3, -5),
        "gap_axes": (12, 24),
        "gap_angle": 0,
        "angles": (0, torch.pi / 2),
        "periods": (12, 8),
        "phases": (0, 0),
    }
    projection = gap_projection(wire)
    axis = torch.arange(PATCH) - (PATCH - 1) / 2
    y, x = torch.meshgrid(axis, axis, indexing="ij")
    outside = ((x - 3) / 12).square() + ((y + 5) / 24).square() >= 1
    assert projection[outside[CORE, CORE].flatten()].count_nonzero() == 0
    pure_strong = (2 * torch.pi * x / 12).cos() + (4 * torch.pi * x / 12).sin()
    clean = batch["sensor_target"]
    prediction = clean + 1e-2 * (pure_strong + 0.01 * y + outside)
    assert bands.gap_loss(prediction, batch, projection).item() < 1e-8

    # Opposite leakage in the two present draws must not cancel in this loss.
    weak = 3e-3 * (2 * torch.pi * y / 8).sin()
    prediction[0] += weak
    prediction[2] -= weak
    prediction.requires_grad_()
    loss = bands.gap_loss(prediction, batch, projection)
    assert loss.item() > 1e-3
    (gradient,) = torch.autograd.grad(loss, prediction)
    assert torch.isfinite(gradient).all()
    assert gradient[..., outside].count_nonzero() == 0
    assert gradient[[1, 3, 4, 5]].count_nonzero() == 0


@pytest.mark.parametrize("law", ["coupled", "independent"])
def test_second_draw_keeps_clean_pair_and_original_observations(tmp_path, law):
    field = np.random.default_rng(45).integers(5000, 20000, (PATCH, PATCH, 3), dtype=np.uint16)
    path = tmp_path / "photo.npy"
    np.save(path, field, allow_pickle=False)
    source = {
        "id": "fixture",
        "cache": str(path),
        "cache_sha256": reference(path)["sha256"],
        "shape": list(field.shape),
    }
    case = {"source": source, "kind": "wire", "iso": "ISO6400", "pattern": "GBRG", "law": law}
    single, _ = observations(case, 12)
    double, record = observations(case, 12, pair_draws=2)
    for key, first in single.items():
        assert torch.equal(first, torch.cat([double[key][:2], double[key][4:]]))
    for key in ("target", "sensor_target", "colors", "wb", "matrix"):
        assert torch.equal(double[key][:2], double[key][2:4])
    assert not torch.equal(double["packed"][:2], double["packed"][2:4])
    assert len(set(record["seeds"].values())) == 8


def test_continuing_wire_supervision_respects_true_double_gaps_and_support():
    bands, _, batch = _paired_sinusoid()
    photo = torch.full((3, PATCH, PATCH), 0.2)
    present, absent, wire = wire_pair(photo, random.Random(91), strong_continues=True)
    double, double_absent, meta = wire_pair(photo, random.Random(91), strong_continues=False)
    assert not meta["strong_continues"]
    projection = gap_projection(wire, continuing=True)
    assert torch.equal(projection, gap_projection(meta, continuing=True))
    keep = projection.reshape(96, 96) != 0
    inner = (..., CORE, CORE)
    assert torch.equal(present[inner][:, keep], absent[inner][:, keep])
    assert torch.equal(double[inner][:, keep], double_absent[inner][:, keep])
    torch.testing.assert_close(double[inner][:, keep], torch.full_like(double[inner][:, keep], 0.2))
    clean = torch.stack((present, absent, present, absent))
    blank = torch.stack((double, double_absent, double, double_absent))
    batch["sensor_target"] = clean
    assert bands.continuing_wire_loss(clean, batch, projection).item() == 0
    missing = bands.continuing_wire_loss(blank.requires_grad_(), batch, projection)
    assert missing.item() > 1e-4
    (gradient,) = torch.autograd.grad(missing, blank)
    assert gradient[..., CORE, CORE][..., ~keep].count_nonzero() == 0
    assert gradient[..., CORE, CORE][..., keep].count_nonzero() > 0
    assert torch.equal(gradient[0], gradient[3])
    batch["sensor_target"] = blank.detach()
    torch.testing.assert_close(bands.continuing_wire_loss(clean, batch, projection), missing)

    # Clipped pixels outside the tapered footprint keep the supervision valid.
    outside = (~keep).nonzero()[0] + CORE.start
    batch["sensor_target"][:, :, outside[0], outside[1]] = 1
    assert bands.continuing_wire_loss(clean, batch, projection).item() > 1e-4
    inside = keep.nonzero()[0] + CORE.start
    batch["sensor_target"][:, :, inside[0], inside[1]] = 1
    assert bands.continuing_wire_loss(clean, batch, projection).item() == 0
