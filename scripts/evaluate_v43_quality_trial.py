"""Freeze and serially evaluate completed matched V43 quality-training endpoints."""

import argparse
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import psutil
from recover_v43_quality_trial import (
    headroom,
    resource_snapshot,
    signal_owned_group,
    stop_owned_child,
)
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import DINO_SHA, live, resources

REPO = Path(__file__).resolve().parents[1]
PANEL = Path("/mnt/external/demosaic/evaluation/manifests/common-8192-44732-val-v1.jsonl")
CAMERAS = {
    "known": Path(
        "/mnt/external/demosaic/evaluation/paired-raw-development-prepared-v1/manifest.json"
    ),
    "unseen": Path(
        "/mnt/external/demosaic/evaluation/paired-unseen-development-prepared-v1/manifest.json"
    ),
}
RAWNIND = Path("/mnt/external/demosaic/references/rawnind")
COLOR = Path("/mnt/external/demosaic/evaluation/prospective-color-grid-20261017-v1/plan.json")


def prepare(
    training_root,
    root,
    *,
    cpu_proof=False,
    artifact_root=None,
    palette=False,
    adc_training=False,
    source_repository=None,
):
    import yaml

    helper_repository = REPO if source_repository is None else Path(source_repository).resolve()
    assert helper_repository == REPO or helper_repository.is_relative_to(REPO / ".cache")
    assert os.path.ismount("/mnt/external")
    status_path = training_root / "status.json"
    status, training = read(status_path), read(training_root / "plan.json")
    assert sum((palette, cpu_proof, adc_training)) <= 1
    assert status["status"] == (
        "completed-matched-V95-palette-training-awaiting-full-quality-and-native-review"
        if palette
        else "completed-matched-V95-ADC-training-awaiting-full-quality-and-native-review"
        if adc_training
        else "completed-discarded-CPU-launcher-proof"
        if cpu_proof
        else "completed-matched-V43-training-awaiting-full-evaluation-and-native-review"
    )
    assert not live(status["controller"]) and not live(status["child"])
    guard(training)
    assert status["plan"] == ref(training_root / "plan.json")
    inputs = [ref(status_path), ref(training_root / "plan.json"), training["parent"]]
    if palette or adc_training:
        original_ref = training["original_training_plan"]
        assert ref(original_ref["path"]) == original_ref
        original = read(original_ref["path"])
        guard(original)
        inputs.append(original_ref)
        checkpoints = [
            {"arm": "V43", **original["parent"], "expected_lineage": {"step": 2000}},
            {
                "arm": "V95",
                **training["parent"],
                "expected_lineage": {
                    "step": 20000,
                    "initialized_from": {**original["parent"], "step": 2000},
                },
            },
        ]
        inputs.append(original["parent"])
        assert training["arms"] == (["V98", "V99"] if adc_training else ["V96", "V97"])
        assert training["planned_updates"] == 4000
        arms = training["arms"]
    else:
        checkpoints = [{"arm": "V43", **training["parent"]}]
        arms = ("V93", "V94", "V95")
    for arm in arms:
        item = status["completed"][("CPU-" if cpu_proof else "train-") + arm]
        assert ref(item["path"]) == item
        result = read(item["path"])
        assert not live(result["owner"]) and result["engineering_only"] is cpu_proof
        assert result["plan"] == ref(training_root / "plan.json")
        assert ref(result["checkpoint"]["path"]) == result["checkpoint"]
        inputs += [item, result["checkpoint"]]
        record = {"arm": arm, **result["checkpoint"]}
        if palette or adc_training:
            record["expected_lineage"] = {
                "step": 4000,
                "initialized_from": {**training["parent"], "step": 20000},
            }
        if adc_training:
            audit_path = training_root / f"independent-{arm}-training-audit-v1.json"
            audit = read(audit_path)
            assert (
                audit["status"]
                == "completed-matched-V43-arm-independent-saved-state-and-trace-audit-passed"
            )
            assert audit["plan"] == ref(training_root / "plan.json")
            assert audit["primary_final_EMA_checkpoint"] == result["checkpoint"]
            inputs.append(ref(audit_path))
            record["expected_adc_projection"] = True
        checkpoints.append(record)
    reference_witnesses = {}
    if palette or adc_training:
        review_path = REPO / "docs/results/v43-curated-original20k-complete-review-v1.json"
        review = read(review_path)
        previous = read(review["plan"]["path"])
        assert ref(review["plan"]["path"]) == review["plan"]
        assert [r["arm"] for r in previous["checkpoints"]] == ["V43", "V93", "V94", "V95"]
        assert [r["sha256"] for r in checkpoints[:2]] == [
            previous["checkpoints"][i]["sha256"] for i in (0, 3)
        ]
        inputs += [ref(review_path), review["plan"]]
        for stage, panel in review["panels"].items():
            witness = panel["result"]
            assert ref(witness["path"]) == witness
            result = read(witness["path"])
            assert result["plan"] == review["plan"] and not live(result["owner"])
            assert result["weights_DINO_config_parameter_ids_RNG_and_inputs_preserved"]
            reference_witnesses[stage] = witness
            inputs.append(witness)
    root = root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    if artifact_root is None:
        assert cpu_proof, "Production evaluation requires an external artifact namespace"
        artifact_root = work / "evaluation"
    else:
        artifact_root = Path(artifact_root).resolve()
        assert artifact_root.is_relative_to(Path("/mnt/external/demosaic"))
        artifact_root.mkdir(parents=True, exist_ok=False)
        owner = artifact_root / "artifact-owner.json"
        save(owner, {"plan_root": str(root), "scope": "Matched V43 quality evaluation only"})
        inputs.append(ref(owner))
    if adc_training:
        from export_adc_cfa_projection import export

        for source in (Path(training["work"]) / "src/demosaic").glob("*.py"):
            assert (
                source.read_bytes()
                == (helper_repository / "src/demosaic" / source.name).read_bytes()
            )
        control = next(c for c in checkpoints if c["arm"] == "V98")
        original_control = {k: control[k] for k in ("path", "sha256")}
        exported = export(
            control["path"],
            artifact_root / "V98-projected-control",
            control["sha256"],
            preserve_training_lineage=True,
        )
        control.update(
            path=exported["export"],
            sha256=exported["export_sha256"],
            training_checkpoint=original_control,
        )
        inputs += [
            ref(exported["export"]),
            ref(artifact_root / "V98-projected-control/receipt.json"),
            ref(helper_repository / "scripts/export_adc_cfa_projection.py"),
        ]
    trained = Path(training["work"])
    files = [*trained.glob("src/demosaic/*.py")]
    files += [trained / p for p in ("pyproject.toml", "uv.lock", "configs/evaluation.yaml")]
    files += [
        helper_repository / "scripts" / name
        for name in (
            "evaluate_v43_quality_trial.py",
            "recover_v43_quality_trial.py",
            "train_v43_quality_trial.py",
            "train_directional_bank_trial.py",
            "profile_raw_kernel_inference.py",
            "audit_fresh_dino_statistics.py",
            "evaluate_texture_candidates.py",
            "diagnose_texture_response.py",
            "report_raw_pair.py",
            "evaluate_color_grid_cuda.py",
            "prepare_color_grid.py",
            "audit_colored_flats.py",
        )
    ]
    if adc_training:
        files.append(helper_repository / "scripts/export_adc_cfa_projection.py")
    for source in files:
        relative = (
            source.relative_to(trained)
            if source.is_relative_to(trained)
            else source.relative_to(helper_repository)
        )
        target = work / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    protocol = yaml.safe_load((work / "configs/evaluation.yaml").read_text())
    assert len(protocol["conditions"]) == 7 and len(protocol["patterns"]) == 4
    if cpu_proof:
        protocol["conditions"] = [
            c for c in protocol["conditions"] if c["name"] in ("adc-only", "iso12800-prior")
        ]
        protocol["patterns"] = ["RGGB", "BGGR"]
        (work / "configs/engineering-evaluation.yaml").write_text(yaml.safe_dump(protocol))
    rows = [
        r
        for r in (json.loads(line) for line in PANEL.read_text().splitlines())
        if r["split"] == "val"
    ]
    assert len(rows) == 427
    inputs.append(ref(PANEL))
    for row in rows[:2] if cpu_proof else rows:
        path = Path(row["cache"])
        path = path if path.is_absolute() else PANEL.parent / path
        item = ref(path)
        assert item["sha256"] == row["cache_sha256"]
        inputs.append(item)
    gfx = {}
    if not cpu_proof:
        for key, path in CAMERAS.items():
            inputs.append(ref(path))
            data = read(path)
            assert len({c["scene"] for c in data["cases"]}) == (4 if key == "known" else 5)
            assert sum(len(c["crops"]) for c in data["cases"]) == (72 if key == "known" else 90)
            for case in data["cases"]:
                for crop in case["crops"]:
                    item = ref(path.parent / crop["path"])
                    assert item["sha256"] == crop["sha256"]
                    inputs.append(item)
        for name in ("utnet2-bayer.pt", "raw_denoiser.py", "LICENSE", "provenance.json"):
            inputs.append(ref(RAWNIND / name))
        inputs.append(ref(COLOR))
        for case in read(COLOR)["cases"]:
            item = ref(case["arrays"])
            assert item["sha256"] == case["sha256"]
            inputs.append(item)
        for key, name in (
            ("gfx", "gfx-qualitative-20231231.json"),
            ("gfx-highlights", "gfx-qualitative-20231231-highlights.json"),
        ):
            original = REPO / "configs" / name
            selected = read(original)
            inputs.append(ref(original))
            for role in ("noisy", "reference"):
                path = (REPO / selected[role]).resolve()
                assert path.is_relative_to(REPO / ".cache/gfx-qualitative-20231231")
                inputs.append(ref(path))
                selected[role] = str(path)
            destination = work / "configs" / name
            save(destination, selected)
            gfx[key] = str(destination)
    # Avoid repeated whole-file verification of identical inputs in one guard.
    inputs = list({(r["path"], r["sha256"]): r for r in inputs}.values())
    plan = {
        "root": str(root),
        "work": str(work),
        "artifact_root": str(artifact_root),
        "training_status": ref(status_path),
        "training_plan": ref(training_root / "plan.json"),
        "checkpoints": checkpoints,
        "reference_witnesses": reference_witnesses,
        "cpu_proof": cpu_proof,
        "stages": ["photo"]
        if cpu_proof
        else ["photo", "known", "unseen", "texture", "color", "gfx", "gfx-highlights"],
        "photo_manifest": ref(PANEL),
        "camera_manifests": {k: ref(p) for k, p in CAMERAS.items()} if not cpu_proof else {},
        "rawnind": str(RAWNIND),
        "color": str(COLOR),
        "gfx": gfx,
        "size": 176 if cpu_proof else 256,
        "batch_size": 1 if cpu_proof else 4,
        "photo_count": 2 if cpu_proof else 427,
        "synthetic_count": 1 if cpu_proof else 16,
        "photo_ids": [r["id"] for r in (rows[:2] if cpu_proof else rows)],
        "protocol": str(
            work / "configs" / ("engineering-evaluation.yaml" if cpu_proof else "evaluation.yaml")
        ),
        "precision": "float32",
        "DINO_SHA256": DINO_SHA,
        "disk_reserves": {
            "root_reserve_gib": 64,
            "external_reserve_gib": 500 if cpu_proof else 384,
        },
        "python": training["python"],
        "cache_environment": training["cache_environment"],
        "stable_seconds": 2 if cpu_proof else 60,
        "wait_seconds": 7200,
        "stage_timeout_seconds": 900 if cpu_proof else 43200,
        "external_device": Path("/mnt/external").stat().st_dev,
        "resource_policy": "Record actual RAM/free-space/mount readings every2s. Active RAM floor24GiB; disk-only shortages suspend the owned worker and resume the same PID after original48GiB/disk thresholds are stable. Disk wait bounded7200s; stage wall-time bound includes suspension. No automatic retry or numerical change.",
        "inputs": inputs,
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "scope": "Discarded CPU/native176/B1 reporting-launcher integration on2 photos/1 procedural source,2 conditions/2CFAs; not quality, CUDA or final curation evidence."
        if cpu_proof
        else (
            "Fixed final4000-stage V96/V97 EMAs vs parent V95 final20k and original V43 step2000. Each checkpoint has explicit exact step/initializer lineage. "
            if palette
            else "Fixed final4000 V98/V99 EMAs under common projected inference, versus original V43/V95 policies. V98 projection is an inference-only exact-EMA export with retained training lineage; V99 trained through projection. "
            if adc_training
            else "Fixed final20k EMAs vs original V43. "
        )
        + "Fresh IEEE FP32/channels-last observations and metrics. Full427-photo/16-procedural,7-condition/4-CFA suite, known4/unseen5 real development scenes, carrier/flat/color diagnostics and standing GFX plus highlights. RawNIND global/per-channel input-only gains included in photo/real/GFX. Declared checkpoint policies only, no additional output correction, model selection, speed claim or automatic promotion; independent numeric/native review required.",
    }
    if adc_training:
        gfx_conditioning = {}
        for stage in ("gfx", "gfx-highlights"):
            witness = read(reference_witnesses[stage]["path"])
            previous_report = witness["report"]
            assert ref(previous_report["path"]) == previous_report
            gfx_conditioning[stage] = read(previous_report["path"])["conditioning"]
            inputs.append(previous_report)
        plan["ADC_fidelity_observations_per_projected_model"] = expected_adc_coverage(
            protocol,
            plan["photo_count"] + plan["synthetic_count"],
            read(COLOR)["cases"],
            {stage: read(path)["cases"] for stage, path in CAMERAS.items()},
            gfx_conditioning,
        )
        plan["ADC_valid_sample_error_limit"] = 1e-6
    save(root / "plan.json", plan)
    guard(plan)
    print(ref(root / "plan.json"))


