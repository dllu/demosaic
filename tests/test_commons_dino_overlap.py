import hashlib
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest
import torch


def script():
    path = Path("scripts/audit_commons_dino_overlap.py")
    spec = importlib.util.spec_from_file_location("commons_content_audit", path)
    module = importlib.util.module_from_spec(spec)
    # Match the sibling-import path used by the actual script entry point.
    sys.path.insert(0, str(path.parent.resolve()))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


def test_center_linear_area_srgb_preprocessing_is_read_only(tmp_path):
    audit = script()
    array = np.zeros((256, 512, 3), dtype=np.uint16)
    array[:, :128] = 65535
    array[:, 128:384] = [12000, 24000, 36000]
    path = tmp_path / "cache.npy"
    np.save(path, array)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    row = {"id": "fixture", "cache": str(path), "cache_sha256": digest, "shape": list(array.shape)}
    value = audit.image_tensor(row)
    assert value.shape == (3, 192, 192) and value.dtype == torch.float32
    linear = np.array([12000, 24000, 36000], dtype=np.float64) / 65535
    expected = np.where(linear <= 0.0031308, 12.92 * linear, 1.055 * linear ** (1 / 2.4) - 0.055)
    np.testing.assert_allclose(
        value.numpy(), np.broadcast_to(expected[:, None, None], value.shape), atol=2e-7, rtol=0
    )
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    with pytest.raises(AssertionError):
        audit.image_tensor({**row, "cache_sha256": "0" * 64})


def test_three_cohort_retrieval_matches_independent_all_pair_float64_cosines():
    audit = script()
    generator = np.random.default_rng(427)
    vectors = generator.normal(size=(68, 8))
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors[4:8] = vectors[:4]
    vectors[8] = vectors[4]  # Explicit duplicate: ID must break the similarity tie.
    embeddings = vectors.astype(np.float32)
    queries = [{"id": f"q{i}"} for i in range(4)]
    train = [{"id": f"t{i:02}"} for i in range(64)]
    cohorts = {
        "first": {r["id"] for r in train[:16]},
        "larger": {r["id"] for r in train[:48]},
        "all": {r["id"] for r in train},
    }
    result = audit.neighbors(embeddings, train, queries, cohorts)
    for row in result:
        q = embeddings[row["query_index"]].astype(np.float64)
        candidates = []
        for index, identity in enumerate(train):
            if identity["id"] not in cohorts[row["cohort"]]:
                continue
            t = embeddings[4 + index].astype(np.float64)
            cosine = np.dot(q, t) / np.sqrt(np.dot(q, q) * np.dot(t, t))
            candidates.append((float(cosine), identity["id"]))
        expected = sorted(candidates, key=lambda r: (-r[0], r[1]))[row["rank"] - 1]
        assert row["train_id"] == expected[1]
        assert abs(row["cosine_F64"] - expected[0]) < 1e-14
