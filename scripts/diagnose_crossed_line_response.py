"""Matched exact mesh/empty diagnostic; separate from fixed photographic reviews."""

import argparse
import os
import random
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
import yaml
from PIL import Image, ImageDraw, ImageFont
from report_checkpoint_pilot import pixels
from report_pilot_flat_safety import spatial_metrics
from train_directional_bank_trial import guard, read, ref, save

from demosaic.archive_metrics import noisy_malvar
from demosaic.data import augment_before_downsample
from demosaic.prediction_archive import fingerprint
from demosaic.suite import observation as make_observation
from demosaic.textures import crossed_line_texture

REPO = Path(__file__).resolve().parents[1]
BASE = REPO / ".cache/quality-20261102"
TEMPLATE = BASE / "V143-fixed-reviews-v3/step2500"
SEEDS = (2026110201, 2026110202, 2026110203, 2026110204)
ROI = [48, 48, 160, 160]


def mesh_metrics(prediction, target, present, empty):
    """Known-target projection, with per-channel affine backgrounds removed.

    The template is diagnostic ground truth, never an inference calibration.
    An absent example projects onto the same hypothetical present template.
    """
    arrays = [np.asarray(v, dtype=np.float64) for v in (prediction, target, present, empty)]
    if any(v.shape != (1, 3, 256, 256) or not np.isfinite(v).all() for v in arrays):
        raise ValueError("Require finite native256 RGB arrays")
    p, t, a, b = [v[..., 48:208, 48:208] for v in arrays]
    y, x = np.mgrid[-1:1:160j, -1:1:160j]
    design = np.stack([np.ones_like(x), x, y], -1).reshape(-1, 3)

    def detrend(value):
        channels = value.reshape(3, -1).T
        coefficients = np.linalg.lstsq(design, channels, rcond=None)[0]
        residual = channels - design @ coefficients
        # Independent orthonormal projection checks all native values.
        q = np.linalg.qr(design, mode="reduced")[0]
        np.testing.assert_allclose(
            residual, channels - q @ (q.T @ channels), rtol=1e-10, atol=2e-14
        )
        return residual

    signal, output = detrend(a - b), detrend(p - b)
    energy = float(np.sum(signal**2))
    if energy <= 1e-20:
        raise ValueError("Require a nonzero exact hypothetical mesh template")
    gain = float(np.sum(output * signal) / energy)
    nonmesh = output - gain * signal
    np.testing.assert_allclose(np.sum(nonmesh * signal), 0, atol=1e-16, rtol=0)
    return {
        "known_mesh_gain": gain,
        "target_mesh_RMS": float(np.sqrt(np.mean(signal**2))),
        "detrended_nonmesh_RMS": float(np.sqrt(np.mean(nonmesh**2))),
        "error": spatial_metrics(p - t),
    }