def audit_triplets(output, crops):
    import numpy as np
    from PIL import Image

    common, groups, count = {}, {}, 0
    for crop in crops:
        path = output / crop["image"]
        assert ref(path)["sha256"] == crop["png_sha256"]
        with Image.open(path) as im:
            pixels = np.asarray(im.convert("RGB"))
        panels = []
        for panel in crop["panels"]:
            x, y, w, h = panel["png_xywh"]
            assert w == h == 160
            panels.append(pixels[y : y + h, x : x + w].copy())
        assert len(panels) == 3
        # Exact crop selection/reference/display metadata remain in the report.
        if "source_id" in crop:
            key = crop["source_id"]
        elif "prepared_crop" in crop:
            key = crop["prepared_crop"]["id"]
        elif "region" in crop:
            key = crop["region"]["name"]
        else:
            case = crop["case"]
            key = json.dumps([case["id"], case["pattern"], case["condition"]], sort_keys=True)
        groups[key] = groups.get(key, 0) + 1
        if key in common:
            assert np.array_equal(common[key][0], panels[0])
            assert np.array_equal(common[key][1], panels[2])
        else:
            common[key] = panels[0], panels[2]
        count += 1
    assert count >= 8 and min(groups.values()) >= 4
    return {
        "native160_triplets": count,
        "shared_source_groups": len(groups),
        "common_noisy_and_reference_pixels_exact": True,
    }


