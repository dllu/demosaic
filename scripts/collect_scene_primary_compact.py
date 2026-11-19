"""Replay the fixed photo and camera panels with compact IEEE FP32 CUDA receipts."""

import argparse
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import torch
from collect_local_primary import summarize_stages
from collect_scene_primary import ARGUMENTS, ContextFields, numbers
from profile_raw_kernel_inference import model_hash

from demosaic.color import render
from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.experiments.runtime import exclusive_run
from demosaic.inference import _stage_tiled_cuda
from demosaic.losses import psnr
from demosaic.models import load_model
from demosaic.precision import ieee_fp32
from demosaic.prediction_archive import fingerprint
from demosaic.real_suite import measured_sensor_psnr
from demosaic.scene_inference import load_scene_checkpoint

COUNTS = {"photo": 3108, "known": 24, "unseen": 30}


def prepare(root, historic_plan, matched, *, probe=False, continuation=None):
    template = read_json(historic_plan)
    combined = read_json(matched)
    assert combined["matched_input_traces"] and (probe or combined["training_complete"])
    step = combined["through_update"]
    models = {name: template["models"][name] for name in ("V120", "parent100k")}
    for mode in ("none", "spatial"):
        endpoint = combined["arms"][mode]
        models[mode] = {"kind": "scene", "checkpoint": endpoint["checkpoint"], "step": step}
    assert models["parent100k"]["checkpoint"] == read_json(checked(combined["plan"]))["parent"]
    secondary = []
    if continuation is not None:
        secondary.append(reference(continuation))
        extended = read_json(checked(secondary[0]))
        assert not extended["qualification"] and extended["DINO_unchanged"]
        assert extended["parent"] == models["none"]["checkpoint"]
        for name, checkpoint in extended["checkpoints"].items():
            models[name] = {
                "kind": "scene",
                "checkpoint": checkpoint,
                "step": extended["updates_per_arm"],
            }
    root.mkdir(parents=True)
    work, sources = freeze_sources(Path.cwd(), root, [Path(__file__).name])
    required_keys = (
        "canonical_inputs",
        "photo_inventory",
        "parent_CPU_probes",
        "preview_long_side",
        "preview_exposure",
        "stages",
        "DINO_sha256",
    )
    input_refs = [
        reference(historic_plan),
        reference(matched),
        combined["plan"],
        *(template[key] for key in ("canonical_inputs", "photo_inventory", "parent_CPU_probes")),
        *(values["checkpoint"] for values in models.values()),
        *(v["manifest"] for v in template["stages"].values() if "manifest" in v),
        *secondary,
    ]
    plan = {key: template[key] for key in required_keys}
    plan.update(
        root=str(root),
        inputs=input_refs,
        probe_only=probe,
        models=models,
        frozen_files=sources,
        driver=reference(work / "scripts" / Path(__file__).name),
        policy="CUDA channels-last IEEE FP32. Retain per-case PSNR, input fingerprints and CPU checks.",
    )
    write_json(root / "plan.json", plan)


def score(stage, prediction, batch):
    border = 8 if stage == "photo" else 32
    crop = (..., slice(border, -border), slice(border, -border))
    value = prediction[crop]
    clean = batch["target" if stage == "photo" else "reference_rgb"][crop]
    wb, matrix = batch["wb"], batch["matrix"]
    if stage == "photo":
        return {
            "linear_psnr": psnr(value.clamp(0, 1), clean.clamp(0, 1)),
            "srgb_psnr": psnr(render(value, wb, matrix), render(clean, wb, matrix)),
        }
    sensor, count = measured_sensor_psnr(
        value, batch["sensor_reference"][crop], batch["sensor_mask"][crop]
    )
    return {
        "sensor_psnr": sensor,
        "reference_samples": count,
        "ahd_srgb_psnr": psnr(render(value, wb, matrix), render(clean, wb, matrix)),
    }


def metric_rows_for(record, arm, measured):
    marks = record["context"]
    rows = []
    for index, identity in enumerate(marks["ids"]):
        row = {
            "model": arm,
            "id": identity,
            "pattern": marks["pattern"],
            "metrics": {key: values[index] for key, values in measured.items()},
        }
        if record["stage"] == "photo":
            row["kind"] = "synthetic" if identity.startswith("synthetic-") else "photo"
            row["condition"] = marks["condition"]["name"]
        else:
            row.update(scene=marks["scene"], pair=marks["raw_source"]["sha256"])
        rows.append(row)
    return rows


def load_models(plan):
    models = {}
    for name, spec in plan["models"].items():
        ref = spec["checkpoint"]
        path = checked(ref)
        if spec["kind"] == "parent":
            model, state = load_model("v120", checkpoint=path, expected_sha256=ref["sha256"])
            backbone = model.context.backbone
        else:
            model, state = load_scene_checkpoint(path, weights="ema", expected_sha256=ref["sha256"])
            backbone = model.base.context.backbone
        assert state["step"] == spec["step"] and model_hash(backbone) == plan["DINO_sha256"]
        models[name] = _stage_tiled_cuda(model.eval(), "cuda")
    return models


@torch.inference_mode()
def collect(plan_path, action):
    plan = read_json(plan_path)
    verify_plan(plan)
    assert checked(plan["driver"]) == Path(__file__)
    torch.set_num_threads(2)
    torch.backends.cudnn.benchmark = False
    root = Path(plan["root"])
    owner = root / action
    owner.mkdir(exist_ok=True)
    with exclusive_run(owner):
        replay(plan_path, plan, owner, action)


