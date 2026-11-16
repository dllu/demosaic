"""Whole-context A-only neural nuisance and matched conditional-wave pilot."""

import argparse
import os
import shutil
import sys
import time
from pathlib import Path

import numpy as np

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)

REPO = next(p for p in Path(__file__).resolve().parents if (p / "PROMPT.md").is_file())
BACKGROUND_SHA = "a9d9b6b4f974e24a6b11e5e740aab32314233a7f53c056cf37c7d2aac1c589fb"
BACKBONE_SHA = "691963f0f796aac860d818d59d9d14287a4675612829fbe9467c7f5df8ce5b14"


def prepare(root, background_cache=None, *, fixed_analytic_frequencies=False):
    from demosaic.local_validated_waves import LocalWaveConfig

    source = REPO / ".cache/experiments/phase-aggregation-projected-pilot-v1"
    previous = read_json(source / "plan.json")
    checkpoint = reference(Path("/mnt/external/demosaic/models/v120-final20000.pt"))
    assert checkpoint["sha256"] == BACKGROUND_SHA
    assert len(previous["rows"]) == 48 and len(previous["finite_groups"]) == 12
    geometry = LocalWaveConfig().to_dict()
    background_config = {
        "checkpoint": checkpoint,
        "backbone_sha256": BACKBONE_SHA,
        "global_split_seed": geometry["split_seed"],
        "transform": "Same-phase normalized Gaussian sigma1packed/truncate3; retain A exactly, A-only mean fallback. Original explicit shot/read, variance from filled A-only signal. No parent/reference/GT inputs.",
    }
    cache = reference(background_cache) if background_cache else None
    if cache:
        old = read_json(checked(cache))
        assert old["background_configuration"] == background_config
        assert old["all91_restoration_and_backbone_tensors_unchanged"]
        assert len(old["rows"]) == len(previous["rows"]) and {
            r["id"] for r in old["rows"]
        } == {r["id"] for r in previous["rows"]}
    root.mkdir(parents=True, exist_ok=False)
    work, files = freeze_sources(
        REPO,
        root,
        entries=(
            "pilot_neural_nuisance.py",
            "pilot_phase_aggregation.py",
            "report_local_validated_waves.py",
            "audit_local_wave_pilot.py",
            "report_checkpoint_pilot.py",
            "audit_checkpoint_pilot.py",
            "report_phase_aggregation.py",
            "profile_raw_kernel_inference.py",
        ),
    )
    model = {
        "kind": "A-only whole-context neural nuisance with conditional H1 wave replacement",
        "geometry": geometry,
        "background_configuration": background_config,
        "neural_frequency_source": "fixed-analytic-proposals"
        if fixed_analytic_frequencies
        else "residual-reselection",
        "source": reference(work / "src/demosaic/neural_nuisance.py"),
        "shared_wave_source": reference(work / "src/demosaic/local_validated_waves.py"),
        "parents": read_json(checked(previous["model"]))["parents"],
        "nuisance": "One own-color neural CFA coordinate, upper-censored at sensor white; same analytic A-only edge and variance proxy. Frequency source explicitly declared above, joint per-color WLS. No neural training update.",
        "delivery": "Unique full-minus-conditional-null prediction for both analytic and neural nuisance arms. Raw-sinusoid H1 control retained separately. Parent projected after all scores; empirical support is not calibrated confidence.",
    }
    write_json(root / "analytic-model.json", model)
    positive = sum(r["noise"]["shot"] + r["noise"]["read"] > 0 for r in previous["rows"])
    inputs = [reference(source / "plan.json"), reference(root / "analytic-model.json"), checkpoint]
    inputs += [r[k] for r in previous["rows"] for k in ("arrays", "parent")]
    if cache:
        inputs.append(cache)
    plan = {
        "root": str(root),
        "work": str(work),
        "python": sys.executable,
        "script": reference(work / "scripts/pilot_neural_nuisance.py"),
        "model": reference(root / "analytic-model.json"),
        "geometry_config": geometry,
        "background_configuration": background_config,
        "background_cache": cache,
        "fixed_analytic_frequencies": fixed_analytic_frequencies,
        "rows": previous["rows"],
        "finite_groups": previous["finite_groups"],
        "thresholds": [0, 2, 4],
        "primary": "local-t2",
        "modes": [
            "H1-global",
            "H1-local",
            "conditional-global",
            "conditional-local",
            "global",
            "local",
        ],
        "shared_global_CFA_partition": True,
        "positive_noise_cases": positive,
        "background_field_count": 2 * positive,
        "maximum_new_neural_forwards": 0 if cache else 2 * positive,
        "minimum_start_RAM_GiB": 48,
        "minimum_runtime_RAM_GiB": 32,
        "minimum_disk_GiB": 96,
        "maximum_stage_seconds": 7200,
        "standalone_H1_checks": ["iso400-index0024-role2", "main-building-detail"],
        "inputs": list({(x["path"], x["sha256"]): x for x in inputs}.values()),
        "frozen_files": files,
        "scope": "Fixed48-case development cohort: sources0/1, RGGB/repeat0, near/far400/1600/6400 roles, original materials and both protected GFX families/profiles/ROIs/JPEGs. One global A/B split shared by whole-context frozen V120 predictions and overlapping analytic tiles; all new controls use that split. Same A-only analytic edge/variance proxy for both nuisance models. Controls separate raw-H1 delivery, conditional analytic delivery, and conditional neural-nuisance delivery. All88 background fields and all48 corrections close before new GT/reference scoring. Four ADC cases bypass with zero NN calls. No new sensor noise/source observation, original RAW decode, optimizer update or parent-feature leakage. Reused adaptive2-source cohort, no broad quality/generalization claim.",
    }
    write_json(root / "plan.json", plan)
    verify_plan(plan)
    return root / "plan.json"