def check_reference_witnesses(invariants, previous):
    """Check fresh V43/V95 state, counts and sampled inputs against the reviewed run."""
    assert len(invariants) == len(previous) == 4
    counts = {}
    for name, current_index, previous_index in (("V43", 0, 0), ("V95", 1, 3)):
        actual, expected = invariants[current_index], previous[previous_index]
        assert actual == expected, name
        counts[name] = {
            "model_SHA256": actual["model_SHA256"],
            "sampled_input_hashes_exact_previous": len(
                actual["sampled_input_hashes_before_after_exact"]
            ),
            "forwards": actual["forwards"],
            "observations": actual["observations"],
        }
    return counts


def check_joint_model_config(actual, reference, *, adc_projection=False):
    """Permit the declared ADC policy only; all learned architecture fields match."""
    assert type(adc_projection) is bool
    expected = dict(reference)
    if adc_projection:
        expected["adc_cfa_projection"] = True
    assert json.dumps(actual, sort_keys=True) == json.dumps(expected, sort_keys=True)


def adc_profile_indices(profiles, batch_size):
    """Use explicit profile families, independently of observed variance values."""
    assert type(batch_size) is int and batch_size > 0
    assert profiles is not None and len(profiles) in (1, batch_size)
    assert all(len(p) == 3 and type(p[2]) is bool for p in profiles)
    profiles = profiles * batch_size if len(profiles) == 1 else profiles
    return [i for i, (_, _, stochastic) in enumerate(profiles) if not stochastic]


