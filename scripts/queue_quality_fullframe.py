"""Queue complete GFX RGB16 exports after the matched quality evaluation."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import psutil
from evaluate_v43_quality_trial import monitor_child
from recover_v43_quality_trial import headroom, resource_snapshot, stop_owned_child
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import live

REPO = Path(__file__).resolve().parents[1]
COMPLETE = "completed-quality-recipe-evaluation-awaiting-image-review"


def evaluation_ready(state, plan_ref, owner, *, is_live=live):
    assert state["plan"] == plan_ref and state["controller"] == owner, (
        "Evaluation owner/plan changed"
    )
    assert not state["status"].startswith("failed"), state.get("error", state["status"])
    if state["status"] != COMPLETE:
        assert is_live(owner), "Evaluation controller exited before completion"
        return False
    return not is_live(owner)


def prepare(queue_root, root, artifact_root, *, cpu_smoke=False):
    queue_root, root, artifact_root = queue_root.resolve(), root.resolve(), artifact_root.resolve()
    assert root.is_relative_to(REPO / ".cache") and not root.exists()
    assert artifact_root.is_relative_to(Path("/mnt/external/demosaic"))
    assert not artifact_root.exists() and os.path.ismount("/mnt/external")
    queue, launch = read(queue_root / "plan.json"), read(queue_root / "launch.json")
    guard(queue)
    assert not queue["cpu_smoke"] and launch["plan"] == ref(queue_root / "plan.json")
    if not cpu_smoke:
        evaluation_ready(read(queue_root / "status.json"), launch["plan"], launch["controller"])
    root.mkdir(parents=True, exist_ok=False)
    worker_file = root / "worker.py"
    shutil.copyfile(__file__, worker_file)
    selection = read(queue["gfx"]["gfx"])
    highlights = read(queue["gfx"]["gfx-highlights"])
    assert all(selection[k] == highlights[k] for k in ("noisy", "reference", "display_exposure"))
    selection["regions"] += highlights["regions"]
    assert len({r["name"] for r in selection["regions"]}) == 6
    window = None
    if cpu_smoke:
        region = next(r for r in selection["regions"] if r["name"] == "foliage")
        x, y = region["noisy_xy"]
        window = [x - 176, y - 176, 512, 512]
        assert region["noisy_xy"] == region["reference_xy"]
        selection["regions"] = [{**region, "noisy_xy": [176, 176], "reference_xy": [176, 176]}]
        selection["notes"] = (
            "Discarded CPU512 export smoke cropped from the cached GFX foliage context; not a complete101.996MP restoration or quality result."
        )
    path = root / "selection.json"
    save(path, selection)
    plan = {
        "root": str(root),
        "work": queue["work"],
        "worker": str(worker_file),
        "artifact_root": str(artifact_root),
        "evaluation_queue_root": str(queue_root),
        "evaluation_queue_plan": launch["plan"],
        "evaluation_queue_owner": launch["controller"],
        "training_root": queue["training_root"],
        "cpu_smoke": cpu_smoke,
        "smoke_window_xywh": window,
        "selection": str(path),
        "python": queue["python"],
        "cache_environment": queue["cache_environment"],
        "rawnind": queue["rawnind"],
        "disk_reserves": queue["disk_reserves"],
        "external_device": queue["external_device"],
        "stable_seconds": 2 if cpu_smoke else 15,
        "wait_seconds": 7200,
        "dependency_wait_seconds": 172800,
        "stage_timeout_seconds": 1200 if cpu_smoke else 43200,
        "inputs": [launch["plan"], ref(queue_root / "launch.json")],
        "frozen_files": {str(p): ref(p)["sha256"] for p in (worker_file, path)},
        "scope": f"Cropped CPU512/one-tile export integration, {queue.get('parent_label', 'V84')} and RawNIND; no production/full-camera quality or timing claim."
        if cpu_smoke
        else f"Complete101.996MP GFX RGB16 exports for {queue.get('parent_label', 'V84')} and fixed {', '.join(queue.get('training_arms', ('V100', 'V101')))} final EMAs, plus RawNIND:CFA-channel. IEEE FP32, tile512/overlap64/B4, cached3879/3880, original four regions plus two fixed highlight regions. Shared+2EV and independent ISO100 reference, never exact GT. No speed optimization or automatic promotion; update actual native comparisons after viewing.",
    }
    save(root / "plan.json", plan)
    return root / "plan.json"


def inspect_export(path, expected, *, color_space, flip):
    import numpy as np
    import tifffile

    from demosaic.io import orient

    expected = orient(expected, flip)
    with tifffile.TiffFile(path) as handle:
        assert len(handle.pages) == 1
        page = handle.pages[0]
        assert page.dtype == np.uint16 and page.bitspersample == 16
        assert page.shape == expected.shape and page.photometric.name == "RGB"
        metadata = json.loads(page.description)
        assert metadata["color_space"] == color_space and metadata["bits_per_sample"] == 16
        if color_space == "sRGB":
            assert page.tags.get(34675) is not None, "sRGB ICC tag missing"
    pixels = tifffile.memmap(path, mode="r")
    indices = np.unique(np.linspace(0, len(expected) - 1, min(33, len(expected)), dtype=int))
    reference = np.clip(expected[indices].astype(np.float64), 0, 1) * 65535
    error = np.abs(pixels[indices].astype(np.float64) - reference)
    maximum = float(error.max())
    # FP32 scaling before round-to-even can add at most ~.004DN to half a DN.
    assert maximum <= 0.504, "Sampled RGB16 values differ from the supplied float image"
    return {
        "image": ref(path),
        "shape": list(pixels.shape),
        "dtype": "uint16",
        "color_space": color_space,
        "sampled_RGB_values": int(error.size),
        "sampled_maximum_quantization_error_DN16": maximum,
        "scope": "TIFF shape/type/tags and 33 decoded full-width rows versus supplied float pixels; not a whole-image precision comparison.",
    }


def worker(path):
    import numpy as np
    import report_raw_pair as gfx
    import torch
    from PIL import Image
    from profile_raw_kernel_inference import model_hash
    from queue_quality_recipe_evaluation import DINO_SHA, checkpoints, training_ready

    plan = read(path)
    guard(plan)
    queue = read(plan["evaluation_queue_plan"]["path"])
    guard(queue)
    training = read(Path(plan["training_root"]) / "plan.json")
    guard(training)
    state = read(Path(plan["training_root"]) / "status.json")
    if plan["cpu_smoke"]:
        records = [
            {
                "arm": queue.get("parent_label", "V84"),
                **training["parent"],
                "expected_lineage": {"step": training.get("parent_step", 20000)},
            }
        ]
    else:
        assert training_ready(
            state,
            queue["training_plan"],
            queue["training_controller"],
            arms=queue.get("training_arms", ("V100", "V101")),
        )
        records, _ = checkpoints(
            state,
            training,
            cpu_smoke=False,
            parent_label=queue.get("parent_label", "V84"),
        )
        torch.cuda.set_per_process_memory_fraction(
            24 * 2**30 / torch.cuda.get_device_properties(0).total_memory
        )
    device = "cpu" if plan["cpu_smoke"] else "cuda"
    torch.set_num_threads(2 if plan["cpu_smoke"] else 4)
    before, exports, overviews = [], [], []
    original_loader, original_writer = gfx.load_checkpoint, gfx.write_rgb16

    def loaded(*args, **kwargs):
        model, checkpoint = original_loader(*args, **kwargs)
        record = next(r for r in records if r["sha256"] == checkpoint["loaded_sha256"])
        assert checkpoint["step"] == record["expected_lineage"]["step"]
        if "initialized_from" in record["expected_lineage"]:
            assert (
                checkpoint["config"]["initialized_from"]
                == record["expected_lineage"]["initialized_from"]
            )
        assert model_hash(model.context.backbone) == DINO_SHA
        before.append((model, model_hash(model)))
        return model, checkpoint

    def written(target, rgb, **kwargs):
        original_writer(target, rgb, **kwargs)
        color_space = kwargs.get("color_space", "linear-camera-RGB")
        exports.append(
            inspect_export(target, rgb, color_space=color_space, flip=kwargs.get("flip", 0))
        )
        if color_space == "sRGB":
            import tifffile

            pixels = tifffile.memmap(target, mode="r")
            overview = Image.fromarray((pixels >> 8).astype(np.uint8))
            overview.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
            output = Path(target).with_suffix(".overview.png")
            overview.save(output)
            overviews.append(
                {
                    "image": ref(output),
                    "size": list(overview.size),
                    "scope": "Resized RGB16 sRGB overview only; native crop pixels remain unchanged.",
                }
            )

    if plan["cpu_smoke"]:
        read_raw, read_reference = gfx.read_raw, gfx.read_reference
        x, y, w, h = plan["smoke_window_xywh"]

        def cropped_raw(source):
            raw, metadata = read_raw(source)
            return raw[y : y + h, x : x + w].copy(), metadata

        def cropped_reference(source):
            raw, rgb, metadata, calibration = read_reference(source)
            return (
                raw[y : y + h, x : x + w].copy(),
                rgb[y : y + h, x : x + w].copy(),
                metadata,
                calibration,
            )

        gfx.read_raw, gfx.read_reference = cropped_raw, cropped_reference
    gfx.load_checkpoint, gfx.write_rgb16 = loaded, written
    sys.argv = [
        str(gfx.__file__),
        plan["selection"],
        *[r["path"] for r in records],
        "--output",
        plan["artifact_root"],
        "--rawnind",
        plan["rawnind"],
        "--rawnind-gain-modes",
        "cfa-channel",
        "--full-frame",
        "--device",
        device,
        "--precision",
        "float32",
    ]
    gfx.main()
    output = Path(plan["artifact_root"])
    report = read(output / "report.json")
    assert len(report["full_frames"]) == len(records) + 1
    assert len(exports) == 2 * (len(records) + 1)
    assert report["quality_scores"] is None and all(c["full_frame"] for c in report["native_crops"])
    expected_shape = (512, 512, 3) if plan["cpu_smoke"] else (8746, 11662, 3)
    assert all(tuple(e["shape"]) == expected_shape for e in exports)
    assert all(model_hash(model) == digest for model, digest in before)
    assert len(before) == len(records)
    if plan["cpu_smoke"]:
        assert not torch.cuda.is_initialized()
    guard(plan)
    guard(queue)
    save(
        Path(plan["root"]) / "result.json",
        {
            "status": "completed-GFX-exports-awaiting-native-and-overview-review",
            "plan": ref(path),
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "checkpoints": records,
            "report": ref(output / "report.json"),
            "exports": exports,
            "overviews": overviews,
            "restoration_weights_unchanged": True,
            "scope": plan["scope"],
        },
    )


def controller(path):
    plan = read(path)
    guard(plan)
    root = Path(plan["root"])
    (root / "controller.claim").open("x").close()
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    child = identity = None

    def record(status, **details):
        save(
            root / "status.json",
            {
                "plan": ref(path),
                "controller": owner,
                "status": status,
                "updated_unix": time.time(),
                **details,
            },
        )

    def observe():
        value = resource_snapshot(root)
        with (root / "resource-history.jsonl").open("a") as stream:
            stream.write(json.dumps(value) + "\n")
        return value

    try:
        record("waiting-for-quality-evaluation")
        started = time.monotonic()
        while not plan["cpu_smoke"]:
            state = read(Path(plan["evaluation_queue_root"]) / "status.json")
            if evaluation_ready(
                state, plan["evaluation_queue_plan"], plan["evaluation_queue_owner"]
            ):
                break
            assert time.monotonic() - started < plan["dependency_wait_seconds"]
            time.sleep(15)
        guard(read(plan["evaluation_queue_plan"]["path"]))
        started, stable = time.monotonic(), None
        while True:
            assert time.monotonic() - started < plan["wait_seconds"]
            enough = headroom(observe(), plan, 48)
            stable = (time.monotonic() if stable is None else stable) if enough else None
            if stable is not None and time.monotonic() - stable >= plan["stable_seconds"]:
                break
            time.sleep(2)
        work = Path(plan["work"])
        env = dict(
            os.environ,
            PYTHONPATH=f"{work / 'src'}:{work / 'scripts'}",
            CUDA_VISIBLE_DEVICES="" if plan["cpu_smoke"] else "0",
            HF_HUB_OFFLINE="1",
            TRANSFORMERS_OFFLINE="1",
            OPENBLAS_NUM_THREADS="1",
            CUBLAS_WORKSPACE_CONFIG=":4096:8",
        )
        env.update(plan["cache_environment"])
        with (root / "worker.log").open("xb") as log:
            child = subprocess.Popen(
                [plan["python"], "-P", plan["worker"], "worker", str(path)],
                cwd=work,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            identity = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
            record("running-GFX-fullframe-exports", child=identity)
            monitor_child(
                child,
                identity,
                plan=plan,
                observe=observe,
                record=record,
                deadline=time.monotonic() + plan["stage_timeout_seconds"],
            )
            assert child.wait() == 0, child.returncode
        result = read(root / "result.json")
        assert result["owner"] == identity and not live(identity)
        record(
            "completed-GFX-fullframe-exports-awaiting-image-review",
            result=ref(root / "result.json"),
        )
    except BaseException as error:
        if child is not None and child.poll() is None:
            stop_owned_child(child, identity)
        record("failed-GFX-fullframe-exports-preserved", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller", "worker"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--evaluation-queue", type=Path)
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--cpu-smoke", action="store_true")
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.evaluation_queue, args.path, args.artifacts, cpu_smoke=args.cpu_smoke))
    elif args.mode == "controller":
        controller(args.path.resolve())
    else:
        worker(args.path.resolve())
