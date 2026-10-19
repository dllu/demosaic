"""Check exact normalized retrieval and held-out source partitioning."""

import importlib
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture
def retrieval(monkeypatch):
    monkeypatch.syspath_prepend(str(Path("scripts").resolve()))
    return importlib.import_module("retrieve_commons_content")


def test_all_candidates_ranked_by_normalized_cosine_with_stable_ties(retrieval):
    # A large vector must not outrank an aligned small vector. More than K
    # identical cosines must retain ID ordering across the partition boundary.
    database = np.array([[1.0, 0], [1, 0], [1, 0], [1, 0], [1000, 1000]])
    ranked = retrieval.nearest([[1, 0]], database, ["d", "b", "c", "a", "e"])[0]
    assert [index for index, _ in ranked] == [3, 1, 2]
    assert all(score == 1 for _, score in ranked)


def test_exhaustive_results_match_independent_dense_float64_cosines(retrieval):
    rng = np.random.default_rng(572)
    queries = rng.normal(size=(7, 11)).astype(np.float32)
    database = rng.normal(size=(37, 11)).astype(np.float32) * np.arange(1, 38)[:, None]
    identities = [f"id{i:02d}" for i in range(37)]
    actual = retrieval.nearest(queries, database, identities)
    for q, ranked in zip(queries, actual, strict=True):
        q = q.astype(np.float64)
        scores = [
            float(np.dot(q, d) / (np.linalg.norm(q) * np.linalg.norm(d)))
            for d in database.astype(np.float64)
        ]
        expected = sorted(range(37), key=lambda i: (-scores[i], identities[i]))[:3]
        assert [i for i, _ in ranked] == expected
        np.testing.assert_allclose(
            [s for _, s in ranked], [scores[i] for i in expected], rtol=0, atol=3e-16
        )


@pytest.mark.parametrize(
    "queries,database",
    [([[0.0, 0]], [[1.0, 1]]), ([[1.0, 0]], [[float("nan"), 1]]), ([[1.0]], [[1.0, 1]])],
)
def test_invalid_features_refused(retrieval, queries, database):
    with pytest.raises(ValueError):
        retrieval.nearest(queries, database, ["a"])


def test_small_and_empty_reference_pools_keep_complete_available_neighbors(retrieval):
    assert retrieval.nearest([[1.0, 1]], [[1.0, 1]], ["a"]) == [[(0, pytest.approx(1.0))]]
    assert retrieval.nearest([[1.0, 1]], np.empty((0, 2)), []) == [[]]


def test_new_holdout_buckets_are_only_anchors_and_never_training_queries(retrieval):
    rows = [
        {"id": str(i), "split": split} for i, split in enumerate(["val", "train", "test", "train"])
    ]
    assert retrieval.partitions(rows) == ([1, 3], [0, 2])
    with pytest.raises(ValueError, match="complete direct8x"):
        retrieval.partitions([{"id": "a", "split": "quarantine"}])
    with pytest.raises(ValueError, match="Duplicate"):
        retrieval.partitions([{"id": "a", "split": "train"}, {"id": "a", "split": "val"}])
