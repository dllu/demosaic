"""Inspect fixed native photo detail at three noise levels after full evaluation."""

import argparse
import copy
import json
import math
import os
import random
import shutil
import subprocess
import time
from pathlib import Path

import psutil
import yaml
from evaluate_v43_quality_trial import audit_triplets, monitor_child
from recover_v43_quality_trial import headroom, resource_snapshot, stop_owned_child
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import DINO_SHA, live

REPO = Path(__file__).resolve().parents[1]
CONDITIONS = ("adc-only", "iso100-prior", "iso12800-prior")
COMPLETE = "completed-V43-quality-panels-awaiting-independent-and-native-review"


def condition_protocols(protocol):
    """Keep the full suite's physical settings and select one condition/RGGB."""
    values = {c["name"]: c for c in protocol["conditions"]}
    if len(values) != len(protocol["conditions"]) or "RGGB" not in protocol["patterns"]:
        raise ValueError("Ambiguous conditions or missing RGGB")
    if not set(CONDITIONS) <= values.keys():
        raise ValueError("Missing a declared native-photo condition")
    result = {}
    for name in CONDITIONS:
        condition = values[name]
        if condition["exposure"] != 1 or any(
            not math.isfinite(condition[k]) or condition[k] < 0 for k in ("shot", "read")
        ):
            raise ValueError("Native detail requires finite unit-exposure sensor priors")
        if name == "adc-only" and (condition["shot"] != 0 or condition["read"] != 0):
            raise ValueError("ADC-only must have zero simulated shot/read noise")
        selected = copy.deepcopy(protocol)
        selected.update(patterns=["RGGB"], conditions=[copy.deepcopy(condition)])
        result[name] = selected
    return result


def dependency_ready(state, parent, *, is_live=live):
    """A completed parent still owns the GPU until both recorded owners exit."""
    if state["plan"] != parent["reference"]:
        raise ValueError("Dependency plan identity changed")
    alive = any(is_live(state[k]) for k in ("controller", "child") if state.get(k))
    if state["status"].startswith("failed"):
        raise RuntimeError("Full evaluation failed; no automatic diagnostic retry")
    if state["status"] == COMPLETE:
        if set(state["completed"]) != set(parent["stages"]):
            raise ValueError("Full evaluation lacks a declared stage")
        return not alive
    if not alive:
        raise RuntimeError("Dependency owners are missing before terminal completion")
    return False


def compare_high_noise_previews(current_path, previous_path):
    """Check the repeated high-noise native cells against the full suite."""
    import numpy as np
    from build_native_crop_board import identity, read_crop

    previous = {(r["source_id"], identity(r)): r for r in read(previous_path)["native_crops"]}
    differences = []
    for crop in read(current_path)["native_crops"]:
        old = previous[(crop["source_id"], identity(crop))]
        parts, settings, _ = read_crop(current_path, crop, "synthetic")
        old_parts, old_settings, _ = read_crop(previous_path, old, "synthetic")
        assert settings == old_settings
        assert np.array_equal(parts[0], old_parts[0]) and np.array_equal(parts[2], old_parts[2])
        difference = np.abs(parts[1].astype(np.int16) - old_parts[1].astype(np.int16))
        assert difference.max() <= 1
        differences.append(
            {
                "source_id": crop["source_id"],
                "model": identity(crop)[0],
                "maximum_RGB8_code_difference": int(difference.max()),
                "unequal_RGB8_values": int(np.count_nonzero(difference)),
            }
        )
    assert len(differences) == 12
    return {
        "noisy_and_GT_native_pixels_exact": True,
        "restored_RGB8_rounding_bound": 1,
        "cases": differences,
    }


