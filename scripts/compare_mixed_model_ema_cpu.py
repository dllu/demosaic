"""Check current versus EMA weights on the existing fixed mixed16 CPU inputs."""

import argparse
import gc
import json
import os
from pathlib import Path

import numpy as np
import psutil
import torch
from preview_completed_mixed_arm_cpu import batch, board, verify_png
from review_mixed_packed_trial import read, ref, sha

from demosaic.cfa import malvar
from demosaic.color import render
from demosaic.inference import load_checkpoint
from demosaic.precision import amp_context
from demosaic.reporting import display_crop, save_triplet
from demosaic.safety import writable_path

BASE = Path("/mnt/external/demosaic")
REVIEW = BASE / "benchmarks/packed-isotropic-mixed16-first32000-review-workflow-v1/plan.json"
ARMS = {
    "no-dino": "8d67375e2169adb88f7dcdafd253e23642eb0d87b1dc2d79416cb0f22320416a",
    "dino": "43c10f2a0af38761f9418f19c725edc4129284e76b5b2da89f66c184d1f643e1",
}


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def check_guards(plan):
    for path, digest in {**plan["inputs"], **plan["guards"]}.items():
        assert sha(path) == digest, path


def prepare(output):
    assert not torch.cuda.is_initialized()
    assert sha(REVIEW) == "77435a0e0f3b255a52751c4caaaecc4c9cef2e969730af1c12288d9874a1841d"
    review = read(REVIEW)
    check_guards(review)
    output = writable_path(output)
    assert not output.exists()
    arms = []
    inputs = {str(REVIEW): sha(REVIEW)}
    for arm, digest in ARMS.items():
        source = BASE / f"evaluation/packed-isotropic-mixed16-{arm}-first32000-CPU-preview-v1"
        report = read(source / "report.json")
        assert report["selected_arm"] == arm and not report["CUDA_initialized"]
        checkpoint = report["selected_boundary"]["checkpoint"]
        assert checkpoint["sha256"] == sha(checkpoint["path"]) == digest
        inputs[str(source / "report.json")] = sha(source / "report.json")
        inputs[checkpoint["path"]] = digest
        crops = [c for c in report["native_crops"] if c["checkpoint_sha256"] == digest]
        assert len(crops) == 6
        for crop in crops:
            for item in (crop["observation"], crop["prediction"]):
                assert sha(item["path"]) == item["sha256"]
                inputs[item["path"]] = item["sha256"]
            path = source / crop["image"]
            assert sha(path) == crop["png_sha256"]
            inputs[str(path)] = crop["png_sha256"]
            if "reference_RGB" in crop:
                item = crop["reference_RGB"]
                assert sha(item["path"]) == item["sha256"]
                inputs[item["path"]] = item["sha256"]
        arms.append({"arm": arm, "preview": ref(source / "report.json"), "checkpoint": checkpoint})
    import preview_completed_mixed_arm_cpu
    import review_mixed_packed_trial

    import demosaic

    guards = dict(review["guards"])
    guards.update(review["inputs"])
    sources = [
        Path(__file__),
        Path(preview_completed_mixed_arm_cpu.__file__),
        Path(review_mixed_packed_trial.__file__),
        *Path(demosaic.__file__).parent.glob("*.py"),
    ]
    guards.update({str(path.resolve()): sha(path) for path in sources})
    output.mkdir(parents=True)
    (output / "driver.py").write_bytes(Path(__file__).read_bytes())
    guards[str(output / "driver.py")] = sha(output / "driver.py")
    plan = {
        "root": str(output),
        "arms": arms,
        "inputs": inputs,
        "guards": guards,
        "protocol": "For each immutable 2k/32000-example checkpoint, first replay its existing CPU EMA predictions bitwise, then replace only restoration parameters with the same checkpoint's current model state. Same six preselected observations, IEEE FP32 NCHW, native coordinates/display/noise. Save all12 current predictions/triplets and direct current/EMA native boards. Photo error uses the fixed240x240 interior after border8, float64 accumulation; no real-reference scores. No optimization, diagnostic-weight archive, policy selection, training, GPU use, promotion or source admission. Selected examples cannot establish population performance, convergence or EMA's optimal decay.",
    }
    save(output / "plan.json", plan)
    print(
        json.dumps(
            {"prepared": ref(output / "plan.json"), "inputs": len(inputs), "guards": len(guards)}
        ),
        flush=True,
    )


def photo_metrics(prediction, target, values):
    result = {}
    for label, first, second in (
        ("camera", prediction, target),
        (
            "srgb",
            render(prediction, values["wb"], values["matrix"]),
            render(target, values["wb"], values["matrix"]),
        ),
    ):
        error = first[..., 8:-8, 8:-8].numpy().astype(np.float64) - second[
            ..., 8:-8, 8:-8
        ].numpy().astype(np.float64)
        mse = float(np.mean(error**2))
        result[label + "_mse"] = mse
        result[label + "_psnr"] = float(-10 * np.log10(max(mse, 1e-12)))
    return result


