"""Probe uniform-field preprocessing without a neural network or output fitting.

The inverse of the spatially averaged GAT/Malvar field assumes a constant scene.
It is a numerical diagnostic, not a proposed photographic denoiser or correction.
"""

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
from prepare_color_grid import sha, validate

import demosaic.pretrained_rgb as frontend
from demosaic.cfa import malvar
from demosaic.safety import writable_path
from demosaic.vst import GeneralizedAnscombe


def read(path):
    return json.loads(Path(path).read_text())


def independent_inverse(z, transform):
    """NumPy64 scalar interpolation/tail, using the same numerical GAT table."""
    z = np.asarray(z, dtype=np.float32).astype(np.float64)
    expected, means = transform.expected.numpy(), transform.means.numpy()
    index = np.clip(np.searchsorted(expected, z), 1, len(means) - 1)
    left, right = expected[index - 1], expected[index]
    value = means[index - 1] + (z - left) / (right - left) * (means[index] - means[index - 1])
    algebraic = z * math.sqrt(transform.q) + z**2 / 4
    anchor = expected[-1] * math.sqrt(transform.q) + expected[-1] ** 2 / 4
    correction = means[-1] - anchor - 0.25
    tail = algebraic + 0.25 + correction * anchor / np.maximum(algebraic, anchor)
    return (np.where(z > expected[-1], tail, value) * transform.shot).astype(np.float32)


def descriptive(values):
    return {
        "mean": float(np.mean(values)),
        "p95": float(np.quantile(values, 0.95)),
        "maximum": float(np.max(values)),
    }


