import json

import plot_version_history as history
import pytest


def photo_study(tmp_path, monkeypatch, filename):
    results = tmp_path / "docs/results"
    results.mkdir(parents=True)
    summary = {
        "models": [{"label": "V104", "sha256": "a" * 64, "step": 20000}],
        "overall": [
            {"model": "V104", "kind": "photo", "metrics": {"srgb_psnr": {"mean": 36.8}}},
            {"model": "V104", "kind": "synthetic", "metrics": {"srgb_psnr": {"mean": 50.0}}},
        ],
        "sources": 443,
        "precision": "float32",
    }
    (results / filename).write_text(json.dumps({"runs": {"full427": summary}}))
    monkeypatch.setattr(history, "REPO", tmp_path)
    monkeypatch.setattr(history, "STUDIES", [(filename, [104], "review.md")])


def test_declared_photo_panel_does_not_fabricate_camera_scores(tmp_path, monkeypatch):
    photo_study(tmp_path, monkeypatch, "v104-reviewed-corpus-photo-statistics-v1.json")
    points, evidence = history.collect()
    assert len(evidence) == len(points) == 1
    assert history.metric_points(points, "photo_srgb_PSNR") == ([104], [36.8])
    assert history.metric_points(points, "known_CFA_PSNR") == ([], [])
    assert history.metric_points(points, "unseen_CFA_PSNR") == ([], [])
    assert history.metric_text(points[0], "known_CFA_PSNR") == "pending"


def test_undeclared_missing_camera_panels_still_fail(tmp_path, monkeypatch):
    photo_study(tmp_path, monkeypatch, "complete-study.json")
    with pytest.raises(AssertionError):
        history.collect()


def test_declared_camera_panels_do_not_fabricate_a_full_photo_score(tmp_path, monkeypatch):
    results = tmp_path / "docs/results"
    results.mkdir(parents=True)
    filename = "v111-camera-complete-v1.json"
    comparisons = [
        {
            "panel": panel,
            "kind": "real",
            "metric": "sensor_psnr",
            "sources": count,
            "first": "V111-final20000",
            "second": "V104-final20000",
            "first_checkpoint_sha256": "a" * 64,
            "second_checkpoint_sha256": "b" * 64,
            "first_source_balanced_mean": value,
            "second_source_balanced_mean": 54.0,
        }
        for panel, count, value in [("known", 4, 54.25), ("unseen", 5, 53.94)]
    ]
    (results / filename).write_text(json.dumps({"comparisons": comparisons}))
    monkeypatch.setattr(history, "REPO", tmp_path)
    monkeypatch.setattr(history, "STUDIES", [(filename, [111], "review.md")])
    points, _ = history.collect()
    assert history.metric_points(points, "known_CFA_PSNR") == ([111], [54.25])
    assert history.metric_points(points, "unseen_CFA_PSNR") == ([111], [53.94])
    assert history.metric_points(points, "photo_srgb_PSNR") == ([], [])
    assert history.metric_text(points[0], "photo_srgb_PSNR") == "pending"


@pytest.mark.parametrize("invalid", [None, float("nan"), float("inf"), True])
def test_unfinished_or_invalid_values_cannot_be_plotted_as_measurements(invalid):
    with pytest.raises(ValueError, match="must be finite"):
        history.metric_points([{"version": 104, "photo_srgb_PSNR": invalid}], "photo_srgb_PSNR")


def test_each_camera_series_uses_only_its_own_completed_endpoints():
    points = [
        {"version": 102, "known_CFA_PSNR": 54.2, "unseen_CFA_PSNR": 53.9},
        {"version": 104, "known_CFA_PSNR": 54.3},
    ]
    assert history.metric_points(points, "known_CFA_PSNR") == ([102, 104], [54.2, 54.3])
    assert history.metric_points(points, "unseen_CFA_PSNR") == ([102], [53.9])
