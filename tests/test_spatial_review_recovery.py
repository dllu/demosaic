import pytest
from review_v143_spatial_trial import completed_review_bindings
from train_directional_bank_trial import ref, save


def finished(root):
    point, flat = root / "V144", root / "V144-flat"
    for directory, count in ((point, 102), (flat, 48)):
        directory.mkdir(parents=True)
        save(directory / "plan-v1.json", {})
        save(
            directory / "collection-v1.json",
            {
                "plan": ref(directory / "plan-v1.json"),
                "counts": {"root": count, "encoder": count},
                "RNG_unchanged": True,
                "full_model_before": "model",
                "full_model_after": "model",
                "backbone_before": "DINO",
                "backbone_after": "DINO",
            },
        )
    paths = [
        point / "independent-audit-v1.json",
        flat / "independent-flat-audit-v1.json",
        point / "faint-detail-v1/independent-audit-v1.json",
        point / "camera-JPEG-v1/manifest-v1.json",
        root / "V144-flat-vs-V143/result-v1.json",
    ]
    for p in paths:
        p.parent.mkdir(exist_ok=True)
        save(p, {"status": "passed-independent-fixture"})
    return point, flat


def test_adopt_complete_review_without_constructing_a_neural_module(tmp_path, monkeypatch):
    import torch

    def forbidden(*args, **kwargs):
        raise AssertionError("Receipt adoption must not construct or replay a model")

    point, flat = finished(tmp_path)
    monkeypatch.setattr(torch.nn.Module, "__init__", forbidden)
    assert not (flat / "independent-audit-v1.json").exists()
    result = completed_review_bindings(tmp_path, "V144")
    assert result["flat_audit"] == ref(flat / "independent-flat-audit-v1.json")
    assert result["primary_audit"] == ref(point / "independent-audit-v1.json")
    assert len(result) == 5


@pytest.mark.parametrize(
    "key,value",
    [
        ("RNG_unchanged", False),
        ("full_model_after", "changed"),
        ("counts", {"root": 47, "encoder": 47}),
    ],
)
def test_incomplete_or_mutated_collection_cannot_be_adopted(tmp_path, key, value):
    from train_directional_bank_trial import read

    _, flat = finished(tmp_path)
    path = flat / "collection-v1.json"
    save(path, {**read(path), key: value})
    with pytest.raises(AssertionError):
        completed_review_bindings(tmp_path, "V144")