def expected_adc_coverage(protocol, photo_sources, color_cases, camera_cases, gfx_conditioning):
    """Derive coverage from explicit priors, not ISO names or observed noise."""

    def is_adc(condition):
        assert all(math.isfinite(condition[k]) and condition[k] >= 0 for k in ("shot", "read"))
        return condition["shot"] == condition["read"] == 0

    assert set(protocol["patterns"]) == {"RGGB", "BGGR", "GRBG", "GBRG"}
    assert len(protocol["patterns"]) == 4
    assert sum(is_adc(c) for c in protocol["conditions"]) == 1
    assert set(camera_cases) == {"known", "unseen"}
    assert set(gfx_conditioning) == {"gfx", "gfx-highlights"}
    result = {
        "photo": photo_sources * 4,
        "texture": 14 * 4 * 4,
        "color": sum(is_adc(c["condition"]) for c in color_cases),
    }
    result.update(
        {
            stage: sum(len(c["crops"]) for c in cases if is_adc(c["conditioning"]))
            for stage, cases in camera_cases.items()
        }
    )
    result.update(
        {
            stage: (4 if stage == "gfx" else 2) * int(is_adc(condition))
            for stage, condition in gfx_conditioning.items()
        }
    )
    return result


def adc_sample_fidelity(prediction, packed, colors):
    """Read valid sensor-channel errors without modifying a prediction or RNG."""
    import torch

    from demosaic.cfa import mosaic

    assert prediction.dtype == packed.dtype == torch.float32
    assert torch.isfinite(prediction).all() and torch.isfinite(packed).all()
    sampled = mosaic(prediction, colors)
    assert sampled.shape == packed.shape
    valid = (packed > 1 / 65535) & (packed < 1 - 1 / 65535)
    errors = (sampled - packed).abs()[valid]
    return {
        "observations": len(packed),
        "valid_CFA_values": errors.numel(),
        "maximum_absolute_error_sensor_units": float(errors.max()) if errors.numel() else None,
    }


