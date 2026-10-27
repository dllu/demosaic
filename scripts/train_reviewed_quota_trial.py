"""Test a lower photographic ROI quota against the existing full V131 control."""

import argparse
import hashlib
import random
import shutil
from collections import Counter
from pathlib import Path

from train_directional_bank_trial import guard, read, ref, save
from train_quality_recipes import REPO, controller
from train_quality_recipes import prepare as prepare_recipes
from train_reviewed_shadow_trial import worker as training_worker
from train_v43_quality_trial import live

ARM = "V133"
CONTROL = REPO / ".cache/current-quality-20261023-v1/raw-spatial-training-v1/run"
CONTROL_CONTROLLER = (
    REPO / ".cache/current-quality-20261023-v1/raw-spatial-training-admission-v2/run"
)


def validate_recipes(candidate, control):
    ignored = {"run", "experiment_notes", "reviewed_roi_fraction"}
    assert {k: v for k, v in candidate.items() if k not in ignored} == {
        k: v for k, v in control.items() if k not in ignored
    }, "Quota comparison differs beyond the photographic quota"
    assert candidate["reviewed_roi_fraction"] == 0.05
    assert control["reviewed_roi_fraction"] == 0.5
    assert candidate["steps"] == 20000 and candidate["seed"] == 70
    assert candidate["batch_size"] == 16 and candidate["patch_size"] == 256
    assert candidate["precision"] == "bfloat16"
    assert candidate["checkpoint_every"] == 1000
    assert candidate["model"]["raw_spatial_features"] is False


def source_compatibility(candidate, original):
    """Permit exactly the early ROI resume check; valid training is unchanged."""
    a, b = Path(candidate).read_bytes(), Path(original).read_bytes()
    if a == b:
        return {"candidate": ref(candidate), "control": ref(original), "bytes_exact": True}
    assert Path(candidate).name == "train.py"
    early = b'        require_resume_rois(resume_state["config"], config)\n'
    late = b'        require_resume_rois(state["config"], config)\n'
    position = b'        require_resume_photo_sampling(state["config"], config)\n'
    assert a.count(early) == 1 and a.count(position) == 1
    assert a.replace(early, b"").replace(position, late + position) == b
    return {
        "candidate": ref(candidate),
        "control": ref(original),
        "bytes_exact": False,
        "only_change": "Move pure ROI resume compatibility check before model construction",
        "reversing_guard_relocation_restores_all_original_bytes": True,
    }


def unchanged_slots(config, step):
    """Compare the existing independent ROI gates without reading any pixels."""
    result = []
    for index in range((step - 1) * config["batch_size"], step * config["batch_size"]):
        if random.Random(config["seed"] + index).random() < (
            config["flat_fraction"] + config["synthetic_fraction"]
        ):
            result.append(True)
            continue
        payload = hashlib.sha256(
            f"reviewed-photo-roi-v1:{config['seed']}:{index}".encode()
        ).digest()
        gate = random.Random(int.from_bytes(payload[:8], "little")).random()
        result.append(gate < 0.05 or gate >= 0.5)
    return result


def checked_control(binding, phase):
    assert ref(binding["path"]) == binding
    result = read(binding["path"])
    assert result["status"] == "completed-raw-spatial-training-phase"
    assert result["arm"] == "V131" and result["phase"] == phase
    assert result["updates"] == (20000 if phase == "train" else 18)
    assert result["all_AdamW_steps"] == result["updates"]
    assert result["model_EMA_Adam_finite"] and result["optimizer_state_count"] == 89
    assert result["model_EMA_tensor_count"] == 91
    assert len(result["observed_inputs"]) == result["updates"]
    assert not live(result["owner"])
    assert ref(result["checkpoint"]["path"]) == result["checkpoint"]
    return result


