import numpy as np
import pytest

from demosaic._mesh_frequency import infer_prior
from demosaic.cfa import PATTERNS
from demosaic.mesh_refinement import refine_local_raw_mesh

pytest.importorskip("scipy.ndimage")


def mesh_scene(native_size=512):
    y, x = np.indices((native_size, native_size))
    p = 0.074 * x + 0.048 * y - 0.2
    q = 0.070 * x - 0.053 * y + 0.1
    front, rear = (np.exp(-0.5 * ((phase - np.rint(phase)) / 0.08) ** 2) for phase in (p, q))
    exterior = (x < 96) | (x >= 416) | (y < 96) | (y >= 416)
    texture = exterior * (0.08 * front + 0.07 * rear)
    base = np.broadcast_to(0.29 + 0.00002 * x - 0.00001 * y, (3, native_size, native_size))
    parent = (base + 0.028 * front).astype(np.float32)
    return base, parent, exterior, texture, 0.005 * rear * (1 - front)


def mosaic(rgb, colors):
    return np.stack([rgb[color, k // 2 :: 2, k % 2 :: 2] for k, color in enumerate(colors)]).astype(
        np.float32
    )


def test_local_mesh_recovers_measured_crossings_and_preserves_a_flat_query():
    box = (128, 128, 256, 256)
    roi = (176, 176, 160, 160)
    colors = PATTERNS["GBRG"]
    noise = {"shot": 8e-5, "read": 2.56e-8}
    base, parent, exterior, texture, detail = mesh_scene()
    actual = (parent + detail).astype(np.float32)
    textured = mosaic(np.where(exterior, base + texture, actual), colors)
    flat = mosaic(base + texture, colors)
    variance = np.full_like(textured, 0.29 * noise["shot"] + noise["read"])
    prior = infer_prior(textured, colors, box, noise, span=80)
    assert prior is not None and prior == infer_prior(flat, colors, box, noise, span=80)
    region = np.s_[:, 176:336, 176:336]
    output = refine_local_raw_mesh(parent, textured, variance, colors, box, roi, **noise)
    assert np.linalg.norm(output - actual[region]) < 0.55 * np.linalg.norm(
        parent[region] - actual[region]
    )
    continuous = refine_local_raw_mesh(
        parent, textured, variance, colors, box, roi, **noise, suppress_gaps=True
    )
    np.testing.assert_array_equal(continuous, output)

    flat_parent = base.astype(np.float32)
    unchanged = refine_local_raw_mesh(flat_parent, flat, variance, colors, box, roi, **noise)
    np.testing.assert_array_equal(unchanged, flat_parent[region])


def test_gap_support_attenuates_false_extension_of_a_measured_wire():
    colors = PATTERNS["GBRG"]
    noise = {"shot": 8e-5, "read": 2.56e-8}
    box = (128, 128, 256, 256)
    roi = (176, 176, 160, 160)
    base, parent, exterior, texture, detail = mesh_scene()
    y, x = np.indices(parent.shape[-2:])
    gap = np.abs(x + 0.3 * (y - 256) - 256) <= 28
    complete = parent + detail * ~gap
    raw = mosaic(np.where(exterior, base + texture, complete), colors)
    variance = np.full_like(raw, 0.29 * noise["shot"] + noise["read"])
    old = refine_local_raw_mesh(parent, raw, variance, colors, box, roi, **noise)
    output = refine_local_raw_mesh(
        parent, raw, variance, colors, box, roi, **noise, suppress_gaps=True
    )
    crop = parent[:, 176:336, 176:336]
    missing = gap[176:336, 176:336]
    spill = np.linalg.norm((old - crop)[:, missing])
    assert spill > 0.1
    assert np.linalg.norm((output - crop)[:, missing]) < 0.25 * spill
    assert np.linalg.norm((output - old)[:, ~missing]) < 0.1 * np.linalg.norm(
        (old - crop)[:, ~missing]
    )


def test_adjacent_donor_recovers_the_query_only_with_local_wire_evidence():
    box = (192, 192, 256, 256)
    roi = (240, 240, 160, 160)
    region = np.s_[:, 240:400, 240:400]
    colors = PATTERNS["GBRG"]
    noise = {"shot": 8e-5, "read": 2.56e-8}
    base, parent, _, texture, detail = mesh_scene(native_size=640)
    y, x = np.indices(parent.shape[-2:])
    donor = (x < 160) & (y >= 240) & (y < 400)
    exterior = np.broadcast_to(base + np.where(donor, texture, 0), parent.shape)
    measured = mosaic(np.where(donor, exterior, parent + detail), colors)
    flat = mosaic(exterior, colors)
    variance = np.full_like(measured, 0.29 * noise["shot"] + noise["read"])
    options = noise | {"donor_span": 224}
    default = refine_local_raw_mesh(parent, measured, variance, colors, box, roi, **options)
    np.testing.assert_array_equal(default, parent[region])
    restored = refine_local_raw_mesh(
        parent, measured, variance, colors, box, roi, adjacent_donors=True, **options,
    )
    expected = (parent + detail)[region]
    assert np.linalg.norm(restored - expected) < 0.65 * np.linalg.norm(default - expected)

    flat_parent = base.astype(np.float32)
    unchanged = refine_local_raw_mesh(
        flat_parent, flat, variance, colors, box, roi, adjacent_donors=True, **options,
    )
    np.testing.assert_array_equal(unchanged, flat_parent[region])