def prepare(root):
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    torch.set_num_threads(1)
    root.mkdir(parents=True, exist_ok=False)
    (root / "inputs").mkdir()
    protocol = yaml.safe_load((REPO / "configs/evaluation.yaml").read_text())
    conditions = [
        next(c for c in protocol["conditions"] if c["name"] == "adc-only"),
        {"name": "iso6400-prior", "shot": 0.00128, "read": 6.5536e-6, "exposure": 1.0},
    ]
    rng_before = torch.get_rng_state().clone()
    observations = []
    for seed in SEEDS:
        scenes, recipes = {}, {}
        for present in (True, False):
            rng = random.Random(seed)
            rgb, recipe = crossed_line_texture(512, rng, pixel_scale=2, present=present)
            scenes[present] = augment_before_downsample(rgb, 256, rng, optical_blur_probability=0)[
                None
            ] * (0.02 / recipe["level"])
            recipes[present] = {"recipe": recipe, "geometry_final_rng_state": repr(rng.getstate())}
        assert (
            recipes[True]["geometry_final_rng_state"] == recipes[False]["geometry_final_rng_state"]
        )
        for condition in conditions:
            for pattern in protocol["patterns"]:
                batches = {}
                for present in (True, False):
                    identity = f"mesh-seed{seed}-{'present' if present else 'absent'}"
                    batches[present] = make_observation(
                        scenes[present],
                        [identity],
                        condition,
                        pattern,
                        protocol["white_balance"],
                        protocol["camera_to_srgb"],
                        20261102,
                    )
                for present, batch in batches.items():
                    identity = f"mesh-seed{seed}-{'present' if present else 'absent'}-{condition['name']}-{pattern}"
                    arrays = {k: v.numpy() for k, v in batch.items()}
                    arrays.update(
                        target_present=batches[True]["target"].numpy(),
                        target_empty=batches[False]["target"].numpy(),
                    )
                    target = root / "inputs" / f"{identity}.npz"
                    np.savez(target, **arrays)
                    observations.append(
                        {
                            "id": identity,
                            "arrays": ref(target),
                            "present": present,
                            "seed": seed,
                            "source": recipes[present],
                            "noise": condition,
                            "pattern": pattern,
                            "scene_level_before_camera": 0.02,
                            "input_fingerprints": {
                                k: fingerprint(arrays[k])
                                for k in ("packed", "variance", "colors", "wb", "matrix")
                            },
                            "output_shape": [1, 3, 256, 256],
                            "ROI_xywh": ROI,
                            "display_exposure": 8,
                            "reference_role": "Exact procedural mesh or empty GT; hypothetical present template used only for diagnostic metrics",
                        }
                    )
    assert len(observations) == 64 and torch.equal(rng_before, torch.get_rng_state())
    models = {}
    for label, source in [
        ("V120", BASE / "V142-native-v1"),
        ("V142", BASE / "V142-native-v1"),
        ("V143-2500", TEMPLATE),
    ]:
        original = read(source / "plan-v1.json")
        checkpoint = (
            original["checkpoint"]
            if label != "V120"
            else read(BASE / "V143-crossed-gradient5000-v1/plan.json")["parent"]
        )
        checkpoint = {k: checkpoint[k] for k in ("path", "sha256")}
        assert ref(checkpoint["path"]) == checkpoint
        state = torch.load(checkpoint["path"], weights_only=True, map_location="cpu", mmap=True)
        model_root = root / label
        work = model_root / "work"
        for directory in ("src", "scripts"):
            shutil.copytree(
                Path(original["work"]) / directory,
                work / directory,
                ignore=shutil.ignore_patterns("__pycache__"),
            )
        collector = work / "scripts/collect_retained_checkpoint_pilot.py"
        text = collector.read_text()
        assert text.count("torch.set_num_threads(2)") + text.count("torch.set_num_threads(1)") == 1
        collector.write_text(text.replace("torch.set_num_threads(2)", "torch.set_num_threads(1)"))
        plan = {
            **original,
            "root": str(model_root),
            "work": str(work),
            "checkpoint": checkpoint,
            "step": state["step"],
            "training_horizon": state["config"]["steps"],
            "progress_checkpoint": label == "V143-2500",
            "expected_lineage": state["config"]["initialized_from"],
            "observations": observations,
            "model_label": label,
            "collector": ref(collector),
            "planned_new_root_forwards": 64,
            "planned_new_encoder_forwards": 64,
            "inputs": [
                ref(__file__),
                ref(REPO / "configs/evaluation.yaml"),
                checkpoint,
                *[o["arrays"] for o in observations],
            ],
            "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
            "scope": "New explicit64-input procedural diagnostic:4 fixed new recipes, present/absent, ADC/ISO6400,4CFAs,1 noise draw. Native256 through original2x geometry; normalize scene level to.02. No real-photo or heldout-capture input. Same64 arrays across3 models,192 root/DINO calls including128 new V120/V142 control calls. Separate from original fixed photographic review ledger. Model/RNG/input checks retained; one CPU thread/IEEE FP32. Known-target projection is report-only, not inference calibration or broad quality/flat-safety proof.",
        }
        del state
        save(model_root / "plan-v1.json", plan)
        guard(plan)
        models[label] = ref(model_root / "plan-v1.json")
    save(
        root / "plan-v1.json",
        {
            "operator": ref(__file__),
            "models": models,
            "new_noise_observations": 64,
            "root_DINO_calls_planned": 192,
            "new_control_calls_planned": 128,
            "RAW_decodes": 0,
            "source_seeds": list(SEEDS),
            "scope": plan["scope"],
        },
    )


def collect(root):
    master = read(root / "plan-v1.json")
    assert master["operator"] == ref(__file__)
    for binding in master["models"].values():
        assert ref(binding["path"]) == binding
        plan = read(binding["path"])
        with (Path(plan["root"]) / "collect.log").open("x") as log:
            subprocess.run(
                [plan["python"], "-P", plan["collector"]["path"], binding["path"]],
                cwd=plan["work"],
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                env=dict(
                    os.environ,
                    CUDA_VISIBLE_DEVICES="0",
                    OMP_NUM_THREADS="1",
                    OPENBLAS_NUM_THREADS="1",
                    HF_HUB_OFFLINE="1",
                    TRANSFORMERS_OFFLINE="1",
                    PYTHONPATH=f"{plan['work']}/src:{plan['work']}/scripts",
                ),
                timeout=1800,
                check=True,
            )


