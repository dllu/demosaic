"""Training-only frozen DINO input-sensitivity diagnostic; no restoration claim."""

import argparse
import hashlib
import json
import random
import shutil
from pathlib import Path

import numpy as np
import torch
import yaml
from torch.nn import functional as F

from demosaic.cfa import malvar, mosaic
from demosaic.color import render
from demosaic.model import DinoContext, ModelConfig
from demosaic.prior import wiener_packed
from demosaic.reporting import display_crop, save_triplet
from demosaic.safety import writable_path
from demosaic.suite import observation

BASE = Path("/mnt/external/demosaic")
MANIFEST = BASE / "audits/commons-bin4-frozen44732-v1/manifest.jsonl"
MANIFEST_SHA = "22d07361d1b67de077560f6b8571388db699ead2d164201c71fe71ec5755f4c3"
REVISION = "114c1379950215c8b35dfcd4e90a5c251dde0d32"
SEED = 20261016
CONDITIONS = ["adc-only", "iso100-prior", "iso12800-prior", "shadows"]


def sha(path):
    with Path(path).open("rb") as reader:
        return hashlib.file_digest(reader, "sha256").hexdigest()


def feature_metrics(candidate, reference):
    """Patch-vector agreement, with and without each channel's spatial DC."""
    metrics = {}
    for prefix, center in [("", False), ("spatial_centered_", True)]:
        a, b = candidate.double(), reference.double()
        if center:
            a = a - a.mean((-2, -1), keepdim=True)
            b = b - b.mean((-2, -1), keepdim=True)
        metrics[prefix + "cosine"] = F.cosine_similarity(a, b, dim=1).mean((-2, -1))
        metrics[prefix + "relative_l2"] = (
            (a - b).square().sum((1, 2, 3)) / b.square().sum((1, 2, 3)).clamp_min(1e-24)
        ).sqrt()
    return {name: value.tolist() for name, value in metrics.items()}


def summarize(rows):
    """Paired bootstrap over source photographs; CFA cases stay together."""
    groups = {}
    for row in rows:
        key = (row["condition"], row["layer"], row["reference"])
        groups.setdefault(key, []).append(row)
    result = []
    for (condition, layer, reference), cases in sorted(groups.items()):
        identities = sorted({r["id"] for r in cases})
        means = {}
        for method in ["noisy-malvar", "wiener7-malvar", "clean-malvar"]:
            means[method] = {
                name: float(np.mean([r["metrics"][name] for r in cases if r["method"] == method]))
                for name in cases[0]["metrics"]
            }
        differences = {}
        for metric in cases[0]["metrics"]:
            by_source = []
            for identity in identities:
                values = {
                    method: np.mean(
                        [
                            r["metrics"][metric]
                            for r in cases
                            if r["id"] == identity and r["method"] == method
                        ]
                    )
                    for method in ["noisy-malvar", "wiener7-malvar"]
                }
                by_source.append(values["wiener7-malvar"] - values["noisy-malvar"])
            values = np.asarray(by_source)
            generator = np.random.default_rng(SEED)
            resamples = values[generator.integers(0, len(values), (4000, len(values)))].mean(1)
            differences[metric] = {
                "mean": float(values.mean()),
                "source_bootstrap_95": np.quantile(resamples, [0.025, 0.975]).tolist(),
                "sources_positive": int((values > 0).sum()),
            }
        result.append(
            {
                "condition": condition,
                "layer": layer,
                "reference": reference,
                "sources": len(identities),
                "means": means,
                "wiener_minus_noisy": differences,
            }
        )
    return result


