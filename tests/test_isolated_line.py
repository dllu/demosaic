import numpy as np
import pytest

from demosaic.cfa import PATTERNS
from demosaic.isolated_line import external_guide, refine_isolated_raw_line

pytest.importorskip("scipy.ndimage")


def scene_case():
    shape = 576, 576
    box = (160, 160, 256, 256)
    x, y = np.meshgrid(np.arange(shape[1]), np.arange(shape[0]))
    chroma = np.array([-0.45, 1, -0.32])[:, None, None]
    envelope = (x < 112) | (x >= 464)
    exterior = 0.12 * np.exp(-0.5 * ((y - 292) / 2.8) ** 2) * envelope
    wire = 0.0055 * np.exp(-0.5 * ((y - 292) / 1.2) ** 2)
    wire[(x < 160) | (x >= 416) | (np.abs(x - 288) <= 23)] = 0
    rgb = 0.29 + chroma * (exterior + wire)
    colors = PATTERNS["GBRG"]
    packed = np.stack([rgb[c, i // 2 :: 2, i % 2 :: 2] for i, c in enumerate(colors)])
    variance = np.full_like(packed, 0.00002)
    parent = np.full((3, 256, 256), 0.29, dtype=np.float32)
    return packed, variance, colors, box, parent


def test_exterior_guide_is_invariant_to_native_query_changes():
    packed, variance, colors, box, _ = scene_case()
    guide = external_guide(packed, variance, colors, box)
    assert guide is not None
    packed[:, 80:208, 80:208] = 0.55
    variance[:, 80:208, 80:208] = 0.001
    assert external_guide(packed, variance, colors, box) == guide


def test_local_support_recovers_the_wire_and_preserves_its_gap():
    packed, variance, colors, box, parent = scene_case()
    output = refine_isolated_raw_line(parent, packed, variance, colors, box)
    assert output[1, 132, 75] - parent[1, 132, 75] > 0.004
    np.testing.assert_array_equal(output[:, :, 126:130], parent[:, :, 126:130])

    # Removing the exterior measurement removes the isolated proposal.
    packed[:, :, :56] = 0.29
    packed[:, :, 232:] = 0.29
    assert refine_isolated_raw_line(parent, packed, variance, colors, box) is parent