def prepare(root):
    import yaml

    from demosaic.train import training_domain

    recipe = REPO / "configs/quality-v120-reviewed-quota-v133.yaml"
    original = REPO / "configs/quality-v120-raw-spatial-v131.yaml"
    config, baseline = [yaml.safe_load(p.read_text()) for p in (recipe, original)]
    validate_recipes(config, baseline)
    old_plan_path = CONTROL / "plan.json"
    old_controller_path = CONTROL_CONTROLLER / "plan.json"
    old_plan, old_controller = [read(p) for p in (old_plan_path, old_controller_path)]
    guard(old_plan)
    guard(old_controller)
    status = read(CONTROL_CONTROLLER / "status.json")
    assert status["plan"] == ref(old_controller_path) and live(status["controller"])
    assert not status["status"].startswith("failed")
    controls = {phase: ref(CONTROL / f"{phase}-V131-result.json") for phase in ("CPU", "CUDA")}
    for phase, binding in controls.items():
        checked_control(binding, phase)
    path = prepare_recipes(root, root / "work/artifacts", [recipe])
    plan = read(path)
    work = Path(plan["work"])
    script = work / "scripts/train_reviewed_quota_trial.py"
    core = work / "scripts/train_reviewed_shadow_trial.py"
    shutil.copyfile(__file__, script)
    shutil.copyfile(REPO / "scripts/train_reviewed_shadow_trial.py", core)
    source_proof = {}
    for p in (work / "src").rglob("*.py"):
        relative = p.relative_to(work / "src")
        source_proof[str(relative)] = source_compatibility(
            p, Path(old_plan["work"]) / "src" / relative
        )
    for phase in ("CPU", "CUDA", "train"):
        current_path = Path(plan["arms"][ARM][phase])
        actual = yaml.safe_load(current_path.read_text())
        if phase == "CPU":
            actual["patch_size"] = 128
            current_path.write_text(yaml.safe_dump(actual, sort_keys=False))
        previous_path = Path(old_plan["arms"]["V131"][phase])
        previous = yaml.safe_load(previous_path.read_text())
        for options in (actual, previous):
            for key in ("run", "experiment_notes", "reviewed_roi_fraction"):
                options.pop(key)
        assert (
            ref(actual.pop("validation_protocol"))["sha256"]
            == ref(previous.pop("validation_protocol"))["sha256"]
        )
        # Implementation checks log each step in both studies.
        assert actual == previous
        if phase != "train":
            rejected = yaml.safe_load(current_path.read_text())
            rejected["reviewed_roi_fraction"] = 0.5
            rejected["run"] += "-rejected-quota-resume"
            target = work / "configs" / f"{phase}-{ARM}-rejected-quota.yaml"
            target.write_text(yaml.safe_dump(rejected, sort_keys=False))
            plan["arms"][ARM][f"{phase}_rejected_quota"] = str(target)
    plan.update(
        worker_script=ref(script),
        core_worker_script=ref(core),
        training_format="reviewed-photographic-quota-v1",
        arm_fractions={ARM: 0.0},
        saved_control_arm="V131",
        matched_control_results=controls,
        deferred_train_control={
            "result": str(CONTROL / "train-V131-result.json"),
            "controller_plan": ref(old_controller_path),
            "controller_status": str(CONTROL_CONTROLLER / "status.json"),
            "controller_owner": status["controller"],
        },
        require_matched_clean_inputs=False,
        require_matched_noisy_inputs=False,
        require_unchanged_noncommons_inputs=True,
        require_equal_initial_outputs=False,
        restoration_tensors_by_arm={ARM: 91},
        phase_result_status="completed-reviewed-quota-training-phase",
        resume_rejection_changes=["quota"],
        resume_rejection_error_keyword="reviewed",
        rejection_result_key="changed_reviewed_quota_resume_rejections",
        smoke_updates=16,
        resume_new_updates=2,
        expected_train_validation_forwards=640,
        progress_steps=[1000],
        launch_available_RAM_GiB=52,
        runtime_available_RAM_GB=32,
        CUDA_allocator_cap_GiB=16,
        maximum_train_worker_seconds=172800,
        maximum_smoke_worker_seconds=1800,
        prospective_domain_batches=dict(
            Counter(training_domain(s, 70, 0.25, 0.25) for s in range(1, 20001))
        ),
        before_train_admission={
            "plan": ref(old_controller_path),
            "status": str(CONTROL_CONTROLLER / "status.json"),
            "controller": status["controller"],
            "arm": "V132",
            "running_status": "running-quality-training",
            "require_completed": True,
            "completed_phases": [
                f"{phase}-{arm}" for phase in ("CPU", "CUDA", "train") for arm in ("V131", "V132")
            ],
            "maximum_wait_seconds": 691200,
        },
        training_source_compatibility_with_control=source_proof,
        production_scope="Completed full20000 quota-only endpoint; matched V131 quality and actual native review pending.",
        scope=(
            "V133 .05 reviewed quota versus original V131 .5, same V120 EMA/90781photos/"
            "29regions/seed70/native256/B16/BF16/singleview/zeroPSF/LR1e-5/warm100/"
            "cosine20000/paired32/native128. Reuse V131 CPU/CUDA/fulltrain receipts; "
            "no old control training/inference. New CPU128/B1 and CUDA256/B16 actual16+2 "
            "checks reject changed quota resumes before construction. Require exact "
            "native/paired and unaffected Commons batch hashes; first18 unaffected "
            "per-example prepared tensors also match. Fresh20000 production updates,"
            "640validation/20640encoder calls/320000 clean slots; retain progress1000 "
            "inside original horizon. Production waits for both original spatial arms "
            "to complete and exit.52GiB launch/16GiB CUDAcap/32GB runtime floor,"
            "30min/check,48h production,8day dependency wait. No automatic retry/reset. "
            "Prepared newest90780/31 is separate; this study isolates quota. Quality "
            "remains unmeasured and V120 recommendation is unchanged."
        ),
    )
    plan["inputs"] += [
        ref(original),
        ref(old_plan_path),
        ref(old_controller_path),
        *controls.values(),
    ]
    plan["frozen_files"] = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    save(path, plan)
    guard(plan)
    return path