@torch.inference_mode()
def run(plan_path):
    assert not torch.cuda.is_available() and not torch.cuda.is_initialized(), "Hide CUDA"
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    os.nice(10)
    plan = read(plan_path)
    check_guards(plan)
    output = Path(plan["root"])
    with (output / "run.claim").open("x") as stream:
        stream.write(str(os.getpid()))
    crops, predictions, metrics, state_witnesses = [], [], [], []
    replays = 0
    for arm in plan["arms"]:
        preview_path = Path(arm["preview"]["path"])
        preview = read(preview_path)
        checkpoint = arm["checkpoint"]
        selected = [
            c for c in preview["native_crops"] if c["checkpoint_sha256"] == checkpoint["sha256"]
        ]
        model, state = load_checkpoint(checkpoint["path"], "cpu")
        assert (
            state["step"] == 2000 and state["data_step"] == 8000 and state["example_draws"] == 32000
        )
        assert state["model"].keys() == state["ema"].keys()
        version = "V72" if arm["arm"] == "no-dino" else "V73"
        model.eval()
        for policy in ("ema", "model"):
            incompatible = model.load_state_dict(state[policy], strict=False)
            assert not incompatible.unexpected_keys
            assert all(k.startswith("context.backbone.") for k in incompatible.missing_keys)
            assert all(
                torch.equal(v, state[policy][k]) for k, v in model.restoration_state_dict().items()
            )
            label = version + (" EMA2k" if policy == "ema" else " current2k")
            for meta in selected:
                values = batch(meta["observation"]["path"])
                if "sample_index" in meta["observation"]:
                    i = meta["observation"]["sample_index"]
                    values = {k: v[i : i + 1] for k, v in values.items()}
                with amp_context("cpu", dtype="float32"):
                    prediction = model(
                        *(values[k] for k in ("packed", "variance", "colors", "wb", "matrix"))
                    )
                assert prediction.dtype == torch.float32 and torch.isfinite(prediction).all()
                synthetic = meta["case"].startswith("photo-")
                if synthetic:
                    target = values["target"]
                    metrics.append(
                        {
                            "arm": arm["arm"],
                            "case": meta["case"],
                            "policy": policy,
                            **photo_metrics(prediction, target, values),
                        }
                    )
                if policy == "ema":
                    saved = np.load(meta["prediction"]["path"], allow_pickle=False)
                    np.testing.assert_array_equal(prediction.numpy(), saved)
                    replays += 1
                    crops.append(
                        {**meta, "image": str(preview_path.parent / meta["image"]), "method": label}
                    )
                    continue
                path = output / f"{arm['arm']}-{meta['case']}-current-RGB-f32.npy"
                np.save(path, prediction.numpy(), allow_pickle=False)
                np.testing.assert_array_equal(np.load(path, allow_pickle=False), prediction.numpy())
                saved = {
                    **ref(path),
                    "case": meta["case"],
                    "arm": arm["arm"],
                    "policy": policy,
                    "shape": list(prediction.shape),
                    "dtype": "float32",
                }
                predictions.append(saved)
                target = (
                    values["target"]
                    if synthetic
                    else torch.from_numpy(
                        np.load(meta["reference_RGB"]["path"], allow_pickle=False).copy()
                    )
                )
                panels = [
                    display_crop(
                        x, values["wb"], values["matrix"], roi, exposure=meta["display_exposure"]
                    )
                    for x, roi in (
                        (
                            malvar(values["packed"], values["colors"], values["wb"]),
                            meta["context_roi_xywh"],
                        ),
                        (prediction, meta["context_roi_xywh"]),
                        (target, meta["reference_roi_xywh"]),
                    )
                ]
                crop = save_triplet(
                    output,
                    label + meta["case"],
                    list(
                        zip(
                            (
                                "Noisy Malvar",
                                label,
                                "GT (synthetic)" if synthetic else "ISO100 ref, not GT",
                            ),
                            panels,
                            strict=True,
                        )
                    ),
                    caption=label + " / " + meta["case"],
                    metadata={
                        **{
                            k: v
                            for k, v in meta.items()
                            if k
                            not in (
                                "image",
                                "caption",
                                "panels",
                                "png_sha256",
                                "method",
                                "prediction",
                            )
                        },
                        "method": label,
                        "prediction": saved,
                        "selected_checkpoint_state": "model (current restoration parameters, no EMA)",
                        "comparison": "Same immutable checkpoint and fixed observation as EMA; no model weights saved or changed.",
                    },
                )
                verify_png(output, crop, panels)
                crops.append(crop)
                print(
                    json.dumps({"arm": arm["arm"], "policy": policy, "case": meta["case"]}),
                    flush=True,
                )
        assert all(
            torch.equal(v, state["model"][k]) for k, v in model.restoration_state_dict().items()
        )
        state_witnesses.append(
            {
                "checkpoint": checkpoint,
                "restoration_tensors": len(state["model"]),
                "EMA_tensors": len(state["ema"]),
                "tensors_with_current_EMA_difference": sum(
                    not torch.equal(state["model"][k], v) for k, v in state["ema"].items()
                ),
                "current_load_exact": True,
            }
        )
        del model, state
        gc.collect()
    assert replays == 12 and len(predictions) == 12 and len(crops) == 24 and len(metrics) == 8
    labels = ["V72 EMA2k", "V72 current2k", "V73 EMA2k", "V73 current2k"]
    boards = [
        board(output, crops, labels, cases, name)
        for cases, name in (
            (["photo-0", "photo-1"], "photos-current-EMA-native.png"),
            (
                ["overcast-sky", "building-detail", "foliage", "chain-link-fence"],
                "GFX-current-EMA-native.png",
            ),
        )
    ]
    check_guards(plan)
    assert not torch.cuda.is_initialized()
    save(
        output / "result.json",
        {
            "status": "completed-selected-current-versus-EMA-CPU-diagnostic-awaiting-native-view",
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "plan": ref(plan_path),
            "driver": ref(__file__),
            "state_witnesses": state_witnesses,
            "exact_existing_EMA_F32_replays": replays,
            "photo_metrics": metrics,
            "current_predictions": predictions,
            "native_crops": crops,
            "native_boards": boards,
            "CUDA_initialized": False,
            "scope": plan["protocol"],
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", type=Path)
    mode.add_argument("--run", type=Path)
    options = parser.parse_args()
    if options.prepare:
        prepare(options.prepare)
    else:
        run(options.run)
