import torch

from demosaic.cfa import bilinear
from demosaic.suite import evaluate_panel, observation, summarize


def test_observation_pairs_noise_by_source_independently_of_batch_size():
    rgb = torch.rand(2, 3, 32, 32)
    case = {"name": "test", "exposure": 2, "shot": 0.001, "read": 1e-6}
    wb = [2.0, 1.0, 1.5]
    matrix = [[1.1, -0.05, -0.05], [-0.05, 1.1, -0.05], [-0.05, -0.05, 1.1]]
    first = observation(rgb, ["a", "b"], case, "GBRG", wb, matrix, 42)
    second = observation(rgb[1:], ["b"], case, "GBRG", wb, matrix, 42)
    torch.testing.assert_close(first["packed"][1:], second["packed"], atol=0, rtol=0)
    torch.testing.assert_close(first["target"][1:], second["target"], atol=0, rtol=0)


def test_suite_aggregates_per_source_and_retains_empty_region_counts():
    rows = []
    for model, bias in [("a", 2.0), ("b", 0.0)]:
        for identity in ["one", "two"]:
            for pattern in ["RGGB", "GBRG"]:
                rows.append(
                    {
                        "model": model,
                        "kind": "photo",
                        "id": identity,
                        "condition": "normal",
                        "pattern": pattern,
                        "metrics": {
                            "linear_psnr": 30.0 + bias,
                            "srgb_psnr": 25.0 + bias,
                            "srgb_ssim": 0.9,
                            "highlight_boundary_chroma_mae": None,
                        },
                    }
                )
    result = summarize(rows)
    assert len(result["groups"]) == 4
    assert result["overall"][0]["metrics"]["highlight_boundary_chroma_mae"]["count"] == 0
    delta = next(r for r in result["paired_comparisons"] if r["metric"] == "srgb_psnr")
    assert delta["sources"] == 2
    assert delta["mean_first_minus_second"] == 2
    assert delta["source_bootstrap_95_interval"] == [2.0, 2.0]


def test_suite_only_pairs_shared_sources_when_methods_have_different_coverage():
    rows = []
    for model, kind, identity in [
        ("full", "photo", "photo-one"),
        ("full", "synthetic", "pattern-one"),
        ("large-tile", "synthetic", "pattern-one"),
    ]:
        rows.append(
            {
                "model": model,
                "kind": kind,
                "id": identity,
                "condition": "adc-only",
                "pattern": "RGGB",
                "metrics": {"linear_psnr": 35.0, "srgb_psnr": 30.0, "srgb_ssim": 0.9},
            }
        )
    result = summarize(rows)
    assert len(result["overall"]) == 3
    assert len(result["paired_comparisons"]) == 3
    for comparison in result["paired_comparisons"]:
        assert comparison["kind"] == "synthetic"
        assert comparison["sources"] == 1
        assert comparison["mean_first_minus_second"] == 0


def test_training_panel_is_balanced_and_does_not_change_global_rng(tmp_path):
    import yaml

    class FlatData:
        def __init__(self):
            self.rows = [{"id": "flat"}]

        def __len__(self):
            return 1

        def __getitem__(self, index):
            return {"rgb": torch.full((3, 32, 32), 0.2)}

    class Interpolate(torch.nn.Module):
        def forward(self, packed, variance, colors, wb, matrix):
            return bilinear(packed, colors)

    config = {
        "patterns": ["RGGB", "GBRG"],
        "white_balance": [1.0, 1.0, 1.0],
        "camera_to_srgb": torch.eye(3).tolist(),
        "border": 2,
        "conditions": [{"name": "adc", "shot": 0, "read": 0, "exposure": 1}],
    }
    path = tmp_path / "panel.yaml"
    path.write_text(yaml.safe_dump(config))
    before = torch.get_rng_state()
    result = evaluate_panel(Interpolate(), FlatData(), path, "cpu", images=1)
    assert torch.equal(torch.get_rng_state(), before)
    assert result["panel_srgb_psnr"] > 100
    assert result["panel_srgb_ssim"] > 0.9999
    assert len(result["panel_cases"]) == 2