def prepare(parent_path, root, artifact_root):
    parent = read(parent_path)
    guard(parent)
    assert not parent["cpu_proof"] and parent["precision"] == "float32"
    assert (
        parent["size"],
        parent["batch_size"],
        parent["photo_count"],
        parent["synthetic_count"],
    ) == (256, 4, 427, 16)
    assert [c["arm"] for c in parent["checkpoints"]] == ["V43", "V95", "V96", "V97"]
    assert len(parent["stages"]) == 7
    protocols = condition_protocols(yaml.safe_load(Path(parent["protocol"]).read_text()))
    rows = [
        row
        for row in (
            json.loads(line)
            for line in Path(parent["photo_manifest"]["path"]).read_text().splitlines()
        )
        if row["split"] == "val"
    ]
    assert len(rows) == 427 and len({r["id"] for r in rows[:4]}) == 4
    root, artifact_root = root.resolve(), artifact_root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    assert artifact_root.is_relative_to(Path("/mnt/external/demosaic"))
    assert os.path.ismount("/mnt/external")
    assert shutil.disk_usage(REPO).free >= 64 * 2**30
    assert shutil.disk_usage("/mnt/external").free >= 384 * 2**30
    root.mkdir(parents=True, exist_ok=False)
    artifact_root.mkdir(parents=True, exist_ok=False)
    marker = artifact_root / "artifact-owner.json"
    save(marker, {"plan_root": str(root), "scope": "Three-condition native photo diagnosis only"})
    work = root / "work"
    old_work = Path(parent["work"])
    for name, sha in parent["frozen_files"].items():
        source = Path(name)
        target = work / source.relative_to(old_work)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        assert ref(target)["sha256"] == sha
    for name in (
        "scripts/evaluate_v95_native_photo_conditions.py",
        "third_party/dinov3/LICENSE.md",
        "third_party/gaussian/Noise2VST-LICENSE",
        "third_party/gaussian/KAIR-LICENSE",
    ):
        target = work / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / name, target)
    selected_protocols = {}
    for name, value in protocols.items():
        target = work / "configs" / f"native-{name}.yaml"
        target.write_text(yaml.safe_dump(value, sort_keys=False))
        selected_protocols[name] = str(target)
    inputs = [ref(parent_path), parent["photo_manifest"], ref(parent["protocol"]), ref(marker)]
    inputs += [{k: c[k] for k in ("path", "sha256")} for c in parent["checkpoints"]]
    for row in rows[:4]:
        path = Path(row["cache"])
        if not path.is_absolute():
            path = Path(parent["photo_manifest"]["path"]).parent / path
        item = ref(path)
        assert item["sha256"] == row["cache_sha256"]
        inputs.append(item)
    for name in ("utnet2-bayer.pt", "raw_denoiser.py", "LICENSE", "provenance.json"):
        inputs.append(ref(Path(parent["rawnind"]) / name))
    plan = {
        "root": str(root),
        "work": str(work),
        "artifact_root": str(artifact_root),
        "parent": {
            "reference": ref(parent_path),
            "root": parent["root"],
            "stages": parent["stages"],
        },
        "checkpoints": parent["checkpoints"],
        "photo_manifest": parent["photo_manifest"],
        "source_ids": [r["id"] for r in rows[:4]],
        "protocols": selected_protocols,
        "rawnind": parent["rawnind"],
        "DINO_SHA256": DINO_SHA,
        "python": parent["python"],
        "cache_environment": parent["cache_environment"],
        "disk_reserves": {"root_reserve_gib": 64, "external_reserve_gib": 384},
        "external_device": Path("/mnt/external").stat().st_dev,
        "dependency_wait_seconds": 43200,
        "wait_seconds": 7200,
        "stable_seconds": 60,
        "worker_timeout_seconds": 3600,
        "inputs": inputs,
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "scope": "Secondary native detail diagnosis on the full suite's first4 sources, same four fixed checkpoints/numerical package, IEEEFP32/B4/native256, RGGB, ADC-only/ISO100/ISO12800. Each single-condition suite retains its first2 preselected native cases, all9 methods and unchanged physical settings. No GPU worker until all7 full-evaluation stages and their owners exit. Full suite remains primary; no training, source/checkpoint selection, output correction, speed or automatic promotion.",
    }
    save(root / "plan.json", plan)
    guard(plan)
    print(ref(root / "plan.json"))


