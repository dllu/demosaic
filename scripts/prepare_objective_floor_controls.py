"""Cache held-out ADC photos/planes and their fixed V143 parent predictions."""

import argparse
import os
import shutil
from pathlib import Path

import numpy as np
import psutil
from train_directional_bank_trial import guard, read, ref, save

REPO = Path(__file__).resolve().parents[1]


def prepare(root):
    import torch
    import yaml

    from demosaic.cfa import color_indices, mosaic
    from demosaic.prediction_archive import fingerprint

    root = root.absolute()
    assert root.is_relative_to(REPO / ".cache") and not root.exists()
    adcroot = REPO / ".cache/current-quality-20261023-v1/fp32-faint-adc-quality-v1/run"
    old = read(adcroot / "plan-v1.json")
    holdout = read(adcroot / "holdout-and-model-identity-v1.json")
    assert holdout["training_row_source_ID_occurrences"] == 0
    assert all(ref(x["path"]) == x for x in holdout["training_manifests"].values())
    selected = [c for c in old["cases"] if c["id"].startswith(("bark-", "raccoon-fur-"))]
    assert len(selected) == 2 and all(
        c["reference_role"].startswith("Exact synthetic") for c in selected
    )
    sources = {c["source_id"] for c in selected}
    shared = REPO / "configs/quality-v143-late-spectral-v147.yaml"
    config = yaml.safe_load(shared.read_text())
    assert ref(config["manifest"])["sha256"] == holdout["training_manifests"]["manifest"]["sha256"]
    cache = read(REPO / ".cache/quality-20261103/V148-phase-matrix-v1/cache-result-v1.json")
    assert all(s not in str([x["metadata"] for x in cache["batches"]]) for s in sources)
    assert psutil.virtual_memory().available > 52 * 2**30
    assert shutil.disk_usage(REPO).free > 98 * 2**30
    assert shutil.disk_usage("/mnt/external").free > 208 * 2**30
    root.mkdir(parents=True)
    (root / "inputs").mkdir()
    (root / "parents").mkdir()
    cases = []
    inputs = [
        ref(adcroot / "plan-v1.json"),
        ref(adcroot / "holdout-and-model-identity-v1.json"),
        ref(shared),
        ref(config["manifest"]),
    ]
    for case in selected:
        assert ref(case["target"]["path"]) == case["target"]
        target = dict(np.load(case["target"]["path"]))
        inputs.append(case["target"])
        for oldobs in [x for x in old["observations"] if x["case_id"] == case["id"]]:
            assert ref(oldobs["arrays"]["path"]) == oldobs["arrays"]
            arrays = dict(np.load(oldobs["arrays"]["path"]))
            assert {k: fingerprint(v) for k, v in arrays.items()} == oldobs["input_fingerprints"]
            assert all(np.array_equal(arrays[k], target[k]) for k in ["wb", "matrix"])
            inputs.append(oldobs["arrays"])
            dest = root / "inputs" / (oldobs["id"] + ".npz")
            np.savez_compressed(dest, **arrays, target=target["target"])
            cases.append(
                {
                    **oldobs,
                    "id": "V150-control-" + oldobs["id"],
                    "kind": "photo",
                    "cohort": "adc-photo256",
                    "arrays": ref(dest),
                    "variant": {"name": "adc-only", "additional_contrast_factor": 0.025},
                    "source": case,
                    "noise": {
                        "name": "adc-only",
                        "shot": 0.0,
                        "read": 0.0,
                        "ADC_bits": 16,
                        "black_level": 0.03,
                    },
                    "reference_role": case["reference_role"],
                    "fresh": False,
                }
            )
    assert len(cases) == 8
    calibration = dict(np.load(cases[0]["arrays"]["path"]))
    y, x = np.mgrid[:512, :512].astype(np.float64)
    recipes = [
        (0.004, [1.0, 0.8, 0.6], 0.043, -0.031),
        (0.02, [0.4, 1.0, 0.7], -0.037, 0.029),
        (0.18, [0.7, 0.9, 1.0], 0.019, 0.047),
        (0.75, [0.6, 1.0, 0.4], -0.041, -0.023),
    ]
    patterns = ["RGGB", "BGGR", "GRBG", "GBRG"]
    maximum_ADC_longdouble_difference = 0.0
    for index, (level, tint, sx, sy) in enumerate(recipes):
        target = (
            level
            * np.array(tint)[:, None, None]
            * (1 + sx * ((x + 0.5) / 512 - 0.5) + sy * ((y + 0.5) / 512 - 0.5))
        )[None].astype(np.float32)
        for pattern in patterns:
            colors = color_indices(pattern)[None]
            sampled = mosaic(torch.from_numpy(target), colors).numpy()
            packed = (
                (np.rint((sampled.astype(np.float64) * 0.97 + 0.03) * 65535) / 65535 - 0.03) / 0.97
            ).astype(np.float32)
            independent = (
                np.rint(
                    (sampled.astype(np.longdouble) * np.longdouble(".97") + np.longdouble(".03"))
                    * 65535
                )
                / 65535
                - np.longdouble(".03")
            ) / np.longdouble(".97")
            difference = float(np.max(np.abs(packed.astype(np.longdouble) - independent)))
            assert difference < 1.04 / 65535
            maximum_ADC_longdouble_difference = max(maximum_ADC_longdouble_difference, difference)
            arrays = {
                "packed": packed,
                "variance": np.zeros_like(packed),
                "colors": colors.numpy(),
                "wb": calibration["wb"],
                "matrix": calibration["matrix"],
                "target": target,
            }
            identity = f"V150-control-ADC-plane{index}-{pattern}"
            dest = root / "inputs" / (identity + ".npz")
            np.savez_compressed(dest, **arrays)
            cases.append(
                {
                    "id": identity,
                    "kind": "flat",
                    "cohort": "adc-sloped512",
                    "pattern": pattern,
                    "arrays": ref(dest),
                    "noise": {
                        "name": "adc-only",
                        "shot": 0.0,
                        "read": 0.0,
                        "ADC_bits": 16,
                        "black_level": 0.03,
                    },
                    "ROI_xywh": [176, 176, 160, 160],
                    "display_exposure": 1 / level,
                    "reference_role": "Exact analytically constructed camera-RGB affine-plane target; deterministic16-bit ADC, not a physical capture",
                    "source": {
                        "recipe": "camera-linear affine plane at native512, no resize",
                        "level": level,
                        "tint": tint,
                        "slopes": [sx, sy],
                    },
                    "fresh": True,
                }
            )
    assert len(cases) == 24 and len({c["id"] for c in cases}) == 24
    work = root / "work"
    for source in (REPO / "src/demosaic").glob("*.py"):
        target = work / "src/demosaic" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for name in [
        Path(__file__).name,
        "train_directional_bank_trial.py",
        "profile_raw_kernel_inference.py",
    ]:
        target = work / "scripts" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / "scripts" / name, target)
    runner = work / "scripts" / Path(__file__).name
    save(
        root / "plan-v1.json",
        {
            "root": str(root),
            "work": str(work),
            "runner": ref(runner),
            "inputs": inputs + [c["arrays"] for c in cases],
            "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
            "parent": config["parent"],
            "expected_DINO_sha256": config["expected_DINO_sha256"],
            "cases": cases,
            "source_ids_disjoint_from_training": sorted(sources),
            "longdouble_ADC_maximum_difference_DN16": maximum_ADC_longdouble_difference * 65535,
            "new_deterministic_ADC_observations": 16,
            "adopted_ADC_observations": 8,
            "planned_parent_and_DINO_forwards": 24,
            "new_stochastic_noise_draws": 0,
            "scope": "Eight existing faint Commons ADC observations plus16 fresh analytic sloped-plane ADC observations;4CFA placements per source/recipe are related. Photographic references are exact synthetic array targets, not physical-scene GT. Two approximate binned camera references were deliberately not adopted. Both source IDs excluded from existing train manifests and all adopted training metadata. No source/original lookup, no RAW/dataz access. Inputs and full target/ROI set fixed before V150 training.",
        },
    )
    print(root / "plan-v1.json")