@torch.inference_mode()
def main(output, count):
    from huggingface_hub import try_to_load_from_cache

    if count < 2:
        raise ValueError("At least two training photographs are required")
    assert sha(MANIFEST) == MANIFEST_SHA
    protocol_path = Path("configs/evaluation.yaml")
    protocol = yaml.safe_load(protocol_path.read_text())
    conditions = [
        next(c for c in protocol["conditions"] if c["name"] == name) for name in CONDITIONS
    ]
    records = [json.loads(line) for line in MANIFEST.read_text().splitlines()]
    eligible = sorted(
        [row for row in records if row["split"] == "train" and min(row["shape"][:2]) >= 512],
        key=lambda row: row["id"],
    )
    selected = random.Random(SEED).sample(eligible, count)
    sources, images = [], []
    for record in selected:
        path = MANIFEST.parent / record["cache"]
        assert record["bin_factor"] == 4 and record["color_space"] == "linear-sRGB"
        assert sha(path) == record["cache_sha256"]
        array = np.load(path, mmap_mode="r")
        assert array.dtype == np.uint16 and list(array.shape) == record["shape"]
        rng = random.Random(f"{SEED}:{record['id']}")
        y, x = rng.randrange(array.shape[0] - 511), rng.randrange(array.shape[1] - 511)
        rgb = torch.from_numpy(array[y : y + 512, x : x + 512].copy().astype(np.float32))
        rgb = F.avg_pool2d(rgb.permute(2, 0, 1)[None] / 65535, 2)
        images.append(rgb)
        sources.append({**record, "cache_roi_xywh": [x, y, 512, 512], "final_area_downsample": 2})
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    source_bytes = {p.name: p.read_bytes() for p in Path("src/demosaic").glob("*.py")}
    (output / "source").mkdir()
    for name, value in source_bytes.items():
        (output / "source" / name).write_bytes(value)
    shutil.copyfile(__file__, output / Path(__file__).name)
    plan = {
        "scope": "CPU FP32 frozen genuine DINO-S feature diagnostic on training-only photographs; no learned restoration, evaluation promotion or quality/convergence claim.",
        "manifest": str(MANIFEST),
        "manifest_sha256": MANIFEST_SHA,
        "eligible_training_photographs": len(eligible),
        "seed": SEED,
        "sources": sources,
        "selection": "Uniform source sample, then one source-keyed 512px bin4 ROI and exact area2 to native256; no geometry, exposure optimization or output-based selection.",
        "protocol_path": str(protocol_path),
        "protocol_sha256": sha(protocol_path),
        "conditions": conditions,
        "patterns": protocol["patterns"],
        "white_balance": protocol["white_balance"],
        "camera_to_srgb": protocol["camera_to_srgb"],
        "policy": "Only candidate is existing fixed phase-wise Wiener window7 with observation-derived variance_map; clean previews are diagnostic references only, unavailable to inference.",
        "source_files": {n: hashlib.sha256(v).hexdigest() for n, v in source_bytes.items()},
        "driver_sha256": sha(__file__),
    }
    (output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    cfg = ModelConfig(dino=True, dino_revision=REVISION)
    context = DinoContext(cfg, channels=1).cpu().eval()
    assert cfg.dino_revision == REVISION and not any(
        p.requires_grad for p in context.backbone.parameters()
    )
    weights = Path(try_to_load_from_cache(cfg.dino_model, "model.safetensors", revision=REVISION))
    foundation = {
        "model": cfg.dino_model,
        "revision": REVISION,
        "weights": str(weights),
        "sha256": sha(weights),
    }
    captured = []
    handle = context.adapter.register_forward_pre_hook(
        lambda module, args: captured.append(args[0].detach())
    )
    rows, crops = [], []
    for source_index, (source, rgb) in enumerate(zip(sources, images)):
        identity = source["id"]
        for condition in conditions:
            for pattern in protocol["patterns"]:
                batch = observation(
                    rgb,
                    [identity],
                    condition,
                    pattern,
                    protocol["white_balance"],
                    protocol["camera_to_srgb"],
                    SEED,
                )
                clean = batch["target"]
                clean_mhc = malvar(mosaic(clean, batch["colors"]), batch["colors"], batch["wb"])
                noisy = malvar(batch["packed"], batch["colors"], batch["wb"])
                filtered = malvar(
                    wiener_packed(batch["packed"], batch["variance"], 7),
                    batch["colors"],
                    batch["wb"],
                )
                methods = ["clean-rgb", "clean-malvar", "noisy-malvar", "wiener7-malvar"]
                previews = torch.cat(
                    [
                        render(value, batch["wb"], batch["matrix"])
                        for value in [clean, clean_mhc, noisy, filtered]
                    ]
                )
                assert previews.shape == (4, 3, 256, 256) and torch.isfinite(previews).all()
                context(previews, (1, 1))
                features = captured.pop()
                assert (
                    not captured
                    and features.shape == (4, 1152, 16, 16)
                    and torch.isfinite(features).all()
                )
                for layer, values in zip([4, 8, 12], features.chunk(3, dim=1)):
                    for reference_index, reference_name in [(0, "clean-rgb"), (1, "clean-malvar")]:
                        for method in ["clean-malvar", "noisy-malvar", "wiener7-malvar"]:
                            metrics = feature_metrics(
                                values[methods.index(method) : methods.index(method) + 1],
                                values[reference_index : reference_index + 1],
                            )
                            rows.append(
                                {
                                    "id": identity,
                                    "condition": condition["name"],
                                    "pattern": pattern,
                                    "layer": layer,
                                    "reference": reference_name,
                                    "method": method,
                                    "metrics": {k: v[0] for k, v in metrics.items()},
                                }
                            )
                if source_index < 2 and condition["name"] == "iso12800-prior" and pattern == "RGGB":
                    crops.append(
                        save_triplet(
                            output,
                            identity,
                            [
                                (
                                    label,
                                    display_crop(
                                        value, batch["wb"], batch["matrix"], [48, 48, 160, 160]
                                    ),
                                )
                                for label, value in [
                                    ("Noisy (Malvar)", noisy),
                                    ("Wiener7 prior", filtered),
                                    ("GT (synthetic)", clean),
                                ]
                            ],
                            caption=f"Training-only {identity}: fixed preview prior, no learned restoration",
                            metadata={
                                "source": source,
                                "evaluation_tile_xywh": [48, 48, 160, 160],
                                "condition": condition,
                                "pattern": pattern,
                                "display_exposure": 1,
                                "white_balance": protocol["white_balance"],
                                "camera_to_srgb": protocol["camera_to_srgb"],
                                "foundation": foundation,
                                "restoration_checkpoint": None,
                                "reference": "Exact synthetic clean target derived from binned Commons RGB; not a paired real capture.",
                            },
                        )
                    )
        print(
            json.dumps({"completed_sources": source_index + 1, "total_sources": count}), flush=True
        )
    handle.remove()
    assert len(rows) == count * len(conditions) * len(protocol["patterns"]) * 3 * 2 * 3
    assert len(crops) == 2
    assert all(
        Path("src/demosaic", name).read_bytes() == value for name, value in source_bytes.items()
    )
    assert sha(MANIFEST) == MANIFEST_SHA and sha(protocol_path) == plan["protocol_sha256"]
    assert not torch.cuda.is_initialized()
    result = {
        **plan,
        "foundation": foundation,
        "device": "cpu",
        "precision": "float32",
        "cuda_initialized": False,
        "feature_implementation": "Production DinoContext.forward adapter pre-hook, before any learned adapter or gate; native256,16px patch tokens, hidden layers4/8/12.",
        "metrics": "Cosine over channel vectors, averaged over native patch positions; relative Euclidean error over all features. Spatial-centered variants subtract each channel spatial mean per image before comparison.",
        "confidence": "4000 paired bootstrap resamples over the selected training sources; four CFA cases grouped within source. One ROI and noise draw per case. These intervals describe feature distances, not restoration quality.",
        "summary": summarize(rows),
        "native_crops": crops,
    }
    (output / "per-case.jsonl").write_text(
        "".join(json.dumps(row, allow_nan=False) + "\n" for row in rows)
    )
    (output / "summary.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": "complete", "summary": str(output / "summary.json")}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=BASE / "benchmarks/dino-preview-training16-v1"
    )
    parser.add_argument("--photos", type=int, default=16)
    args = parser.parse_args()
    torch.set_num_threads(2)
    main(args.output, args.photos)
