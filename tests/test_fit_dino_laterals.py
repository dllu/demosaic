import hashlib
import json

import fit_dino_laterals as fitting
import numpy as np
import pytest


def test_known_orthogonal_system_has_expected_ridge_shrinkage():
    z = np.array([[1 if (i >> j) & 1 else -1 for j in range(4)] for i in range(16)])
    center = np.array([2, -3, 0, 100])
    x = z*np.array([.1, 1, 10, 100]) + center
    w = np.array([[.3, -.7, .2, 1.1], [-1, .5, .8, .01]])
    b = np.array([.2, -.5])
    for ridge in [0, .001, 1]:
        actual_w, actual_b = fitting.fit_affine(x, x@w.T+b, ridge)
        expected_w = w/(1+ridge)
        expected_b = b+center@(w-expected_w).T
        np.testing.assert_allclose(actual_w, expected_w, atol=1e-6, rtol=0)
        np.testing.assert_allclose(actual_b, expected_b, atol=2e-6, rtol=0)


def test_constant_input_channels_fit_intercept_without_division_by_zero():
    w, b = fitting.fit_affine(np.ones((4, 3)), np.tile([.1, .2], (4, 1)))
    np.testing.assert_array_equal(w, np.zeros((2, 3)))
    np.testing.assert_allclose(b, [.1, .2])


@pytest.mark.parametrize("ridge", [-1, np.inf, np.nan])
def test_invalid_ridge_is_rejected(ridge):
    with pytest.raises(ValueError, match="finite"):
        fitting.fit_affine(np.ones((3, 2)), np.ones((3, 1)), ridge)


def test_refit_excludes_check_sources_and_verifies_training_provenance(tmp_path, monkeypatch):
    monkeypatch.setattr(fitting, "writable_path", lambda p: p)
    path = tmp_path/"pairs.npz"
    np.savez(path, **{f"{kind}{i}": np.array([[-1.], [1.]]) for i in range(4) for kind in ["X", "Y"]})
    binding = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    record = {"sample": {"source_record": {"split": "train"}, "source_id": "fit", "partition": "fit"}, "arrays": binding}
    # The check archive deliberately does not exist. It must never be loaded.
    check = {"sample": {"source_record": {"split": "train"}, "source_id": "check", "partition": "feature-check"}, "arrays": {"path": "missing", "sha256": "unused"}}
    report = tmp_path/"features.json"
    report.write_text(json.dumps({"records": [record, check]}))
    result = fitting.refit(report, tmp_path/"fit.npz")
    assert result["fit_sources"] == 1 and result["feature_check_sources_used_for_fit"] == 0
    record["sample"]["source_record"]["split"] = "val"
    report.write_text(json.dumps({"records": [record]}))
    with pytest.raises(ValueError, match="training"):
        fitting.refit(report, tmp_path/"forbidden.npz")
    assert not (tmp_path/"forbidden.npz").exists()
