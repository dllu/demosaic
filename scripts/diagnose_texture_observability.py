"""Known-carrier RAW evidence companion to the analytic texture-response probe."""

import argparse
import json
import math
from pathlib import Path

import diagnose_texture_response as probe
import torch
import yaml

from demosaic.cfa import mosaic, pack
from demosaic.data import camera_pair
from demosaic.safety import writable_path
from demosaic.suite import observation


def carrier_fit(observed, base, cosine, sine, variance):
    """WLS with four independent phase DC terms and common cos/sin contrast.

    All arrays are already cropped packed CFA. Base/frequency/variance are
    known only to this synthetic diagnostic. Independent-second-moment
    uncertainty is an approximation, not an information-theoretic bound.
    """
    if observed.ndim != 4 or observed.shape[1] != 4:
        raise ValueError("Expected a batch of four packed sensor phases")
    shape = observed.shape[1:]
    if any(tuple(v.shape) != shape for v in [base, cosine, sine, variance]):
        raise ValueError("Base, carriers and variance must match one packed sample")
    if not (variance > 0).all():
        raise ValueError("Independent variance approximation must be positive")
    background, co, si, var = (v.double().flatten() for v in [base, cosine, sine, variance])
    phase = torch.eye(4, dtype=torch.float64).repeat_interleave(shape[1] * shape[2], 0)
    design = torch.cat([phase, co[:, None], si[:, None]], 1) * background[:, None]
    gram = design.T @ (design / var[:, None])
    inverse = torch.linalg.inv(gram)
    beta = (inverse @ (design.T @ (observed.double().flatten(1).T / var[:, None]))).T
    return beta, float(inverse[4, 4].sqrt())


@torch.inference_mode()
def main(output):
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    sources = {
        str(p): p.read_bytes()
        for p in [
            Path(__file__),
            Path("scripts/diagnose_texture_response.py"),
            *Path("src/demosaic").glob("*.py"),
        ]
    }
    for name, value in sources.items():
        archived = (
            output / "source" / Path(name).relative_to(Path.cwd())
            if Path(name).is_absolute()
            else output / "source" / name
        )
        archived.parent.mkdir(parents=True, exist_ok=True)
        archived.write_bytes(value)
    protocol = yaml.safe_load(Path("configs/evaluation.yaml").read_text())
    coordinates = torch.arange(probe.SIZE, dtype=torch.float32)
    records = []
    for level in probe.LEVELS:
        for contrast in probe.CONTRASTS:
            for period in probe.PERIODS:
                angle = coordinates * (2 * math.pi / period)
                cosine = angle.cos()[None, None, None].expand(1, 1, probe.SIZE, probe.SIZE)
                sine = angle.sin()[None, None, None].expand_as(cosine)
                rgb = (level * (1 + contrast * cosine)).expand(probe.DRAWS, 3, -1, -1).clone()
                identities = [
                    f"carrier-l{level}-c{contrast}-p{period}-draw{i}" for i in range(probe.DRAWS)
                ]
                for name in probe.CONDITIONS:
                    condition = next(c for c in protocol["conditions"] if c["name"] == name)
                    for pattern in protocol["patterns"]:
                        batch = observation(
                            rgb,
                            identities,
                            condition,
                            pattern,
                            protocol["white_balance"],
                            protocol["camera_to_srgb"],
                            probe.SEED,
                        )
                        background, _ = camera_pair(
                            torch.full_like(rgb[:1], level),
                            torch.linalg.inv(batch["matrix"][:1]),
                            batch["wb"][:1],
                        )
                        base = mosaic(background, batch["colors"][:1])[0]
                        clean = mosaic(batch["target"], batch["colors"])[0]
                        variance = (
                            condition["shot"] * clean
                            + condition["read"]
                            + 1 / (12 * (0.97 * 65535) ** 2)
                        )
                        x, y, w, h = probe.ROI
                        region = (..., slice(y // 2, (y + h) // 2), slice(x // 2, (x + w) // 2))
                        beta, std = carrier_fit(
                            batch["packed"][region],
                            base[region],
                            pack(cosine)[0][region],
                            pack(sine)[0][region],
                            variance[region],
                        )
                        for i in range(probe.DRAWS):
                            records.append(
                                {
                                    "id": identities[i],
                                    "condition": name,
                                    "pattern": pattern,
                                    "level": level,
                                    "contrast": contrast,
                                    "period": period,
                                    "fitted_in_phase_gain": float(beta[i, 4]) / contrast,
                                    "fitted_quadrature_gain": float(beta[i, 5]) / contrast,
                                    "relative_contrast_std_approx": std,
                                    "known_carrier_snr_approx": contrast / std,
                                }
                            )
    assert len(records) == 384 and not torch.cuda.is_initialized()
    assert all(Path(name).read_bytes() == value for name, value in sources.items())
    result = {
        "scope": "Input-only companion on exactly the same384 seeded analytic observations as the model response probe, cropped to the same160px ROI. CPU FP64 WLS on raw CFA; no model, training, held-out image or inference calibration.",
        "method": "Four phase DC nuisances and a common known horizontal cos/sin carrier in physical camera units. Weights use clean analytic shot/read plus ADC16/.03-black quantization-variance approximation. Coefficient covariance is inverse weighted normal matrix.",
        "limitations": "Frequency, background, clean variance and carrier family are oracle information for this diagnostic. Approximate known-carrier SNR is not a bound for a generic denoiser, proof of natural-texture recoverability, or an exact confidence interval under clipped/quantized Poisson noise. It only checks that a coherent carrier has measurable evidence within the selected ROI.",
        "records": records,
        "roi_xywh": probe.ROI,
        "cuda_initialized": False,
        "source_files": {
            str(p): probe.sha(p)
            for p in [
                Path(__file__),
                Path("scripts/diagnose_texture_response.py"),
                *Path("src/demosaic").glob("*.py"),
            ]
        },
    }
    (output / "receipt.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"receipt": str(output / "receipt.json"), "records": len(records)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=probe.BASE / "benchmarks/weak-texture-observability-v1"
    )
    args = parser.parse_args()
    torch.set_num_threads(2)
    main(args.output)
