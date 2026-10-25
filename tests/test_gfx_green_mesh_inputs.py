"""Camera-JPEG coordinate selection must handle larger shifts without warping."""

import hashlib

import numpy as np
import pytest
from PIL import Image
from prepare_gfx_green_mesh_inputs import jpeg_offset


@pytest.mark.parametrize("dx,dy", [(-39, 16), (42, -28)])
def test_coarse_native_coordinate_match_handles_offsets_beyond_old_window(dx, dy):
    rng = np.random.default_rng(20261025)
    pixels = rng.integers(0, 256, (1152, 1152, 3), dtype=np.uint8)
    before = hashlib.sha256(pixels.tobytes()).hexdigest()
    x = y = 160
    anchor = pixels[y+dy:y+dy+768, x+dx:x+dx+768, 1].astype(np.float32) / 255
    actual_x, actual_y, score, coarse_score = jpeg_offset(anchor, Image.fromarray(pixels), x, y)
    assert (actual_x, actual_y) == (dx, dy)
    assert score > .99999 and coarse_score > 0
    assert hashlib.sha256(pixels.tobytes()).hexdigest() == before
