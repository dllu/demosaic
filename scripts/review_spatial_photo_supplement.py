"""Compare V144/V145 on retained512 and additional organic384 photo contexts."""

import argparse
import json
import os
import shutil
import subprocess
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import psutil
from PIL import Image, ImageDraw, ImageFont
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import live

REPO = Path(__file__).resolve().parents[1]
STUDIES = REPO / ".cache/quality-20261103"
TRAINING = STUDIES / "V144-V145-spatial-v1"
PRIMARY = STUDIES / "V144-V145-review-v1"
RETAINED = STUDIES / "supported-amplitude-v1/prospective-v1/V143-5000"
ORGANIC_INDICES = (0, 2, 4, 5, 8, 9, 11, 12)


def prepare(root):
    import torch
    import yaml

    from demosaic.prediction_archive import fingerprint
    from demosaic.suite import observation

    torch.set_num_threads(1)
    assert not (root / "supplement-plan-v1.json").exists()
    assert not (TRAINING / "train-V144-result.json").exists()
    training = read(TRAINING / "plan.json")
    guard(training)
    old = read(RETAINED / "plan-v1.json")
    guard(old)
    collection = read(RETAINED / "collection-v1.json")
    assert collection["plan"] == ref(RETAINED / "plan-v1.json")
    assert collection["counts"] == {"root": 576, "encoder": 576}
    assert (
        collection["RNG_unchanged"]
        and collection["full_model_before"] == collection["full_model_after"]
    )
    original_predictions = {r["id"]: r["prediction"] for r in collection["observations"]}
    cases = [
        {**o, "cohort": "retained512", "parent_prediction": original_predictions[o["id"]]}
        for o in old["observations"]
        if o["kind"] == "photo"
    ]
    assert len(cases) == 64
    candidates = read(root / "organic-candidates-v2.json")
    assert ref(candidates["preview"]["path"]) == candidates["preview"]
    sources = [candidates["candidates"][i] for i in ORGANIC_INDICES]
    recipes = [yaml.safe_load(Path(training["arms"]["V144"]["train"]).read_text())]
    excluded_ids = set()
    manifests = []
    for key in ("manifest", "photo_sampling_reference_manifest"):
        path = Path(recipes[0][key])
        manifests.append(ref(path))
        excluded_ids.update(
            x["id"] for x in map(json.loads, path.read_text().splitlines()) if x["split"] == "train"
        )
    all_sources = [o["source"] for o in cases] + sources
    assert len({o["id"] for o in all_sources}) == 16
    assert all(o["id"] not in excluded_ids and o["split"] == "val" for o in all_sources)
    for source in sources:
        assert source["bin_factor"] == 8
        assert ref(source["cache"])["sha256"] == source["cache_sha256"]
    choice = {
        "candidates": ref(root / "organic-candidates-v2.json"),
        "indices": list(ORGANIC_INDICES),
        "sources": sources,
        "training_manifests": manifests,
        "all16_sources_absent_from_both_training_ID_sets": True,
        "selection": "Source-only native preview: feather, wet leaves, moth scales, grass/bark, "
        "apple skin, butterfly, heron feathers, moth hairs. Before any new noise/parent/endpoint "
        "inference. Native384 bin8 contexts; retain64 earlier native512 photo observations.",
    }
    save(root / "organic-source-choice-v1.json", choice)
    protocol = yaml.safe_load((REPO / "configs/evaluation.yaml").read_text())
    variants = read(STUDIES / "supported-amplitude-v1/photo-source-choice-v1.json")["conditions"]
    condition = {"name": "iso6400-prior", "shot": 0.00128, "read": 6.5536e-6, "exposure": 1.0}
    inputs = root / "inputs"
    inputs.mkdir()
    rng = torch.get_rng_state().clone()
    for source in sources:
        original = np.load(source["cache"], allow_pickle=False)
        assert original.dtype == np.uint16 and min(original.shape[:2]) >= 384
        h, w = original.shape[:2]
        oy, ox = 2 * ((h - 384) // 4), 2 * ((w - 384) // 4)
        crop = (
            torch.from_numpy(
                original[oy : oy + 384, ox : ox + 384].astype(np.float32).transpose(2, 0, 1)
            )
            / 65535
        )
        mean = crop.mean((-2, -1), keepdim=True)
        for variant in variants:
            scale = variant["mean_linear_srgb"] / float(crop.mean())
            clean = (mean + variant["contrast_about_channel_means"] * (crop - mean)) * scale
            for pattern in protocol["patterns"]:
                identity = f"organic-{source['id']}-{variant['name']}-{pattern}"
                batch = observation(
                    clean[None],
                    [identity],
                    condition,
                    pattern,
                    protocol["white_balance"],
                    protocol["camera_to_srgb"],
                    2026110301,
                )
                arrays = {k: v.numpy() for k, v in batch.items()}
                target = inputs / (identity + ".npz")
                np.savez(target, **arrays)
                cases.append(
                    {
                        "id": identity,
                        "kind": "photo",
                        "cohort": "organic384",
                        "source": source,
                        "source_ROI_xywh": [ox, oy, 384, 384],
                        "variant": variant,
                        "scale": scale,
                        "arrays": ref(target),
                        "noise": condition,
                        "pattern": pattern,
                        "input_fingerprints": {
                            k: fingerprint(arrays[k])
                            for k in ("packed", "variance", "colors", "wb", "matrix")
                        },
                        "output_shape": [1, 3, 384, 384],
                        "ROI_xywh": [112, 112, 160, 160],
                        "display_exposure": 1 / scale,
                        "reference_role": "Exact constructed camera-RGB target from nativebin8 "
                        "Commons linearRGB16; not exact physical scene GT",
                    }
                )
    assert len(cases) == 128 and torch.equal(rng, torch.get_rng_state())
    template = read(PRIMARY / "V144/queue-plan-v1.json")
    plans = {}
    for label in ("V143", "V144", "V145"):
        point = root / label
        work = point / "work"
        for directory in ("src", "scripts"):
            shutil.copytree(
                Path(template["work"]) / directory,
                work / directory,
                ignore=shutil.ignore_patterns("__pycache__"),
            )
        selected = [o for o in cases if o["cohort"] == "organic384"] if label == "V143" else cases
        plan = {
            **template,
            "root": str(point),
            "work": str(work),
            "observations": selected,
            "planned_new_root_forwards": len(selected),
            "planned_new_encoder_forwards": len(selected),
            "model_label": label,
            "EMA_tensors": 114 if label == "V145" else 91,
            "raw_spatial_features": label == "V145",
            "collector": ref(work / "scripts/collect_retained_checkpoint_pilot.py"),
            "inputs": [
                ref(root / "organic-source-choice-v1.json"),
                *[o["arrays"] for o in selected],
            ],
            "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
            "scope": "Independent supplement: retained64 photo512 plus64 new organic384 "
            "observations. Same exact inputs and camera/display transforms across models. "
            "New64 V143 parent calls; retain64 prior parent predictions. V144/V145128 each. "
            "No training/RAW decode/source-drive access or change to original150-input reviews.",
        }
        if label == "V143":
            plan.update(
                checkpoint=old["checkpoint"],
                step=5000,
                training_horizon=5000,
                expected_lineage=old["expected_lineage"],
            )
            plan["inputs"].append(old["checkpoint"])
            path = point / "plan-v1.json"
        else:
            plan.pop("checkpoint", None)
            path = point / "queue-plan-v1.json"
        guard(plan)
        save(path, plan)
        plans[label] = ref(path)
    operator = root / "operator-v1.py"
    operator.write_text(
        Path(__file__)
        .read_text()
        .replace("REPO = Path(__file__).resolve().parents[1]", f"REPO = Path({str(REPO)!r})")
    )
    auditor = root / "auditor-v1.py"
    shutil.copyfile(REPO / "scripts/audit_spatial_photo_supplement.py", auditor)
    master = {
        "root": str(root),
        "python": training["python"],
        "operator": ref(operator),
        "auditor": ref(auditor),
        "plans": plans,
        "observations": cases,
        "primary_review_plan": ref(PRIMARY / "review-plan-v1.json"),
        "training_plan": ref(TRAINING / "plan.json"),
        "primary_owner": read(PRIMARY / "review-status.json")["owner"],
        "planned_new_root_and_encoder_calls": 320,
        "new_noise_observations": 64,
        "ADC_bits": 16,
        "ADC_black_level": 0.03,
        "inputs": [
            ref(RETAINED / "plan-v1.json"),
            ref(RETAINED / "collection-v1.json"),
            ref(root / "organic-source-choice-v1.json"),
            *plans.values(),
            *[o["parent_prediction"] for o in cases if o["cohort"] == "retained512"],
        ],
        "frozen_files": {
            str(operator): ref(operator)["sha256"],
            str(auditor): ref(auditor)["sha256"],
        },
    }
    guard(master)
    save(root / "supplement-plan-v1.json", master)
    print(root / "supplement-plan-v1.json")


def retained_parent_collection(root, binding):
    assert ref(binding["path"]) == binding
    actual = read(binding["path"])
    assert actual["plan"] == ref(root / "V143/plan-v1.json")
    assert actual["counts"] == {"root": 64, "encoder": 64}
    assert actual["RNG_unchanged"] and actual["full_model_before"] == actual["full_model_after"]
    assert actual["backbone_before"] == actual["backbone_after"]
    assert len(actual["observations"]) == 64
    for row in actual["observations"]:
        assert ref(row["prediction"]["path"]) == row["prediction"]


def prepare_recovery(path, primary_path):
    old = read(path)
    guard(old)
    root = Path(old["root"])
    failed = read(root / "supplement-status.json")
    assert failed["status"] == "failed-photographic-supplement-preserved"
    assert not live(failed["owner"]) and set(failed["completed"]) == {"V143"}
    retained_parent_collection(root, failed["completed"]["V143"])
    primary = read(primary_path)
    guard(primary)
    status_path = Path(primary["status_path"])
    status = read(status_path)
    assert live(status["owner"]) and status["plan"] == ref(primary_path)
    assert "V144" in status["completed"]
    assert primary["training_plan"] == old["training_plan"]
    assert not any((root / label / "collection-v1.json").exists() for label in ("V144", "V145"))
    operator = root / "operator-v2.py"
    assert not operator.exists()
    operator.write_text(
        Path(__file__)
        .read_text()
        .replace("REPO = Path(__file__).resolve().parents[1]", f"REPO = Path({str(REPO)!r})")
    )
    plan = {
        **old,
        "operator": ref(operator),
        "primary_review_plan": ref(primary_path),
        "primary_owner": status["owner"],
        "primary_status_path": str(status_path),
        "status_path": str(root / "supplement-recovery-status-v2.json"),
        "claim_path": str(root / "supplement-recovery-v2.claim"),
        "adopted_collections": failed["completed"],
        "absolute_deadline_unix": failed["owner"]["created"] + 72000,
        "inputs": [
            *old["inputs"],
            ref(path),
            ref(root / "supplement-status.json"),
            ref(primary_path),
            failed["completed"]["V143"],
        ],
        "frozen_files": {**old["frozen_files"], str(operator): ref(operator)["sha256"]},
        "recovery_scope": "Original primary review stopped on a receipt-name error after "
        "V144 completed; dependency stop preserved. Adopt exact64 parent outputs without "
        "replay. Follow separately recovered primary owner/plan. Same128 observations, "
        "same320 root/DINO total and original conservative deadline; no new noise/training.",
    }
    target = root / "supplement-recovery-plan-v2.json"
    assert not target.exists()
    guard(plan)
    save(target, plan)
    return target


def run(path):
    plan = read(path)
    guard(plan)
    root = Path(plan["root"])
    Path(plan.get("claim_path", root / "run.claim")).open("x").close()
    state = {
        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "plan": ref(path),
        "completed": dict(plan.get("adopted_collections", {})),
    }

    def record(status, **extra):
        state.update(status=status, updated_unix=time.time(), **extra)
        save(Path(plan.get("status_path", root / "supplement-status.json")), state)

    try:
        for label in ("V143", "V144", "V145"):
            point = root / label
            if label in state["completed"]:
                assert label == "V143"
                retained_parent_collection(root, state["completed"][label])
                record("adopted-parent-collection-without-replay", model=label)
                continue
            if label != "V143":
                record("waiting-for-both-original-primary-reviews", model=label)
                deadline = min(
                    time.time() + 72000, plan.get("absolute_deadline_unix", float("inf"))
                )
                while True:
                    primary = read(
                        Path(plan.get("primary_status_path", PRIMARY / "review-status.json"))
                    )
                    assert primary["owner"] == plan["primary_owner"]
                    assert primary["plan"] == plan["primary_review_plan"]
                    assert not primary["status"].startswith("failed"), primary
                    if primary[
                        "status"
                    ] == "completed-both-pilots-awaiting-native-viewing" and not live(
                        primary["owner"]
                    ):
                        break
                    assert time.time() < deadline
                    time.sleep(10)
                executed = read(PRIMARY / label / "plan-v1.json")
                guard(executed)
                queued = read(point / "queue-plan-v1.json")
                save(
                    point / "plan-v1.json",
                    {
                        **queued,
                        "checkpoint": executed["checkpoint"],
                        "inputs": [
                            *queued["inputs"],
                            executed["checkpoint"],
                            ref(PRIMARY / label / "plan-v1.json"),
                        ],
                    },
                )
            actual = read(point / "plan-v1.json")
            guard(actual)
            record("collecting-declared-photographic-contexts", model=label)
            with (point / "collect.log").open("x") as log:
                subprocess.run(
                    [
                        plan["python"],
                        "-P",
                        actual["collector"]["path"],
                        str(point / "plan-v1.json"),
                    ],
                    cwd=Path(actual["work"]),
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    check=True,
                    timeout=3600,
                    env={
                        **os.environ,
                        "CUDA_VISIBLE_DEVICES": "0",
                        "HF_HUB_OFFLINE": "1",
                        "TRANSFORMERS_OFFLINE": "1",
                        "OMP_NUM_THREADS": "1",
                        "OPENBLAS_NUM_THREADS": "1",
                        "PYTHONPATH": f"{actual['work']}/src:{actual['work']}/scripts",
                    },
                )
            state["completed"][label] = ref(point / "collection-v1.json")
            record("completed-photographic-collection", model=label)
        record("completed-photo-collections-making-report")
        report(path)
        record("auditing-photographic-supplement")
        with (root / "independent-audit.log").open("x") as log:
            subprocess.run(
                [plan["python"], "-P", plan["auditor"]["path"], str(path)],
                cwd=REPO,
                env={**os.environ, "CUDA_VISIBLE_DEVICES": ""},
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=1800,
            )
        record("completed-photographic-supplement-awaiting-native-viewing")
    except BaseException as error:
        record("failed-photographic-supplement-preserved", error=repr(error))
        raise


def photo_metrics(value, target, arrays, roi):
    from report_checkpoint_pilot import band

    from demosaic.archive_metrics import linear_rgb

    x, y, w, h = roi
    a, b = [v[..., y : y + h, x : x + w].astype(np.float64) for v in (value, target)]
    error = a - b
    dc = error.mean((-1, -2), keepdims=True)
    predicted, _ = band(linear_rgb(a, arrays))
    truth, _ = band(linear_rgb(b, arrays))
    energy = float(np.sum(truth * truth))
    if energy <= 0:
        raise ValueError("Photo diagnostic needs nonzero target detail")
    gain = float(np.sum(predicted * truth) / energy)
    return {
        "full_error_RMS_DN16": float(
            np.sqrt(np.mean((value.astype(np.float64) - target) ** 2)) * 65535
        ),
        "crop_error_RMS_DN16": float(np.sqrt(np.mean(error**2)) * 65535),
        "crop_DC_RMS_DN16": float(np.sqrt(np.mean(dc**2)) * 65535),
        "crop_spatial_RMS_DN16": float(np.sqrt(np.mean((error - dc) ** 2)) * 65535),
        "crop_linear_sRGB_luma_band_gain": gain,
        "crop_relative_band_error": float(np.sqrt(np.sum((predicted - truth) ** 2) / energy)),
        "crop_orthogonal_band_RMS_DN16": float(
            np.sqrt(np.sum((predicted - gain * truth) ** 2) / (100 * 256)) * 65535
        ),
    }


def report(path):
    from report_checkpoint_pilot import pixels

    from demosaic.archive_metrics import noisy_malvar

    plan = read(path)
    guard(plan)
    root = Path(plan["root"])
    parent = {
        o["id"]: o["parent_prediction"] for o in plan["observations"] if "parent_prediction" in o
    }
    predictions, checkpoints = {}, {}
    for label, count in (("V143", 64), ("V144", 128), ("V145", 128)):
        point = root / label
        actual = read(point / "plan-v1.json")
        guard(actual)
        collection = read(point / "collection-v1.json")
        assert collection["plan"] == ref(point / "plan-v1.json")
        assert collection["counts"] == {"root": count, "encoder": count}
        assert collection["RNG_unchanged"]
        assert collection["full_model_before"] == collection["full_model_after"]
        assert collection["backbone_before"] == collection["backbone_after"]
        bindings = {o["id"]: o["prediction"] for o in collection["observations"]}
        if label == "V143":
            assert not parent.keys() & bindings.keys()
            parent.update(bindings)
            bindings = parent
        predictions[label] = bindings
        checkpoints[label] = actual["checkpoint"]
    assert all(set(p) == {o["id"] for o in plan["observations"]} for p in predictions.values())
    out = root / "report-v1"
    out.mkdir(exist_ok=False)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    rows, images = [], []
    for observation in plan["observations"]:
        assert ref(observation["arrays"]["path"]) == observation["arrays"]
        with np.load(observation["arrays"]["path"], allow_pickle=False) as data:
            arrays = {k: data[k] for k in data.files}
        values = {}
        for label, bindings in predictions.items():
            binding = bindings[observation["id"]]
            assert ref(binding["path"]) == binding
            values[label] = np.load(binding["path"], allow_pickle=False)
            rows.append(
                {
                    "id": observation["id"],
                    "source_id": observation["source"]["id"],
                    "cohort": observation["cohort"],
                    "variant": observation["variant"]["name"],
                    "pattern": observation["pattern"],
                    "method": label,
                    "prediction": binding,
                    **photo_metrics(
                        values[label], arrays["target"], arrays, observation["ROI_xywh"]
                    ),
                }
            )
        if observation["pattern"] != "RGGB":
            continue
        all_values = {"Noisy": noisy_malvar(arrays), **values, "Constructed GT": arrays["target"]}
        roi = observation["ROI_xywh"]
        x, y, w, h = roi
        anchor = (
            arrays["target"][..., y : y + h, x : x + w]
            .astype(np.float64)
            .mean((-1, -2), keepdims=True)
        )

        def emit(
            labels,
            contrast,
            suffix,
            observation=observation,
            all_values=all_values,
            anchor=anchor,
            arrays=arrays,
            roi=roi,
        ):
            canvas = Image.new("RGB", (8 + 168 * len(labels), 192), "#eeeeee")
            draw = ImageDraw.Draw(canvas)
            panels = []
            for i, label in enumerate(labels):
                value = anchor + contrast * (all_values[label].astype(np.float64) - anchor)
                cell = pixels(value, arrays, roi, observation["display_exposure"])
                assert cell.shape == (160, 160, 3)
                x0 = 8 + 168 * i
                canvas.paste(Image.fromarray(cell), (x0, 24))
                draw.text((x0, 5), label, font=font, fill="black")
                panels.append({"label": label, "xywh": [x0, 24, 160, 160]})
            target = out / (observation["id"] + "-" + suffix + ".png")
            canvas.save(target)
            reread = np.asarray(Image.open(target))
            for panel in panels:
                label = panel["label"]
                value = anchor + contrast * (all_values[label].astype(np.float64) - anchor)
                cell = pixels(value, arrays, roi, observation["display_exposure"])
                x0, y0, w0, h0 = panel["xywh"]
                np.testing.assert_array_equal(reread[y0 : y0 + h0, x0 : x0 + w0], cell)
            images.append(
                {
                    "image": ref(target),
                    "observation": observation,
                    "panels": panels,
                    "checkpoint_hashes": {k: v["sha256"] for k, v in checkpoints.items()},
                    "shared_display_contrast": contrast,
                    "shared_camera_RGB_anchor": anchor.ravel().tolist(),
                    "display_exposure": observation["display_exposure"],
                    "no_resize": True,
                }
            )

        emit(list(all_values), 1, "comparison")
        if observation["variant"]["name"] == "photo-faint":
            emit(list(all_values), 8, "contrast8-comparison")
        if observation["cohort"] == "organic384" and observation["source"]["id"] in (
            read(root / "organic-source-choice-v1.json")["sources"][0]["id"],
            read(root / "organic-source-choice-v1.json")["sources"][1]["id"],
        ):
            for method in ("V144", "V145"):
                emit(["Noisy", method, "Constructed GT"], 1, method + "-triplet")
    groups = defaultdict(list)
    for row in rows:
        groups[row["cohort"], row["variant"], row["method"]].append(row)
    keys = [k for k, v in rows[0].items() if isinstance(v, float)]
    summary = [
        {
            "cohort": k[0],
            "variant": k[1],
            "method": k[2],
            "cases": len(v),
            "independent_source_images": len({r["source_id"] for r in v}),
            **{metric: float(np.mean([r[metric] for r in v])) for metric in keys},
        }
        for k, v in groups.items()
    ]
    save(
        out / "result-v1.json",
        {
            "status": "completed-photographic-supplement-report-awaiting-independent-audit-and-viewing",
            "plan": ref(path),
            "checkpoints": checkpoints,
            "rows": rows,
            "summary": summary,
            "images": images,
            "actual_new_root_and_encoder_calls": 320,
            "new_noise_observations": 64,
            "metric_definition": "Camera-RGB error and DC/spatial decomposition; native160 linear-sRGB "
            "luma DCT16 annulus1/8<=frequency<1/3, no content selection. Ideal gain1; gain requires "
            "error/residual checks. Constructed targets are not exact physical scene GT. Per-CFA "
            "cases share16 source images; do not treat128 cases as128 independent photos.",
        },
    )
    print(out / "result-v1.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "recover", "run", "report"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--primary-plan", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.path.resolve())
    elif args.mode == "recover":
        if args.primary_plan is None:
            parser.error("recover requires --primary-plan")
        print(prepare_recovery(args.path.resolve(), args.primary_plan.resolve()))
    elif args.mode == "run":
        run(args.path.resolve())
    else:
        report(args.path.resolve())
