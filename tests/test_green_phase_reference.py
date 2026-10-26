import numpy as np
from report_green_phase_reference import aggregate, reference_phases


def test_reference_sampling_uses_physical_phase_positions_without_resizing():
    rgb = np.arange(1 * 3 * 16 * 20, dtype=np.float32).reshape(1, 3, 16, 20)
    phase = reference_phases(rgb)
    for i, (y, x) in enumerate(((0, 0), (0, 1), (1, 0), (1, 1))):
        np.testing.assert_array_equal(phase[i], rgb[0, 1, y::2, x::2])


def test_equal_source_histogram_weights_pool_repeated_cases_and_track_missing_support():
    rows = []
    for condition in ("iso100-prior", "iso12800-prior"):
        for source, amounts in (
            ("a", [5, 5, 0, 0]),
            ("b", [0, 0, 100, 0]),
            ("b", [0, 0, 100, 0]),
            ("c", None),
        ):
            counts = np.zeros((5, 4), dtype=int)
            counts[0 if amounts is not None else 1] = (
                amounts if amounts is not None else [0, 0, 0, 20]
            )
            rows.append(
                {
                    "domain": "fixture",
                    "condition": condition,
                    "source_id": source,
                    "bin_counts": counts.tolist(),
                    "reference_power_at_least4_bins": 0,
                    "reference_power_at_least4_nonpositive_observed_cross_bins": 0,
                    "peaks": [],
                }
            )
    results = aggregate(rows)
    assert len(results) == 2
    for group in results:
        np.testing.assert_array_equal(group["source_counts_by_cross_bin"], [2, 1, 0, 0, 0])
        np.testing.assert_allclose(
            group["source_balanced_reference_power_fractions_by_cross_bin"][0], [0.25, 0.25, 0.5, 0]
        )
        np.testing.assert_array_equal(
            group["source_balanced_reference_power_fractions_by_cross_bin"][1], [0, 0, 0, 1]
        )
        assert group["total_band_bins"] == 230