def parents(path):
    import torch
    from profile_raw_kernel_inference import model_hash

    from demosaic.inference import load_checkpoint
    from demosaic.precision import ieee_fp32
    from demosaic.prediction_archive import fingerprint

    plan = read(path)
    guard(plan)
    root = Path(plan["root"])
    assert ref(__file__) == plan["runner"]
    (root / "parents.claim").open("x").close()
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    torch.cuda.set_per_process_memory_fraction(
        12 * 2**30 / torch.cuda.get_device_properties(0).total_memory
    )
    assert psutil.virtual_memory().available > 52 * 2**30
    with torch.random.fork_rng(devices=[0]):
        model, state = load_checkpoint(plan["parent"]["path"], "cuda")
    assert state["loaded_sha256"] == plan["parent"]["sha256"]
    model.eval().requires_grad_(False).to(memory_format=torch.channels_last)
    before, backbone = model_hash(model), model_hash(model.context.backbone)
    assert backbone == plan["expected_DINO_sha256"]
    counts = {"parent": 0, "DINO": 0}
    model.register_forward_hook(lambda *args: counts.__setitem__("parent", counts["parent"] + 1))
    model.context.backbone.register_forward_hook(
        lambda *args: counts.__setitem__("DINO", counts["DINO"] + 1)
    )
    cpu, cuda = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
    rows = []
    for i, case in enumerate(plan["cases"]):
        assert psutil.virtual_memory().available > 32 * 2**30
        assert (
            shutil.disk_usage(root).free > 96 * 2**30
            and shutil.disk_usage("/mnt/external").free > 208 * 2**30
        )
        arrays = dict(np.load(case["arrays"]["path"]))
        assert ref(case["arrays"]["path"]) == case["arrays"]
        keys = ["packed", "variance", "colors", "wb", "matrix"]
        tensors = [torch.from_numpy(arrays[k]).cuda() for k in keys]
        model.set_noise(0.0, 0.0)
        with torch.inference_mode(), ieee_fp32():
            value = model(*tensors).cpu().numpy()
        assert (
            value.dtype == np.float32
            and value.shape == arrays["target"].shape
            and np.isfinite(value).all()
        )
        dest = root / "parents" / f"parent-{i:03d}.npy"
        np.save(dest, value)
        rows.append(
            {
                **case,
                "parent": ref(dest),
                "input_fingerprints": {k: fingerprint(arrays[k]) for k in keys},
            }
        )
        print(case["id"], flush=True)
    assert counts == {"parent": 24, "DINO": 24}
    assert model_hash(model) == before and model_hash(model.context.backbone) == backbone
    assert torch.equal(cpu, torch.get_rng_state()) and torch.equal(cuda, torch.cuda.get_rng_state())
    guard(plan)
    save(
        root / "result-v1.json",
        {
            "status": "completed24-fixed-ADC-parent-contexts",
            "plan": ref(path),
            "observations": rows,
            "counts": counts,
            "parent_before": before,
            "parent_after": model_hash(model),
            "DINO_before": backbone,
            "DINO_after": model_hash(model.context.backbone),
            "RNG_unchanged": True,
            "new_stochastic_noise_draws": 0,
            "CUDA_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "scope": plan["scope"],
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "parents"])
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    (prepare if args.mode == "prepare" else parents)(args.path.absolute())
