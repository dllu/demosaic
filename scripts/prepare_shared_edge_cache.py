"""Freeze, inspect and cache shared-edge training pairs; reuse all other rows."""

import argparse
import json
import os
import shutil
import time

import numpy as np
import psutil
import torch
from directional_trial_protocol import REPO, freeze, guard, launch, read, ref, require_launch, save
from paired_response_counters import count_source_draws
from shared_edge_mesh_data import SEED, shared_edge_observation

from demosaic.prediction_archive import fingerprint

ROOT = REPO / ".cache/quality-20261108/V202-shared-edge-data-v2"


def resource_check(plan):
    assert shutil.disk_usage(REPO).free > plan["minimum_GiB"]["local"] * 2**30
    assert psutil.virtual_memory().available > plan["minimum_GiB"]["RAM"] * 2**30


def prepare():
    previous = REPO / ".cache/quality-20261108/V200-scale-supported-CFA-trial-v1/plan-v1.json"
    old = read(previous)
    cache = read(old["cache"]["path"])
    assert ref(old["cache"]["path"]) == old["cache"]
    publication = REPO / "docs/results/v200-scale-supported-cfa-wave-final-v1.json"
    proof = read(
        REPO / "docs/results/v200-scale-supported-cfa-wave-publication-verification-v1.json"
    )
    assert proof["publication"] == ref(publication) and proof["status"].startswith("pass-")
    source = read(REPO / "docs/results/v200-completed-execution-v1.json")
    neural = source["all107_neural_hashes_unchanged"]
    for name, digest in neural.items():
        assert ref(REPO / "src/demosaic" / name)["sha256"] == digest
    data_plan = read(old["training_provenance"]["path"])
    selected = [
        {
            "step": item["step"],
            "ordinal": n,
            "old_arrays": item["arrays"],
            "old_parent": item["parent"],
        }
        for n, item in enumerate(
            [x for x in cache["batches"] if x["metadata"]["domain"] == "mixed"]
        )
    ]
    assert len(selected) == 156
    chosen = [v["step"] for v in selected[:4]]
    for predicate in [
        lambda m: m["noise"]["shot"] == m["noise"]["read"] == 0,
        lambda m: m["noise"]["shot"] == 0.00256,
    ]:
        chosen.append(
            next(
                x["step"]
                for x in selected
                if x["step"] not in chosen
                and predicate(cache["batches"][x["step"] - 1]["metadata"])
            )
        )
    tests = REPO / ".cache/v202-shared-edge-tests-v2.log"
    assert "19 passed" in tests.read_text()
    assert not ROOT.exists()
    ROOT.mkdir()
    (ROOT / "training-batches").mkdir()
    work, sources = freeze(ROOT, ["prepare_shared_edge_cache.py"])
    plan = {
        "status": "prepared-shared-edge-paired-training-data-not-quality",
        "created_unix_UTC": time.time(),
        "root": str(ROOT),
        "work": str(work),
        "runner": ref(work / "scripts/prepare_shared_edge_cache.py"),
        "cache": old["cache"],
        "old_pair_units": old["pair_units"],
        "parent": data_plan["parent"],
        "parent_module_hash": cache["parent_before"],
        "DINO_module_hash": cache["DINO_before"],
        "sampling_library": old["sampling_library"],
        "selected": selected,
        "inspection_steps": chosen,
        "data_seed": SEED,
        "unchanged_batches": 844,
        "new_input_batches": 156,
        "planned_pair_constructions": 312,
        "planned_geometry_transforms": 624,
        "planned_sensor_Poisson_calls": 468,
        "planned_sensor_Gaussian_calls": 156,
        "planned_parent_validation_roots": 1,
        "planned_new_parent_roots": 156,
        "planned_total_parent_DINO_images": 628,
        "parent_validation_step": selected[0]["step"],
        "parent_policy": "FP32;TF32off;cudnn.benchmarkFalse;cudnn.deterministicTrue;deterministic_algorithmsTrue;channels_last;frozen V1435k and DINO;12GiB allocator cap;CUBLAS4096:8",
        "CPU_tests": ref(tests),
        "all107_neural_hashes": neural,
        "minimum_GiB": {"local": 64, "RAM": 32},
        "launch_RAM_GiB": 52,
        "CUDA_quota_GiB": 12,
        "new_cache_forecast_GiB": 6,
        "future_trial_forecast_GiB": 2,
        "new_external_bytes": 0,
        "source_plan": ref(previous),
        "domain_weights_unchanged": old["domain_weights"],
        "inputs": [
            ref(previous),
            old["cache"],
            old["pair_units"],
            old["training_provenance"],
            ref(data_plan["parent"]["path"]),
            old["sampling_library"],
            ref(tests),
            ref(publication),
            ref(REPO / "docs/results/v201-training-distribution-audit-v1.json"),
        ],
        "frozen_files": sources,
        "scope": "Replace156 mixed rows only;844 arrays/parents and their unit rows reused byte-exactly.139 noisy mixed updates/17ADCskips retain original condition coefficients and schedule. Two shared-camera/CFA pairs instead of four unrelated members;members0and2 supply original calibration. Generic strong-edge/background is identical in both clean members;weak compact crossed-mesh increment in one,with one-in-five no-increment controls. Edge/background range,content,geometry,coupling and noise draws change together;not an isolated paired-loss or brightness ablation. Same V200643parameter architecture and Whole ten-term loss planned for fresh900update comparison;this phase trains no model. Six input constructions inspected once and adopted. One original cached parent parity plus156 new parent/DINO roots planned;no hidden replay. Deterministic archived V143 parent policy explicit. All107 neural sources unchanged. All procedural sources,no original/photo/dataz reads;both GFXfamilies/JPEGs/siblings heldout. All new files local;6GiBcache+2GiBfuturetrial above64GiBfree reserve;zeroexternalwrites. Actual trained quality and full822case/rawEMA/native comparisons remain required.",
    }
    assert shutil.disk_usage(REPO).free > (64 + 8) * 2**30
    resource_check(plan)
    save(ROOT / "plan-v1.json", plan)
    print("Prepared156shared-edge rows/844exact adoptions/6native inspections/6GiB local bound")