def compare_inputs(candidate, control, config):
    """Verify saved unaffected batches and real example tensors without NN calls."""
    import numpy as np

    assert len(candidate["observed_inputs"]) == len(control["observed_inputs"])
    counts = Counter()
    for actual, previous in zip(
        candidate["observed_inputs"], control["observed_inputs"], strict=True
    ):
        step, domain = actual["step"], actual["domain"]
        assert (step, domain) == (previous["step"], previous["domain"])
        mask = (
            unchanged_slots(config, step) if domain == "commons" else [True] * config["batch_size"]
        )
        counts[f"{domain}_steps"] += 1
        if all(mask):
            assert all(actual[k] == previous[k] for k in ("clean_sha256", "batch_sha256"))
            counts[f"{domain}_whole_batches_exact"] += 1
        else:
            counts["Commons_batches_with_expected_selection_changes"] += 1
        if step <= 18:
            assert ref(actual["prepared_tensors"]["path"]) == actual["prepared_tensors"]
            assert ref(previous["prepared_tensors"]["path"]) == previous["prepared_tensors"]
            with (
                np.load(actual["prepared_tensors"]["path"], allow_pickle=False) as a,
                np.load(previous["prepared_tensors"]["path"], allow_pickle=False) as b,
            ):
                assert set(a.files) == set(b.files)
                for key in a.files:
                    av, bv = a[key], b[key]
                    assert av.shape == bv.shape and av.dtype == bv.dtype
                    if av.ndim and av.shape[0] == config["batch_size"]:
                        av, bv = av[mask], bv[mask]
                    assert np.array_equal(av, bv), (step, key, "unaffected examples")
                    counts["exact_unaffected_prepared_values"] += av.size
            counts["unaffected_first18_examples"] += sum(mask)
    return dict(counts)


def worker(path, phase, arm):
    import yaml

    assert arm == ARM
    plan = read(path)
    guard(plan)
    root = Path(plan["root"])
    if phase == "train":
        dependency = plan["deferred_train_control"]
        status = read(dependency["controller_status"])
        assert status["plan"] == dependency["controller_plan"]
        assert status["controller"] == dependency["controller_owner"]
        assert status["status"] == "completed-training-awaiting-model-comparisons"
        assert not live(status["controller"])
        binding = ref(dependency["result"])
        assert status["completed"]["train-V131"] == binding
        plan["matched_control_results"][phase] = binding
        plan["inputs"] = [*plan["inputs"], binding]
    binding = plan["matched_control_results"][phase]
    control = checked_control(binding, phase)
    resolved = root / f"{phase}-{arm}-resolved-plan-v1.json"
    assert not resolved.exists()
    save(resolved, {**plan, "original_worker_plan": ref(path)})
    training_worker(resolved, phase, arm)
    result = ref(root / f"{phase}-{arm}-result.json")
    config = yaml.safe_load(Path(plan["arms"][arm][phase]).read_text())
    proof = compare_inputs(read(result["path"]), control, config)
    save(
        root / f"{phase}-{arm}-input-comparison-v1.json",
        {
            "status": "passed-quota-only-unaffected-batch-and-example-proof",
            "candidate": result,
            "control": binding,
            "config": ref(plan["arms"][arm][phase]),
            "counts": proof,
            "new_forwards_for_comparison": 0,
            "scope": "Different model training states; saved input arrays only. This is not quality evidence.",
        },
    )


