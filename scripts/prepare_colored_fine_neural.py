"""Prepare fresh coloured-wire observations and genuine frozen V120 parent/A-only fields."""

import argparse
import os
import shutil
import sys
import time
import traceback
from pathlib import Path

import numpy as np
from colored_fine_wire_data import PATTERNS, PRIORS, observe, render

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)

REPO = next(p for p in Path(__file__).resolve().parents if (p / "PROMPT.md").exists())


def prepare(root):
    source = REPO / ".cache/experiments/neural-nuisance-joint-fine129-pilot-v1/plan.json"
    base = read_json(source)
    root.mkdir(parents=True, exist_ok=False)
    inputs = root / "inputs"
    inputs.mkdir()
    groups = []
    rows = []
    for source_index in [0, 1]:
        target, recipe = render(source_index)
        for pattern in PATTERNS:
            for prior, noise in PRIORS.items():
                physical, identities = observe(
                    target["target"], pattern, prior, source=source_index
                )
                group = f"{prior}-source{source_index}-{pattern}"
                path = inputs / (group + ".npz")
                with path.open("xb") as stream:
                    np.savez_compressed(stream, **target, **physical)
                binding = reference(path)
                cases = []
                for role in range(3):
                    case = group + f"-role{role}"
                    cases.append(case)
                    rows.append(
                        {
                            "id": case,
                            "group": group,
                            "kind": "coloured-finite-wire",
                            "arrays": binding,
                            "sample": role,
                            "noise": {"name": prior + "-prior", **noise},
                            "source": source_index,
                            "pattern": pattern,
                            "repeat": 0,
                            "ROI_xywh": [176, 176, 160, 160],
                            "display_exposure": 16.0,
                            "reference_role": "Exact freshly constructed coloured finite-wire sensor RGB GT",
                        }
                    )
                groups.append(
                    {
                        "id": group,
                        "profile": prior,
                        "source": source_index,
                        "pattern": pattern,
                        "cases": cases,
                        "arrays": binding,
                        "recipe": recipe,
                        "noise": noise,
                        "identities": identities,
                        "noise_coupling": "none: independent source/CFA/prior/role keys",
                    }
                )
    work, files = freeze_sources(
        REPO,
        root,
        entries=(
            "prepare_colored_fine_neural.py",
            "pilot_neural_nuisance.py",
            "audit_neural_nuisance_inputs.py",
            "profile_raw_kernel_inference.py",
        ),
    )
    plan = {
        "root": str(root),
        "work": str(work),
        "python": sys.executable,
        "script": reference(work / "scripts/prepare_colored_fine_neural.py"),
        "groups": groups,
        "rows": rows,
        "background_configuration": base["background_configuration"],
        "checkpoint": base["background_configuration"]["checkpoint"],
        "backbone_sha256": base["background_configuration"]["backbone_sha256"],
        "inputs": [
            reference(source),
            base["background_configuration"]["checkpoint"],
            *[g["arrays"] for g in groups],
        ],
        "frozen_files": files,
        "minimum_start_RAM_GiB": 48,
        "minimum_runtime_RAM_GiB": 32,
        "minimum_disk_GiB": 96,
        "maximum_stage_seconds": 7200,
        "expected_full_parent_forwards": 48,
        "expected_masked_forwards": 96,
        "expected_total_root_and_encoder_forwards": 144,
        "scope": "Fresh adaptive development benchmark, two new procedural multiscale geometries (neutral and coloured) x4CFAs x2 declared priors x3 independent-noise roles=48 observations. Two dominant broad nuisance carriers plus finite subpixel fine wires,8x8 area integration, no optical blur. Source1 weak direction has negative green contrast. Fixed fictional WB/matrix, no photos or protected media/training admission. V120 full-input parent and96 genuine A-only fields, same91 tensors and DINO. No GT/reference arrays in neural inference. Future broad/fine-phase/fine-H1/joint-support comparison must close all corrections before scoring; no new learned weights, camera generalization or calibrated confidence claim.",
    }
    write_json(root / "plan.json", plan)
    verify_plan(plan)
    print(reference(root / "plan.json"), flush=True)