def worker(plan_path):
    plan = read(plan_path)
    guard(plan)
    root = Path(plan["root"])
    bridge = read(root / "dependency-evidence.json")
    assert ref(bridge["parent_status"]["path"]) == bridge["parent_status"]
    parent_status = read(bridge["parent_status"]["path"])
    assert dependency_ready(parent_status, plan["parent"])
    assert bridge["photo_result"] == parent_status["completed"]["photo"]
    assert ref(bridge["photo_result"]["path"]) == bridge["photo_result"]
    parent_result = read(bridge["photo_result"]["path"])
    assert ref(parent_result["report"]["path"]) == parent_result["report"]
    reference = read(parent_result["report"]["path"])
    assert parent_result["plan"] == plan["parent"]["reference"]
    assert parent_result["weights_DINO_config_parameter_ids_RNG_and_inputs_preserved"]
    (root / "worker.claim").open("x").close()
    assert headroom(resource_snapshot(root), plan, 32)
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "0"

    import gc

    import torch
    from audit_fresh_dino_statistics import compare_summary
    from evaluate_color_grid_cuda import check_joint_lineage
    from profile_raw_kernel_inference import model_hash

    from demosaic import suite
    from demosaic.train import batch_fingerprint

    torch.set_num_threads(4)
    torch.cuda.set_per_process_memory_fraction(
        min(
            torch.cuda.get_per_process_memory_fraction(),
            24 * 2**30 / torch.cuda.get_device_properties(0).total_memory,
        )
    )

    def strict():
        torch.set_float32_matmul_precision("highest")
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False

    original_loader = suite.load_checkpoint
    results = {}
    for condition in CONDITIONS:
        guard(plan)
        models, rng = [], {}

        def loaded(*args, _models=models, _rng=rng, **kwargs):
            python_rng = random.getstate()
            with torch.random.fork_rng(devices=[0]):
                model, state = original_loader(*args, **kwargs)
            random.setstate(python_rng)
            strict()
            index = len(_models)
            checkpoint = plan["checkpoints"][index]
            assert state["loaded_sha256"] == checkpoint["sha256"]
            check_joint_lineage(
                state,
                checkpoint["sha256"],
                plan["checkpoints"][0]["sha256"],
                4000,
                lineage=checkpoint["expected_lineage"],
            )
            assert model_hash(model.context.backbone) == plan["DINO_SHA256"]
            record = {
                "model": model,
                "before": model_hash(model),
                "config": model.config.to_dict(),
                "ids": [id(p) for p in model.parameters()],
                "forwards": 0,
                "observations": 0,
                "DINO_calls": 0,
                "inputs": [],
            }
            assert record["before"] == parent_result["invariants"][index]["model_SHA256"]
            assert record["config"] == reference["models"][index]["effective_model_config"]
            _models.append(record)

            def before(module, args, kwargs):
                assert len(args) == 5 and not kwargs and not module.training
                assert all(isinstance(x, torch.Tensor) and x.device.type == "cuda" for x in args)
                assert len(args[0]) == 4 and torch.get_float32_matmul_precision() == "highest"
                assert (
                    not torch.backends.cuda.matmul.allow_tf32
                    and not torch.backends.cudnn.allow_tf32
                )
                if not _rng:
                    _rng.update(
                        torch=torch.get_rng_state(),
                        python=random.getstate(),
                        cuda=torch.cuda.get_rng_state_all(),
                    )
                record["forwards"] += 1
                record["observations"] += len(args[0])
                record["pending"] = batch_fingerprint(
                    dict(zip(("packed", "variance", "colors", "wb", "matrix"), args, strict=True))
                )

            def after(_module, args, prediction):
                assert prediction.dtype == torch.float32 and torch.isfinite(prediction).all()
                assert record["pending"] == batch_fingerprint(
                    dict(zip(("packed", "variance", "colors", "wb", "matrix"), args, strict=True))
                )
                record["inputs"].append(record.pop("pending"))

            def dino(*_):
                record["DINO_calls"] += 1

            model.register_forward_pre_hook(before, with_kwargs=True)
            model.register_forward_hook(after)
            model.context.backbone.register_forward_hook(dino)
            return model, state

        suite.load_checkpoint = loaded
        strict()
        output = Path(plan["artifact_root"]) / condition
        assert not output.exists()
        suite.run_suite(
            [Path(c["path"]) for c in plan["checkpoints"]],
            Path(plan["photo_manifest"]["path"]),
            output,
            Path(plan["protocols"][condition]),
            device="cuda",
            precision="float32",
            patch_size=256,
            batch_size=4,
            limit=4,
            synthetic_count=0,
            rawnind=Path(plan["rawnind"]),
        )
        report = read(output / "summary.json")
        rows = [json.loads(line) for line in (output / "per-image.jsonl").read_text().splitlines()]
        methods = {r["model"] for r in rows}
        expected = {
            (m, "photo", source, condition, "RGGB")
            for m in methods
            for source in plan["source_ids"]
        }
        actual = [(r["model"], r["kind"], r["id"], r["condition"], r["pattern"]) for r in rows]
        assert (
            len(methods) == 9
            and len(actual) == len(set(actual)) == len(expected) == 36
            and set(actual) == expected
        )
        arithmetic = compare_summary(rows, report)
        assert report["inference_source_sha256"] == reference["inference_source_sha256"]
        assert len(models) == 4 and rng
        invariants = []
        for index, record in enumerate(models):
            model = record["model"]
            assert (
                model_hash(model) == record["before"]
                and model_hash(model.context.backbone) == plan["DINO_SHA256"]
            )
            assert all(
                not p.requires_grad and p.grad is None for p in model.context.backbone.parameters()
            )
            assert (
                model.config.to_dict() == record["config"]
                and [id(p) for p in model.parameters()] == record["ids"]
            )
            assert record["forwards"] == record["DINO_calls"] == len(record["inputs"]) == 1
            assert record["observations"] == 4
            if condition == "adc-only":
                assert parent_result["invariants"][index][
                    "sampled_input_hashes_before_after_exact"
                ][0] == {"forward": 1, "sha256": record["inputs"][0]}
            invariants.append(
                {
                    "model_SHA256": record["before"],
                    "forwards": record["forwards"],
                    "DINO_calls": record["DINO_calls"],
                    "observations": record["observations"],
                    "physical_input_hashes_before_after_exact": record["inputs"],
                }
            )
        assert all(r["inputs"] == models[0]["inputs"] for r in models)
        assert (
            torch.equal(rng["torch"], torch.get_rng_state()) and rng["python"] == random.getstate()
        )
        assert all(
            torch.equal(a, b)
            for a, b in zip(rng["cuda"], torch.cuda.get_rng_state_all(), strict=True)
        )
        assert len(report["native_crops"]) == 12
        results[condition] = {
            "report": ref(output / "summary.json"),
            "invariants": invariants,
            "arithmetic": arithmetic,
            "triplets": audit_triplets(output, report["native_crops"]),
        }
        if condition == "iso12800-prior":
            results[condition]["full_suite_native_preview_witness"] = compare_high_noise_previews(
                output / "summary.json", Path(parent_result["report"]["path"])
            )
        suite.load_checkpoint = original_loader
        del loaded, model, models, record
        gc.collect()
    guard(plan)
    save(
        root / "worker-result.json",
        {
            "status": "completed-native-photo-conditions-awaiting-independent-and-actual-native-review",
            "plan": ref(plan_path),
            "dependency_evidence": ref(root / "dependency-evidence.json"),
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "conditions": results,
            "joint_forwards_and_DINO_calls": 12,
            "joint_observations": 48,
            "all_native_triplets": 36,
            "ADC_first4_physical_inputs_exact_full_suite_reference": True,
            "CUDA_initialized": torch.cuda.is_initialized(),
            "scope": plan["scope"],
        },
    )


