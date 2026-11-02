"""Review V143's retained1000/2500 prefixes and complete5000 endpoint on fixed inputs."""

import argparse
import os
import subprocess
import time
from pathlib import Path

import psutil
from review_standalone_patch_memory_pilot import prepare as prepare_native
from review_standalone_patch_memory_pilot import run as run_native
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import live

REPO = Path(__file__).resolve().parents[1]
STEPS = (1000, 2500, 5000)
V142 = REPO / ".cache/quality-20261102/V142-native-v1"
V141 = REPO / ".cache/quality-20261102/V141-native-v1"
FLAT_CONTROL = REPO / ".cache/quality-20261102/V142-flat-safety-v1"


def matching_prefix(observed, control, step):
    """Check every shared input, without claiming matched data after control step1000."""
    assert len(observed) == step and len(control) == 1000
    assert [r["step"] for r in observed] == list(range(1, step + 1))
    for i, (a, b) in enumerate(zip(observed[:1000], control, strict=True), 1):
        assert a["step"] == b["step"] == i
        assert all(a[k] == b[k] for k in ("domain", "clean_sha256", "batch_sha256"))
    return 1000


def selected_steps(from_step):
    if type(from_step) is not int or from_step not in STEPS:
        raise ValueError("Review must start at a declared checkpoint")
    return tuple(step for step in STEPS if step >= from_step)


