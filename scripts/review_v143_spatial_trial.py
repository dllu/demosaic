"""Bind the V144/V145 pilot to retained photo, GFX, faint and exact-flat inputs."""

import argparse
import os
import subprocess
import time
from pathlib import Path

import psutil
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import live

REPO = Path(__file__).resolve().parents[1]
PARENT_NATIVE = REPO / ".cache/quality-20261102/V143-fixed-reviews-v4/step5000"
PARENT_FLAT = REPO / ".cache/quality-20261102/V143-fixed-reviews-v4/step5000-flat"
PARENT_LABEL = "V143 5000of5000 EMA"


def prepare(root, training_path):
    training = read(training_path)
    guard(training)
    assert set(training["arms"]) == {"V144", "V145"}
    assert training["parent_step"] == 5000 and training["train_updates"] == 1000
    root.mkdir(parents=True, exist_ok=False)
    helpers = root / "helpers"
    helpers.mkdir()
    for source in (REPO / "scripts").glob("*.py"):
        # Helpers which locate retained artifacts must keep the actual repository root.
        text = source.read_text().replace(
            "REPO = Path(__file__).resolve().parents[1]", f"REPO = Path({str(REPO)!r})"
        )
        (helpers / source.name).write_text(text)
    operator = root / "review-controller.py"
    operator.write_text(
        Path(__file__)
        .read_text()
        .replace("REPO = Path(__file__).resolve().parents[1]", f"REPO = Path({str(REPO)!r})")
    )
    plan = {
        "root": str(root),
        "training_plan": ref(training_path),
        "training_root": training["root"],
        "helpers": str(helpers),
        "python": training["python"],
        "operator": ref(operator),
        "inputs": [
            ref(training_path),
            ref(PARENT_NATIVE / "plan-v1.json"),
            ref(PARENT_NATIVE / "collection-v1.json"),
            ref(PARENT_FLAT / "plan-v1.json"),
            ref(PARENT_FLAT / "collection-v1.json"),
        ],
        "frozen_files": {str(p): ref(p)["sha256"] for p in root.rglob("*.py")},
        "scope": "For each completed1000 endpoint:102 retained photo/faint/mainGFX/mesh "
        "contexts plus48 analytic flat observations, IEEE FP32, identical noise/ROI/display. "
        "Reuse V120 and V143; V145 also reuses V144. No training/noise generation/RAW decode "
        "or original-drive opens in this review. Independent ISO100/AHD/JPEG references "
        "are not exactGT. Native160 triplets, foliage/chain-link/sky/building and mesh/JPEG "
        "boards. Not full427, full-frame, camera/color or speed qualification.",
    }
    guard(plan)
    save(root / "review-plan-v1.json", plan)
    return root / "review-plan-v1.json"


def bind(point, training, arm):
    import torch

    queue = read(point / "queue-plan-v1.json")
    guard(queue)
    binding = ref(Path(training["root"]) / f"train-{arm}-result.json")
    actual = read(binding["path"])
    assert not live(actual["owner"]) and actual["arm"] == arm and actual["phase"] == "train"
    assert actual["updates"] == actual["counts"]["optimizer_steps"] == 1000
    assert actual["model_EMA_Adam_finite"] and actual["frozen_encoder_no_gradients"]
    assert actual["counts"]["training_forwards"] == 1000
    assert actual["counts"]["encoder_forwards"] == 1064
    if arm == "V145":
        control = read(Path(training["root"]) / "train-V144-result.json")
        keys = ("step", "domain", "clean_sha256", "batch_sha256")
        assert len(actual["observed_inputs"]) == len(control["observed_inputs"]) == 1000
        assert all(
            all(a[k] == b[k] for k in keys)
            for a, b in zip(actual["observed_inputs"], control["observed_inputs"], strict=True)
        )
        assert actual["all_observed_inputs_match_saved_control"]
    torch.set_num_threads(1)
    checkpoint = actual["checkpoint"]
    assert ref(checkpoint["path"]) == checkpoint
    saved = torch.load(checkpoint["path"], map_location="cpu", weights_only=True, mmap=True)
    assert saved["step"] == saved["config"]["steps"] == 1000
    assert saved["config"]["initialized_from"] == queue["expected_lineage"]
    spatial = arm == "V145"
    assert saved["model_config"].get("raw_spatial_features", False) is spatial
    assert saved["config"].get("raw_spatial_lr_multiplier", 1) == (100 if spatial else 1)
    assert saved["config"]["seed"] == 144 and saved["config"]["lr"] == 1e-5
    assert len(saved["model"]) == len(saved["ema"]) == queue["EMA_tensors"]
    states = saved["optimizer"]["state"]
    assert len(states) == (112 if spatial else 89)
    assert all(float(s["step"]) == 1000 for s in states.values())
    values = [*saved["model"].values(), *saved["ema"].values()]
    values += [v for s in states.values() for v in s.values() if isinstance(v, torch.Tensor)]
    assert all(torch.isfinite(v).all() for v in values)
    trained = Path(saved["config"]["source_snapshot"])
    sources = list((Path(queue["work"]) / "src/demosaic").glob("*.py"))
    assert sources and all(p.read_bytes() == (trained / p.name).read_bytes() for p in sources)
    target = point / f"{arm}-1000-inference.pt"
    os.link(checkpoint["path"], target)
    target.chmod(0o444)
    save(
        point / "endpoint-verification-v1.json",
        {
            "training_result": binding,
            "checkpoint": ref(target),
            "all_Adam_steps": 1000,
            "EMA_tensors": queue["EMA_tensors"],
            "Adam_states": len(states),
            "trained_source_modules_exact": len(sources),
            "new_neural_forwards": 0,
            "all1000_inputs_match_V144": True if spatial else None,
        },
    )
    save(
        point / "plan-v1.json",
        {
            **queue,
            "checkpoint": ref(target),
            "inputs": [
                *queue["inputs"],
                binding,
                ref(target),
                ref(point / "endpoint-verification-v1.json"),
            ],
        },
    )


