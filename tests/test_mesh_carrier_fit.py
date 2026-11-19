import numpy as np
import pytest

from demosaic.cfa import PATTERNS
from demosaic.mesh_carrier_fit import refine_raw_mesh_carriers

pytest.importorskip("scipy")


def scene_fixture():
    y, x = np.indices((480, 480), dtype=np.float32)
    return (
        0.08
        + 0.003 * np.cos(2 * np.pi * (0.1171875 * x + 0.07421875 * y) + 0.8)
        + 0.002 * np.cos(2 * np.pi * (0.08984375 * x - 0.072265625 * y) - 0.9)
    ).astype(np.float32)


def pack(raw):
    return np.stack([raw[p // 2 :: 2, p % 2 :: 2] for p in range(4)])


@pytest.mark.parametrize("pattern", tuple(PATTERNS))
def test_measured_mesh_with_odd_native_origin(pattern):
    image = scene_fixture()
    crop = (151, 149, 160, 160)
    clean = image[149:309, 151:311]
    previous = np.full((3, 160, 160), 0.08, dtype=np.float32)
    restored = refine_raw_mesh_carriers(
        previous,
        pack(image),
        PATTERNS[pattern],
        crop,
        shot=0.00128,
        read=6.5536e-6,
        white_balance=np.ones(3),
        camera_to_srgb=np.eye(3),
    )
    center = np.s_[..., 16:-16, 16:-16]
    expected = np.repeat(clean[None], 3, axis=0)
    error = np.sqrt(np.mean((restored[center] - expected[center]) ** 2))
    starting_error = np.sqrt(np.mean((previous[center] - expected[center]) ** 2))
    assert error < 0.55 * starting_error
    assert restored.dtype == previous.dtype


def test_ring_of_donors_does_not_fill_measured_flat_center():
    image = scene_fixture()
    image[149:309, 151:311] = 0.08
    previous = np.full((3, 160, 160), 0.08, dtype=np.float32)
    args = {
        "shot": 0.00128,
        "read": 6.5536e-6,
        "white_balance": np.ones(3),
        "camera_to_srgb": np.eye(3),
    }
    result = refine_raw_mesh_carriers(
        previous, pack(image), PATTERNS["RGGB"], (151, 149, 160, 160), **args
    )
    np.testing.assert_array_equal(result, previous)
    edge = refine_raw_mesh_carriers(
        previous, pack(image), PATTERNS["RGGB"], (16, 16, 160, 160), **args
    )
    np.testing.assert_array_equal(edge, previous)