def prepare(root, training_path, *, from_step=1000, collector_cpu_threads=2):
    review_steps = selected_steps(from_step)
    if type(collector_cpu_threads) is not int or collector_cpu_threads not in (1, 2):
        raise ValueError("Collector CPU threads must be1 or2")
    training = read(training_path)
    guard(training)
    status = read(Path(training["root"]) / "status.json")
    assert status["plan"] == ref(training_path) and live(status["controller"])
    assert training["train_updates"] == 5000 and training["progress_steps"] == [1000, 2500]
    root.mkdir(parents=True, exist_ok=False)
    operator = root / "review-controller.py"
    operator.write_text(
        Path(__file__)
        .read_text()
        .replace("REPO = Path(__file__).resolve().parents[1]", f"REPO = Path({str(REPO)!r})")
    )
    # Bind all review orchestration helpers, while keeping original operator bytes archived.
    helpers = [
        REPO / "scripts" / name
        for name in (
            "review_standalone_patch_memory_pilot.py",
            "train_directional_bank_trial.py",
            "train_v43_quality_trial.py",
        )
    ]
    points = {}
    for step in review_steps:
        point = root / f"step{step}"
        scope = f"V143 {step}of5000: fresh V120 parent, V142 crossed-line/empty data, gradient epsilon3e-5, "
        scope += "pixel3e-4/native256B16BF16/90782/27/seed70/quota.5/zeroPSF/LR1e-5/warm100. "
        scope += "Combined longer-horizon+gradient intervention versus V1421k, not equal-budget/isolated causality. "
        scope += "Original5k worker continues; first1000 clean/noisy inputs must match V142. "
        scope += "102 fixed IEEE-FP32 inputs, reuse408 V120/V129/V141/V142 predictions, identical ROI/noise/display. "
        scope += "Native160 exact synthetic-GT triplets, binned/independentISO100 references notGT; both protectedGFX pairs, both mesh priors/cameraJPEGs. "
        scope += "No new noise/RAW/control inference. Not full427/camera/color/fullframe/speed or hallucination-safety proof."
        prepare_native(
            point,
            training_path,
            camera_control="V142",
            comparison_scope=scope,
            step=step,
            additional_control_roots=[V141, V142],
            retained_control_labels=["V120", "V129 1k EMA", "V141 1k EMA", "V142 1k EMA"],
            collector_cpu_threads=collector_cpu_threads,
        )
        queue = read(point / "queue-plan-v1.json")
        assert queue["training_horizon"] == 5000 and queue["step"] == step
        assert all(len(o["controls"]) == 4 for o in queue["observations"])
        for original, destination in [
            ("report_pilot_flat_safety.py", "flat-operator-v1.py"),
            ("audit_pilot_flat_safety.py", "flat-auditor-v1.py"),
        ]:
            text = (REPO / "scripts" / original).read_text()
            text = text.replace("V140 1k EMA", queue["model_label"]).replace("V140", "V143")
            text = text.replace(
                "REPO = Path(__file__).resolve().parents[1]", f"REPO = Path({str(REPO)!r})"
            )
            (point / destination).write_text(text)
        flat = root / f"step{step}-flat"
        env = dict(os.environ, CUDA_VISIBLE_DEVICES="", PYTHONPATH="src:scripts")
        subprocess.run(
            [
                training["python"],
                str(point / "flat-operator-v1.py"),
                "prepare",
                str(flat),
                "--primary",
                str(point),
            ],
            cwd=REPO,
            env=env,
            check=True,
        )
        assert (
            read(flat / "queue-plan-v1.json")["observations"]
            == read(FLAT_CONTROL / "plan-v1.json")["observations"]
        )
        compare = (REPO / "scripts/compare_pilot_flat_controls.py").read_text()
        compare = compare.replace(
            "V129 controls were newly collected separately",
            "V142 controls were previously collected separately",
        )
        (point / "compare-flat-controls-v1.py").write_text(compare)
        peaks = root / f"step{step}-mesh-peaks"
        old = read(REPO / ".cache/quality-20261102/V142-mesh-peaks-v1/plan-v1.json")
        v142_plan = read(V142 / "plan-v1.json")
        pred = next(
            o["prediction"]
            for o in read(V142 / "collection-v1.json")["observations"]
            if o["id"] == "mesh-profile3879"
        )
        methods = [
            old["methods"][0],
            old["methods"][2],
            {
                "label": v142_plan["model_label"],
                "checkpoint": v142_plan["checkpoint"],
                "prediction": pred,
            },
        ]
        peaks.mkdir()
        save(
            peaks / "plan-v1.json",
            {
                **old,
                "methods": methods,
                "primary_root": str(point),
                "primary_queue": ref(point / "queue-plan-v1.json"),
                "candidate_label": queue["model_label"],
            },
        )
        points[str(step)] = {
            "root": str(point),
            "flat": str(flat),
            "peaks": str(peaks),
            "primary_queue": ref(point / "queue-plan-v1.json"),
            "flat_queue": ref(flat / "queue-plan-v1.json"),
            "operators": [
                ref(point / name)
                for name in (
                    "flat-operator-v1.py",
                    "flat-auditor-v1.py",
                    "compare-flat-controls-v1.py",
                )
            ],
        }
    plan = {
        "root": str(root),
        "training_plan": ref(training_path),
        "training_controller": status["controller"],
        "operator": ref(operator),
        "helpers": [ref(p) for p in helpers],
        "python": training["python"],
        "points": points,
        "prefix_control": training["prefix_control_result"],
        "flat_control": ref(FLAT_CONTROL / "collection-v1.json"),
        "new_candidate_forwards_planned": 150 * len(review_steps),
        "collector_cpu_threads": collector_cpu_threads,
        "reused_control_predictions_per_point": 504,
        "new_noise_observations": 0,
        "RAW_decodes": 0,
        "scope": f"Declared checkpoint subset{list(review_steps)} fixed native/faint/GFX/flat/mesh-peak reviews. Each150 candidate root/DINO calls; no control reruns. Numeric/pixel audits precede actual native viewing. Original5k training budget/owner unchanged.",
    }
    save(root / "plan-v1.json", plan)


