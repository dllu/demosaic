"""Compare saved models at the original input-selected green-phase mesh peaks."""

import argparse
import sys
from pathlib import Path

import numpy as np
from green_phase_spectrum import green_pair
from report_green_phase_spectrum import sample_green
from train_directional_bank_trial import guard, read, ref, save

REPO = Path(__file__).resolve().parents[1]


def checked(binding):
    assert ref(binding["path"]) == binding
    return Path(binding["path"])


def prepare(root, primary):
    queue = read(primary / "queue-plan-v1.json")
    guard(queue)
    mesh = next(o for o in queue["observations"] if o["id"] == "mesh-profile3879")
    historical = REPO / "docs/results/green-phase-cross-spectrum-v1.json"
    old = read(historical)
    assert mesh["arrays"] == old["prospective_plan"]["inputs"]
    training = read(queue["training_plan"]["path"])
    v129 = read(checked(training["matched_control_results"]["train"]))
    methods = []
    for label, checkpoint in (
        ("V120", mesh["controls"][0]["checkpoint"]),
        ("V129 1k EMA", v129["checkpoint"]),
    ):
        control = next(
            c
            for c in mesh["controls"]
            if c.get("model", {}).get("label", c.get("label", "")).startswith(label)
        )
        checked(control["prediction"])
        methods.append(
            {"label": label, "checkpoint": checkpoint, "prediction": control["prediction"]}
        )
    v141_root = REPO / ".cache/quality-20261102/V141-native-v1"
    v141 = read(v141_root / "plan-v1.json")
    assert (
        next(o for o in v141["observations"] if o["id"] == mesh["id"])["arrays"] == mesh["arrays"]
    )
    collection = read(v141_root / "collection-v1.json")
    assert collection["plan"] == ref(v141_root / "plan-v1.json")
    pred = next(o["prediction"] for o in collection["observations"] if o["id"] == mesh["id"])
    methods.append({"label": "V141 1k EMA", "checkpoint": v141["checkpoint"], "prediction": pred})
    root.mkdir(parents=True, exist_ok=False)
    save(
        root / "plan-v1.json",
        {
            "primary_queue": ref(primary / "queue-plan-v1.json"),
            "primary_root": str(primary),
            "old_input_selection_and_results": ref(historical),
            "arrays": mesh["arrays"],
            "methods": methods,
            "candidate_label": queue["model_label"],
            "windows_and_fixed_peaks": old["executed_result"]["cases"],
            "operator": ref(__file__),
            "spectral_operator": ref(REPO / "scripts/green_phase_spectrum.py"),
            "scope": "Same two256px windows and all10 input-only peaks fixed Oct25; no new selection/window/profile/threshold or inference. Descriptive saved green-power/noisy green-power ratio includes observed noise; not signal transfer, correct mesh recovery, quality, significance or proof against hallucinations. IndependentISO100 differs in aperture/time and is notGT; not used in this extension.",
        },
    )


def direct_power(field, noise, y, x):
    """Independent weighted-plane least squares and nine explicit DFT rows."""
    h, w = field.shape
    yy, xx = np.meshgrid(np.linspace(-1, 1, h), np.linspace(-1, 1, w), indexing="ij")
    basis = np.column_stack((np.ones(h * w), xx.ravel(), yy.ravel()))
    window = np.outer(np.hanning(h), np.hanning(w))
    coefficients = np.linalg.lstsq(
        basis * window.ravel()[:, None], field.ravel() * window.ravel(), rcond=None
    )[0]
    residual = (field.ravel() - basis @ coefficients).reshape(h, w) * window
    sy, sx = np.indices((h, w))
    powers, variances = [], []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            ky, kx = (y + dy) % h, (x + dx) % w
            coefficient = np.sum(
                residual * np.exp(-2j * np.pi * (ky * sy / h + kx * sx / w))
            ) / np.sqrt(h * w)
            powers.append(abs(coefficient) ** 2)
            variances.append(noise[ky, kx])
    return float(np.mean(powers) / np.mean(variances))


