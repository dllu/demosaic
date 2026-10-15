import torch

from demosaic.suite import observation, summarize


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