def bind(root, step):
    master = read(root / "plan-v1.json")
    for binding in [master["training_plan"], master["prefix_control"], *master["helpers"]]:
        assert ref(binding["path"]) == binding
    training = read(master["training_plan"]["path"])
    guard(training)
    state = read(Path(training["root"]) / "status.json")
    assert (
        state["plan"] == master["training_plan"]
        and state["controller"] == master["training_controller"]
    )
    point = Path(master["points"][str(step)]["root"])
    queue = read(point / "queue-plan-v1.json")
    guard(queue)
    if step < 5000:
        binding = ref(Path(training["root"]) / f"train-V143-progress{step}.json")
        actual = read(binding["path"])
        assert actual["status"] == "immutable-progress-checkpoint-within-original-training-budget"
        assert actual["step"] == step and actual["declared_training_horizon"] == 5000
        counts = actual["counts_at_checkpoint"]
    else:
        assert state["status"] == "completed-training-awaiting-model-comparisons" and not live(
            state["controller"]
        )
        binding = state["completed"]["train-V143"]
        assert ref(binding["path"]) == binding
        actual = read(binding["path"])
        assert actual["status"] == "completed-crossed-gradient5000-training-phase"
        assert actual["updates"] == actual["all_AdamW_steps"] == step
        counts = actual["counts"]
    assert actual["arm"] == "V143" and actual["owner"] == state["child"]
    assert (
        counts["training_forwards"]
        == counts["optimizer_steps"]
        == counts["prepared_training_batches"]
        == step
    )
    assert counts["validation_forwards"] == step // 500 * 32
    assert counts["encoder_forwards"] == step + counts["validation_forwards"]
    matching_prefix(
        actual["observed_inputs"], read(master["prefix_control"]["path"])["observed_inputs"], step
    )
    import torch

    torch.set_num_threads(master.get("collector_cpu_threads", 2))
    checkpoint = actual["checkpoint"]
    assert ref(checkpoint["path"]) == checkpoint
    saved = torch.load(checkpoint["path"], weights_only=True, map_location="cpu", mmap=True)
    assert saved["step"] == step and saved["config"]["steps"] == 5000
    assert (
        saved["config"]["gradient_charbonnier_epsilon"] == 0.00003
        and saved["config"]["mesh_texture_fraction"] == 0.1
    )
    assert saved["config"]["reconstruction_charbonnier_epsilon"] == 0.0003
    assert saved["config"]["initialized_from"] == queue["expected_lineage"]
    assert len(saved["model"]) == len(saved["ema"]) == 91 and len(saved["optimizer"]["state"]) == 89
    assert all(float(s["step"]) == step for s in saved["optimizer"]["state"].values())
    values = [*saved["model"].values(), *saved["ema"].values()]
    values += [
        v
        for s in saved["optimizer"]["state"].values()
        for v in s.values()
        if isinstance(v, torch.Tensor)
    ]
    assert all(torch.isfinite(v).all() for v in values)
    trained = Path(saved["config"]["source_snapshot"])
    sources = list((Path(queue["work"]) / "src/demosaic").glob("*.py"))
    assert len(sources) == 69 and all(
        p.read_bytes() == (trained / p.name).read_bytes() for p in sources
    )
    assert not torch.cuda.is_initialized()
    target = point / f"V143-step{step}-inference.pt"
    os.link(checkpoint["path"], target)
    target.chmod(0o444)
    save(
        point / "endpoint-verification-v1.json",
        {
            "training_result": binding,
            "checkpoint": ref(target),
            "review_step": step,
            "declared_horizon": 5000,
            "matched_V142_prefix_inputs": 1000,
            "trained_source_modules_exact": 69,
            "EMA_tensors": 91,
            "Adam_states": 89,
            "all_Adam_steps": step,
            "finite_state_values": sum(v.numel() for v in values),
            "new_neural_forwards": 0,
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


def run(root, step):
    master = read(root / "plan-v1.json")
    point_info = master["points"][str(step)]
    point, flat, peaks = [Path(point_info[k]) for k in ("root", "flat", "peaks")]
    for binding in point_info["operators"]:
        assert ref(binding["path"]) == binding
    bind(root, step)
    run_native(point)
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="", PYTHONPATH="src:scripts")
    for name, script, args in [
        ("flat-collect", point / "flat-operator-v1.py", ["collect", flat]),
        ("flat-report", point / "flat-operator-v1.py", ["report", flat]),
        ("flat-audit", point / "flat-auditor-v1.py", [flat]),
        (
            "flat-control",
            point / "compare-flat-controls-v1.py",
            [flat, FLAT_CONTROL, root / f"step{step}-flat-control"],
        ),
        ("mesh-peaks", REPO / "scripts/compare_retained_mesh_peaks.py", ["compare", peaks]),
    ]:
        with (point / f"{name}-runner.log").open("x") as log:
            subprocess.run(
                [master["python"], str(script), *map(str, args)],
                cwd=REPO,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=3600,
                check=True,
            )


def watch(root):
    """Wait for the original producer; never reset training or retry a collection."""
    import json

    master = read(root / "plan-v1.json")
    assert ref(__file__) == master["operator"]
    (root / "controller.claim").open("x").close()
    training = read(master["training_plan"]["path"])
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    state = {"owner": owner, "plan": ref(root / "plan-v1.json"), "completed": {}}

    def record(value, **fields):
        state.update(status=value, updated_unix=time.time(), **fields)
        save(root / "status.json", state)

    began = time.monotonic()
    try:
        for step in sorted(map(int, master["points"])):
            path = Path(training["root"]) / (
                f"train-V143-progress{step}.json" if step < 5000 else "train-V143-result.json"
            )
            record("waiting-for-original-V143-checkpoint", step=step)
            while True:
                producer = read(Path(training["root"]) / "status.json")
                assert producer["plan"] == master["training_plan"]
                assert producer["controller"] == master["training_controller"]
                ready = False
                if path.exists():
                    try:
                        read(path)
                        ready = step < 5000 or (
                            producer["status"] == "completed-training-awaiting-model-comparisons"
                            and not live(producer["controller"])
                        )
                    except json.JSONDecodeError:
                        pass  # Re-poll the same owned producer during a receipt write.
                if ready:
                    break
                assert not producer["status"].startswith("failed"), producer
                assert live(producer["controller"]), producer
                assert time.monotonic() - began < 10 * 3600
                time.sleep(10)
            record("waiting-for-review-headroom", step=step)
            while psutil.virtual_memory().available < 50 * 2**30:
                assert time.monotonic() - began < 10 * 3600
                time.sleep(10)
            record("running-fixed-checkpoint-review", step=step)
            run(root, step)
            point = Path(master["points"][str(step)]["root"])
            flat = Path(master["points"][str(step)]["flat"])
            state["completed"][str(step)] = {
                "primary_audit": ref(point / "independent-audit-v1.json"),
                "faint_audit": ref(point / "faint-detail-v1/independent-audit-v1.json"),
                "flat_audit": ref(flat / "independent-flat-audit-v1.json"),
            }
            record("completed-numeric-checkpoint-review-awaiting-actual-viewing", step=step)
        record("completed-declared-reviews-awaiting-actual-native-viewing")
    except BaseException as error:
        record("failed-review-preserved-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("prepare", "bind", "run", "watch"))
    p.add_argument("root", type=Path)
    p.add_argument("--training-plan", type=Path)
    p.add_argument("--step", type=int, choices=STEPS)
    p.add_argument("--from-step", type=int, choices=STEPS, default=1000)
    p.add_argument("--cpu-threads", type=int, choices=(1, 2), default=2)
    args = p.parse_args()
    if args.mode == "prepare":
        prepare(
            args.root.resolve(),
            args.training_plan.resolve(),
            from_step=args.from_step,
            collector_cpu_threads=args.cpu_threads,
        )
    elif args.mode == "bind":
        bind(args.root.resolve(), args.step)
    elif args.mode == "watch":
        watch(args.root.resolve())
    else:
        run(args.root.resolve(), args.step)
