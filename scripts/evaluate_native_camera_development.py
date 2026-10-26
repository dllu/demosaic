"""Collect new native-camera predictions once, then score retained arrays on CPU."""

import argparse
import datetime
import hashlib
import json
import math
import os
import random
import sys
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import psutil
from PIL import Image

from demosaic import archive_metrics
from demosaic.prediction_archive import PredictionArchive, fingerprint, iter_predictions


def read(path):
    return json.loads(Path(path).read_text())


def binding(path):
    path = Path(path).absolute()
    with path.open("rb") as stream:
        return {"path": str(path), "sha256": hashlib.file_digest(stream, "sha256").hexdigest()}


def checked(item):
    if binding(item["path"]) != item:
        raise ValueError(f"Changed native comparison input: {item['path']}")
    return Path(item["path"])


def write(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def guard(plan):
    for item in plan["inputs"]:
        checked(item)
    for path, digest in plan["frozen_files"].items():
        checked({"path": path, "sha256": digest})


def local_time():
    return datetime.datetime.now(ZoneInfo("America/Los_Angeles")).isoformat()


def source_means(rows, metric):
    groups = defaultdict(list)
    for row in rows:
        groups[row["source_id"]].append(row[metric])
    return {source: float(np.mean(values)) for source, values in sorted(groups.items())}


def proof(output):
    """Closed-form photometry and unequal-coverage source-weighting checks."""
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "" and "torch" not in sys.modules
    target = np.full((1, 3, 256, 256), .1, np.float32)
    prediction = np.full_like(target, .2)
    supervision = {"target": target, "wb": np.ones((1, 3), np.float32),
                   "matrix": np.eye(3, dtype=np.float32)[None]}
    scores = archive_metrics.photometry(prediction, supervision, border=48)
    delta = float(np.float32(.2)) - float(np.float32(.1))
    expected = -20 * math.log10(delta)
    assert abs(float(scores["linear_psnr"][0]) - expected) < 1e-11
    assert abs(float(scores["gradient_mae"][0])) < 1e-12
    a, b = (1.055 * float(v)**(1/2.4) - .055 for v in (np.float32(.2), np.float32(.1)))
    assert abs(float(scores["srgb_psnr"][0]) + 20 * math.log10(a-b)) < 1e-11
    rows = [{"source_id": "A", "change": 1.0}] * 3 + [{"source_id": "B", "change": -1.0}]
    equal = float(np.mean(list(source_means(rows, "change").values())))
    pooled = float(np.mean([r["change"] for r in rows]))
    assert equal == 0 and pooled == .5
    result = {"driver": binding(__file__), "status": "completed-closed-form-native-metric-proof",
              "constant_camera_PSNR_expected": expected, "constant_camera_PSNR_actual": float(scores["linear_psnr"][0]),
              "equal_source_change": equal, "incorrect_case_pooled_change": pooled,
              "new_neural_forwards": 0, "new_noise_observations": 0, "Torch_imported": False}
    write(output, result)
    return result


def collect(plan_path):
    tracking = {"started_root_calls": 0, "completed_valid_root_calls": 0,
                "encoder_calls": 0, "reference_network_calls": 0, "method": None}
    try:
        return _collect(plan_path, tracking)
    except BaseException as error:
        root = Path(read(plan_path)["root"])
        write(root / "collection-failure-v1.json", {
            "recorded_local": local_time(), "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "execution_plan": binding(plan_path), "actual_tracking": tracking, "error": repr(error),
            "scope": "Preserve completed predictions and actual attempted/completed call counts; no automatic retry."})
        raise


def reuse_completed_joint_predictions(plan, dataset, archive):
    """Recover a fully saved joint prefix after a pre-forward reference failure.

    Preserve the original manifest and call receipt. Append verified NPY links
    to a new archive, without loading any joint model or rerunning its encoder.
    """
    retained = plan.get("retained_collection")
    if retained is None:
        return []
    failure = read(checked(retained["failure"]))
    previous = read(checked(retained["execution_plan"]))
    assert failure["execution_plan"] == retained["execution_plan"]
    assert previous["dataset_manifest"] == plan["dataset_manifest"]
    labels = [m["label"] for m in plan["methods"] if m["kind"] == "joint"]
    assert labels == ["V114", "V115", "V117", "V119"]
    expected = {o["id"]: o for o in dataset["observations"]}
    total = len(expected) * len(labels)
    tracking = failure["actual_tracking"]
    assert tracking["method"] == "RawNIND-preup"
    assert tracking["started_root_calls"] == tracking["completed_valid_root_calls"] == total
    assert tracking["encoder_calls"] == total and tracking["reference_network_calls"] == 0
    methods = {m["label"]: m for m in plan["methods"] if m["kind"] == "joint"}
    prior = {m["label"]: m for m in previous["methods"] if m["kind"] == "joint"}
    assert methods == prior
    references = {
        r["case_id"]: fingerprint(np.load(checked(r["reference_camera_FP32"]), allow_pickle=False))
        for r in dataset["rows"]
    }
    seen = {label: set() for label in labels}
    for record, prediction, supervision in iter_predictions(checked(retained["archive"])):
        label, context = record["model"]["label"], record["context"]
        assert label in methods and len(context["ids"]) == 1
        identity = context["ids"][0]
        assert identity in expected and identity not in seen[label]
        observation = expected[identity]
        assert context["input_arrays"] == observation["arrays"]
        assert context["input_fingerprints"] == observation["input_fingerprints"]
        assert context["case_id"] == observation["case_id"]
        assert fingerprint(supervision["target"]) == references[context["case_id"]]
        for key in ("wb", "matrix"):
            assert fingerprint(supervision[key]) == observation["input_fingerprints"][key]
        method = methods[label]
        assert record["model"] == {
            "label": label,
            "sha256": method["checkpoint"]["sha256"],
            "step": 20000,
            "self_ensemble": "none",
            "kind": "joint",
        }
        archive.append(
            record["model"],
            context,
            prediction,
            supervision,
            prediction_file=record["prediction"]["path"],
        )
        seen[label].add(identity)
    assert all(values == set(expected) for values in seen.values())
    return [
        {
            "method": methods[label],
            "root_calls": len(expected),
            "encoder_calls": len(expected),
            "reference_network_calls": 0,
            "new_root_calls": 0,
            "reused_prediction_count": len(expected),
            "source_failure": retained["failure"],
            "source_archive": retained["archive"],
            "integrity": "Original collector passed each joint method's final state/gradient checks before failing the reference pre-forward check; saved arrays and all input/reference bindings are verified here.",
        }
        for label in labels
    ]


def _collect(plan_path, tracking):
    import torch
    from frozen_backbone_identity import verify_backbone_identity
    from profile_raw_kernel_inference import model_hash

    from demosaic.inference import load_checkpoint
    from demosaic.reference import load_rawnind

    plan = read(plan_path)
    guard(plan)
    root, work = Path(plan["root"]), Path(plan["work"])
    assert binding(__file__) == plan["collector_source"]
    assert [m["label"] for m in plan["methods"]] == ["V114", "V115", "V117", "V119", "RawNIND-preup"]
    assert len({m["checkpoint"]["sha256"] for m in plan["methods"]}) == 5
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "0"
    assert Path(load_checkpoint.__code__.co_filename).absolute().is_relative_to(work / "src")
    (root / "collector.claim").open("x").close()
    assert psutil.virtual_memory().available >= 48 * 2**30
    torch.set_num_threads(4)
    torch.cuda.set_per_process_memory_fraction(min(1, 24*2**30/torch.cuda.get_device_properties(0).total_memory))
    torch.set_float32_matmul_precision("highest")
    torch.backends.cuda.matmul.allow_tf32 = torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = True
    dataset = read(checked(plan["dataset_manifest"]))
    targets = {r["case_id"]: r for r in dataset["rows"]}
    manifest = dataset["observations"]
    assert len(manifest) == 240 and len(targets) == 20
    loaded, references = [], {}
    for row in targets.values():
        values = np.load(checked(row["reference_camera_FP32"]), allow_pickle=False)
        assert values.shape == (1, 3, 256, 256) and values.dtype == np.float32
        references[row["case_id"]] = values
    for observation in manifest:
        with np.load(checked(observation["arrays"]), allow_pickle=False) as values:
            batch = {k: torch.from_numpy(values[k].copy()) for k in values.files}
        assert {k: fingerprint(v) for k, v in batch.items()} == observation["input_fingerprints"]
        loaded.append((observation, batch))
    archive = PredictionArchive(root / "archive")
    results = reuse_completed_joint_predictions(plan, dataset, archive)
    reused = {r["method"]["label"] for r in results}
    for method in plan["methods"]:
        if method["label"] in reused:
            continue
        tracking["method"] = method["label"]
        record = {"method": method, "root_calls": 0, "encoder_calls": 0, "reference_network_calls": 0}
        python_rng = random.getstate()
        with torch.random.fork_rng(devices=[0]):
            if method["kind"] == "joint":
                model, state = load_checkpoint(checked(method["checkpoint"]), "cuda")
                assert state["loaded_sha256"] == method["checkpoint"]["sha256"] and state["step"] == 20000
                assert state["config"]["initialized_from"] == method["expected_lineage"]["initialized_from"]
                actual = model.restoration_state_dict()
                assert len(actual) == 91 and actual.keys() == state["ema"].keys()
                assert all(torch.equal(v.cpu(), state["ema"][k]) for k, v in actual.items())
                verify_backbone_identity(model.config.to_dict(), model_hash(model.context.backbone),
                                         {"expected_backbone": method["expected_backbone"]},
                                         legacy_sha256=method["expected_backbone"]["sha256"])
                assert all(not p.requires_grad for p in model.context.backbone.parameters())
                del actual, state
            else:
                assert method["kind"] == "rawnind-preup"
                model = load_rawnind(method["directory"], gain_mode="cfa-channel", device="cuda",
                                     input_scale=None, clip_input=False)
                assert model.reference_config["preupsample"] and model.reference_config["funit"] == 32
                # Established hash includes wrapper network.* state keys.
                expected = method.get("expected_wrapper_sha256", method.get("expected_network_sha256"))
                assert model_hash(model) == expected
        random.setstate(python_rng)
        model.eval()
        record["initial_model_sha256"] = model_hash(model)
        if method["kind"] == "joint":
            assert record["initial_model_sha256"] == method["expected_full_model_sha256"]
        handles = []

        def before(module, args, record=record):
            tracking["started_root_calls"] += 1
            assert not module.training and len(args) == 5
            assert not torch.backends.cuda.matmul.allow_tf32 and not torch.backends.cudnn.allow_tf32
            actual_inputs = {k: fingerprint(v) for k, v in zip(("packed", "variance", "colors", "wb", "matrix"), args, strict=True)}
            assert actual_inputs == record["expected_inputs"]
            record["latest_inputs"] = actual_inputs
            assert psutil.virtual_memory().available >= 24 * 2**30

        def after(module, args, prediction, record=record):
            assert prediction.shape == (1, 3, 256, 256) and prediction.dtype == torch.float32
            assert torch.isfinite(prediction).all()
            assert {k: fingerprint(v) for k, v in zip(("packed", "variance", "colors", "wb", "matrix"), args, strict=True)} == record["latest_inputs"]
            record["root_calls"] += 1
            tracking["completed_valid_root_calls"] += 1

        def encoded(*args, record=record):
            record["encoder_calls"] += 1
            tracking["encoder_calls"] += 1

        def reference_called(*args, record=record):
            record["reference_network_calls"] += 1
            tracking["reference_network_calls"] += 1

        handles.extend((model.register_forward_pre_hook(before), model.register_forward_hook(after)))
        if method["kind"] == "joint":
            handles.append(model.context.backbone.register_forward_hook(encoded))
        else:
            handles.append(model.network.register_forward_hook(reference_called))
        descriptor = {"label": method["label"], "sha256": method["checkpoint"]["sha256"],
                      "step": 20000 if method["kind"] == "joint" else None, "self_ensemble": "none",
                      "kind": method["kind"]}
        with torch.inference_mode():
            for index, (observation, cpu) in enumerate(loaded):
                record["expected_inputs"] = observation["input_fingerprints"]
                batch = {k: v.to("cuda") for k, v in cpu.items()}
                if hasattr(model, "set_noise"):
                    model.set_noise(observation["condition"]["shot"], observation["condition"]["read"])
                with torch.autocast(device_type="cuda", enabled=False):
                    prediction = model(*(batch[k] for k in ("packed", "variance", "colors", "wb", "matrix")))
                target = targets[observation["case_id"]]
                context = {"stage": "native-camera-development", "ids": [observation["id"]],
                           "case_id": observation["case_id"], "source_id": observation["source_id"],
                           "scene_group": observation["scene_group"], "source_file_id": observation["source_file_id"],
                           "condition": observation["condition"], "pattern": observation["pattern"],
                           "input_fingerprints": observation["input_fingerprints"], "input_arrays": observation["arrays"],
                           "target_role": dataset["target_role"], "score_ROI_xywh": [48, 48, 160, 160],
                           "display_exposure": target["display_exposure"]}
                archive.append(descriptor, context, prediction,
                               {"target": references[observation["case_id"]],
                                "wb": cpu["wb"], "matrix": cpu["matrix"]})
                if (index+1) % 40 == 0:
                    print({"method": method["label"], "new_input_predictions": index+1}, flush=True)
                del batch, prediction
        assert record["root_calls"] == 240
        assert record["encoder_calls"] == (240 if method["kind"] == "joint" else 0)
        assert record["reference_network_calls"] == (240 if method["kind"] != "joint" else 0)
        assert model_hash(model) == record["initial_model_sha256"]
        assert all(p.grad is None for p in model.parameters())
        for handle in handles:
            handle.remove()
        del model
        import gc
        gc.collect()
        torch.cuda.empty_cache()
        record.pop("latest_inputs")
        record.pop("expected_inputs")
        record["new_root_calls"] = record["root_calls"]
        record["reused_prediction_count"] = 0
        write(root / (method["label"] + "-method-v1.json"), record)
        results.append(record)
    alignment = archive.verify_alignment()
    assert alignment["models"] == 5 and alignment["observations_per_model"] == 240 and alignment["records"] == 1200
    assert sum(r["root_calls"] for r in results) == 1200
    assert sum(r["encoder_calls"] for r in results) == 960
    guard(plan)
    write(root / "collection-result-v1.json", {"status": "completed-new-native-input-predictions-awaiting-CPU-review",
          "recorded_local": local_time(), "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
          "execution_plan": binding(plan_path), "archive": binding(archive.manifest), "methods": results,
          "alignment": alignment, "neural_root_calls": 1200, "frozen_DINO_encoder_calls": 960,
          "actual_tracking": tracking,
          "retained_collection": plan.get("retained_collection"),
          "new_neural_root_calls": sum(r["new_root_calls"] for r in results),
          "reused_prediction_count": sum(r["reused_prediction_count"] for r in results),
          "new_noise_observations": 0, "optimizer_updates": 0, "RAW_decodes": 0,
          "scope": "First predictions on the frozen 240 native-camera development inputs; single-view IEEE FP32. Identical stored inputs and target estimates across methods. No new noise, target/inverse-camera conversion or intermediate V119 checkpoint. Native viewing and recommendation remain separate."})


def analyze(plan_path):
    from diagnose_local_material_detail import basis
    from PIL import ImageDraw, ImageFont

    assert os.environ["CUDA_VISIBLE_DEVICES"] == "" and "torch" not in sys.modules
    os.nice(10)
    process = psutil.Process()
    process.cpu_affinity(process.cpu_affinity()[:2])
    plan = read(plan_path)
    guard(plan)
    root = Path(plan["root"])
    (root / "analysis.claim").open("x").close()
    collection = read(checked(binding(root / "collection-result-v1.json")))
    assert collection["neural_root_calls"] == 1200 and collection["execution_plan"] == binding(plan_path)
    output = root / "analysis"
    output.mkdir(exist_ok=False)
    proof(output / "metric-proof-v1.json")
    dataset = read(checked(plan["dataset_manifest"]))
    targets = {r["case_id"]: r for r in dataset["rows"]}
    observations = {r["id"]: r for r in dataset["observations"]}
    c = basis(16)
    f = np.arange(16)/32
    band = (np.hypot(f[:, None], f[None, :]) >= 1/8) & (np.hypot(f[:, None], f[None, :]) < 1/3)
    edges = np.array([0, .02, .05, .1, .2, np.inf])
    reference_cache, numerical, local, displayed, predictions = {}, [], defaultdict(lambda: np.zeros(4)), {}, {}
    physical_blocks = set()
    def reference(value, data, case_id):
        if case_id in reference_cache:
            return reference_cache[case_id]
        rgb = archive_metrics.linear_rgb(value, data)[0, :, 48:208, 48:208]
        luma = np.einsum("c,chw->hw", np.array([.2126, .7152, .0722]), rgb)
        block = luma.reshape(10, 16, 10, 16).transpose(0, 2, 1, 3).reshape(100, 16, 16)
        coeff = (c @ block @ c.T)[..., band]
        rms = np.sqrt(np.sum(coeff**2, axis=1)/256)
        mean = block.mean((1, 2))
        valid_rgb = ((rgb >= 0) & (rgb <= 1)).all(0).reshape(10,16,10,16).transpose(0,2,1,3).reshape(100,256).all(1)
        eligible = valid_rgb & (mean >= .02) & (mean <= .9) & (rms >= 1e-5)
        bins = np.digitize(rms/np.maximum(mean, 1e-12), edges[1:-1])
        row = targets[case_id]
        x, y, _, _ = row["xywh"]
        for j in range(100):
            physical_blocks.add((row["source_id"], x+48+(j%10)*16, y+48+(j//10)*16))
        result = coeff, eligible, bins
        reference_cache[case_id] = result
        return result
    archive = checked(collection["archive"])
    with (output / "per-observation-v1.jsonl").open("x") as stream:
        for record, prediction, supervision in iter_predictions(archive):
            context, model = record["context"], record["model"]
            row = observations[context["ids"][0]]
            assert context["input_arrays"] == row["arrays"] and context["input_fingerprints"] == row["input_fingerprints"]
            scores = archive_metrics.photometry(prediction, supervision, border=48)
            p, t = (v[..., 48:208, 48:208].astype(np.float64) for v in (prediction, supervision["target"]))
            error = p-t
            flat = (np.clip(p,0,1)-np.clip(t,0,1)).ravel()
            independent = -10*math.log10(max(float(np.dot(flat,flat)/len(flat)),1e-12))
            assert abs(float(scores["linear_psnr"][0])-independent) < 1e-10
            metrics = {k: float(v[0]) for k,v in scores.items()}
            bias = error.mean((0,2,3))
            result = {"method": model["label"], "checkpoint_sha256": model["sha256"],
                      "observation_id": row["id"], "case_id": row["case_id"], "source_id": row["source_id"],
                      "condition": row["condition"]["name"], "pattern": row["pattern"], **metrics,
                      "unclipped_camera_RGB_MSE": float(np.mean(error**2)),
                      "camera_RGB_mean_error_DN16": (bias*65535).tolist(),
                      "spatially_centered_camera_error_RMS": float(np.sqrt(np.mean((error-bias[None,:,None,None])**2)))}
            assert all(math.isfinite(result[k]) for k in ("linear_psnr", "srgb_psnr", "chroma_mae", "gradient_mae", "unclipped_camera_RGB_MSE"))
            numerical.append(result)
            stream.write(json.dumps(result, allow_nan=False)+"\n")
            truth, eligible, bins = reference(supervision["target"], supervision, row["case_id"])
            rgb = archive_metrics.linear_rgb(prediction, supervision)[0,:,48:208,48:208]
            luma = np.einsum("c,chw->hw", np.array([.2126,.7152,.0722]),rgb)
            blocks = luma.reshape(10,16,10,16).transpose(0,2,1,3).reshape(100,16,16)
            coeff = (c @ blocks @ c.T)[...,band]
            for bin_index in range(5):
                mask = eligible & (bins == bin_index)
                if mask.any():
                    key = model["label"], result["condition"], row["source_id"], bin_index
                    local[key] += [np.sum(truth[mask]**2),np.sum(truth[mask]*coeff[mask]),np.sum(coeff[mask]**2),mask.sum()]
            if row["pattern"] == "RGGB":
                key = row["case_id"], result["condition"]
                predictions[(model["label"],*key)] = record["prediction"]
                if key not in displayed:
                    with np.load(checked(row["arrays"]), allow_pickle=False) as values:
                        data = {k:values[k] for k in values.files}
                    noisy = archive_metrics.noisy_malvar(data)
                    exposure = targets[row["case_id"]]["display_exposure"]
                    def pixels(value, supervision=supervision, exposure=exposure):
                        return np.rint(np.clip(archive_metrics.display(value, supervision, exposure)[0,:,48:208,48:208].transpose(1,2,0),0,1)*255).astype(np.uint8)
                    displayed[key] = (pixels(noisy),pixels(supervision["target"]),supervision)
    assert len(numerical) == 1200 and len(reference_cache) == 20
    summaries = []
    for method in plan["methods"]:
        for condition in dataset["noise_protocol"]["conditions"]:
            selected = [r for r in numerical if r["method"] == method["label"] and r["condition"] == condition["name"]]
            assert len(selected) == 80
            summaries.append({"method":method["label"],"condition":condition["name"],"sources":11,
                "metrics":{k:{"mean":float(np.mean(list(source_means(selected,k).values()))),"by_source":source_means(selected,k)}
                           for k in ("linear_psnr","srgb_psnr","chroma_mae","gradient_mae","unclipped_camera_RGB_MSE")}})
    local_summaries = []
    for method in plan["methods"]:
        for condition in dataset["noise_protocol"]["conditions"]:
            for b in range(5):
                values = []
                for (label,name,source,bin_index),sums in local.items():
                    if (label,name,bin_index)!=(method["label"],condition["name"],b):
                        continue
                    energy,cross,power,count = sums
                    values.append({"source_id":source,"reference_projected_gain":float(cross/energy),
                         "band_error_RMS":float(np.sqrt(max(power+energy-2*cross,0)/(count*256))),
                         "orthogonal_band_RMS":float(np.sqrt(max(power-cross*cross/energy,0)/(count*256))),"block_observations":int(count)})
                local_summaries.append({"method":method["label"],"condition":condition["name"],"reference_contrast_bin":b,
                    "contributing_sources":len(values),"by_source":values,
                    "equal_source_means":{k:float(np.mean([v[k] for v in values])) if values else None
                                           for k in ("reference_projected_gain","band_error_RMS","orthogonal_band_RMS")}})
    comparisons = []
    index = {(r["method"],r["condition"]):r for r in summaries}
    resampling = np.random.default_rng(20261025).integers(0,11,size=(10000,11))
    for control in ("V114","V115","V117","RawNIND-preup"):
        for condition in dataset["noise_protocol"]["conditions"]:
            for metric in ("linear_psnr","srgb_psnr","chroma_mae","gradient_mae"):
                left = index[(control,condition["name"])]["metrics"][metric]["by_source"]
                right = index[("V119",condition["name"])]["metrics"][metric]["by_source"]
                assert left.keys()==right.keys() and len(left)==11
                changes = np.array([right[k]-left[k] for k in sorted(left)])
                sampled = changes[resampling].mean(1)
                comparisons.append({"control":control,"candidate":"V119","condition":condition["name"],
                    "metric":metric,"change":float(changes.mean()),"capture_bootstrap_95_interval":np.quantile(sampled,[.025,.975]).tolist(),
                    "source_changes":dict(zip(sorted(left),changes.tolist(),strict=True)),
                    "positive_is_better":metric.endswith("psnr")})
    images, boards = [], []
    labels = [m["label"] for m in plan["methods"]]
    font = ImageFont.load_default(size=12)
    for condition in dataset["noise_protocol"]["conditions"]:
        name = condition["name"]
        for page in range(4):
            case_rows = dataset["rows"][page*5:page*5+5]
            board = Image.new("RGB",(1120,960),(25,25,25))
            draw = ImageDraw.Draw(board)
            for j,label in enumerate(["Noisy Malvar",*labels,"Low-noise reference"]):
                draw.text((j*160+4,7),label,font=font,fill="white")
            for i,target in enumerate(case_rows):
                key = target["case_id"], name
                noisy,truth,supervision = displayed[key]
                cells = [noisy]
                for label in labels:
                    value = np.load(checked(predictions[(label,*key)]),allow_pickle=False)
                    pixels = np.rint(np.clip(archive_metrics.display(value,supervision,target["display_exposure"])[0,:,48:208,48:208].transpose(1,2,0),0,1)*255).astype(np.uint8)
                    cells.append(pixels)
                    if name=="iso12800-prior" and target["case_id"] in {"pixls-5002-fine","pixls-1951-field"}:
                        pixels3 = np.concatenate([noisy,pixels,truth],axis=1)
                        path=output/f"{label}-{target['case_id']}-native-triplet.png"
                        Image.fromarray(pixels3).save(path)
                        images.append({"image":binding(path),"method":label,"case_id":target["case_id"],
                             "checkpoint":next(m["checkpoint"] for m in plan["methods"] if m["label"]==label),
                             "observation":observations[next(r['id'] for r in dataset['observations'] if r['case_id']==target['case_id'] and r['condition']['name']==name and r['pattern']=='RGGB')],
                             "ROI":target["xywh"],"score_display_ROI":[48,48,160,160],"display_exposure":target["display_exposure"],
                             "target_role":dataset["target_role"],"resized":False})
                cells.append(truth)
                assert all(cell.shape==(160,160,3) for cell in cells)
                for j,cell in enumerate(cells):
                    board.paste(Image.fromarray(cell),(j*160,38+i*182))
                draw.text((4,201+i*182),target["case_id"]+" / "+target["raw_metadata"]["camera"],font=font,fill="white")
            path=output/f"all-native-{name}-{page+1}.png"
            board.save(path)
            boards.append({"image":binding(path),"condition":name,"pattern":"RGGB","case_ids":[r["case_id"] for r in case_rows],"resized":False})
    write(output/"native-images-v1.json",{"triplets":images,"boards":boards,"methods":plan["methods"],"dataset":plan["dataset_manifest"],
         "target_role":dataset["target_role"],"scope":"All cells native160 without resizing; noisy Malvar/method/low-noise reference. Same source transforms/exposure across methods. Source estimates retain noise/optics; actual viewing remains pending."})
    write(output/"metrics-v1.json",{"primary":summaries,"V119_comparisons":comparisons,"local_reference_band":local_summaries,
         "unique_physical_reference_blocks":len(physical_blocks),"total_ROI_reference_blocks":2000,
         "local_definition":{"block":16,"band":[1/8,1/3],"reference_RMS_minimum":1e-5,"reference_luma_range":[.02,.9],"relative_reference_contrast_edges":[0,.02,.05,.1,.2]},
         "scope":"NumPy64 scored native160. CFA/ROI repetitions average within source before equal-source means. Local band pools CFA/ROI blocks within source; repeated/overlapping blocks add no independent sources. Reference noise may contribute to fine bands; these measure reference recovery, not exact scene-detail recovery."})
    lines = ["# Native camera development comparison", "",
             "First predictions on 20 fixed binned contexts from 11 captures, three declared noise priors/four CFAs. References are low-noise estimates, not exact noiseless GT. Actual native viewing and interpretation remain pending.", "",
             "Source-level means average the repeated CFA/ROI cases within capture before equal-capture aggregation. Camera/place identities and training-seed uncertainty are not resolved by these small-set bootstrap intervals. The full 427-photo, measured-camera and standing GFX results retain their own scope.", "",
             "| Method | Condition | Camera RGB PSNR | Rendered sRGB PSNR | Chroma MAE | Gradient MAE |",
             "| --- | --- | ---: | ---: | ---: | ---: |"]
    for summary in summaries:
        m = summary["metrics"]
        lines.append(f"| {summary['method']} | {summary['condition']} | {m['linear_psnr']['mean']:.6f} | {m['srgb_psnr']['mean']:.6f} | {m['chroma_mae']['mean']:.8f} | {m['gradient_mae']['mean']:.8f} |")
    lines += ["", "All checkpoint hashes, source/ROI/conditioning/display transforms, unclipped camera errors and per-case/source values are retained in the bound JSON files. Local reference-band responses can include residual reference noise.", ""]
    for method in plan["methods"]:
        lines += [f"{method['label']}: `{method['checkpoint']['sha256']}`.", ""]
    for image in images:
        lines += [f"![Native160 noisy, {image['method']} and low-noise reference]({Path(image['image']['path']).name})", ""]
    for board in boards:
        lines += [f"![All methods and low-noise reference; {board['condition']}]({Path(board['image']['path']).name})", ""]
    (output/"report.md").write_text("\n".join(lines))
    assert "torch" not in sys.modules
    guard(plan)
    write(root/"analysis-result-v1.json",{"status":"completed-native-camera-scores-and-images-actual-viewing-pending",
         "recorded_local":local_time(),"owner":{"pid":os.getpid(),"created":process.create_time()},
         "execution_plan":binding(plan_path),"collection":binding(root/"collection-result-v1.json"),
         "per_observation":binding(output/"per-observation-v1.jsonl"),"metrics":binding(output/"metrics-v1.json"),
         "native_images":binding(output/"native-images-v1.json"),"metric_proof":binding(output/"metric-proof-v1.json"),
         "report":binding(output/"report.md"),
         "methods":5,"observations":1200,"sources":11,"native_triplets":10,"native_boards":12,
         "new_neural_forwards":0,"new_noise_observations":0,"RAW_decodes":0,"Torch_imported":False,
         "scope":"First source-balanced camera-RGB/sRGB/local-reference-band results on the frozen native development inputs. Capture-level/finite identity limits apply. Actual native viewing, interpretation and useful-model documentation remain required; no automatic promotion."})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("collect", "analyze", "proof"))
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    {"collect": collect, "analyze": analyze, "proof": proof}[args.mode](args.path)
