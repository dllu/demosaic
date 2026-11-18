from dataclasses import replace

import numpy as np

from demosaic.experiments.evaluation.withheld import geometry, stratified_split
from demosaic.flexible_edge import edge_terms, fit_flexible_edges
from demosaic.local_validated_waves import LocalWaveConfig, fit_local_candidate
from demosaic.surface_phase_aggregation import SurfacePhaseOperator


def test_four_boundaries_explain_two_curved_rails():
    n = 96
    _, _, affine, _ = geometry((n, n))
    xy = affine[:, 1:]
    curves = [[-0.30, 0.01, 0.04], [-0.14, 0.02, 0.04], [0.16, -0.04, -0.03], [0.27, -0.02, -0.03]]
    normal = 0.67
    terms = edge_terms(xy, normal, curves, 0.84 / n)
    clean = affine @ np.array([0.08, 0.008, -0.005]) + terms @ [0.10, -0.10, 0.06, -0.06]
    selected = stratified_split((n, n), 88).ravel()
    x, values = xy[selected], clean[selected]
    args = (values, x, normal, [-0.29, -0.13], n, 8e-5, 2.56e-8)
    few = fit_flexible_edges(*args, maximum=2)
    more = fit_flexible_edges(*args, maximum=4)
    assert len(few[1]) == 2 and len(more[1]) == 4

    def error(fit):
        design = np.column_stack((affine, edge_terms(xy, *fit)))
        weight = np.linalg.lstsq(design[selected], values, rcond=1e-9)[0]
        return np.linalg.norm((design @ weight - clean)[~selected])

    assert error(more) < error(few) / 10


def test_curved_query_geometry_and_surface_groups_ignore_withheld_raw():
    n = 96
    _, _, affine, _ = geometry((n, n))
    terms = edge_terms(affine[:, 1:], 0.95, [[-0.1, 0.01, 0.12], [0.09, 0.06, 0.11]], 0.84 / n)
    raw = (0.08 + terms @ [0.11, -0.11]).reshape(n, n)
    cfa = np.tile([[0, 1], [1, 2]], (n // 2, n // 2))
    selected = stratified_split((n, n), 112)
    cfg = LocalWaveConfig(window=n, stride=n, edge_search="full-frame", background="curved_step")
    options = {
        "shot": 8e-5,
        "read": 2.56e-8,
        "config": cfg,
        "phase_bins": 8,
        "phase_edge_side": "validation",
        "guide_frequencies_xy": ((0.083, 0.047), (-0.047, 0.083)),
    }
    curved = fit_local_candidate(raw, cfa, selected, **options)
    withheld = fit_local_candidate(np.where(selected, raw, np.nan), cfa, selected, **options)
    assert curved.flexible_edges is not None
    assert curved.flexible_edges == withheld.flexible_edges
    np.testing.assert_array_equal(curved.full_cfa, withheld.full_cfa)
    fitted = SurfacePhaseOperator(curved, cfa, 0)
    assert len(np.unique(fitted.side)) == 3

    previous = fit_local_candidate(
        raw, cfa, selected, **(options | {"config": replace(cfg, background="parallel_step")})
    )
    error_new = np.linalg.norm((curved.conditional_null_cfa[0] - raw)[~selected])
    error_old = np.linalg.norm((previous.conditional_null_cfa[0] - raw)[~selected])
    assert error_new < error_old / 3
