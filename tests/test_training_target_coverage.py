import hashlib
import random

import numpy as np
import pytest
from analyze_training_target_coverage import (
    block_statistics,
    commons_identity,
    statistics_row,
    summarize,
)


def carrier(contrast=0.03, mean=0.2):
    x = np.arange(256)
    row = mean + mean * contrast * np.sqrt(2) * np.cos(np.pi * (x + 0.5) * 6 / 16)
    return np.broadcast_to(row, (1, 3, 256, 256)).copy()


def test_dct_carrier_has_analytic_relative_rms_and_no_pixel_resampling():
    values = carrier()
    before = values.copy()
    stats = block_statistics(values)
    np.testing.assert_allclose(stats["mean_luma"], 0.2, atol=1e-15)
    np.testing.assert_allclose(stats["band_RMS"], 0.006, atol=1e-15)
    np.testing.assert_allclose(stats["relative_band_RMS"], 0.03, atol=1e-14)
    assert stats["valid"].all()
    assert np.all(stats["contrast_bin"] == 1)
    assert statistics_row(stats, 0)["counts"] == [0, 100, 0, 0, 0]
    assert np.array_equal(values, before)


def test_constant_target_is_not_counted_as_fine_detail():
    stats = block_statistics(np.full((1, 3, 256, 256), 0.3))
    assert not stats["valid"].any()
    assert statistics_row(stats, 0)["valid_blocks"] == 0


def test_out_of_gamut_channel_invalidates_block_instead_of_clipping():
    values = carrier()
    values[0, 0, 48, 48] = -0.001
    stats = block_statistics(values)
    assert stats["valid"].sum() == 99
    assert not stats["valid"][0, 0]
    assert values[0, 0, 48, 48] == -0.001


def test_paired_cfa_mask_accepts_one_measured_channel_per_pixel():
    values = carrier()
    mask = np.zeros_like(values, dtype=bool)
    mask[:, 0, ::2, ::2] = True
    mask[:, 1, ::2, 1::2] = True
    mask[:, 1, 1::2, ::2] = True
    mask[:, 2, 1::2, 1::2] = True
    assert block_statistics(values, mask)["valid"].sum() == 100
    mask[0, 0, 48, 48] = False
    assert block_statistics(values, mask)["valid"].sum() == 99
    with pytest.raises(ValueError, match="Boolean"):
        block_statistics(values, mask.astype(np.float32))


@pytest.mark.parametrize("value", [np.zeros((1, 3, 160, 160)), np.full((1, 3, 256, 256), np.nan)])
def test_invalid_target_shape_or_values_are_rejected(value):
    with pytest.raises(ValueError, match="finite"):
        block_statistics(value)


def test_summary_keeps_context_and_block_denominators_separate():
    rows = [
        {
            "family": "native",
            "valid_blocks": 10,
            "counts": [2, 3, 5, 0, 0],
            "blocks_below_2_percent": 2,
            "blocks_below_5_percent": 5,
            "source_id": None,
        },
        {
            "family": "native",
            "valid_blocks": 0,
            "counts": [0] * 5,
            "blocks_below_2_percent": 0,
            "blocks_below_5_percent": 0,
            "source_id": None,
        },
    ]
    result = summarize(rows)[0]
    assert result["context_slots"] == 2 and result["total_blocks"] == 200
    assert result["valid_blocks"] == 10
    assert result["valid_block_fractions"] == [0.2, 0.3, 0.5, 0, 0]
    assert result["contexts_with_below_5_percent_blocks"] == 1


def test_source_choice_retries_excluded_photo_and_keeps_global_rng():
    recipe = {
        "seed": 67,
        "flat_fraction": 0.0,
        "synthetic_fraction": 0.0,
        "weak_texture_fraction": 0.0,
        "reviewed_roi_fraction": 0.0,
    }
    for index in range(100):
        rng = random.Random(67 + index)
        rng.random()
        if rng.randrange(2) == 0:
            break
    else:
        raise AssertionError("Fixture needs a draw of the excluded source")
    state = random.getstate()
    assert commons_identity(recipe, index, ["excluded", "eligible"], {"eligible"}, []) == (
        "commons-photographic",
        "eligible",
    )
    assert random.getstate() == state


def test_roi_selection_uses_independent_stream_before_exclusion_retry():
    recipe = {
        "seed": 67,
        "flat_fraction": 0.0,
        "synthetic_fraction": 0.0,
        "weak_texture_fraction": 0.0,
        "reviewed_roi_fraction": 1.0,
    }
    regions = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    digest = hashlib.sha256(b"reviewed-photo-roi-v1:67:4").digest()
    chooser = random.Random(int.from_bytes(digest[:8], "little"))
    chooser.random()
    expected = regions[chooser.randrange(3)]["id"]
    assert commons_identity(recipe, 4, ["excluded"], {"a", "b", "c"}, regions) == (
        "commons-reviewed-photo",
        expected,
    )


def test_procedural_family_does_not_need_photographic_source_list():
    recipe = {
        "seed": 67,
        "flat_fraction": 1.0,
        "synthetic_fraction": 0.0,
        "weak_texture_fraction": 0.0,
        "reviewed_roi_fraction": 0.0,
    }
    assert commons_identity(recipe, 0, [], set(), []) == ("commons-smooth-field", None)
