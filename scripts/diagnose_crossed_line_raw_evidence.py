"""Input-only oracle template fit on the saved procedural mesh/empty observations."""

import argparse
from pathlib import Path

import numpy as np
import torch
from train_directional_bank_trial import read, ref, save

from demosaic.cfa import mosaic


def template_fit(observed, present, empty, variance):
    values = [np.asarray(v, dtype=np.float64) for v in (observed, present, empty, variance)]
    shape = values[0].shape
    if (
        len(shape) != 3
        or shape[0] != 4
        or any(v.shape != shape or not np.isfinite(v).all() for v in values)
        or np.any(values[3] <= 0)
    ):
        raise ValueError("Require four packed finite phases and positive variance")
    observed, present, empty, variance = values
    h, w = shape[-2:]
    y, x = np.mgrid[-1 : 1 : complex(h), -1 : 1 : complex(w)]
    plane = np.stack([np.ones_like(x), x, y], -1).reshape(-1, 3)
    nuisance = np.zeros((4 * h * w, 12))
    for phase in range(4):
        nuisance[phase * h * w : (phase + 1) * h * w, phase * 3 : phase * 3 + 3] = plane
    deviation = (observed - empty).ravel() / np.sqrt(variance.ravel())
    signal = (present - empty).ravel() / np.sqrt(variance.ravel())
    nuisance /= np.sqrt(variance.ravel())[:, None]
    q = np.linalg.qr(nuisance, mode="reduced")[0]
    a, b = (v - q @ (q.T @ v) for v in (signal, deviation))
    energy = float(a @ a)
    if energy <= 1e-16:
        raise ValueError("Nonzero oracle template required")
    gain = float(a @ b / energy)
    std = energy**-0.5
    design = np.column_stack([nuisance, signal])
    independent = np.linalg.lstsq(design, deviation, rcond=None)[0]
    covariance = np.linalg.inv(design.T @ design)
    np.testing.assert_allclose(gain, independent[-1], atol=3e-12, rtol=2e-10)
    np.testing.assert_allclose(std, np.sqrt(covariance[-1, -1]), atol=3e-12, rtol=2e-10)
    return {
        "oracle_template_gain": gain,
        "gain_std_approx": std,
        "known_template_SNR_approx": 1 / std,
    }


def run(root):
    torch.set_num_threads(1)
    master = read(root / "plan-v1.json")
    binding = next(iter(master["models"].values()))
    assert ref(binding["path"]) == binding
    observations = read(binding["path"])["observations"]
    rows = []
    for observation in observations:
        if observation["noise"]["name"] != "iso6400-prior":
            continue
        assert ref(observation["arrays"]["path"]) == observation["arrays"]
        with np.load(observation["arrays"]["path"], allow_pickle=False) as archive:
            arrays = {k: archive[k] for k in archive.files}
        colors = torch.from_numpy(arrays["colors"])
        present, empty, truth = [
            mosaic(torch.from_numpy(arrays[k]), colors)[0].numpy().astype(np.float64)
            for k in ("target_present", "target_empty", "target")
        ]
        noise = observation["noise"]
        variance = noise["shot"] * truth + noise["read"] + 1 / (12 * (0.97 * 65535) ** 2)
        region = (..., slice(24, 104), slice(24, 104))
        rows.append(
            {
                "id": observation["id"],
                "seed": observation["seed"],
                "present": observation["present"],
                "pattern": observation["pattern"],
                **template_fit(
                    arrays["packed"][0][region], present[region], empty[region], variance[region]
                ),
            }
        )
    assert len(rows) == 32 and not torch.cuda.is_initialized()
    result = {
        "status": "completed-saved-RAW-oracle-template-diagnostic",
        "operator": ref(__file__),
        "input_plan": ref(root / "plan-v1.json"),
        "rows": rows,
        "native_ROI_xywh": [48, 48, 160, 160],
        "new_neural_calls": 0,
        "new_noise_observations": 0,
        "RAW_decodes": 0,
        "scope": "Same32 noisy procedural observations from64-input response diagnostic. Exact present/empty template and clean variance are oracle information. Weighted least squares removes separate affine nuisance planes in all4 packed phases; QR residualization independently matches joint13-column least squares and inverse normal-matrix approximate covariance. Known-template SNR is a second-moment approximation, not a generic denoiser bound, natural-detail recoverability proof or exact confidence interval under Poisson/ADC. No fitting/calibration enters model inference.",
    }
    save(root / "raw-evidence-v1.json", result)
    for seed in sorted({r["seed"] for r in rows}):
        group = [r for r in rows if r["seed"] == seed and r["present"]]
        print(
            seed,
            {
                k: float(np.mean([r[k] for r in group]))
                for k in ("oracle_template_gain", "gain_std_approx", "known_template_SNR_approx")
            },
        )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    run(p.parse_args().root.resolve())
