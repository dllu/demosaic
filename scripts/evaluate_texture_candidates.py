"""Matched candidate texture/flat diagnostics; full photographic review is separate."""

import argparse
import hashlib
import json
import math
import shutil
from pathlib import Path

import diagnose_texture_response as probe
import torch
import yaml

from demosaic.cfa import malvar
from demosaic.inference import load_checkpoint
from demosaic.precision import amp_context
from demosaic.reporting import display_crop, save_triplet
from demosaic.safety import writable_path
from demosaic.suite import observation


def flat_metrics(prediction, target, roi=probe.ROI):
    """Absolute error and false spatial/band energy, without a zero-signal ratio."""
    x, y, w, h = roi
    a = prediction[..., y : y + h, x : x + w].double()
    b = target[..., y : y + h, x : x + w].double()
    luma = a[:, 0] * 0.2126 + a[:, 1] * 0.7152 + a[:, 2] * 0.0722
    truth = b[:, 0] * 0.2126 + b[:, 1] * 0.7152 + b[:, 2] * 0.0722
    centered = luma - luma.mean((-2, -1), keepdim=True)
    spectrum = torch.fft.fft2(centered)
    fy = torch.fft.fftfreq(h, device=a.device)[:, None]
    fx = torch.fft.fftfreq(w, device=a.device)[None]
    radius = (fx.square() + fy.square()).sqrt()
    band = (radius >= 1 / 48) & (radius <= 0.22)
    level = truth.mean((-2, -1)).abs().clamp_min(1e-12)
    result = {
        "dc_bias_abs_rgb": (a.mean((-2, -1)) - b.mean((-2, -1))).abs().mean(1),
        "linear_srgb_rmse": (a - b).square().mean((1, 2, 3)).sqrt(),
        "spatial_luma_rms": centered.square().mean((-2, -1)).sqrt(),
        "relative_band_rms": (spectrum.abs().square() * band).sum((-2, -1)).sqrt()
        / (h * w)
        / level,
        "relative_peak_band_contrast": 2
        * spectrum.abs().masked_fill(~band, 0).amax((-2, -1))
        / (h * w)
        / level,
    }
    return {name: value.tolist() for name, value in result.items()}