@torch.inference_mode()
def main(inputs, saved_report, output):
    assert not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    plan = read(inputs)
    validate(plan)
    saved = read(saved_report)
    old = read(saved["plan"])
    assert sha(saved["plan"]) == saved["plan_sha256"]
    assert old["input_plan_sha256"] == sha(inputs) and old["cases"] == plan["cases"]
    previous = {(r["model_index"], r["case"]): r for r in saved["results"]}
    assert len(previous) == 1176 * len(saved["checkpoints"])
    output = writable_path(output)
    if output.exists():
        raise ValueError("Physical diagnostic exists; choose a new output")
    source_dir = Path(frontend.__file__).parent
    source_files = [
        source_dir / n
        for n in ["pretrained_rgb.py", "vst.py", "cfa.py", "prior.py", "color.py", "precision.py"]
    ]
    sources = {str(p): sha(p) for p in source_files}
    profiles = {}
    results, groups = [], defaultdict(list)
    for i, case in enumerate(plan["cases"]):
        assert sha(case["arrays"]) == case["sha256"]
        with np.load(case["arrays"], allow_pickle=False) as values:
            b = {k: torch.from_numpy(values[k].copy()) for k in values.files}
        assert torch.equal(b["target"], b["target"][..., :1, :1].expand_as(b["target"]))
        condition = case["condition"]
        key = condition["shot"], condition["read"]
        if key not in profiles:
            profiles[key] = GeneralizedAnscombe(*key) if key[0] else None
        transform = profiles[key]
        packed = b["packed"]
        z = packed if transform is None else transform(packed)
        gat_difference, inverse_difference = 0.0, 0.0
        if transform is not None:
            counts = np.maximum(packed.numpy().astype(np.float64) / transform.shot, -transform.q)
            expected = (
                2 * counts / (np.sqrt(counts + transform.q) + math.sqrt(transform.q))
            ).astype(np.float32)
            gat_difference = float(np.max(np.abs(expected - z.numpy())))
            assert gat_difference < 2e-6
        proxy = torch.zeros_like(z) if not any(key) else torch.ones_like(z)
        rgb = malvar(z, b["colors"], b["wb"] if transform is None else None)
        rgb, normalized, noise, _, offset, span = frontend.physical_rgb_features(
            z, proxy, b["colors"], b["wb"], b["matrix"], rgb=rgb, stabilized=True
        )
        assert all(torch.isfinite(v).all() for v in [rgb, normalized, noise, offset, span])
        roundtrip = float((normalized * span + offset - rgb).abs().max())
        assert roundtrip < 1e-5
        dc = rgb[..., 48:208, 48:208].double().mean((2, 3), keepdim=True).float()
        estimate = dc if transform is None else transform.inverse(dc)
        if transform is not None:
            expected = independent_inverse(dc.numpy(), transform)
            inverse_difference = float(np.max(np.abs(expected - estimate.numpy())))
            assert inverse_difference < 1e-7
        truth = b["target"][0, :, 0, 0].double().numpy()
        phase_means = packed[..., 24:104, 24:104].numpy().astype(np.float64).mean((0, 2, 3))
        sensor_mean = np.array([phase_means[b["colors"].numpy()[0] == c].mean() for c in range(3)])
        error = estimate.numpy().reshape(3).astype(np.float64) - truth
        row = {
            "case": i,
            "palette": case["palette"],
            "source": case["source"],
            "condition": condition["name"],
            "pattern": case["pattern"],
            "uniform_GAT_MHC_mean_estimate_error_camera_RGB": error.tolist(),
            "direct_CFA_mean_error_camera_RGB": (sensor_mean - truth).tolist(),
            "normalization_roundtrip_max_abs_transformed_error": roundtrip,
            "NumPy64_GAT_forward_max_abs_difference": gat_difference,
            "NumPy64_inverse_of_mean_max_abs_difference": inverse_difference,
            "normalized_noise_max": float(noise.max()),
            "offset": float(offset.flatten()[0]),
            "span": float(span.flatten()[0]),
            "saved_model_max_abs_channel_mean_error": {
                m["label"]: max(abs(v) for v in previous[mi, i]["metrics"]["camera_RGB_mean_error"])
                for mi, m in enumerate(saved["checkpoints"])
            },
        }
        groups[condition["name"], case["source"]["saturation"], case["source"]["peak"]].append(row)
        results.append(row)
        if (i + 1) % 196 == 0:
            print(json.dumps({"completed": i + 1, "total": 1176}), flush=True)
    summaries = []
    for key, rows in sorted(groups.items()):
        summaries.append(
            {
                "condition": key[0],
                "saturation": key[1],
                "peak": key[2],
                "cases": len(rows),
                "uniform_GAT_MHC_mean_max_abs_channel_error": descriptive(
                    [
                        max(abs(v) for v in r["uniform_GAT_MHC_mean_estimate_error_camera_RGB"])
                        for r in rows
                    ]
                ),
                "direct_CFA_mean_max_abs_channel_error": descriptive(
                    [max(abs(v) for v in r["direct_CFA_mean_error_camera_RGB"]) for r in rows]
                ),
                "saved_model_max_abs_channel_mean_error": {
                    m["label"]: descriptive(
                        [r["saved_model_max_abs_channel_mean_error"][m["label"]] for r in rows]
                    )
                    for m in saved["checkpoints"]
                },
            }
        )
    assert len(results) == 1176 and len(summaries) == 18
    assert all(sha(p) == s for p, s in sources.items()) and not torch.cuda.is_initialized()
    output.mkdir(parents=True, exist_ok=False)
    (output / "source").mkdir()
    for p in [Path(__file__), *source_files]:
        (output / "source" / p.name).write_bytes(p.read_bytes())
    result = {
        "status": "completed-CPU-uniform-field-physical-frontend-diagnostic",
        "input_plan": str(inputs),
        "input_plan_sha256": sha(inputs),
        "saved_model_report": str(saved_report),
        "saved_model_report_sha256": sha(saved_report),
        "source_files": sources,
        "driver_sha256": sha(__file__),
        "rows": results,
        "groups": summaries,
        "CUDA_initialized": False,
        "scope": "All fixed1176 uniform fields, no neural model loaded/inferred, new random draws or source photographs. Rebuild production GAT/Malvar/normalization; invert the spatial mean under an explicit uniform-scene assumption. Direct CFA mean is another constant-scene estimator. No target fitting, learned-output correction or proposed photographic denoiser. Independent NumPy forward/scalar interpolation uses the same numerical expectation table, not an independent derivation of that table. Finite numerical checks cannot identify why the trained CNN shifts color or establish photo quality.",
    }
    (output / "report.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"report": str(output / "report.json"), "cases": len(results)}), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inputs", required=True, type=Path)
    p.add_argument("--saved-report", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    main(a.inputs, a.saved_report, a.output)