def input_arrays(row):
    with np.load(checked(row["arrays"]), allow_pickle=False) as z:
        sample = row["sample"]
        return {
            "packed": z["packed"][sample],
            "colors": z["colors"][sample],
            "wb": z["wb"][sample : sample + 1],
            "matrix": z["matrix"][sample : sample + 1],
        }


def raw_frame(data):
    packed = data["packed"]
    h, w = packed.shape[-2] * 2, packed.shape[-1] * 2
    raw = np.empty((h, w), packed.dtype)
    for phase in range(4):
        raw[phase // 2 :: 2, phase % 2 :: 2] = packed[phase]
    return raw


def background_arguments(raw, mask, data, noise):
    from demosaic.neural_nuisance import masked_packed_input

    packed = masked_packed_input(raw, mask)
    damaged = raw.copy()
    damaged[~mask] = np.nan
    np.testing.assert_array_equal(packed, masked_packed_input(damaged, mask))
    variance = packed.clip(0) * noise["shot"] + noise["read"]
    return {
        "packed": packed[None],
        "variance": variance[None],
        "colors": data["colors"][None],
        "wb": data["wb"],
        "matrix": data["matrix"],
    }


def backgrounds(root):
    import psutil
    import torch
    from profile_raw_kernel_inference import model_hash

    from demosaic.experiments.evaluation.withheld import stratified_split
    from demosaic.experiments.runtime import owner_identity
    from demosaic.models import load_model
    from demosaic.prediction_archive import fingerprint

    plan = read_json(root / "plan.json")
    verify_plan(plan)
    assert reference(__file__) == plan["script"]
    (root / "backgrounds.claim").open("x").close()
    write_json(root / "backgrounds-owner.json", owner_identity())
    os.nice(10)
    torch.set_num_threads(2)
    torch.set_float32_matmul_precision("highest")
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = True
    torch.cuda.set_per_process_memory_fraction(
        min(1, 24 * 2**30 / torch.cuda.get_device_properties(0).total_memory)
    )
    output = root / "backgrounds"
    output.mkdir()
    adopted = read_json(checked(plan["background_cache"])) if plan["background_cache"] else None
    old = {r["id"]: r for r in adopted["rows"]} if adopted else {}
    model = state = selected = None
    counts = [0, 0]
    records = []
    began = time.monotonic()
    for row in plan["rows"]:
        if (
            psutil.virtual_memory().available < plan["minimum_runtime_RAM_GiB"] * 2**30
            or shutil.disk_usage(root).free < plan["minimum_disk_GiB"] * 2**30
        ):
            raise RuntimeError("Background runtime reserve unavailable")
        if time.monotonic() - began > plan["maximum_stage_seconds"]:
            raise TimeoutError("Background stage deadline reached")
        data = input_arrays(row)
        raw = raw_frame(data)
        physical = {k: fingerprint(v) for k, v in data.items()}
        record = {"id": row["id"], "input_fingerprints": physical, "noise": row["noise"]}
        if row["noise"]["shot"] + row["noise"]["read"] == 0:
            record.update(identity_zero_noise=True, fields=[])
        else:
            mask = stratified_split(
                raw.shape, plan["background_configuration"]["global_split_seed"]
            )
            mask_path = output / (row["id"] + "-A-mask.npy")
            with mask_path.open("xb") as f:
                np.save(f, mask, allow_pickle=False)
            expected = [background_arguments(raw, m, data, row["noise"]) for m in [mask, ~mask]]
            fingerprints = [{k: fingerprint(v) for k, v in args.items()} for args in expected]
            if row["id"] in old:
                prior = old[row["id"]]
                assert prior["input_fingerprints"] == physical and prior["noise"] == row["noise"]
                assert prior["argument_fingerprints"] == fingerprints
                np.testing.assert_array_equal(np.load(checked(prior["mask_A"])), mask)
                for item in prior["fields"]:
                    value = np.load(checked(item))
                    assert (
                        value.shape == (3, *raw.shape)
                        and value.dtype == np.float32
                        and np.isfinite(value).all()
                    )
                record.update(fields=prior["fields"], adopted_from=plan["background_cache"])
            else:
                if model is None:
                    if psutil.virtual_memory().available < plan["minimum_start_RAM_GiB"] * 2**30:
                        raise RuntimeError("Neural-load RAM reserve unavailable")
                    model, state = load_model(
                        "v120",
                        checkpoint=checked(plan["background_configuration"]["checkpoint"]),
                        device="cuda",
                    )
                    model.eval().to(memory_format=torch.channels_last)
                    selected = state["ema"] if "ema" in state else state["model"]
                    assert len(model.restoration_state_dict()) == 91 and set(selected) == set(
                        model.restoration_state_dict()
                    )
                    for key, value in model.restoration_state_dict().items():
                        assert torch.equal(value.detach().cpu(), selected[key].cpu())
                    assert model_hash(model.context.backbone) == BACKBONE_SHA
                    model.register_forward_pre_hook(lambda *_: counts.__setitem__(0, counts[0] + 1))
                    model.context.backbone.register_forward_pre_hook(
                        lambda *_: counts.__setitem__(1, counts[1] + 1)
                    )
                fields = []
                with torch.inference_mode():
                    for fold, args in enumerate(expected):
                        tensors = {k: torch.from_numpy(v.copy()).cuda() for k, v in args.items()}
                        assert {k: fingerprint(v) for k, v in tensors.items()} == fingerprints[fold]
                        model.set_noise(row["noise"]["shot"], row["noise"]["read"])
                        value = (
                            model(
                                *(
                                    tensors[k]
                                    for k in ["packed", "variance", "colors", "wb", "matrix"]
                                )
                            )
                            .cpu()
                            .numpy()[0]
                        )
                        assert (
                            value.shape == (3, *raw.shape)
                            and value.dtype == np.float32
                            and np.isfinite(value).all()
                        )
                        path = output / f"{row['id']}-fold{fold}.npy"
                        with path.open("xb") as f:
                            np.save(f, value, allow_pickle=False)
                        fields.append(reference(path))
                        write_json(
                            output / f"{row['id']}-fold{fold}-receipt.json",
                            {
                                "id": row["id"],
                                "fold": fold,
                                "prediction": fields[-1],
                                "arguments": fingerprints[fold],
                                "source_plan": reference(root / "plan.json"),
                                "discovery_only_input_invariance": True,
                            },
                        )
                record.update(fields=fields, adopted_from=None)
            record.update(
                identity_zero_noise=False,
                mask_A=reference(mask_path),
                argument_fingerprints=fingerprints,
            )
        write_json(output / (row["id"] + "-receipt.json"), record)
        records.append(record)
        write_json(
            root / "background-progress.json",
            {
                "owner": owner_identity(),
                "completed_cases": len(records),
                "expected_cases": len(plan["rows"]),
                "root_forwards": counts[0],
                "encoder_forwards": counts[1],
                "last_case": row["id"],
                "seconds": time.monotonic() - began,
            },
            replace=True,
        )
        print("background", len(records), "of", len(plan["rows"]), row["id"], counts, flush=True)
    if model is not None:
        for key, value in model.restoration_state_dict().items():
            assert torch.equal(value.detach().cpu(), selected[key].cpu())
        assert model_hash(model.context.backbone) == BACKBONE_SHA
    fresh = sum(not r["identity_zero_noise"] and r["adopted_from"] is None for r in records)
    assert counts == [2 * fresh, 2 * fresh] and counts[0] <= plan["maximum_new_neural_forwards"]
    verify_plan(plan)
    write_json(
        root / "backgrounds-collection.json",
        {
            "plan": reference(root / "plan.json"),
            "rows": records,
            "background_configuration": plan["background_configuration"],
            "new_root_forwards": counts[0],
            "new_encoder_forwards": counts[1],
            "complete_background_fields": plan["background_field_count"],
            "all91_restoration_and_backbone_tensors_unchanged": True,
            "target_or_reference_arrays_loaded": 0,
            "seconds": time.monotonic() - began,
            "scope": "All whole-context A/B fields close before correction. Actual NN arguments invariant to withheld NaNs, no full-input parent/GT/reference feature. Existing cache fields adopted only with exact source/argument/mask/checkpoint configuration checks.",
        },
    )


def predict(root):
    import psutil

    from demosaic.experiments.evaluation.withheld import stratified_split
    from demosaic.experiments.runtime import owner_identity
    from demosaic.local_validated_waves import LocalWaveConfig, restore_local_waves
    from demosaic.neural_nuisance import WithheldBackground, restore_neural_nuisance
    from demosaic.prediction_archive import fingerprint

    plan = read_json(root / "plan.json")
    verify_plan(plan)
    assert reference(__file__) == plan["script"] and "torch" not in sys.modules
    cache = read_json(root / "backgrounds-collection.json")
    assert cache["plan"] == reference(root / "plan.json")
    assert (
        len(cache["rows"]) == len(plan["rows"])
        and cache["background_configuration"] == plan["background_configuration"]
    )
    by_id = {r["id"]: r for r in cache["rows"]}
    config = LocalWaveConfig(**plan["geometry_config"])
    (root / "predict.claim").open("x").close()
    write_json(root / "owner.json", owner_identity())
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[-2:])
    output = root / "predictions"
    output.mkdir()
    records = []
    controls = []
    began = time.monotonic()
    for row in plan["rows"]:
        if (
            psutil.virtual_memory().available < plan["minimum_runtime_RAM_GiB"] * 2**30
            or shutil.disk_usage(root).free < plan["minimum_disk_GiB"] * 2**30
        ):
            raise RuntimeError("CPU runtime reserve unavailable")
        if time.monotonic() - began > plan["maximum_stage_seconds"]:
            raise TimeoutError("CPU correction deadline reached")
        data = input_arrays(row)
        raw = raw_frame(data)
        record = by_id[row["id"]]
        assert (
            record["input_fingerprints"] == {k: fingerprint(v) for k, v in data.items()}
            and record["noise"] == row["noise"]
        )
        mask = fields = None
        if not record["identity_zero_noise"]:
            mask = np.load(checked(record["mask_A"]))
            np.testing.assert_array_equal(mask, stratified_split(raw.shape, config.split_seed))
            for fold, m in enumerate([mask, ~mask]):
                args = background_arguments(raw, m, data, row["noise"])
                assert {k: fingerprint(v) for k, v in args.items()} == record[
                    "argument_fingerprints"
                ][fold]
            fields = tuple(
                WithheldBackground(np.load(checked(item)), m)
                for item, m in zip(record["fields"], [mask, ~mask], strict=True)
            )
        parent = np.load(checked(row["parent"]))[row["sample"]]
        values, aux = restore_neural_nuisance(
            parent,
            data["packed"],
            data["colors"],
            fields,
            shot=row["noise"]["shot"],
            read=row["noise"]["read"],
            thresholds=tuple(plan["thresholds"]),
            config=config,
            reselect_frequencies=not plan.get("fixed_analytic_frequencies", False),
        )
        if row["id"] in plan["standalone_H1_checks"]:
            expected, _ = restore_local_waves(
                parent,
                data["packed"],
                data["colors"],
                shot=row["noise"]["shot"],
                read=row["noise"]["read"],
                thresholds=tuple(plan["thresholds"]),
                config=config,
                discovery_mask=mask,
            )
            for (mode, t), value in expected.items():
                np.testing.assert_array_equal(value, values["H1-" + mode, t])
            controls.append({"id": row["id"], "all6_H1_outputs_byte_exact_values": True})
        predictions = {}
        for (mode, t), value in values.items():
            assert (
                value.shape == parent.shape
                and value.dtype == parent.dtype
                and np.isfinite(value).all()
            )
            name = f"{mode}-t{t:g}"
            path = output / f"{row['id']}-{name}.npy"
            with path.open("xb") as f:
                np.save(f, value, allow_pickle=False)
            predictions[name] = reference(path)
            if aux["identity_zero_noise"]:
                np.testing.assert_array_equal(value, parent)
        result = {
            "id": row["id"],
            "predictions": predictions,
            "parent_values": fingerprint(parent),
            "packed_values": fingerprint(data["packed"]),
            "colors_values": fingerprint(data["colors"]),
            "background_receipt": reference(root / "backgrounds" / (row["id"] + "-receipt.json")),
            "aux": aux,
        }
        write_json(output / (row["id"] + "-receipt.json"), result)
        records.append(result)
        write_json(
            root / "progress.json",
            {
                "owner": owner_identity(),
                "completed_cases": len(records),
                "expected_cases": len(plan["rows"]),
                "last_case": row["id"],
                "seconds": time.monotonic() - began,
            },
            replace=True,
        )
        print(
            "correction",
            len(records),
            "of",
            len(plan["rows"]),
            row["id"],
            aux["patches"],
            flush=True,
        )
    assert len(controls) == 2 and "torch" not in sys.modules
    verify_plan(plan)
    write_json(
        root / "standalone-controls.json",
        {
            "cases": controls,
            "scope": "Two full-context synthetic/real controls vs standalone analytic H1 under the same global mask; no old per-tile-mask equality claimed. Zero neural replay.",
        },
    )
    write_json(
        root / "collection.json",
        {
            "plan": reference(root / "plan.json"),
            "model": plan["model"],
            "backgrounds": reference(root / "backgrounds-collection.json"),
            "rows": records,
            "target_or_reference_arrays_loaded": 0,
            "new_neural_forwards": 0,
            "Torch_imported": False,
            "elapsed_seconds": time.monotonic() - began,
            "status": "all48-global-split-neural-nuisance-corrections-closed-before-GT",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "backgrounds", "predict", "score"))
    parser.add_argument("root", type=Path)
    parser.add_argument("--background-cache", type=Path)
    parser.add_argument("--fixed-analytic-frequencies", action="store_true")
    args = parser.parse_args()
    if args.mode == "prepare":
        print(
            prepare(
                args.root.resolve(),
                args.background_cache.resolve() if args.background_cache else None,
                fixed_analytic_frequencies=args.fixed_analytic_frequencies,
            )
        )
    elif args.mode == "score":
        from pilot_phase_aggregation import score

        score(args.root.resolve())
    else:
        {"backgrounds": backgrounds, "predict": predict}[args.mode](args.root.resolve())