@torch.inference_mode()
def main(checkpoints, output, *, device="cuda", precision="float16"):
    device = torch.device(device)
    if device.type == "cpu" and precision != "float32":
        raise ValueError("CPU evaluation requires explicit float32")
    torch.set_num_threads(4 if device.type == "cuda" else 2)
    if device.type == "cuda":
        torch.set_float32_matmul_precision("high")
        torch.backends.cudnn.benchmark = True
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    sources = {p.name: p.read_bytes() for p in Path("src/demosaic").glob("*.py")}
    (output / "source").mkdir()
    for name, value in sources.items():
        (output / "source" / name).write_bytes(value)
    for path in [Path(__file__), Path(probe.__file__)]:
        shutil.copyfile(path, output / path.name)
    protocol = yaml.safe_load(Path("configs/evaluation.yaml").read_text())
    models, provenance = [], []
    for index, checkpoint in enumerate(checkpoints):
        model, state = load_checkpoint(checkpoint, device)
        name = Path(state["config"]["run"]).name
        label = f"{index}:{name}:step-{state['step']}"
        models.append((label, model.eval()))
        if device.type == "cuda":
            model.to(memory_format=torch.channels_last)
        provenance.append(
            {
                "label": label,
                "checkpoint": str(checkpoint),
                "sha256": state["loaded_sha256"],
                "config": model.config.to_dict(),
            }
        )
        del state
    conditions = [
        next(c for c in protocol["conditions"] if c["name"] == name) for name in probe.CONDITIONS
    ]
    coordinates = torch.arange(probe.SIZE, dtype=torch.float32)
    specs = [
        ("carrier", level, contrast, period)
        for level in probe.LEVELS
        for contrast in probe.CONTRASTS
        for period in probe.PERIODS
    ]
    specs += [("flat", level, 0, None) for level in probe.LEVELS]
    rows, crops = [], []
    with (output / "per-case.jsonl").open("w") as stream:
        for kind, level, contrast, period in specs:
            if kind == "carrier":
                rgb = (
                    (level * (1 + contrast * (coordinates * (2 * math.pi / period)).cos()))[
                        None, None, None
                    ]
                    .expand(probe.DRAWS, 3, probe.SIZE, probe.SIZE)
                    .clone()
                )
                ids = [
                    f"carrier-l{level}-c{contrast}-p{period}-draw{i}" for i in range(probe.DRAWS)
                ]
            else:
                rgb = torch.full((probe.DRAWS, 3, probe.SIZE, probe.SIZE), level)
                ids = [f"flat-l{level}-draw{i}" for i in range(probe.DRAWS)]
            for condition in conditions:
                for pattern in protocol["patterns"]:
                    # Keep the original CPU Poisson draws; CUDA generation uses a
                    # different RNG stream. Every candidate sees these exact tensors.
                    cpu = observation(
                        rgb,
                        ids,
                        condition,
                        pattern,
                        protocol["white_balance"],
                        protocol["camera_to_srgb"],
                        probe.SEED,
                    )
                    batch = {name: value.to(device) for name, value in cpu.items()}
                    target = probe.linear_srgb(cpu["target"], cpu["wb"], cpu["matrix"])
                    noisy = malvar(cpu["packed"], cpu["colors"], cpu["wb"])
                    predictions = [("malvar", noisy)]
                    for label, model in models:
                        model.set_noise(condition["shot"], condition["read"])
                        with amp_context(device, dtype=precision):
                            prediction = model(
                                batch["packed"],
                                batch["variance"],
                                batch["colors"],
                                batch["wb"],
                                batch["matrix"],
                            )
                        assert torch.isfinite(prediction).all()
                        predictions.append((label, prediction.float().cpu()))
                    for label, prediction in predictions:
                        linear = probe.linear_srgb(prediction, cpu["wb"], cpu["matrix"])
                        metrics = (
                            probe.response_metrics(linear, target, period)
                            if kind == "carrier"
                            else flat_metrics(linear, target)
                        )
                        for i in range(probe.DRAWS):
                            row = {
                                "id": ids[i],
                                "kind": kind,
                                "level": level,
                                "contrast": contrast,
                                "period": period,
                                "condition": condition["name"],
                                "pattern": pattern,
                                "draw": i,
                                "model": label,
                                "metrics": {name: values[i] for name, values in metrics.items()},
                            }
                            rows.append(row)
                            stream.write(json.dumps(row, allow_nan=False) + "\n")
                        selected = kind == "carrier" and (level, contrast, period) in [
                            (0.01, 0.1, 8),
                            (0.18, 0.02, 16),
                        ]
                        selected |= kind == "flat" and level == 0.18
                        if (
                            selected
                            and label != "malvar"
                            and condition["name"] == "iso12800-prior"
                            and pattern == "RGGB"
                        ):
                            identity = next(p for p in provenance if p["label"] == label)
                            crops.append(
                                save_triplet(
                                    output,
                                    f"{ids[0]}:{label}",
                                    [
                                        (
                                            name,
                                            display_crop(
                                                value[:1],
                                                cpu["wb"][:1],
                                                cpu["matrix"][:1],
                                                probe.ROI,
                                            ),
                                        )
                                        for name, value in [
                                            ("Noisy (Malvar)", noisy),
                                            ("Restored", prediction),
                                            ("GT (analytic)", cpu["target"]),
                                        ]
                                    ],
                                    caption=f"{ids[0]} / {label}",
                                    metadata={
                                        "source_id": ids[0],
                                        "source": {
                                            "kind": kind,
                                            "level": level,
                                            "contrast": contrast,
                                            "period": period,
                                            "seed": probe.SEED,
                                        },
                                        "evaluation_tile_xywh": probe.ROI,
                                        "condition": condition,
                                        "pattern": pattern,
                                        "white_balance": protocol["white_balance"],
                                        "camera_to_srgb": protocol["camera_to_srgb"],
                                        "display_exposure": 1,
                                        "checkpoint_sha256": identity["sha256"],
                                        "model_label": label,
                                        "reference": "Exact analytic clean target; no real capture or fitted inference calibration.",
                                    },
                                )
                            )
                    stream.flush()
            print(
                json.dumps(
                    {
                        "kind": kind,
                        "level": level,
                        "contrast": contrast,
                        "period": period,
                        "rows": len(rows),
                    }
                ),
                flush=True,
            )
    assert len(rows) == (384 + 64) * (len(models) + 1) and len(crops) == 3 * len(models)
    assert all(Path("src/demosaic", name).read_bytes() == value for name, value in sources.items())
    result = {
        "scope": "Matched analytic carrier/flat diagnostic only; no natural-photo quality or SOTA claim. Same384 CPU-seeded carriers plus64 flat observations across2 conditions/4 CFAs/4 draws. Flat targets have zero texture; ADC duplicates do not add independent evidence.",
        "device": str(device),
        "precision": precision,
        "models": provenance,
        "native_crops": crops,
        "roi_xywh": probe.ROI,
        "flat_frequency_band_cycles_per_pixel": [1 / 48, 0.22],
        "limitations": "Known horizontal carriers are an artificial task; false-band/peak metrics quantify residual energy, not a complete hallucination detector. GPU FP16 results are not exact replay of earlier CPU FP32 neural scores. Full photo/real/GFX review remains required.",
        "source_files": {n: hashlib.sha256(v).hexdigest() for n, v in sources.items()},
        "driver_sha256": probe.sha(__file__),
        "carrier_summary": probe.summarize([r for r in rows if r["kind"] == "carrier"]),
        "flat_summary": probe.summarize([r for r in rows if r["kind"] == "flat"]),
    }
    (output / "summary.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": "complete", "summary": str(output / "summary.json")}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    parser.add_argument(
        "--precision", choices=["float32", "float16", "bfloat16"], default="float16"
    )
    args = parser.parse_args()
    main(args.checkpoint, args.output, device=args.device, precision=args.precision)