def compare(root):
    assert "torch" not in sys.modules
    plan = read(root / "plan-v1.json")
    for name in (
        "operator",
        "spectral_operator",
        "old_input_selection_and_results",
        "primary_queue",
    ):
        checked(plan[name])
    primary = Path(plan["primary_root"])
    actual = read(primary / "plan-v1.json")
    guard(actual)
    assert actual["model_label"] == plan["candidate_label"]
    assert read(primary / "independent-audit-v1.json")["status"].startswith("passed")
    collection = read(primary / "collection-v1.json")
    assert collection["plan"] == ref(primary / "plan-v1.json")
    prediction = next(
        o["prediction"] for o in collection["observations"] if o["id"] == "mesh-profile3879"
    )
    methods = [
        *plan["methods"],
        {
            "label": plan["candidate_label"],
            "checkpoint": actual["checkpoint"],
            "prediction": prediction,
        },
    ]
    with np.load(checked(plan["arrays"]), allow_pickle=False) as z:
        packed, variance, colors = z["packed"][0], z["variance"][0], z["colors"][0]
    rows, maximum_difference = [], 0.0
    for case in plan["windows_and_fixed_peaks"]:
        x, y, w, h = case["context_xywh"]
        noise = variance[:, y // 2 : (y + h) // 2, x // 2 : (x + w) // 2]
        observed = green_pair(
            packed[:, y // 2 : (y + h) // 2, x // 2 : (x + w) // 2], noise, colors
        )
        indices = np.flatnonzero(colors == 1)
        for method in methods:
            rgb = np.load(checked(method["prediction"]), allow_pickle=False)
            assert rgb.shape == (1, 3, 768, 768) and np.isfinite(rgb).all()
            field = sample_green(rgb, case["context_xywh"])
            model = green_pair(field, noise, colors)
            for rank, peak in enumerate(case["peaks"], 1):
                ky, kx = peak["bin_yx"]
                raw = observed["noise_units_mean_phase_power"][ky, kx]
                np.testing.assert_allclose(
                    raw, peak["conditional_noise_units_phase_power"], rtol=1e-12, atol=1e-12
                )
                value = float(model["noise_units_mean_phase_power"][ky, kx])
                independent = np.mean(
                    [
                        direct_power(field[i], model["noise_variance"][j], ky, kx)
                        for j, i in enumerate(indices)
                    ]
                )
                np.testing.assert_allclose(value, independent, rtol=1e-9, atol=1e-11)
                maximum_difference = max(maximum_difference, abs(value - independent))
                rows.append(
                    {
                        "window": case["name"],
                        "rank": rank,
                        "bin_yx": peak["bin_yx"],
                        "native_frequency_xy": peak["native_frequency_xy"],
                        "method": method["label"],
                        "saved_power_over_observed_power": value / raw,
                    }
                )
    assert len(rows) == 40 and "torch" not in sys.modules
    save(
        root / "result-v1.json",
        {
            "status": "completed-fixed-peak-power-extension-with-independent-DFT-check",
            "plan": ref(root / "plan-v1.json"),
            "primary_collection": ref(primary / "collection-v1.json"),
            "methods": methods,
            "rows": rows,
            "independent_DFT_maximum_absolute_power_difference": maximum_difference,
            "independent_complex_coefficients_checked": 40 * 2 * 9,
            "new_neural_forwards": 0,
            "new_noise_observations": 0,
            "RAW_decodes": 0,
            "scope": plan["scope"],
        },
    )
    print(
        {
            "rows": len(rows),
            "independent_DFT_maximum_absolute_power_difference": maximum_difference,
        },
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "compare"))
    parser.add_argument("root", type=Path)
    parser.add_argument("--primary", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.root.resolve(), args.primary.resolve())
    else:
        compare(args.root.resolve())
