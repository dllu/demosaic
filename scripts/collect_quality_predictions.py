"""Evaluate frozen endpoints once, retaining native predictions and exact targets."""

import argparse
import gc
import json
import os
import random
import shutil
import sys
from pathlib import Path

import numpy as np
import psutil
import torch
from frozen_backbone_identity import verify_backbone_identity
from profile_raw_kernel_inference import model_hash
from train_directional_bank_trial import guard, read, ref, save

from demosaic import real_suite, suite
from demosaic.checkpoint_cache import freeze_checkpoint
from demosaic.prediction_archive import PredictionArchive, fingerprint


def strict_float32():
    torch.set_float32_matmul_precision("highest")
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False


def verify_recorded_backbone(model, checkpoint):
    identity = checkpoint["expected_backbone"]
    return verify_backbone_identity(model.config.to_dict(), model_hash(model.context.backbone), checkpoint,
                                    legacy_sha256=identity["sha256"])


def validate_checkpoint_declarations(checkpoints):
    """Reject invalid or duplicate endpoints before starting neural work."""
    expected = [record["sha256"] for record in checkpoints]
    if (not expected or any(not isinstance(value, str) or len(value) != 64
                           or any(c not in "0123456789abcdef" for c in value)
                           for value in expected) or len(set(expected)) != len(expected)):
        raise ValueError("Declare distinct nonempty endpoint checkpoints")
    return expected


def verify_model_coverage(checkpoints, records, alignment=None):
    """Allow an incremental candidate while requiring every declared endpoint."""
    expected = validate_checkpoint_declarations(checkpoints)
    actual = [record["checkpoint"]["sha256"] for record in records]
    if len(actual) != len(expected) or set(actual) != set(expected):
        raise ValueError("Collected endpoint coverage differs from the declared checkpoints")
    if alignment is not None and alignment["models"] != len(expected):
        raise ValueError("Archive model count differs from the declared checkpoints")
    return len(expected)


def verify_forward_witness(witness, index, actual):
    """Check all five input arguments before any neural work for this batch."""
    if witness is None:
        return
    if not 0 <= index < len(witness):
        raise ValueError("Input witness does not cover the next forward")
    previous = witness[index]
    if {key: value["sha256"] for key, value in actual.items()} != previous["argument_fingerprints"]:
        raise ValueError(f"Input witness differs before forward {index}")
    if "argument_metadata" in previous:
        metadata = {key: {field: value[field] for field in ("shape", "dtype")}
                    for key, value in actual.items()}
        if metadata != previous["argument_metadata"]:
            raise ValueError(f"Input witness shape/dtype differs before forward {index}")


def verify_restoration_state(model, state, checkpoint):
    """Verify the declared restoration state before registering any forward hooks."""
    expected = checkpoint.get("EMA_tensors", 91)
    if type(expected) is not int or expected < 1:
        raise ValueError("Declare a positive integer restoration tensor count")
    actual = model.restoration_state_dict()
    if len(actual) != expected or len(state["ema"]) != expected or actual.keys() != state["ema"].keys():
        raise ValueError(f"Restoration state differs from declared {expected}-tensor EMA")
    if not all(torch.equal(value.cpu(), state["ema"][key]) for key, value in actual.items()):
        raise ValueError("Restoration state differs from the exact checkpoint EMA")
    return expected