def controller(plan_path):
    plan = read(plan_path)
    guard(plan)
    root, work = Path(plan["root"]), Path(plan["work"])
    (root / "controller.claim").open("x").close()
    state = {
        "plan": ref(plan_path),
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
    }
    child, owner, snapshot = None, None, None

    def record(status, **extra):
        state.update(status=status, updated_unix=time.time(), **extra)
        save(root / "status.json", state)

    def observe():
        nonlocal snapshot
        snapshot = resource_snapshot(root)
        with (root / "resource-history.jsonl").open("a") as stream:
            stream.write(json.dumps(snapshot) + "\n")
        return snapshot

    def monitored(status, **extra):
        names = {
            "paused-V43-evaluation-disk-reserve": "paused-native-photo-disk-reserve",
            "running-V43-quality-evaluation": "running-native-photo-condition-worker",
        }
        record(names[status], **extra)

    try:
        started = time.monotonic()
        parent_status_path = Path(plan["parent"]["root"]) / "status.json"
        while True:
            assert time.monotonic() - started < plan["dependency_wait_seconds"]
            try:
                parent = read(parent_status_path)
            except (FileNotFoundError, json.JSONDecodeError) as error:
                record("waiting-for-parent-evaluation-observation", observation_error=repr(error))
                time.sleep(5)
                continue
            if dependency_ready(parent, plan["parent"]):
                break
            record(
                "waiting-for-parent-full-evaluation-exit",
                dependency_controller=parent["controller"],
                dependency_child=parent.get("child"),
                dependency_status=parent["status"],
            )
            time.sleep(5)
        guard(plan)
        for item in parent["completed"].values():
            assert ref(item["path"]) == item
            result = read(item["path"])
            assert result["plan"] == plan["parent"]["reference"] and not live(result["owner"])
            assert result["weights_DINO_config_parameter_ids_RNG_and_inputs_preserved"]
        bridge = root / "dependency-evidence.json"
        assert not bridge.exists()
        save(
            bridge,
            {
                "parent_plan": plan["parent"]["reference"],
                "parent_status": ref(parent_status_path),
                "photo_result": parent["completed"]["photo"],
                "all_seven_stage_owners_exited": True,
            },
        )
        record("waiting-for-native-photo-headroom")
        started, stable = time.monotonic(), None
        while True:
            assert time.monotonic() - started < plan["wait_seconds"]
            stable = (
                (time.monotonic() if stable is None else stable)
                if headroom(observe(), plan, 48)
                else None
            )
            if stable is not None and time.monotonic() - stable >= plan["stable_seconds"]:
                break
            time.sleep(2)
        guard(plan)
        env = dict(
            os.environ,
            PYTHONPATH=str(work / "src") + ":" + str(work / "scripts"),
            CUDA_VISIBLE_DEVICES="0",
            HF_HUB_OFFLINE="1",
            TRANSFORMERS_OFFLINE="1",
            OMP_NUM_THREADS="4",
            OPENBLAS_NUM_THREADS="2",
            PYTHONDONTWRITEBYTECODE="1",
        )
        env.update(plan["cache_environment"])
        with (root / "worker.log").open("xb") as log:
            child = subprocess.Popen(
                [
                    plan["python"],
                    "-P",
                    str(work / "scripts/evaluate_v95_native_photo_conditions.py"),
                    "worker",
                    str(plan_path),
                ],
                cwd=work,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
            record("running-native-photo-condition-worker", child=owner)
            monitor_child(
                child,
                owner,
                plan=plan,
                observe=observe,
                record=monitored,
                deadline=time.monotonic() + plan["worker_timeout_seconds"],
            )
            assert child.wait() == 0, child.returncode
        path = root / "worker-result.json"
        result = read(path)
        assert result["plan"] == ref(plan_path) and result["owner"] == owner
        assert result["joint_forwards_and_DINO_calls"] == 12 and result["all_native_triplets"] == 36
        guard(plan)
        record(
            "completed-native-photo-conditions-awaiting-independent-and-actual-native-review",
            result=ref(path),
        )
    except BaseException as error:
        if child is not None and child.poll() is None:
            stop_owned_child(child, owner)
        record(
            "failed-native-photo-conditions-preserved-no-automatic-retry",
            error=repr(error),
            last_resource_snapshot=snapshot,
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller", "worker"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--artifact-root", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        assert args.output and args.artifact_root
        prepare(args.path.resolve(), args.output, args.artifact_root)
    elif args.mode == "worker":
        worker(args.path.resolve())
    else:
        controller(args.path.resolve())