def run(path):
    from compare_pilot_flat_controls import compare
    from review_standalone_patch_memory_pilot import prepare as prepare_native
    from review_standalone_patch_memory_pilot import run as run_native

    plan = read(path)
    guard(plan)
    training = read(plan["training_plan"]["path"])
    guard(training)
    root = Path(plan["root"])
    (root / "review.claim").open("x").close()
    state = {
        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "plan": ref(path),
        "completed": {},
    }

    def record(status, **extra):
        state.update(status=status, updated_unix=time.time(), **extra)
        save(root / "review-status.json", state)

    try:
        for arm in ("V144", "V145"):
            point = root / arm
            controls = [PARENT_NATIVE] + ([root / "V144"] if arm == "V145" else [])
            labels = ["V120", PARENT_LABEL] + (["V144 1k EMA"] if arm == "V145" else [])
            record("preparing-fixed-review", arm=arm)
            prepare_native(
                point,
                Path(plan["training_plan"]["path"]),
                arm=arm,
                additional_control_roots=controls,
                retained_control_labels=labels,
                camera_control="V144" if arm == "V145" else "V143",
                camera_control_label="V144 1k EMA" if arm == "V145" else PARENT_LABEL,
                collector_cpu_threads=1,
                comparison_scope=plan["scope"],
            )
            flat = root / (arm + "-flat")
            env = {
                **os.environ,
                "CUDA_VISIBLE_DEVICES": "",
                "OMP_NUM_THREADS": "1",
                "OPENBLAS_NUM_THREADS": "1",
            }
            operator = Path(plan["helpers"]) / "report_pilot_flat_safety.py"
            auditor = Path(plan["helpers"]) / "audit_pilot_flat_safety.py"

            def command(script, args, name, cuda=False, *, arm=arm, env=env):
                record("running-fixed-review-stage", arm=arm, stage=name)
                with (root / f"{arm}-{name}.log").open("x") as log:
                    subprocess.run(
                        [plan["python"], "-P", str(script), *map(str, args)],
                        env={**env, "CUDA_VISIBLE_DEVICES": "0" if cuda else ""},
                        cwd=REPO,
                        stdin=subprocess.DEVNULL,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        check=True,
                        timeout=3600,
                    )

            command(operator, ["prepare", flat, "--primary", point], "flat-prepare")
            deadline = time.time() + 36000
            result = Path(training["root"]) / f"train-{arm}-result.json"
            record("waiting-for-declared-training-endpoint", arm=arm)
            while not result.exists() or live(read(result)["owner"]):
                status = read(Path(training["root"]) / "status.json")
                assert not status["status"].startswith("failed"), status
                assert time.time() < deadline
                time.sleep(10)
            bind(point, training, arm)
            record("running-native-faint-GFX-JPEG-review", arm=arm)
            run_native(point)
            command(operator, ["collect", flat], "flat-collect", cuda=True)
            command(operator, ["report", flat], "flat-report")
            command(auditor, [flat], "flat-audit")
            compare(flat, PARENT_FLAT, root / (arm + "-flat-vs-V143"))
            if arm == "V145":
                compare(flat, root / "V144-flat", root / "V145-flat-vs-V144")
            state["completed"][arm] = {
                "primary_audit": ref(point / "independent-audit-v1.json"),
                "flat_audit": ref(flat / "independent-audit-v1.json"),
            }
            record("completed-fixed-numeric-review", arm=arm)
        record("completed-both-pilots-awaiting-native-viewing")
    except BaseException as error:
        record("failed-fixed-review-preserved", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--training-plan", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path.resolve(), args.training_plan.resolve()))
    else:
        run(args.path.resolve())