@torch.inference_mode()
def collect(plan_path, stage):
    plan = read(plan_path)
    guard(plan)
    validate_checkpoint_declarations(plan["checkpoints"])
    assert ref(__file__) == plan["collector_source"]
    assert Path(suite.__file__).resolve().is_relative_to(Path(plan["work"]))
    specification = plan["stages"][stage]
    root, output = Path(plan["root"]), Path(specification["output"])
    (root / f"{stage}.claim").open("x").close()
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "0"
    assert psutil.virtual_memory().available >= 48*2**30
    assert shutil.disk_usage("/mnt/external").free >= plan["runtime_external_reserve_GiB"]*2**30
    output.mkdir(exist_ok=False)
    torch.set_num_threads(4)
    torch.cuda.set_per_process_memory_fraction(min(1, 24*2**30/torch.cuda.get_device_properties(0).total_memory))
    torch.backends.cudnn.benchmark = True
    strict_float32()
    archive = PredictionArchive(output / "archive") if stage in {"photo", "known", "unseen", "texture", "color"} else None
    witness = [json.loads(line) for line in Path(specification["input_witness"]["path"]).read_text().splitlines()] if "input_witness" in specification else None
    if witness is not None and len(witness) != specification["calls_per_model"]:
        raise ValueError("Input witness length differs from the declared forward budget")
    if "noise_profile" in specification and ref(specification["noise_profile"]["path"]) != specification["noise_profile"]:
        raise ValueError("Fixed noise profile binding differs from the stage declaration")
    models, full_native = [], []

    def input_fingerprints(args):
        return {k: fingerprint(v) for k, v in zip(["packed", "variance", "colors", "wb", "matrix"], args, strict=True)}

    def verify_witness(record, context, batch):
        if witness is None:
            return
        old = witness[record["calls"]-1]
        assert {k: v["sha256"] for k, v in record["latest_inputs"].items()} == old["argument_fingerprints"]
        if stage == "photo":
            previous = old["observation"]
            assert context["ids"] == previous["ids"] and context["condition"] == previous["condition"] and context["pattern"] == previous["pattern"]
            assert fingerprint(batch["target"])["sha256"] == previous["input_fingerprints"]["target"]

    def retain(record, context, prediction, batch, *, prediction_file=None):
        assert archive is not None
        verify_witness(record, context, batch)
        targets = {k: batch[k] for k in ["wb", "matrix"]}
        for name in ["target", "reference_rgb", "sensor_reference", "sensor_mask"]:
            if name in batch:
                targets[name] = batch[name]
        if stage == "color" or (stage == "photo" and set(context["ids"]) & set(plan["material_photo_ids"])):
            targets.update(packed=batch["packed"], colors=batch["colors"])
        archive.append({"label": record["checkpoint"]["arm"], "sha256": record["checkpoint"]["sha256"], "step": 20000, "self_ensemble": "none"},
                       {**context, "stage": stage, "input_fingerprints": record["latest_inputs"]}, prediction, targets,
                       prediction_file=prediction_file)

    def callback(label, context, prediction, batch):
        index = int(label.split(":", 1)[0])
        record = models[index]
        assert record["last_output_id"] == id(prediction)
        retain(record, context, prediction, batch)

    def observe_loader(loader):
        def loaded(*args, **kwargs):
            py_rng = random.getstate()
            with torch.random.fork_rng(devices=[0]):
                model, state = loader(*args, **kwargs)
            random.setstate(py_rng)
            strict_float32()
            checkpoint = next(c for c in plan["checkpoints"] if c["sha256"] == state["loaded_sha256"])
            assert state["step"] == 20000 and state["config"]["initialized_from"] == checkpoint["expected_lineage"]["initialized_from"]
            verify_restoration_state(model, state, checkpoint)
            verify_recorded_backbone(model, checkpoint)
            record = {"model": model, "checkpoint": checkpoint, "before": model_hash(model),
                      "calls": 0, "observations": 0, "encoder_calls": 0, "input_sequence": [], "output_hashes": []}
            models.append(record)

            def before(module, arguments):
                assert not module.training and len(arguments) == 5
                assert not torch.backends.cuda.matmul.allow_tf32 and not torch.backends.cudnn.allow_tf32
                assert psutil.virtual_memory().available >= 32*2**30
                assert shutil.disk_usage("/mnt/external").free >= plan["runtime_external_reserve_GiB"]*2**30
                record["latest_inputs"] = input_fingerprints(arguments)
                verify_forward_witness(witness, record["calls"], record["latest_inputs"])

            def after(module, arguments, prediction):
                assert prediction.dtype == torch.float32 and torch.isfinite(prediction).all()
                assert input_fingerprints(arguments) == record["latest_inputs"]
                record["last_output_id"] = id(prediction)
                record["calls"] += 1
                record["observations"] += len(prediction)
                record["input_sequence"].append(record["latest_inputs"])
                record["output_hashes"].append(fingerprint(prediction))
                if record["calls"] % 32 == 0:
                    print({"stage": stage, "model": checkpoint["arm"], "batches": record["calls"]}, flush=True)

            def encoder(*_args):
                record["encoder_calls"] += 1

            record["handles"] = [model.register_forward_pre_hook(before), model.register_forward_hook(after),
                                 model.context.backbone.register_forward_pre_hook(encoder)]
            return model, state
        return loaded

    def shared_checkpoint(source, destination):
        return freeze_checkpoint(source, destination, cache_dir=plan["shared_checkpoint_cache"])

    checkpoints = [Path(c["path"]) for c in plan["checkpoints"]]
    report_dir = output / "report"
    if stage == "photo":
        suite.load_checkpoint = observe_loader(suite.load_checkpoint)
        suite.freeze_checkpoint = shared_checkpoint
        suite.run_suite(checkpoints, specification["manifest"]["path"], report_dir, specification["protocol"]["path"],
                        device="cuda", precision="float32", patch_size=256, batch_size=4, limit=427,
                        synthetic_count=16, prediction_callback=callback)
        report = report_dir / "summary.json"
    elif stage in {"known", "unseen"}:
        real_suite.load_checkpoint = observe_loader(real_suite.load_checkpoint)
        real_suite.freeze_checkpoint = shared_checkpoint
        real_suite.evaluate_pairs(checkpoints, specification["manifest"]["path"], report_dir,
                                  device="cuda", precision="float32", batch_size=4, prediction_callback=callback)
        report = report_dir / "summary.json"
    elif stage == "texture":
        import evaluate_texture_candidates as texture
        texture.load_checkpoint = observe_loader(texture.load_checkpoint)
        texture.main(checkpoints, report_dir, device="cuda", precision="float32", prediction_callback=callback)
        report = report_dir / "summary.json"
    elif stage == "color":
        import evaluate_color_grid_cuda as color
        color.load_checkpoint = observe_loader(color.load_checkpoint)
        def color_callback(model_index, definition, prediction, batch, path):
            record = models[model_index]
            assert fingerprint(prediction) == record["output_hashes"][-1]
            retain(record, {"ids": [definition["id"]], "definition": definition,
                            "case_index": record["calls"]-1}, prediction, batch, prediction_file=path)
        color.evaluate_records(Path(plan["color_inputs"]["path"]), Path(plan_path), report_dir,
                               [{**c, "kind": "joint-checkpoint"} for c in plan["checkpoints"]],
                               plan["checkpoints"][0]["sha256"], expected_step=20000, precision="float32",
                               prediction_callback=color_callback)
        report = report_dir / "report.json"
    else:
        import report_raw_pair as gfx
        gfx.load_checkpoint = observe_loader(gfx.load_checkpoint)
        gfx.freeze_checkpoint = shared_checkpoint
        if stage == "full-gfx":
            original_restore = gfx.restore_tiled
            def retain_full(model, *args, **kwargs):
                value, statistics = original_restore(model, *args, **kwargs)
                record = next(r for r in models if r["model"] is model)
                selection = read(specification["selection"]["path"])
                for region in selection["regions"]:
                    x, y = region["noisy_xy"]
                    path = output / f"{record['checkpoint']['arm']}-{region['name']}-RGB-f32.npy"
                    np.save(path, value[None, :, y:y+160, x:x+160].numpy(), allow_pickle=False)
                    full_native.append({"checkpoint": record["checkpoint"], "region": region, "array": ref(path), "timing": statistics})
                return value, statistics
            gfx.restore_tiled = retain_full
        sys.argv = [str(gfx.__file__), specification["selection"]["path"], *map(str, checkpoints),
                    "--output", str(report_dir), "--device", "cuda", "--precision", "float32"]
        if stage == "full-gfx":
            sys.argv.append("--full-frame")
        if "noise_profile" in specification:
            sys.argv += ["--noise-profile", specification["noise_profile"]["path"]]
        gfx.main()
        report = report_dir / "report.json"
    verify_model_coverage(plan["checkpoints"], models)
    invariants = []
    for record in models:
        assert record["calls"] == record["encoder_calls"] == specification["calls_per_model"]
        assert record["observations"] == specification["observations_per_model"]
        assert model_hash(record["model"]) == record["before"]
        assert record["input_sequence"] == models[0]["input_sequence"]
        for handle in record["handles"]:
            handle.remove()
        invariants.append({k: v for k, v in record.items() if k in ["checkpoint", "before", "calls", "observations", "encoder_calls", "input_sequence", "output_hashes"]})
    alignment = archive.verify_alignment() if archive is not None else None
    if archive is not None:
        verify_model_coverage(plan["checkpoints"], models, alignment)
        assert alignment["observations_per_model"] == specification["calls_per_model"]
    guard(plan)
    save(output / "result.json", {"stage": stage, "plan": ref(plan_path), "source": ref(__file__), "report": ref(report),
                                  "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()}, "invariants": invariants,
                                  "archive": ref(archive.manifest) if archive is not None else None,
                                  "alignment": alignment, "full_native_floats": full_native,
                                  "reference_neural_forwards": 0, "optimizer_updates": 0,
                                  "RAW_decodes": 2 if stage in {"gfx", "gfx-highlights", "full-gfx"} else 0,
                                  "scope": "Declared new final20000 endpoints only; single-view FP32. Complete predictions/targets retained on numerical panels. Existing controls reused separately. Full GFX native floats kept before RGB16 encoding."})
    models.clear()
    gc.collect()
    torch.cuda.empty_cache()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("stage", choices=["photo", "known", "unseen", "texture", "color", "gfx", "gfx-highlights", "full-gfx"])
    options = parser.parse_args()
    collect(options.plan, options.stage)
