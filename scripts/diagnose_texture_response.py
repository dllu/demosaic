"""Exact analytic weak-texture response; CPU only, no photographic quality claim."""

import argparse
import hashlib
import json
import math
import shutil
from pathlib import Path

import numpy as np
import torch
import yaml

from demosaic.cfa import malvar
from demosaic.inference import load_checkpoint
from demosaic.prior import wiener_packed
from demosaic.reference import load_rawnind
from demosaic.reporting import display_crop, save_triplet
from demosaic.safety import writable_path
from demosaic.suite import observation

BASE = Path("/mnt/external/demosaic")
SEED = 20261016
SIZE = 256
ROI = [48, 48, 160, 160]
LEVELS = [0.01, 0.18]
CONTRASTS = [0.02, 0.10]
PERIODS = [4, 8, 16]
CONDITIONS = ["adc-only", "iso12800-prior"]
DRAWS = 4


def sha(path):
    with Path(path).open("rb") as reader:
        return hashlib.file_digest(reader, "sha256").hexdigest()


def linear_srgb(rgb, wb, matrix):
    return torch.einsum(
        "bij,bjhw->bihw", matrix.double(), rgb.double() * wb.double()[..., None, None]
    )


def carrier_basis(period, roi=ROI):
    x, _y, w, h = roi
    angle = torch.arange(x, x + w, dtype=torch.float64) * (2 * math.pi / period)
    return torch.stack(
        [
            torch.ones(h, w, dtype=torch.float64),
            angle.cos()[None].expand(h, -1),
            angle.sin()[None].expand(h, -1),
        ],
        dim=-1,
    ).reshape(-1, 3)


def response_metrics(prediction, target, period, roi=ROI):
    """Fit DC/cos/sin per RGB channel; keep unrelated residual energy separate."""
    x, y, w, h = roi
    a = prediction[..., y : y + h, x : x + w].double().flatten(-2)
    b = target[..., y : y + h, x : x + w].double().flatten(-2)
    basis = carrier_basis(period, roi)
    inverse = torch.linalg.pinv(basis)
    beta_a, beta_b = (values @ inverse.T for values in [a, b])
    carrier_a, carrier_b = beta_a[..., 1:], beta_b[..., 1:]
    power = carrier_b.square().sum(-1).clamp_min(1e-24)
    gain = (carrier_a * carrier_b).sum(-1) / power
    cross = (carrier_b[..., 0] * carrier_a[..., 1] - carrier_b[..., 1] * carrier_a[..., 0]) / power
    residual = a - beta_a @ basis.T
    metrics = {
        "in_phase_gain": gain.mean(1),
        "gain_channel_std": gain.std(1, unbiased=False),
        "quadrature_gain": cross.mean(1),
        "amplitude_ratio": (carrier_a.square().sum(-1) / power).sqrt().mean(1),
        "dc_bias_abs": (beta_a[..., 0] - beta_b[..., 0]).abs().mean(1),
        "noncarrier_rms": residual.square().mean((1, 2)).sqrt(),
        "linear_srgb_rmse": (a - b).square().mean((1, 2)).sqrt(),
    }
    return {name: value.tolist() for name, value in metrics.items()}


def summarize(rows):
    groups = {}
    for row in rows:
        key = (row["level"], row["contrast"], row["period"], row["condition"], row["model"])
        groups.setdefault(key, []).append(row)
    return [
        {
            "level": key[0],
            "contrast": key[1],
            "period": key[2],
            "condition": key[3],
            "model": key[4],
            "cases": len(cases),
            "metrics": {
                name: {
                    "mean": float(np.mean([r["metrics"][name] for r in cases])),
                    "std": float(np.std([r["metrics"][name] for r in cases])),
                    "min": min(r["metrics"][name] for r in cases),
                    "max": max(r["metrics"][name] for r in cases),
                }
                for name in cases[0]["metrics"]
            },
        }
        for key, cases in sorted(groups.items())
    ]