def construct(plan, item, ordinal):
    assert ref(item["arrays"]["path"]) == item["arrays"]
    with np.load(item["arrays"]["path"], allow_pickle=False) as f:
        calibration = {k: f[k] for k in ["wb", "matrix", "colors"]}
    for k, v in calibration.items():
        assert fingerprint(v) == item["inputs"][k]
    before = torch.get_rng_state().clone()
    with count_source_draws() as draws:
        arrays, metadata = shared_edge_observation(item, calibration, ordinal)
    assert draws == {
        "sensor_Poisson": 3,
        "sensor_Gaussian": 1,
        "procedural_Poisson": 0,
        "procedural_Gaussian": 0,
        "coupled_sensor_calls": 1,
        "ordinary_sensor_calls": 0,
    }
    assert torch.equal(before, torch.get_rng_state())
    clean = [
        np.stack(
            [
                np.stack([rgb[int(c), k // 2 :: 2, k % 2 :: 2] for k, c in enumerate(colors)])
                for rgb, colors in zip(arrays["target"][p::2], arrays["colors"][p::2], strict=True)
            ]
        )
        for p in (0, 1)
    ]
    for p, key in enumerate(["clean_packed_a", "clean_packed_b"]):
        assert fingerprint(clean[p]) == metadata["sensor"][key]
    for pair in range(2):
        same = clean[0][pair] == clean[1][pair]
        assert same.sum() > same.size // 5
        np.testing.assert_array_equal(
            arrays["packed"][2 * pair][same], arrays["packed"][2 * pair + 1][same]
        )
        if not metadata["cases"][2 * pair]["source"]["mesh"]["present"]:
            np.testing.assert_array_equal(
                arrays["target"][2 * pair], arrays["target"][2 * pair + 1]
            )
            np.testing.assert_array_equal(
                arrays["packed"][2 * pair], arrays["packed"][2 * pair + 1]
            )
    units = np.maximum(
        np.sqrt(
            np.mean(
                metadata["noise"]["shot"] * np.abs(clean[0].astype(np.float64) - clean[1]),
                axis=(1, 2, 3),
            )
        ),
        16 / 65535,
    )
    np.testing.assert_allclose(arrays["pair_units"].reshape(-1), units, rtol=3e-7, atol=1e-12)
    path = ROOT / "training-batches" / f"step-{item['step']:04d}-inputs.npz"
    with path.open("xb") as stream:
        np.savez(stream, **arrays)
    return arrays, {
        "step": item["step"],
        "arrays": ref(path),
        "metadata": metadata,
        "inputs": {k: fingerprint(v) for k, v in arrays.items()},
        "legacy_arrays": item["arrays"],
        "mixed_ordinal": ordinal,
        "actual_sampler_calls": draws,
        "independent_clean_sensor_and_units_checked": True,
    }


def inspect(plan):
    from PIL import Image, ImageDraw, ImageFont

    from demosaic.archive_metrics import noisy_malvar

    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    items = read(plan["cache"]["path"])["batches"]
    selected = {x["step"]: x for x in plan["selected"]}
    directory = ROOT / "inspection-v1"
    directory.mkdir()
    records, figures = [], []
    for step in plan["inspection_steps"]:
        resource_check(plan)
        arrays, record = construct(plan, items[step - 1], selected[step]["ordinal"])
        noisy = noisy_malvar(arrays)
        board = Image.new("RGB", (4 * 168, 2 * 212), "white")
        draw = ImageDraw.Draw(board)
        metadata = []
        for pair in range(2):
            i = 2 * pair
            source = record["metadata"]["cases"][i]["source"]
            exposure = min(16.0, max(1.0, 0.025 / source["background"]["level"]))
            roi = [176, 176, 160, 160]
            x, y, w, h = roi

            def display(value, exp, arrays=arrays, i=i, x=x, y=y, w=w, h=h):
                rgb = np.einsum(
                    "ij,jhw->ihw",
                    arrays["matrix"][i].astype(np.float64),
                    value[:, y : y + h, x : x + w].astype(np.float64)
                    * exp
                    * arrays["wb"][i, :, None, None],
                ).clip(0, 1)
                rgb = np.where(rgb <= 0.0031308, 12.92 * rgb, 1.055 * rgb ** (1 / 2.4) - 0.055)
                return np.rint(rgb.transpose(1, 2, 0) * 255).astype(np.uint8)

            # Display the signed camera-RGB increment on a neutral scene-linear background.
            neutral = (
                np.einsum(
                    "ij,j->i",
                    np.linalg.inv(arrays["matrix"][i].astype(np.float64)),
                    np.full(3, 0.18),
                )
                / arrays["wb"][i]
            )
            delta = neutral[:, None, None] + 64 * (arrays["target"][i] - arrays["target"][i + 1])
            panels = [
                ("Shared clean edge", arrays["target"][i + 1], exposure),
                ("Edge + mesh clean", arrays["target"][i], exposure),
                ("Noisy present Malvar", noisy[i], exposure),
                ("Exact increment x64", delta, 1.0),
            ]
            draw.text(
                (4, pair * 212 + 2),
                f"TRAINING INPUT step{step}/pair{pair};{source['background']['kind']};mesh{source['mesh']['present']};exposure{exposure:.3f}",
                fill="black",
                font=font,
            )
            for n, (label, value, exp) in enumerate(panels):
                draw.text((n * 168 + 4, pair * 212 + 22), label, fill="black", font=font)
                board.paste(Image.fromarray(display(value, exp)), (n * 168 + 4, pair * 212 + 43))
            metadata.append(
                {
                    "pair": pair,
                    "ROI_xywh": roi,
                    "exposure": exposure,
                    "contrast": 1,
                    "signed_increment_gain": 64,
                    "mesh_present": source["mesh"]["present"],
                }
            )
        path = directory / f"step-{step:04d}.png"
        board.save(path)
        records.append(record)
        figures.append({"image": ref(path), "step": step, "panels": metadata, "no_resize": True})
    save(
        ROOT / "inspection-v1.json",
        {
            "status": "six-training-input-boards-awaiting-actual-viewing",
            "plan": ref(ROOT / "plan-v1.json"),
            "batches": records,
            "figures": figures,
            "new_parent_DINO_roots": 0,
            "scope": "Training input/target inspection only;no restored candidate or quality result.",
        },
    )
    print(
        "Constructed6input batches once;6native boards;no parent/DINO;viewing required", flush=True
    )


def view(plan, notes):
    inspection = read(ROOT / "inspection-v1.json")
    assert notes and len(inspection["figures"]) == 6
    for figure in inspection["figures"]:
        assert ref(figure["image"]["path"]) == figure["image"] and figure["no_resize"]
    save(
        ROOT / "actual-viewing-v1.json",
        {
            "status": "actually-viewed-six-training-input-boards-at-original-detail",
            "inspection": ref(ROOT / "inspection-v1.json"),
            "notes": notes,
            "no_candidate_quality_claim": True,
        },
    )


def cache(plan, owner, *, resume=None):
    from profile_raw_kernel_inference import model_hash

    from demosaic.inference import load_checkpoint

    viewed = read(ROOT / "actual-viewing-v1.json")
    assert viewed["inspection"] == ref(ROOT / "inspection-v1.json")
    inspection = read(viewed["inspection"]["path"])
    adopted = {x["step"]: x for x in inspection["batches"]}
    selected = {x["step"]: x for x in plan["selected"]}
    old = read(plan["cache"]["path"])
    torch.ops.load_library(plan["sampling_library"]["path"])
    torch.cuda.set_per_process_memory_fraction(
        plan["CUDA_quota_GiB"] * 2**30 / torch.cuda.get_device_properties(0).total_memory
    )
    with torch.random.fork_rng(devices=[0]):
        parent, loaded = load_checkpoint(plan["parent"]["path"], "cuda")
    assert loaded["loaded_sha256"] == plan["parent"]["sha256"]
    parent.eval().requires_grad_(False).to(memory_format=torch.channels_last)
    before, backbone = model_hash(parent), model_hash(parent.context.backbone)
    assert before == plan["parent_module_hash"] and backbone == plan["DINO_module_hash"]
    counts = (
        dict(resume["counts"])
        if resume
        else {"parent_entered": 0, "parent_returned": 0, "DINO_entered": 0, "DINO_returned": 0}
    )
    completed_records = resume["records"] if resume else {}
    for module, prefix in [(parent, "parent"), (parent.context.backbone, "DINO")]:
        module.register_forward_pre_hook(
            lambda *a, prefix=prefix: counts.__setitem__(
                prefix + "_entered", counts[prefix + "_entered"] + 1
            )
        )
        module.register_forward_hook(
            lambda *a, prefix=prefix: counts.__setitem__(
                prefix + "_returned", counts[prefix + "_returned"] + 1
            )
        )
    cpu_rng, cuda_rng = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()

    def predict(arrays, condition):
        resource_check(plan)
        tensors = {
            k: torch.from_numpy(arrays[k]).cuda()
            for k in ["packed", "variance", "colors", "wb", "matrix"]
        }
        parent.set_noise(condition["shot"], condition["read"])
        with torch.inference_mode():
            value = (
                parent(*(tensors[k] for k in ["packed", "variance", "colors", "wb", "matrix"]))
                .cpu()
                .numpy()
            )
        assert value.shape == arrays["target"].shape and np.isfinite(value).all()
        assert torch.equal(cpu_rng, torch.get_rng_state()) and torch.equal(
            cuda_rng, torch.cuda.get_rng_state()
        )
        assert torch.cuda.max_memory_allocated() < plan["CUDA_quota_GiB"] * 2**30
        return value

    if not resume:
        original = old["batches"][plan["parent_validation_step"] - 1]
        assert (
            ref(original["arrays"]["path"]) == original["arrays"]
            and ref(original["parent"]["path"]) == original["parent"]
        )
        arrays = dict(np.load(original["arrays"]["path"], allow_pickle=False))
        parity = predict(arrays, original["metadata"]["noise"])
        expected = np.load(original["parent"]["path"], allow_pickle=False)
        np.testing.assert_array_equal(parity.view(np.uint32), expected.view(np.uint32))
        save(
            ROOT / "parent-policy-parity-v1.json",
            {
                "status": "pass-one-original-parent-bit-exact-policy-parity",
                "original": original["parent"],
                "values": fingerprint(parity),
                "counts": dict(counts),
                "owner": owner,
            },
        )
        del arrays, parity, expected
    rows, fresh = [], 0
    journal_name = (
        plan.get("resumption_journal", "resume-cache-trace-v1.jsonl")
        if resume
        else "cache-trace-v1.jsonl"
    )
    with (ROOT / journal_name).open("x") as journal:
        for item in old["batches"]:
            step = item["step"]
            if step not in selected:
                rows.append(item)
                continue
            resource_check(plan)
            if step in completed_records:
                record = completed_records[step]
                assert ref(record["arrays"]["path"]) == record["arrays"]
                assert ref(record["parent"]["path"]) == record["parent"]
                rows.append(record)
                journal.write(
                    json.dumps(
                        {"step": step, "event": "adopted-completed-prefix", "counts": dict(counts)}
                    )
                    + "\n"
                )
                journal.flush()
                continue
            if step in adopted:
                record = adopted[step]
                assert ref(record["arrays"]["path"]) == record["arrays"]
                arrays = dict(np.load(record["arrays"]["path"], allow_pickle=False))
            else:
                arrays, record = construct(plan, item, selected[step]["ordinal"])
                fresh += 1
            assert {k: fingerprint(v) for k, v in arrays.items()} == record["inputs"]
            journal.write(
                json.dumps({"step": step, "event": "before-parent", "counts": dict(counts)}) + "\n"
            )
            journal.flush()
            value = predict(arrays, record["metadata"]["noise"])
            path = ROOT / "training-batches" / f"step-{step:04d}-parent.npy"
            with path.open("xb") as stream:
                np.save(stream, value, allow_pickle=False)
            complete = dict(
                record,
                parent=ref(path),
                parent_values=fingerprint(value),
                inspection_input_adopted=step in adopted,
            )
            rows.append(complete)
            journal.write(
                json.dumps(
                    {"step": step, "event": "completed", "record": complete, "counts": dict(counts)}
                )
                + "\n"
            )
            journal.flush()
            progress = ROOT / "cache-progress-v1.json"
            tmp = progress.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(
                    {
                        "owner": owner,
                        "completed_new_batches": counts["parent_returned"] - 1,
                        "step": step,
                        "counts": counts,
                        "fresh_input_constructions": fresh,
                    }
                )
            )
            tmp.replace(progress)
            if counts["parent_returned"] % 10 == 1:
                print(
                    {
                        "step": step,
                        "completed_new_batches": counts["parent_returned"] - 1,
                        "counts": counts,
                    },
                    flush=True,
                )
            del arrays, value
    assert len(rows) == 1000 and fresh == 150 and all(v == 157 for v in counts.values())
    assert model_hash(parent) == before and model_hash(parent.context.backbone) == backbone
    assert all(p.grad is None and not p.requires_grad for p in parent.parameters())
    guard(plan)
    units = read(plan["old_pair_units"]["path"])
    unit_rows = []
    for item, previous in zip(rows, units["rows"], strict=True):
        if item["step"] not in selected:
            assert item == old["batches"][item["step"] - 1]
            unit_rows.append(previous)
        else:
            values = np.maximum(
                np.sqrt(
                    np.asarray(
                        item["metadata"]["sensor"]["increment_mean_variance"], dtype=np.float64
                    )
                ),
                16 / 65535,
            ).astype(np.float32)
            with np.load(item["arrays"]["path"], allow_pickle=False) as a:
                np.testing.assert_allclose(
                    a["pair_units"].reshape(-1), values, rtol=3e-7, atol=1e-12
                )
            unit_rows.append(
                {
                    "step": item["step"],
                    "batch": item["arrays"],
                    "shape": [2, 1, 1, 1],
                    "candidate_units_FP32": values.tolist(),
                }
            )
    save(
        ROOT / "candidate-pair-unit-table-v1.json",
        {
            "rows": unit_rows,
            "cache": ref(ROOT / "plan-v1.json"),
            "floor_DN16": 16,
            "scope": "844 exact old rows;156 new nominal sensor-increment units,not RGB covariance.",
        },
    )
    save(
        ROOT / "cache-result-v1.json",
        {
            "status": "completed156-shared-edge-parent-batches-and844-exact-adoptions",
            "plan": ref(ROOT / "plan-v1.json"),
            "batches": rows,
            "counts": counts,
            "owner": owner,
            "execution_plan": ref(plan.get("execution_plan_path", ROOT / "resume-plan-v1.json"))
            if resume
            else ref(ROOT / "plan-v1.json"),
            "prefix_adopted_without_source_or_parent_replay": sorted(completed_records),
            "parent_roots_in_this_segment": 157
            - (resume["counts"]["parent_returned"] if resume else 0),
            "CUDA_peak_scope": "Completed segment; first segment satisfied per-call quota but did not record final peak before reporting exception."
            if resume
            else "Complete run",
            "parent_before": before,
            "parent_after": model_hash(parent),
            "DINO_before": backbone,
            "DINO_after": model_hash(parent.context.backbone),
            "new_parent_images": 624,
            "new_DINO_images": 624,
            "validation_parent_images": 4,
            "validation_DINO_images": 4,
            "adopted_legacy_batches": 844,
            "new_input_batches": 156,
            "inspection_inputs_adopted": 6,
            "additional_input_constructions": fresh,
            "actual_pair_constructions": 312,
            "actual_geometry_transforms": 624,
            "actual_sensor_Poisson_calls": 468,
            "actual_sensor_Gaussian_calls": 156,
            "global_Torch_RNG_unchanged": True,
            "CUDA_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "pair_units": ref(ROOT / "candidate-pair-unit-table-v1.json"),
            "scope": plan["scope"],
        },
    )
    print(
        "PASS156new parent/DINO roots+1parity;844exact adoptions;no training or quality claim",
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "phase", choices=["prepare", "inspect", "view", "cache", "launch-inspect", "launch-cache"]
    )
    parser.add_argument("--notes")
    args = parser.parse_args()
    if args.phase == "prepare":
        prepare()
        return
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    if args.phase.startswith("launch-"):
        launch(ROOT, args.phase.removeprefix("launch-"))
        return
    assert ref(__file__) == plan["runner"]
    if args.phase == "view":
        view(plan, args.notes)
        return
    owner = require_launch(ROOT, args.phase)
    (ROOT / f"{args.phase}.claim").open("x").close()
    os.nice(max(0, 10 - psutil.Process().nice()))
    os.sched_setaffinity(0, [4, 5])
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.set_float32_matmul_precision("highest")
    torch.backends.cuda.matmul.allow_tf32 = torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    try:
        inspect(plan) if args.phase == "inspect" else cache(plan, owner)
    except BaseException as error:
        save(
            ROOT / f"{args.phase}-failure-v1.json",
            {"owner": owner, "error": repr(error), "status": "failed-preserved-no-automatic-retry"},
        )
        raise


if __name__ == "__main__":
    main()