def replay(plan_path, plan, owner, action):
    root = owner.parent
    proof = reference(plan_path)
    canonical = read_json(checked(plan["canonical_inputs"]))
    assert canonical["all_input_witnesses_exact"]
    assert Counter(row["stage"] for row in canonical["records"]) == COUNTS
    archived = read_json(checked(plan["parent_CPU_probes"]))
    probes = {(row["stage"], row["batch"]): row for row in archived["records"]}
    if action == "full":
        if plan["probe_only"]:
            raise ValueError("An intermediate-checkpoint probe is limited to preflight")
        qualification = reference(root / "preflight" / "result.json")
        initial = read_json(checked(qualification))
        assert initial["plan"] == proof and initial["scope"] == "preflight"
        assert len(initial["V120_CPU_comparisons"]) == len(probes)
    else:
        qualification = None
    selected = [
        row
        for stage in ("known", "unseen", "photo")
        for row in canonical["records"]
        if row["stage"] == stage and (action == "full" or (stage, row["batch"]) in probes)
    ]
    models = load_models(plan)
    fields = ContextFields(plan, owner / "contexts", models["spatial"], [], save_arrays=False)
    sections, comparisons, cases = defaultdict(list), [], []
    began = time.monotonic()
    elapsed = defaultdict(float)
    with ieee_fp32():
        for index, record in enumerate(selected, start=1):
            stage, number = record["stage"], record["batch"]
            destination = owner / f"{stage}-{number:05d}.json"
            if destination.is_file():
                item = read_json(destination)
                assert item["plan"] == proof and item["arrays"] == record["arrays"]
            else:
                with np.load(checked(record["arrays"]), allow_pickle=False) as archive:
                    batch = {k: torch.from_numpy(archive[k]) for k in archive.files}
                for key in ARGUMENTS:
                    assert fingerprint(batch[key]) == record["fingerprints"][key]
                scenes, boxes, context = fields.queries(record, batch)
                device_batch = {k: v.cuda() for k, v in batch.items()}
                for key in ("packed", "variance"):
                    device_batch[key] = device_batch[key].contiguous(
                        memory_format=torch.channels_last
                    )
                noise = record["context"]["condition" if stage == "photo" else "noise"]
                variants, cpu_check = {}, None
                for name, model in models.items():
                    model_base = model if plan["models"][name]["kind"] == "parent" else model.base
                    model_base.set_noise(noise["shot"], noise["read"])
                    torch.cuda.synchronize()
                    mark = time.monotonic()
                    arguments = [device_batch[key] for key in ARGUMENTS]
                    value = (
                        model(*arguments, scene=scenes, boxes_xywh=boxes)
                        if name == "spatial"
                        else model(*arguments)
                    )
                    torch.cuda.synchronize()
                    seconds = time.monotonic() - mark
                    assert value.dtype == torch.float32 and torch.isfinite(value).all()
                    metrics = numbers(score(stage, value, device_batch))
                    pixels = value.cpu()
                    variants[name] = {
                        "rows": metric_rows_for(record, name, metrics),
                        "output_fingerprint": fingerprint(pixels),
                        "forward_seconds": seconds,
                    }
                    if name == "V120" and (stage, number) in probes:
                        original = probes[(stage, number)]
                        assert record["arrays"] == original["canonical_arrays"]
                        prior = torch.from_numpy(
                            np.load(checked(original["CPU_prediction"]), allow_pickle=False)
                        )
                        error = (pixels - prior).double() * 65535
                        old_scores = numbers(score(stage, prior.cuda(), device_batch))
                        field = "srgb_psnr" if stage == "photo" else "sensor_psnr"
                        delta = [
                            a - b
                            for a, b in zip(metrics[field], old_scores[field], strict=True)
                            if a is not None and b is not None
                        ]
                        cpu_check = {
                            "stage": stage,
                            "batch": number,
                            "reference": original["CPU_prediction"],
                            "maximum_DN16": float(error.abs().max()),
                            "RMS_DN16": float(error.square().mean().sqrt()),
                            "score": field,
                            "delta_dB": delta,
                        }
                item = {
                    "plan": proof,
                    "stage": stage,
                    "batch": number,
                    "arrays": record["arrays"],
                    "boxes": boxes,
                    "context": context,
                    "variants": variants,
                    "V120_CPU_check": cpu_check,
                }
                write_json(destination, item)
            cases.append(reference(destination))
            for name, data in item["variants"].items():
                sections[stage].extend(data["rows"])
                elapsed[name] += data["forward_seconds"]
            if item["V120_CPU_check"] is not None:
                comparisons.append(item["V120_CPU_check"])
            if index % 20 == 0 or index == len(selected):
                print(
                    index,
                    len(selected),
                    stage,
                    number,
                    round(time.monotonic() - began, 2),
                    flush=True,
                )
    write_json(
        owner / "result.json",
        {
            "plan": proof,
            "canonical_inputs": plan["canonical_inputs"],
            "models": plan["models"],
            "policy": plan["policy"],
            "scope": action,
            "complete": True,
            "qualification": qualification,
            "counts": dict(Counter(row["stage"] for row in selected)),
            "cases": cases,
            "summaries": summarize_stages(sections),
            "V120_CPU_comparisons": comparisons,
            "forward_seconds": dict(elapsed),
            "session_seconds": time.monotonic() - began,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_subparsers(dest="action", required=True)
    setup = action.add_parser("prepare")
    for name in ("root", "historic_plan", "matched"):
        setup.add_argument(name, type=Path)
    setup.add_argument("--probe", action="store_true")
    setup.add_argument("--continuation", type=Path)
    for label in ("preflight", "full"):
        action.add_parser(label).add_argument("plan", type=Path)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(
            args.root.absolute(),
            args.historic_plan,
            args.matched,
            probe=args.probe,
            continuation=args.continuation,
        )
    else:
        collect(args.plan, args.action)