@torch.inference_mode()
def main(output):
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    source_bytes = {p.name: p.read_bytes() for p in Path("src/demosaic").glob("*.py")}
    (output / "source").mkdir()
    for name, value in source_bytes.items():
        (output / "source" / name).write_bytes(value)
    shutil.copyfile(__file__, output / Path(__file__).name)
    protocol_path = Path("configs/evaluation.yaml")
    protocol = yaml.safe_load(protocol_path.read_text())
    conditions = [
        next(c for c in protocol["conditions"] if c["name"] == name) for name in CONDITIONS
    ]
    prior = json.loads(Path("docs/results/fresh-dino-capacity-3k-review.json").read_text())
    fresh = prior["workflow"]["checkpoints"]
    inputs = [
        (
            "retained-v43",
            BASE / "models/v43-step2000.pt",
            "0d74cf31fb1c7e3f97fc692c855a2ca0ee3ebf562b454e4f8b135c28fc0aa5c5",
        ),
        *[
            (label, Path(fresh[i]["path"]), fresh[i]["checkpoint_sha256"])
            for label, i in [("fresh-none", 0), ("fresh-dino-s", 1)]
        ],
    ]
    plan = {
        "scope": "Analytic horizontal sinusoid diagnostic only. CPU FP32; no training, photo selection, protected-final scoring or restoration-quality promotion.",
        "signal": "Neutral linear-sRGB level*(1+contrast*cos(2*pi*x/period)); exact native256 samples, no interpolation/PSF. Shared camera/noise/ADC via production observation().",
        "size": SIZE,
        "roi_xywh": ROI,
        "levels": LEVELS,
        "relative_contrasts": CONTRASTS,
        "periods_sensor_pixels": PERIODS,
        "conditions": conditions,
        "patterns": protocol["patterns"],
        "draws": DRAWS,
        "seed": SEED,
        "white_balance": protocol["white_balance"],
        "camera_to_srgb": protocol["camera_to_srgb"],
        "display_exposure": 1,
        "protocol_path": str(protocol_path),
        "protocol_sha256": sha(protocol_path),
        "inputs": [{"label": n, "path": str(p), "sha256": h} for n, p, h in inputs],
        "source_files": {
            name: hashlib.sha256(value).hexdigest() for name, value in source_bytes.items()
        },
        "driver_sha256": sha(__file__),
        "interpretation": "In-phase gain1 and quadrature0 match the reference carrier. Noncarrier RMS contains noise/structured artifacts, not signal contrast. Known-carrier projections are diagnostic measurements, never an inference calibration. Draw/pattern spread is not photographic or training-seed uncertainty.",
    }
    (output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    models, provenance = [], []
    for label, path, expected in inputs:
        assert sha(path) == expected
        model, state = load_checkpoint(path, "cpu")
        assert state["loaded_sha256"] == expected
        models.append((label, model.eval()))
        provenance.append(
            {
                "label": label,
                "checkpoint_sha256": expected,
                "step": state["step"],
                "config": model.config.to_dict(),
            }
        )
        del state
    raw_root = BASE / "references/rawnind"
    raw = load_rawnind(raw_root, gain_mode="cfa-channel", device="cpu")
    models.append(("rawnind-channel", raw))
    provenance.append(
        {
            "label": "rawnind-channel",
            "checkpoint_sha256": sha(raw_root / "utnet2-bayer.pt"),
            "code_sha256": sha(raw_root / "raw_denoiser.py"),
            "gain": "Observed-CFA channel least squares, no target fitting; synthetic global ADC units.",
        }
    )
    assert all(p.device.type == "cpu" for _, model in models for p in model.parameters())
    coordinates = torch.arange(SIZE, dtype=torch.float32)
    rows, crops = [], []
    for level in LEVELS:
        for contrast in CONTRASTS:
            for period in PERIODS:
                rgb = (
                    (level * (1 + contrast * (coordinates * (2 * math.pi / period)).cos()))[
                        None, None, None
                    ]
                    .expand(DRAWS, 3, SIZE, SIZE)
                    .clone()
                )
                identities = [
                    f"carrier-l{level}-c{contrast}-p{period}-draw{i}" for i in range(DRAWS)
                ]
                for condition in conditions:
                    for pattern in protocol["patterns"]:
                        batch = observation(
                            rgb,
                            identities,
                            condition,
                            pattern,
                            protocol["white_balance"],
                            protocol["camera_to_srgb"],
                            SEED,
                        )
                        target = linear_srgb(batch["target"], batch["wb"], batch["matrix"])
                        noisy = malvar(batch["packed"], batch["colors"], batch["wb"])
                        predictions = [
                            ("malvar", noisy),
                            (
                                "wiener7",
                                malvar(
                                    wiener_packed(batch["packed"], batch["variance"], 7),
                                    batch["colors"],
                                    batch["wb"],
                                ),
                            ),
                        ]
                        for label, model in models:
                            if hasattr(model, "set_noise"):
                                model.set_noise(condition["shot"], condition["read"])
                            prediction = model(
                                batch["packed"],
                                batch["variance"],
                                batch["colors"],
                                batch["wb"],
                                batch["matrix"],
                            )
                            assert (
                                prediction.shape == target.shape
                                and torch.isfinite(prediction).all()
                            )
                            predictions.append((label, prediction))
                        for label, prediction in predictions:
                            metrics = response_metrics(
                                linear_srgb(prediction, batch["wb"], batch["matrix"]),
                                target,
                                period,
                            )
                            for i in range(DRAWS):
                                rows.append(
                                    {
                                        "id": identities[i],
                                        "draw": i,
                                        "level": level,
                                        "contrast": contrast,
                                        "period": period,
                                        "condition": condition["name"],
                                        "pattern": pattern,
                                        "model": label,
                                        "metrics": {k: v[i] for k, v in metrics.items()},
                                    }
                                )
                            selected = (level, contrast, period) in [
                                (0.01, 0.10, 8),
                                (0.18, 0.02, 16),
                            ]
                            if (
                                selected
                                and condition["name"] == "iso12800-prior"
                                and pattern == "RGGB"
                                and label != "malvar"
                            ):
                                checkpoint = next(
                                    (
                                        r["checkpoint_sha256"]
                                        for r in provenance
                                        if r["label"] == label
                                    ),
                                    None,
                                )
                                crops.append(
                                    save_triplet(
                                        output,
                                        f"{identities[0]}:{label}",
                                        [
                                            (
                                                name,
                                                display_crop(
                                                    value[:1],
                                                    batch["wb"][:1],
                                                    batch["matrix"][:1],
                                                    ROI,
                                                ),
                                            )
                                            for name, value in [
                                                ("Noisy (Malvar)", noisy),
                                                (label, prediction),
                                                ("GT (analytic)", batch["target"]),
                                            ]
                                        ],
                                        caption=f"{identities[0]} / {label}: exact synthetic carrier",
                                        metadata={
                                            "source_id": identities[0],
                                            "source": {
                                                "generation": plan["signal"],
                                                "level": level,
                                                "relative_contrast": contrast,
                                                "period_sensor_pixels": period,
                                                "seed": SEED,
                                                "draw": 0,
                                            },
                                            "evaluation_tile_xywh": ROI,
                                            "condition": condition,
                                            "pattern": pattern,
                                            "white_balance": protocol["white_balance"],
                                            "camera_to_srgb": protocol["camera_to_srgb"],
                                            "checkpoint_sha256": checkpoint,
                                            "method": label,
                                            "display_exposure": 1,
                                            "reference": "Exact analytic clean target; no real capture or model-generated GT.",
                                        },
                                    )
                                )
                print(
                    json.dumps(
                        {
                            "signal_done": {"level": level, "contrast": contrast, "period": period},
                            "rows": len(rows),
                        }
                    ),
                    flush=True,
                )
    assert len(rows) == 12 * 2 * 4 * DRAWS * 6 and len(crops) == 10
    assert all(
        Path("src/demosaic", name).read_bytes() == value for name, value in source_bytes.items()
    )
    assert not torch.cuda.is_initialized()
    result = {
        **plan,
        "models": provenance,
        "device": "cpu",
        "precision": "float32",
        "cuda_initialized": False,
        "summary": summarize(rows),
        "native_crops": crops,
        "limitations": "Horizontal periodic neutral carriers at one size/camera matrix only;12 signals/2 noise conditions/4 CFA layouts/4 draws. Signal presence/frequency is known only to the diagnostic. This cannot establish natural-texture recovery, SOTA, convergence or GPU FP16 behavior. Retained V43 has different training history; only fresh-none/fresh-dino-s form a matched trained comparison.",
    }
    (output / "per-case.jsonl").write_text(
        "".join(json.dumps(row, allow_nan=False) + "\n" for row in rows)
    )
    (output / "summary.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": "complete", "summary": str(output / "summary.json")}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=BASE / "benchmarks/weak-texture-response-v1")
    args = parser.parse_args()
    torch.set_num_threads(2)
    main(args.output)