def report(root):
    master = read(root / "plan-v1.json")
    assert master["operator"] == ref(__file__)
    plans, predictions = {}, {}
    for label, binding in master["models"].items():
        assert ref(binding["path"]) == binding
        plan = read(binding["path"])
        guard(plan)
        collection = read(Path(plan["root"]) / "collection-v1.json")
        assert collection["plan"] == binding and collection["counts"] == {"root": 64, "encoder": 64}
        assert (
            collection["full_model_before"] == collection["full_model_after"]
            and collection["backbone_before"] == collection["backbone_after"]
            and collection["RNG_unchanged"]
        )
        predictions[label] = {o["id"]: o["prediction"] for o in collection["observations"]}
        plans[label] = plan
    rows, images = [], []
    output = root / "report-v1"
    output.mkdir(exist_ok=False)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    for observation in next(iter(plans.values()))["observations"]:
        with np.load(observation["arrays"]["path"], allow_pickle=False) as archive:
            arrays = {k: archive[k] for k in archive.files}
        values = {"Noisy Malvar": noisy_malvar(arrays)}
        for label, saved in predictions.items():
            binding = saved[observation["id"]]
            assert ref(binding["path"]) == binding
            values[label] = np.load(binding["path"], allow_pickle=False)
        for label, value in values.items():
            rows.append(
                {
                    "id": observation["id"],
                    "seed": observation["seed"],
                    "present": observation["present"],
                    "noise": observation["noise"]["name"],
                    "pattern": observation["pattern"],
                    "method": label,
                    **mesh_metrics(
                        value, arrays["target"], arrays["target_present"], arrays["target_empty"]
                    ),
                }
            )
        if observation["pattern"] == "RGGB":
            cells = [*values.items(), ("GT (procedural exact)", arrays["target"])]
            canvas = Image.new("RGB", (848, 192), "#eeeeee")
            draw = ImageDraw.Draw(canvas)
            for i, (label, value) in enumerate(cells):
                cell = pixels(value, arrays, ROI, 8)
                canvas.paste(Image.fromarray(cell), (8 + 168 * i, 24))
                draw.text((8 + 168 * i, 5), label, fill="black", font=font)
                np.testing.assert_array_equal(
                    np.asarray(canvas)[24:184, 8 + 168 * i : 168 + 168 * i], cell
                )
            path = output / f"{observation['id']}.png"
            canvas.save(path)
            np.testing.assert_array_equal(np.asarray(Image.open(path)), np.asarray(canvas))
            images.append(
                {
                    "image": ref(path),
                    "observation": observation,
                    "checkpoints": {k: p["checkpoint"] for k, p in plans.items()},
                    "no_resize": True,
                }
            )
    groups = defaultdict(list)
    for row in rows:
        groups[(row["method"], row["noise"], row["present"])].append(row)
    summary = [
        {
            "method": key[0],
            "noise": key[1],
            "present": key[2],
            "cases": len(values),
            "mean_known_mesh_gain": float(np.mean([v["known_mesh_gain"] for v in values])),
            "mean_spatial_RMS_DN16": float(
                np.mean([np.sqrt(v["error"]["spatial_MSE"]) * 65535 for v in values])
            ),
            "mean_nonmesh_RMS_DN16": float(
                np.mean([v["detrended_nonmesh_RMS"] * 65535 for v in values])
            ),
        }
        for key, values in groups.items()
    ]
    save(
        output / "result-v1.json",
        {
            "status": "completed-exact-procedural-mesh-response-diagnostic",
            "plan": ref(root / "plan-v1.json"),
            "rows": rows,
            "summary": summary,
            "images": images,
            "root_DINO_calls": 192,
            "new_control_calls": 128,
            "new_noise_observations": 64,
            "RAW_decodes": 0,
            "independent_affine_QR_projection_values_checked": len(rows) * 2 * 3 * 160 * 160,
            "scope": master["scope"],
        },
    )
    print(summary, flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("prepare", "collect", "report"))
    p.add_argument("root", type=Path)
    args = p.parse_args()
    globals()[args.mode](args.root.resolve())