def continue_cpu(path, original_path):
    """Finish only two updates from the preserved actual sixteen-step check."""
    import os
    import time

    import numpy as np
    import psutil
    import torch
    import yaml
    from profile_raw_kernel_inference import model_hash

    import demosaic.train as training

    plan, original = read(path), read(original_path)
    guard(plan)
    guard(original)
    root, old_root = Path(plan["root"]), Path(original["root"])
    failed = read(old_root / "status.json")
    prefix = read(old_root / "CPU-V133-failure.json")
    assert failed["status"].startswith("failed") and not live(failed["controller"])
    assert failed["phase"] == "CPU" and not live(failed["child"])
    deadline = failed["child"]["created"] + original["maximum_smoke_worker_seconds"]
    assert time.time() < deadline and prefix["current"] == "rejected-resume"
    assert all(
        prefix["counts"][k] == 16
        for k in (
            "training_forwards",
            "optimizer_steps",
            "prepared_training_batches",
            "encoder_forwards",
        )
    )
    assert len(prefix["observed_inputs"]) == 16
    checkpoint = old_root / "CPU-V133-step16.pt"
    preserved = torch.load(checkpoint, map_location="cpu", weights_only=True, mmap=True)
    assert preserved["step"] == 16 and preserved["config"]["steps"] == 20000
    assert len(preserved["model"]) == len(preserved["ema"]) == 91
    assert len(preserved["optimizer"]["state"]) == 89
    assert all(float(v["step"]) == 16 for v in preserved["optimizer"]["state"].values())
    execution = root / "CPU-continuation-plan-v1.json"
    assert not execution.exists()
    save(
        execution,
        {
            "worker_plan": ref(path),
            "original_plan": ref(original_path),
            "prefix_failure": ref(old_root / "CPU-V133-failure.json"),
            "checkpoint16": ref(checkpoint),
            "absolute_original_CPU_deadline_unix": deadline,
            "remaining_optimizer_and_neural_calls": 2,
            "scope": "Explicit continuation after terminal prevalidation-order failure; no original prefix replay or new CPU schedule.",
        },
    )
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    config = yaml.safe_load(Path(plan["arms"][ARM]["CPU"]).read_text())
    constructor, factory, optimizer_factory = (
        training.JointDemosaic,
        training.prepare_training_batch,
        training.make_optimizer,
    )
    counts, inputs, gradients, captured = Counter(), [], {}, {}

    def forbidden(*args, **kwargs):
        raise AssertionError("Changed ROI settings must reject before construction")

    rejected = {}
    training.JointDemosaic = forbidden
    try:
        for name, expected_error in (("quota", "ROI fraction"), ("catalogue", "ROI catalogue")):
            options = dict(config, run=config["run"] + "-rejected-" + name)
            if name == "quota":
                options["reviewed_roi_fraction"] = 0.5
            else:
                catalogue = read(config["reviewed_roi_catalogue"])
                catalogue["resume_rejection_note"] = "No original catalogue mutation"
                target = root / "rejected-catalogue-v1.json"
                save(target, catalogue)
                options["reviewed_roi_catalogue"] = str(target)
            recipe = root / f"CPU-rejected-{name}-v1.yaml"
            recipe.write_text(yaml.safe_dump(options, sort_keys=False))
            try:
                training.train(recipe, resume=checkpoint, stop_after=1)
            except ValueError as error:
                assert expected_error in str(error)
                rejected[name] = str(error)
            else:
                raise AssertionError("Changed reviewed settings accepted")
    finally:
        training.JointDemosaic = constructor

    def construct(options):
        model = constructor(options)
        captured["model"] = model

        def before(module, args):
            assert time.time() < deadline
            if not counts["training_forwards"]:
                state = module.restoration_state_dict()
                assert state.keys() == preserved["model"].keys()
                assert all(torch.equal(state[k].cpu(), v) for k, v in preserved["model"].items())
                assert model_hash(module.context.backbone) == config["expected_dino_sha256"]
            assert module.training
            counts["training_forwards"] += 1
            assert counts["training_forwards"] <= 2

        model.register_forward_pre_hook(before)
        model.context.backbone.register_forward_hook(
            lambda *args: counts.update(encoder_forwards=1)
        )
        return model

    def batch(step, domain, clean, **kwargs):
        assert step in (17, 18)
        clean_hash = training.batch_fingerprint(
            {k: v for k, v in clean.items() if isinstance(v, torch.Tensor)}
        )
        value = factory(step, domain, clean, **kwargs)
        counts.update(prepared_training_batches=1, target_contexts=len(value["packed"]))
        dest = root / f"CPU-V133-step-{step:02d}-inputs.npz"
        np.savez(
            dest,
            **{
                k: v.detach().cpu().numpy() for k, v in value.items() if isinstance(v, torch.Tensor)
            },
        )
        inputs.append(
            {
                "step": step,
                "domain": domain,
                "clean_sha256": clean_hash,
                "batch_sha256": training.batch_fingerprint(value),
                "selected_shadow_targets": 0,
                "prepared_tensors": ref(dest),
            }
        )
        return value

    def optimizer(model, options):
        result = optimizer_factory(model, options)

        def before(*args):
            for name, parameter in model.named_parameters():
                if parameter.requires_grad:
                    assert parameter.grad is not None and torch.isfinite(parameter.grad).all()
                    gradients[name] = max(gradients.get(name, 0), float(parameter.grad.abs().max()))

        result.register_step_pre_hook(before)
        result.register_step_post_hook(lambda *args: counts.update(optimizer_steps=1))
        return result

    try:
        training.JointDemosaic, training.prepare_training_batch, training.make_optimizer = (
            construct,
            batch,
            optimizer,
        )
        last = Path(training.train(plan["arms"][ARM]["CPU"], resume=checkpoint, stop_after=2))
    finally:
        training.JointDemosaic, training.prepare_training_batch, training.make_optimizer = (
            constructor,
            factory,
            optimizer_factory,
        )
    assert time.time() < deadline
    assert counts == Counter(
        training_forwards=2,
        encoder_forwards=2,
        optimizer_steps=2,
        prepared_training_batches=2,
        target_contexts=2,
    )
    state = torch.load(last, map_location="cpu", weights_only=True, mmap=True)
    assert state["step"] == 18 and len(state["model"]) == len(state["ema"]) == 91
    assert len(state["optimizer"]["state"]) == 89
    assert all(float(s["step"]) == 18 for s in state["optimizer"]["state"].values())
    assert all(torch.isfinite(v).all() for key in ("model", "ema") for v in state[key].values())
    assert all(
        torch.isfinite(v).all()
        for s in state["optimizer"]["state"].values()
        for v in s.values()
        if isinstance(v, torch.Tensor)
    )
    assert len(gradients) == 89 and any(v > 0 for v in gradients.values())
    rows = prefix["observed_inputs"] + inputs
    result = root / "CPU-V133-result.json"
    save(
        result,
        {
            "status": plan["phase_result_status"],
            "phase": "CPU",
            "arm": ARM,
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "checkpoint": ref(last),
            "updates": 18,
            "counts": dict(Counter(prefix["counts"]) + counts),
            "new_continuation_counts": dict(counts),
            "domain_counts": dict(Counter(r["domain"] for r in rows)),
            "observed_inputs": rows,
            "prefix_adopted_without_replay": ref(execution),
            "initial_checks": [{"resume16_model91_exact": True, "official_encoder_exact": True}],
            "changed_reviewed_quota_resume_rejections": rejected,
            "model_EMA_Adam_finite": True,
            "all_AdamW_steps": 18,
            "optimizer_state_count": 89,
            "model_EMA_tensor_count": 91,
            "source_sha256": state["config"]["source_sha256"],
            "prefix_source_sha256": preserved["config"]["source_sha256"],
            "frozen_encoder_no_gradients": all(
                not p.requires_grad and p.grad is None
                for p in captured["model"].context.backbone.parameters()
            ),
            "CUDA_peak_allocated_bytes": 0,
            "scope": "Discarded CPU16+2 check: original16 states retained; only two actual new resumed updates, original absolute CPU deadline preserved.",
        },
    )
    proof = compare_inputs(
        read(result), checked_control(plan["matched_control_results"]["CPU"], "CPU"), config
    )
    save(
        root / "CPU-V133-input-comparison-v1.json",
        {
            "status": "passed-quota-only-unaffected-batch-and-example-proof",
            "candidate": ref(result),
            "control": plan["matched_control_results"]["CPU"],
            "counts": proof,
            "new_forwards_for_comparison": 0,
        },
    )
    guard(plan)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller", "worker", "continue-cpu"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--phase", choices=("CPU", "CUDA", "train"))
    parser.add_argument("--arm", choices=(ARM,))
    parser.add_argument("--original-plan", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path.resolve()))
    elif args.mode == "controller":
        controller(args.path.resolve())
    elif args.mode == "continue-cpu":
        continue_cpu(args.path.resolve(), args.original_plan.resolve())
    else:
        worker(args.path.resolve(), args.phase, args.arm)