def worker(plan_path, stage):
    import random

    import torch
    from profile_raw_kernel_inference import model_hash

    from demosaic.train import batch_fingerprint

    plan = read(plan_path)
    guard(plan)
    assert stage in plan["stages"]
    root, output = Path(plan["root"]), Path(plan["artifact_root"]) / stage
    (root / (stage + ".claim")).open("x").close()
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    assert resources(root, 32, **plan["disk_reserves"])
    device = "cpu" if plan["cpu_proof"] else "cuda"
    if device == "cpu":
        assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not torch.cuda.is_initialized()
    else:
        torch.cuda.set_per_process_memory_fraction(
            min(
                torch.cuda.get_per_process_memory_fraction(),
                24 * 2**30 / torch.cuda.get_device_properties(0).total_memory,
            )
        )
    torch.set_num_threads(2 if plan["cpu_proof"] else 4)
    models, rng = [], {}

    def strict_float32():
        torch.set_float32_matmul_precision("highest")
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False

    def observe(loader):
        def loaded(*args, **kwargs):
            python_rng = random.getstate()
            with torch.random.fork_rng(devices=[0] if device == "cuda" else []):
                model, state = loader(*args, **kwargs)
            random.setstate(python_rng)
            strict_float32()
            match = next(r for r in plan["checkpoints"] if r["sha256"] == state["loaded_sha256"])
            expected_step = (
                2000
                if state["loaded_sha256"] == plan["checkpoints"][0]["sha256"]
                else (24 if plan["cpu_proof"] else 20000)
            )
            assert state["step"] == match.get("expected_lineage", {}).get("step", expected_step)
            if "initialized_from" in match.get("expected_lineage", {}):
                assert (
                    state["config"].get("initialized_from")
                    == match["expected_lineage"]["initialized_from"]
                )
            assert model_hash(model.context.backbone) == plan["DINO_SHA256"]
            record = {
                "model": model,
                "before": model_hash(model),
                "config": model.config.to_dict(),
                "ids": [id(p) for p in model.parameters()],
                "forwards": 0,
                "observations": 0,
                "dino": 0,
                "sampled_inputs": [],
            }
            if models:
                check_joint_model_config(
                    record["config"],
                    models[0]["config"],
                    adc_projection=match.get("expected_adc_projection", False),
                )
            if match.get("expected_adc_projection", False):
                assert stage in plan["ADC_fidelity_observations_per_projected_model"]
                assert plan["ADC_valid_sample_error_limit"] == 1e-6
                record["ADC_fidelity"] = {
                    "observations": 0,
                    "valid_CFA_values": 0,
                    "maximum_absolute_error_sensor_units": None,
                }
            models.append(record)

            def before(module, args, kwargs):
                assert len(args) == 5 and not kwargs and not module.training
                assert all(isinstance(x, torch.Tensor) and x.device.type == device for x in args)
                assert (
                    not torch.backends.cuda.matmul.allow_tf32
                    and not torch.backends.cudnn.allow_tf32
                )
                assert torch.get_float32_matmul_precision() == "highest"
                if not rng:
                    rng.update(
                        torch=torch.get_rng_state(),
                        python=random.getstate(),
                        cuda=torch.cuda.get_rng_state_all() if device == "cuda" else [],
                    )
                record["forwards"] += 1
                record["observations"] += len(args[0])
                record["pending_input_hash"] = (
                    batch_fingerprint(
                        dict(
                            zip(("packed", "variance", "colors", "wb", "matrix"), args, strict=True)
                        )
                    )
                    if record["forwards"] <= 2 or record["forwards"] % 256 == 0
                    else None
                )

            def after(module, args, value):
                assert value.dtype == torch.float32 and torch.isfinite(value).all()
                if "ADC_fidelity" in record:
                    selected = adc_profile_indices(
                        module.pretrained_rgb._noise_profiles, len(args[0])
                    )
                    if selected:
                        colors = args[2] if args[2].ndim == 1 else args[2][selected]
                        measured = adc_sample_fidelity(value[selected], args[0][selected], colors)
                        maximum = measured["maximum_absolute_error_sensor_units"]
                        if maximum is not None:
                            assert maximum <= plan["ADC_valid_sample_error_limit"]
                        aggregate = record["ADC_fidelity"]
                        aggregate["observations"] += measured["observations"]
                        aggregate["valid_CFA_values"] += measured["valid_CFA_values"]
                        if maximum is not None:
                            old = aggregate["maximum_absolute_error_sensor_units"]
                            aggregate["maximum_absolute_error_sensor_units"] = (
                                maximum if old is None else max(old, maximum)
                            )
                if record["pending_input_hash"] is not None:
                    assert record["pending_input_hash"] == batch_fingerprint(
                        dict(
                            zip(("packed", "variance", "colors", "wb", "matrix"), args, strict=True)
                        )
                    )
                    record["sampled_inputs"].append(
                        {"forward": record["forwards"], "sha256": record["pending_input_hash"]}
                    )

            def dino(*_):
                record["dino"] += 1

            model.register_forward_pre_hook(before, with_kwargs=True)
            model.register_forward_hook(after)
            model.context.backbone.register_forward_hook(dino)
            return model, state

        return loaded

    checkpoints = [Path(r["path"]) for r in plan["checkpoints"]]
    strict_float32()
    arithmetic = None
    if stage == "photo":
        from audit_fresh_dino_statistics import audit_photo, compare_summary

        from demosaic import suite

        suite.load_checkpoint = observe(suite.load_checkpoint)
        suite.run_suite(
            checkpoints,
            Path(plan["photo_manifest"]["path"]),
            output,
            Path(plan["protocol"]),
            device=device,
            precision="float32",
            patch_size=plan["size"],
            batch_size=plan["batch_size"],
            limit=plan["photo_count"],
            synthetic_count=plan["synthetic_count"],
            rawnind=None if plan["cpu_proof"] else Path(plan["rawnind"]),
        )
        report = read(output / "summary.json")
        records = [
            json.loads(line) for line in (output / "per-image.jsonl").read_text().splitlines()
        ]
        if plan["cpu_proof"]:
            expected = {
                (method, kind, identity, condition, pattern)
                for method in {r["model"] for r in records}
                for kind, ids in (("photo", plan["photo_ids"]), ("synthetic", ["synthetic-0"]))
                for identity in ids
                for condition in ("adc-only", "iso12800-prior")
                for pattern in ("RGGB", "BGGR")
            }
            actual = [
                (r["model"], r["kind"], r["id"], r["condition"], r["pattern"]) for r in records
            ]
            assert (
                len(records) == len(actual) == len(set(actual)) == len(expected) == 84
                and set(actual) == expected
            )
            arithmetic = compare_summary(records, report)
        else:
            arithmetic = audit_photo(output, expected_methods=9)
        expected_each = math.ceil(
            (plan["photo_count"] + plan["synthetic_count"]) / plan["batch_size"]
        ) * (4 if plan["cpu_proof"] else 28)
        assert [r["forwards"] for r in models] == [expected_each] * 4
    elif stage in CAMERAS:
        from audit_fresh_dino_statistics import audit_real

        from demosaic import real_suite

        real_suite.load_checkpoint = observe(real_suite.load_checkpoint)
        real_suite.evaluate_pairs(
            checkpoints,
            Path(plan["camera_manifests"][stage]["path"]),
            output,
            rawnind=Path(plan["rawnind"]),
            precision="float32",
            batch_size=4,
            device=device,
        )
        report = read(output / "summary.json")
        arithmetic = audit_real(
            output,
            4 if stage == "known" else 5,
            8 if stage == "known" else 10,
            72 if stage == "known" else 90,
            expected_methods=9,
        )
    elif stage == "texture":
        import evaluate_texture_candidates as texture

        texture.load_checkpoint = observe(texture.load_checkpoint)
        texture.main(checkpoints, output, device=device, precision="float32")
        report = read(output / "summary.json")
        assert [r["observations"] for r in models] == [448] * 4
    elif stage == "color":
        import evaluate_color_grid_cuda as color

        color.load_checkpoint = observe(color.load_checkpoint)
        records = [{**r, "kind": "joint-checkpoint"} for r in plan["checkpoints"]]
        color.evaluate_records(
            Path(plan["color"]),
            Path(plan["training_status"]["path"]),
            output,
            records,
            plan["checkpoints"][0]["sha256"],
            expected_step=20000,
            precision="float32",
        )
        report = read(output / "report.json")
        assert [r["forwards"] for r in models] == [1176] * 4
    else:
        import report_raw_pair as gfx

        gfx.load_checkpoint = observe(gfx.load_checkpoint)
        sys.argv = [
            str(gfx.__file__),
            plan["gfx"][stage],
            *map(str, checkpoints),
            "--output",
            str(output),
            "--rawnind",
            plan["rawnind"],
            "--rawnind-gain-modes",
            "cfa-ls",
            "cfa-channel",
            "--device",
            device,
            "--precision",
            "float32",
        ]
        gfx.main()
        report = read(output / "report.json")
        assert report["quality_scores"] is None and not report["full_frames"]
    assert len(models) == 4 and rng
    invariants = []
    for record in models:
        model = record["model"]
        assert model_hash(model) == record["before"]
        assert model_hash(model.context.backbone) == plan["DINO_SHA256"]
        assert record["config"] == model.config.to_dict() and record["ids"] == [
            id(p) for p in model.parameters()
        ]
        assert record["dino"] == record["forwards"] > 0
        invariants.append(
            {
                "model_SHA256": record["before"],
                "forwards": record["forwards"],
                "DINO_calls": record["dino"],
                "observations": record["observations"],
                "sampled_input_hashes_before_after_exact": record["sampled_inputs"],
            }
        )
    assert all(r["sampled_inputs"] == models[0]["sampled_inputs"] for r in models)
    assert torch.equal(rng["torch"], torch.get_rng_state()) and rng["python"] == random.getstate()
    if device == "cuda":
        assert all(
            torch.equal(a, b)
            for a, b in zip(rng["cuda"], torch.cuda.get_rng_state_all(), strict=True)
        )
    else:
        assert not torch.cuda.is_initialized()
    triplets = audit_triplets(output, report["native_crops"])
    witness = plan.get("reference_witnesses", {}).get(stage)
    witness_audit = None
    if witness is not None:
        assert ref(witness["path"]) == witness
        witness_audit = check_reference_witnesses(invariants, read(witness["path"])["invariants"])
    fidelity = []
    if "ADC_fidelity_observations_per_projected_model" in plan:
        expected = plan["ADC_fidelity_observations_per_projected_model"][stage]
        for index, record in enumerate(models):
            if "ADC_fidelity" not in record:
                continue
            measured = record["ADC_fidelity"]
            assert measured["observations"] == expected
            assert not expected or measured["valid_CFA_values"] > 0
            fidelity.append(
                {"model_index": index, "checkpoint": plan["checkpoints"][index], **measured}
            )
        assert len(fidelity) == 2
    guard(plan)
    save(
        root / (stage + "-result.json"),
        {
            "status": "completed-evaluation-stage-awaiting-native-review",
            "plan": ref(plan_path),
            "owner": owner,
            "stage": stage,
            "engineering_only": plan["cpu_proof"],
            "invariants": invariants,
            "weights_DINO_config_parameter_ids_RNG_and_inputs_preserved": True,
            "arithmetic": arithmetic,
            "triplets": triplets,
            "reviewed_reference_observation_witness": witness_audit,
            "report": ref(
                output
                / ("report.json" if stage in ("color", "gfx", "gfx-highlights") else "summary.json")
            ),
            "scope": plan["scope"],
            **({"ADC_sample_fidelity": fidelity} if fidelity else {}),
        },
    )


