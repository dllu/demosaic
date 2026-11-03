"""Matched exact-flat and real-sky spatial-variation check for a checkpoint pilot.

The 48 flat observations and all V120 predictions already exist. No new noise
is drawn. True-flat error is measured against exact analytic GT; real-sky
variation is descriptive and is never scored against an independent capture.
"""

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from report_checkpoint_pilot import checked, pixels
from train_directional_bank_trial import guard, read, ref, save

REPO = Path(__file__).resolve().parents[1]
ARCHIVE = (
    REPO
    / ".cache/current-quality-20261023-v1/V120-V121-paired32-weak-detail-quality-v1/work/artifacts/color/archive/records.jsonl"
)
PALETTES = {
    "gray-l0.02",
    "gray-l0.18",
    "gray-l0.90",
    "h210-s0.50-l0.02",
    "h210-s0.50-l0.18",
    "h120-s0.50-l0.02",
}
SCALES = (1, 4, 16, 32)


def spatial_metrics(error):
    """DC error and orthogonal block-average spatial error, camera RGB units."""
    error = np.asarray(error, dtype=np.float64)
    assert error.shape == (1, 3, 160, 160) and np.isfinite(error).all()
    dc = error.mean((-1, -2), keepdims=True)
    centered = error - dc
    result = {
        "DC_RGB": dc.ravel().tolist(),
        "MSE": float(np.mean(error**2)),
        "DC_MSE": float(np.mean(dc**2)),
        "spatial_MSE": float(np.mean(centered**2)),
        "block_RMS": {},
    }
    for side in SCALES:
        blocks = centered.reshape(1, 3, 160 // side, side, 160 // side, side).mean((3, 5))
        result["block_RMS"][str(side)] = float(np.sqrt(np.mean(blocks**2)))
    np.testing.assert_allclose(
        result["MSE"], result["DC_MSE"] + result["spatial_MSE"], rtol=1e-13, atol=1e-30
    )
    return result


def sky_metrics(value):
    """Remove one affine camera-RGB plane before measuring spatial variation."""
    y, x = np.mgrid[-1:1:160j, -1:1:160j]
    design = np.stack([np.ones_like(x), x, y], -1).reshape(-1, 3)
    channels = np.asarray(value, dtype=np.float64).reshape(3, -1).T
    coefficients = np.linalg.lstsq(design, channels, rcond=None)[0]
    residual = (channels - design @ coefficients).T.reshape(1, 3, 160, 160)
    return {
        "plane_coefficients_RGB": coefficients.T.tolist(),
        "detrended_variation": spatial_metrics(residual),
    }


def prepare(root, primary):
    original = read(primary / "queue-plan-v1.json")
    guard(original)
    rows = [json.loads(line) for line in ARCHIVE.read_text().splitlines()]
    rows = [
        r
        for r in rows
        if r["model"]["label"] == "V120" and r["context"]["definition"]["id"] in PALETTES
    ]
    assert len(rows) == 48
    assert {r["context"]["definition"]["condition"]["name"] for r in rows} == {
        "adc-only",
        "iso12800-prior",
    }
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    for directory in ("src", "scripts"):
        shutil.copytree(
            Path(original["work"]) / directory,
            work / directory,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
    observations = []
    for row in rows:
        case = row["context"]["definition"]
        arrays = {"path": case["arrays"], "sha256": case["sha256"]}
        checked(arrays)
        checked(row["prediction"])
        observations.append(
            {
                "id": case["id"] + "-" + case["condition"]["name"] + "-" + case["pattern"],
                "arrays": arrays,
                "input_fingerprints": row["context"]["input_fingerprints"],
                "output_shape": [1, 3, 256, 256],
                "noise": case["condition"],
                "case": case,
                "control": row["prediction"],
                "reference_role": "Exact analytic flat GT",
            }
        )
    queue = {
        **original,
        "root": str(root),
        "work": str(work),
        "observations": observations,
        "planned_new_root_forwards": 48,
        "planned_new_encoder_forwards": 48,
        "primary_root": str(primary),
        "collector": ref(work / "scripts/collect_retained_checkpoint_pilot.py"),
        "inputs": [ref(ARCHIVE), ref(primary / "queue-plan-v1.json"), ref(__file__)],
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "scope": "48 retained exact-flat fields: six fixed neutral/blue/green colors, "
        "ADC-only/ISO12800 and all4CFAs; one draw each. Reuse V120 predictions. "
        "Fixed native160 ROI[48,48,160,160], exposure1, DC/spatial/block4/16/32 error. "
        "Primary real-sky native160 affine-detrended variation is descriptive, not GT error. "
        "No noise/RAW/optimizer or old-model inference; limited flat-safety support.",
    }
    save(root / "queue-plan-v1.json", queue)


def collect(root):
    queue = read(root / "queue-plan-v1.json")
    guard(queue)
    primary = Path(queue["primary_root"])
    executed = read(primary / "plan-v1.json")
    checked(executed["checkpoint"])
    plan = {
        **queue,
        "checkpoint": executed["checkpoint"],
        "inputs": [*queue["inputs"], ref(primary / "plan-v1.json"), executed["checkpoint"]],
    }
    save(root / "plan-v1.json", plan)
    work = Path(plan["work"])
    env = dict(
        os.environ,
        CUDA_VISIBLE_DEVICES="0",
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="2",
        PYTHONPATH=f"{work / 'src'}:{work / 'scripts'}",
    )
    with (root / "collect.log").open("x") as log:
        subprocess.run(
            [plan["python"], "-P", plan["collector"]["path"], str(root / "plan-v1.json")],
            env=env,
            cwd=work,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=1800,
            check=True,
        )


def report(root):
    plan = read(root / "plan-v1.json")
    guard(plan)
    collection = read(root / "collection-v1.json")
    assert collection["plan"] == ref(root / "plan-v1.json")
    assert collection["counts"] == {"root": 48, "encoder": 48}
    predictions = {r["id"]: r["prediction"] for r in collection["observations"]}
    rows, images = [], []
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    for observation in plan["observations"]:
        with np.load(checked(observation["arrays"]), allow_pickle=False) as archive:
            arrays = {k: archive[k] for k in archive.files}
        target = arrays["target"]
        assert np.array_equal(target, np.broadcast_to(target[..., :1, :1], target.shape))
        values = [
            ("V120", np.load(checked(observation["control"]), allow_pickle=False)),
            (
                plan["model_label"],
                np.load(checked(predictions[observation["id"]]), allow_pickle=False),
            ),
        ]
        for label, value in values:
            rows.append(
                {
                    "id": observation["id"],
                    "method": label,
                    "case": observation["case"],
                    "reference_role": "Exact analytic flat GT",
                    **spatial_metrics(
                        (value.astype(np.float64) - target.astype(np.float64))[..., 48:208, 48:208]
                    ),
                }
            )
        case = observation["case"]
        if case["pattern"] == "RGGB" and case["condition"]["name"] == "iso12800-prior":
            from demosaic.archive_metrics import noisy_malvar

            cells = [("Noisy Malvar", pixels(noisy_malvar(arrays), arrays, [48, 48, 160, 160], 1))]
            cells += [(label, pixels(v, arrays, [48, 48, 160, 160], 1)) for label, v in values]
            cells += [("GT (analytic flat)", pixels(target, arrays, [48, 48, 160, 160], 1))]
            canvas = Image.new("RGB", (680, 192), "#eeeeee")
            draw = ImageDraw.Draw(canvas)
            for index, (label, cell) in enumerate(cells):
                draw.text((8 + index * 168, 5), label, fill="black", font=font)
                canvas.paste(Image.fromarray(cell), (8 + index * 168, 24))
            dest = root / (case["id"] + "-flat-comparison.png")
            canvas.save(dest)
            saved = np.asarray(Image.open(dest))
            for index, (_, cell) in enumerate(cells):
                np.testing.assert_array_equal(
                    saved[24:184, 8 + index * 168 : 168 + index * 168], cell
                )
            images.append(
                {
                    "image": ref(dest),
                    "case": case,
                    "ROI_xywh": [48, 48, 160, 160],
                    "checkpoint": plan["checkpoint"],
                    "display_exposure": 1,
                    "no_resize": True,
                    "labels": [label for label, _ in cells],
                }
            )
    primary = Path(plan["primary_root"])
    main = read(primary / "plan-v1.json")
    o = next(o for o in main["observations"] if o["id"] == "main-overcast-sky")
    new = next(
        r for r in read(primary / "collection-v1.json")["observations"] if r["id"] == o["id"]
    )
    x, y, w, h = o["ROI_xywh"]
    sky = []
    for label, binding in [
        (c.get("label", c.get("model", {}).get("label")), c["prediction"]) for c in o["controls"]
    ] + [(main["model_label"], new["prediction"])]:
        value = np.load(checked(binding), allow_pickle=False)[..., y : y + h, x : x + w]
        sky.append({"method": label, **sky_metrics(value)})
    save(
        root / "flat-safety-v1.json",
        {
            "plan": ref(root / "plan-v1.json"),
            "checkpoint": plan["checkpoint"],
            "status": "completed-matched-flat-and-real-sky-spatial-check",
            "flat_metrics": rows,
            "flat_images": images,
            "sky_metrics": sky,
            "sky_observation": o,
            "scope": plan["scope"],
            "new_neural_forwards": 48,
            "reused_control_predictions": 48,
            "new_noise_observations": 0,
            "RAW_decodes": 0,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "collect", "report"))
    parser.add_argument("root", type=Path)
    parser.add_argument("--primary", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.root.resolve(), args.primary.resolve())
    elif args.mode == "collect":
        collect(args.root.resolve())
    else:
        report(args.root.resolve())