def neural(root):
    import psutil
    import torch
    from pilot_neural_nuisance import background_arguments, input_arrays, raw_frame
    from profile_raw_kernel_inference import model_hash

    from demosaic.experiments.evaluation.withheld import stratified_split
    from demosaic.experiments.runtime import owner_identity
    from demosaic.models import load_model
    from demosaic.prediction_archive import fingerprint

    plan = read_json(root / "plan.json")
    verify_plan(plan)
    assert reference(__file__) == plan["script"]
    assert len(plan["rows"]) == 48 and len(plan["groups"]) == 16
    (root / "neural.claim").open("x").close()
    write_json(root / "neural-owner.json", owner_identity())
    assert psutil.virtual_memory().available >= plan["minimum_start_RAM_GiB"] * 2**30
    assert shutil.disk_usage(root).free >= plan["minimum_disk_GiB"] * 2**30
    os.nice(10)
    os.sched_setaffinity(0, [12, 13])
    torch.set_num_threads(2)
    torch.set_float32_matmul_precision("highest")
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = True
    torch.cuda.set_per_process_memory_fraction(
        min(1, 24 * 2**30 / torch.cuda.get_device_properties(0).total_memory)
    )
    model, state = load_model("v120", checkpoint=checked(plan["checkpoint"]), device="cuda")
    model.eval().to(memory_format=torch.channels_last)
    selected = state["ema"] if "ema" in state else state["model"]
    assert len(model.restoration_state_dict()) == 91 and set(selected) == set(
        model.restoration_state_dict()
    )
    for key, value in model.restoration_state_dict().items():
        assert torch.equal(value.detach().cpu(), selected[key].cpu())
    assert model_hash(model.context.backbone) == plan["backbone_sha256"]
    counts = {"parent": 0, "masked": 0, "encoder": 0}
    mode = {"value": "parent"}

    def root_hook(*_):
        counts[mode["value"]] += 1

    def encoder_hook(*_):
        counts["encoder"] += 1

    model.register_forward_pre_hook(root_hook)
    model.context.backbone.register_forward_pre_hook(encoder_hook)
    output = root / "neural"
    output.mkdir()
    parents = root / "parents"
    parents.mkdir()
    records = []
    parent_groups = []
    started = time.monotonic()
    for group in plan["groups"]:
        group_records = []
        parent_values = []
        for case in group["cases"]:
            assert psutil.virtual_memory().available >= plan["minimum_runtime_RAM_GiB"] * 2**30
            assert shutil.disk_usage(root).free >= plan["minimum_disk_GiB"] * 2**30
            if time.monotonic() - started > plan["maximum_stage_seconds"]:
                raise TimeoutError("Fresh neural stage deadline")
            row = next(r for r in plan["rows"] if r["id"] == case)
            data = input_arrays(row)
            raw = raw_frame(data)
            mask = stratified_split(
                raw.shape, plan["background_configuration"]["global_split_seed"]
            )
            mask_path = output / (case + "-A-mask.npy")
            with mask_path.open("xb") as stream:
                np.save(stream, mask, allow_pickle=False)
            full = {
                "packed": data["packed"][None],
                "variance": (data["packed"].clip(0) * row["noise"]["shot"] + row["noise"]["read"])[
                    None
                ],
                "colors": data["colors"][None],
                "wb": data["wb"],
                "matrix": data["matrix"],
            }
            arguments = [
                full,
                *[background_arguments(raw, m, data, row["noise"]) for m in [mask, ~mask]],
            ]
            fields = []
            fingerprints = []
            full_fingerprint = None
            with torch.inference_mode():
                for index, args in enumerate(arguments):
                    mode["value"] = "parent" if index == 0 else "masked"
                    physical = {k: fingerprint(v) for k, v in args.items()}
                    tensors = {k: torch.from_numpy(v.copy()).cuda() for k, v in args.items()}
                    assert {k: fingerprint(v) for k, v in tensors.items()} == physical
                    model.set_noise(row["noise"]["shot"], row["noise"]["read"])
                    value = (
                        model(
                            *(tensors[k] for k in ["packed", "variance", "colors", "wb", "matrix"])
                        )
                        .cpu()
                        .numpy()[0]
                    )
                    assert (
                        value.shape == (3, *raw.shape)
                        and value.dtype == np.float32
                        and np.isfinite(value).all()
                    )
                    if index == 0:
                        parent_values.append(value)
                        full_fingerprint = physical
                    else:
                        path = output / f"{case}-fold{index - 1}.npy"
                        with path.open("xb") as stream:
                            np.save(stream, value, allow_pickle=False)
                        fields.append(reference(path))
                        fingerprints.append(physical)
            record = {
                "id": case,
                "input_fingerprints": {k: fingerprint(v) for k, v in data.items()},
                "noise": row["noise"],
                "identity_zero_noise": False,
                "mask_A": reference(mask_path),
                "fields": fields,
                "argument_fingerprints": fingerprints,
                "full_parent_argument_fingerprints": full_fingerprint,
                "adopted_from": None,
            }
            write_json(output / (case + "-receipt.json"), record)
            group_records.append(record)
            write_json(
                root / "neural-progress.json",
                {
                    "owner": owner_identity(),
                    "completed_cases": len(records) + len(group_records),
                    "expected_cases": 48,
                    "counts": counts,
                    "last_case": case,
                    "seconds": time.monotonic() - started,
                },
                replace=True,
            )
            print("neural", len(records) + len(group_records), "of48", case, counts, flush=True)
        path = parents / (group["id"] + ".npy")
        with path.open("xb") as stream:
            np.save(stream, np.stack(parent_values), allow_pickle=False)
        parent_groups.append(
            {"group": group["id"], "parent": reference(path), "cases": group["cases"]}
        )
        records.extend(group_records)
    assert counts == {"parent": 48, "masked": 96, "encoder": 144}
    for key, value in model.restoration_state_dict().items():
        assert torch.equal(value.detach().cpu(), selected[key].cpu())
    assert model_hash(model.context.backbone) == plan["backbone_sha256"]
    verify_plan(plan)
    write_json(
        root / "masked-backgrounds-collection.json",
        {
            "plan": reference(root / "plan.json"),
            "rows": records,
            "background_configuration": plan["background_configuration"],
            "new_root_forwards": 96,
            "new_encoder_forwards": 96,
            "complete_background_fields": 96,
            "parent_root_forwards": 48,
            "total_root_forwards": 144,
            "total_encoder_forwards": 144,
            "all91_restoration_and_backbone_tensors_unchanged": True,
            "target_or_reference_arrays_loaded": 0,
            "scope": "96 fresh masked calls plus48 separately recorded full-parent calls; no target/true-variance/reference arrays accessed. Genuine A-only arguments tested under withheld NaNs. This is new synthetic sensor evidence, not replay of earlier fixed cohorts.",
        },
    )
    write_json(
        root / "parents-collection.json",
        {
            "plan": reference(root / "plan.json"),
            "groups": parent_groups,
            "checkpoint": plan["checkpoint"],
            "full_parent_forwards": 48,
            "target_or_reference_arrays_loaded": 0,
        },
    )
    write_json(
        root / "neural-completed.json",
        {
            "plan": reference(root / "plan.json"),
            "counts": counts,
            "cases": 48,
            "parents": reference(root / "parents-collection.json"),
            "backgrounds": reference(root / "masked-backgrounds-collection.json"),
            "all91_restoration_and_backbone_tensors_unchanged": True,
            "target_or_reference_arrays_loaded": 0,
            "seconds": time.monotonic() - started,
            "owner": owner_identity(),
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "neural"])
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    try:
        {"prepare": prepare, "neural": neural}[args.mode](args.root.absolute())
    except Exception as error:
        if args.root.is_dir() and not (args.root / "failed.json").exists():
            write_json(
                args.root / "failed.json",
                {
                    "mode": args.mode,
                    "error": repr(error),
                    "traceback": traceback.format_exc(),
                    "scope": "Preserve failed stage; no automatic retry or worker restart.",
                },
            )
        raise