def monitor_child(child, owner, *, plan, observe, record, deadline, poll_seconds=2):
    """Keep an owned evaluation alive through bounded disk-only shortages."""
    while child.poll() is None:
        snapshot = observe()
        assert snapshot["RAM_available_bytes"] >= 24 * 2**30, snapshot
        if not headroom(snapshot, plan):
            signal_owned_group(owner, signal.SIGSTOP)
            record("paused-V43-evaluation-disk-reserve", resource_snapshot=snapshot)
            paused_at, stable = time.monotonic(), None
            while True:
                assert child.poll() is None, "Suspended evaluation worker exited"
                assert time.monotonic() < deadline, "Evaluation stage runtime bound"
                assert time.monotonic() - paused_at < plan["wait_seconds"], (
                    "Evaluation disk reserve wait bound"
                )
                current = observe()
                assert current["RAM_available_bytes"] >= 24 * 2**30, current
                stable = (
                    (time.monotonic() if stable is None else stable)
                    if headroom(current, plan, 48)
                    else None
                )
                if stable is not None and time.monotonic() - stable >= plan["stable_seconds"]:
                    guard(plan)
                    signal_owned_group(owner, signal.SIGCONT)
                    record(
                        "running-V43-quality-evaluation",
                        resumed_same_worker=True,
                        resource_snapshot=current,
                    )
                    break
                time.sleep(poll_seconds)
        assert time.monotonic() < deadline, "Evaluation stage runtime bound"
        time.sleep(poll_seconds)


