"""Independent NumPy reconstruction/noise checks of prepared mixed controls."""

import argparse
from pathlib import Path

import numpy as np
from train_directional_bank_trial import read, ref, save


def ideal_target(template):
    y, x = np.mgrid[0:1024, 0:1024].astype(np.float64)
    x, y = (x + 0.5) / 2, (y + 0.5) / 2
    if template == "vertical-step":
        shape = x >= 272
    elif template == "narrow-bar":
        shape = (x >= 272) & (x < 280)
    elif template == "slanted-step":
        shape = x >= y / 4 + 220
    elif template == "striped-patch":
        shape = ((x >= 280) & (y >= 100) & (y < 412)) * (
            0.7 + 0.3 * np.sin(np.pi * x / 4) * np.sin(2 * np.pi * y / 9)
        )
    else:
        raise ValueError(template)
    scene = (
        np.array([0.003, 0.006, 0.004])[:, None, None]
        + np.array([0.05, 0.035, 0.08])[:, None, None] * shape
    )
    scene = scene.reshape(3, 512, 2, 512, 2).mean((2, 4))
    return scene / np.array([2.0, 1.0, 1.5])[:, None, None]


def main(root):
    point = root / "mixed-quiet-v1"
    plan_path = point / "plan-v1.json"
    plan = read(plan_path)
    assert ref(plan["design"]["path"]) == plan["design"]
    design = read(plan["design"]["path"])
    assert plan["actual_noise_draws"] == design["planned_noise_draws"] == 32
    patterns = {
        "RGGB": [0, 1, 1, 2],
        "BGGR": [2, 1, 1, 0],
        "GRBG": [1, 0, 2, 1],
        "GBRG": [1, 2, 0, 1],
    }
    rows = []
    maximum_target = maximum_ADC = maximum_mean_z = maximum_second_z = 0.0
    expected_targets = {template: ideal_target(template) for template in design["templates"]}
    for case in plan["observations"]:
        assert ref(case["arrays"]["path"]) == case["arrays"]
        a = dict(np.load(case["arrays"]["path"]))
        target = a["target"][0].astype(np.float64)
        assert target.shape == (3, 512, 512) and a["packed"].shape == a["variance"].shape == (
            1,
            4,
            256,
            256,
        )
        assert all(np.isfinite(v).all() for v in a.values())
        colors = patterns[case["pattern"]]
        np.testing.assert_array_equal(a["colors"], np.array([colors]))
        np.testing.assert_array_equal(a["wb"], np.array([[2.0, 1.0, 1.5]]))
        np.testing.assert_array_equal(a["matrix"], np.eye(3)[None])
        # Float64 analytic intent vs FP32 trigonometry/area pooling, not a
        # claim that two different floating-point sine implementations agree.
        difference = float(np.max(np.abs(target - expected_targets[case["template"]])))
        assert difference < 2e-6
        quiet = target[:, 176:336, 80:240]
        np.testing.assert_array_equal(quiet, np.broadcast_to(quiet[:, :1, :1], quiet.shape))
        np.testing.assert_allclose(
            quiet[:, 0, 0], np.array([0.003 / 2, 0.006, 0.004 / 1.5]), rtol=0, atol=1e-9
        )
        clean = np.stack(
            [
                target[channel, phase // 2 :: 2, phase % 2 :: 2]
                for phase, channel in enumerate(colors)
            ]
        )
        shot, read_noise = np.float32(case["noise"]["shot"]), np.float32(case["noise"]["read"])
        expected_variance = np.maximum(a["packed"], np.float32(0)) * shot + read_noise
        np.testing.assert_array_equal(a["variance"], expected_variance)
        raw = a["packed"][0].astype(np.float64)
        black = float(np.float32(0.03))
        ADC = (raw * (1 - black) + black) * 65535
        ADC_distance = float(np.max(np.abs(ADC - np.rint(ADC))))
        assert ADC_distance < 0.01 and np.all((ADC >= -0.01) & (ADC <= 65535.01))
        error = raw - clean
        n = raw.shape[-1] * raw.shape[-2]
        variance = float(shot) * clean + float(read_noise)
        mean_z = error.mean((-2, -1)) / np.sqrt(variance.mean((-2, -1)) / n)
        # Independent Poisson+Gaussian fourth central moment gives the
        # standard error of the raw second moment for heterogeneous signals.
        second_sem = np.sqrt((2 * variance**2 + float(shot) ** 3 * clean).mean((-2, -1)) / n)
        second_z = ((error**2).mean((-2, -1)) - variance.mean((-2, -1))) / second_sem
        assert np.max(np.abs(mean_z)) < 7 and np.max(np.abs(second_z)) < 7
        maximum_target = max(maximum_target, difference)
        maximum_ADC = max(maximum_ADC, ADC_distance)
        maximum_mean_z = max(maximum_mean_z, float(np.max(np.abs(mean_z))))
        maximum_second_z = max(maximum_second_z, float(np.max(np.abs(second_z))))
        rows.append(
            {
                "id": case["id"],
                "maximum_analytic_target_difference_DN16": difference * 65535,
                "maximum_ADC_grid_distance": ADC_distance,
                "noise_mean_standard_errors": mean_z.tolist(),
                "noise_second_moment_standard_errors": second_z.tolist(),
                "quiet_target_exactly_constant": True,
                "variance_map_bit_exact": True,
            }
        )
    assert len(rows) == 32
    dest = point / "independent-input-audit-v1.json"
    assert not dest.exists()
    save(
        dest,
        {
            "status": "pass-independent-analytic-target-and-noise-checks",
            "plan": ref(plan_path),
            "auditor": ref(__file__),
            "rows": rows,
            "maximum_target_difference_DN16": maximum_target * 65535,
            "target_tolerance_DN16": 2e-6 * 65535,
            "maximum_ADC_grid_distance": maximum_ADC,
            "maximum_noise_mean_standard_errors": maximum_mean_z,
            "maximum_noise_second_moment_standard_errors": maximum_second_z,
            "all32_quiet_ROIs_exactly_constant": True,
            "all32_variance_maps_bit_exact": True,
            "new_model_forwards": 0,
            "new_noise_draws": 0,
            "scope": "Ideal Float64 closed-form2x area target vs actual FP32 inputs. Seven-standard-error moment checks are diagnostics for the prepared finite samples, not proof of all camera-noise assumptions. Slanted-edge constant claim is limited to the declared quiet ROI.",
        },
    )
    print(
        "PASS32 controls; target difference DN16",
        maximum_target * 65535,
        "max mean/second Z",
        maximum_mean_z,
        maximum_second_z,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    main(parser.parse_args().root.resolve())
