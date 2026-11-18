import numpy as np
import pytest

from demosaic._mesh_frequency import infer_prior
from demosaic.cfa import PATTERNS
from demosaic.mesh_refinement import refine_local_raw_mesh

pytest.importorskip("scipy.ndimage")


def test_local_mesh_recovers_measured_crossings_and_preserves_a_flat_query():
    native_size = 512
    box = (128, 128, 256, 256)
    roi = (176, 176, 160, 160)
    colors = PATTERNS["GBRG"]
    noise = {"shot": 8e-5, "read": 2.56e-8}
    y, x = np.indices((native_size, native_size))
    p = 0.074 * x + 0.048 * y - 0.2
    q = 0.070 * x - 0.053 * y + 0.1
    front, rear = (np.exp(-0.5 * ((phase - np.rint(phase)) / 0.08) ** 2) for phase in (p, q))
    exterior = (x < 96) | (x >= 416) | (y < 96) | (y >= 416)
    texture = exterior * (0.08 * front + 0.07 * rear)
    base = np.broadcast_to(0.29 + 0.00002 * x - 0.00001 * y, (3, native_size, native_size))
    parent = (base + 0.028 * front).astype(np.float32)
    actual = (parent + 0.005 * rear * (1 - front)).astype(np.float32)

    def mosaic(rgb):
        return np.stack([rgb[color, k // 2 :: 2, k % 2 :: 2] for k, color in enumerate(colors)])

    textured = mosaic(np.where(exterior, base + texture, actual).astype(np.float32))
    flat = mosaic((base + texture).astype(np.float32))
    variance = np.full_like(textured, 0.29 * noise["shot"] + noise["read"])
    prior = infer_prior(textured, colors, box, noise, span=80)
    assert prior is not None and prior == infer_prior(flat, colors, box, noise, span=80)
    region = np.s_[:, 176:336, 176:336]
    output = refine_local_raw_mesh(parent, textured, variance, colors, box, roi, **noise)
    assert np.linalg.norm(output - actual[region]) < 0.55 * np.linalg.norm(
        parent[region] - actual[region]
    )

    flat_parent = base.astype(np.float32)
    unchanged = refine_local_raw_mesh(flat_parent, flat, variance, colors, box, roi, **noise)
    np.testing.assert_array_equal(unchanged, flat_parent[region])