def controller(plan_path):
    plan = read(plan_path)
    guard(plan)
    root, work = Path(plan["root"]), Path(plan["work"])
    (root / "controller.claim").open("x").close()
    state = {
        "plan": ref(plan_path),
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "completed": {},
    }
    child, identity = None, None
    last_snapshot = None

    def record(status, **extra):
        state.update(status=status, updated_unix=time.time(), **extra)
        save(root / "status.json", state)

    def observe():
        nonlocal last_snapshot
        last_snapshot = resource_snapshot(root)
        with (root / "resource-history.jsonl").open("a") as stream:
            stream.write(json.dumps(last_snapshot) + "\n")
        return last_snapshot

    try:
        for stage in plan["stages"]:
            guard(plan)
            record("waiting-for-evaluation-headroom", stage=stage)
            began, stable = time.monotonic(), None
            while True:
                assert time.monotonic() - began < plan["wait_seconds"]
                stable = (
                    (time.monotonic() if stable is None else stable)
                    if headroom(observe(), plan, 48)
                    else None
                )
                if stable is not None and time.monotonic() - stable >= plan["stable_seconds"]:
                    break
                time.sleep(2)
            env = dict(
                os.environ,
                PYTHONPATH=str(work / "src") + ":" + str(work / "scripts"),
                CUDA_VISIBLE_DEVICES="" if plan["cpu_proof"] else "0",
                HF_HUB_OFFLINE="1",
                TRANSFORMERS_OFFLINE="1",
                OMP_NUM_THREADS="2" if plan["cpu_proof"] else "4",
                OPENBLAS_NUM_THREADS="2",
                PYTHONDONTWRITEBYTECODE="1",
            )
            env.update(plan["cache_environment"])
            with (root / (stage + ".log")).open("xb") as log:
                child = subprocess.Popen(
                    [
                        plan["python"],
                        "-P",
                        str(work / "scripts/evaluate_v43_quality_trial.py"),
                        "worker",
                        str(plan_path),
                        "--stage",
                        stage,
                    ],
                    cwd=work,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                identity = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                record("running-V43-quality-evaluation", stage=stage, child=identity)
                deadline = time.monotonic() + plan["stage_timeout_seconds"]
                monitor_child(
                    child,
                    identity,
                    plan=plan,
                    observe=observe,
                    record=record,
                    deadline=deadline,
                )
                assert child.wait() == 0, (stage, child.returncode)
            result_path = root / (stage + "-result.json")
            result = read(result_path)
            assert result["owner"] == identity and result["plan"] == ref(plan_path)
            state["completed"][stage] = ref(result_path)
            record("completed-V43-evaluation-stage", stage=stage)
        guard(plan)
        record(
            "completed-CPU-reporting-launcher-proof-awaiting-actual-view"
            if plan["cpu_proof"]
            else "completed-V43-quality-panels-awaiting-independent-and-native-review"
        )
    except BaseException as error:
        if child is not None and child.poll() is None:
            stop_owned_child(child, identity)
        record(
            "failed-V43-evaluation-preserved-no-automatic-retry",
            error=repr(error),
            last_resource_snapshot=last_snapshot,
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "worker", "controller"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--cpu-proof", action="store_true")
    parser.add_argument("--palette", action="store_true")
    parser.add_argument("--adc-training", action="store_true")
    parser.add_argument("--source-repository", type=Path)
    parser.add_argument("--stage")
    args = parser.parse_args()
    if args.mode == "prepare":
        assert args.output
        prepare(
            args.path.resolve(),
            args.output,
            cpu_proof=args.cpu_proof,
            artifact_root=args.artifact_root,
            palette=args.palette,
            adc_training=args.adc_training,
            source_repository=args.source_repository,
        )
    elif args.mode == "worker":
        assert args.stage
        worker(args.path.resolve(), args.stage)
    else:
        controller(args.path.resolve())
