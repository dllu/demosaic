"""Run source-frozen V120 continuations with matched-input and state checks."""

import argparse
import gc
import os
import shutil
from collections import Counter
from pathlib import Path

import psutil
from train_directional_bank_trial import guard, read, ref, save
from train_quality_recipes import REPO, controller
from train_quality_recipes import prepare as prepare_recipes

FRACTIONS = {"V126": 0.0, "V127": 0.5}


def verify_initial_restoration(
    actual, expected, *, spatial, fresh, global_features=False, global_tensors=18
):
    """Check the complete common state and the explicitly declared new branch."""
    import torch

    assert global_tensors in (15, 16, 18)
    count = 91 + global_tensors if global_features else (114 if spatial else 91)
    assert len(actual) == count
    if fresh and (spatial or global_features):
        assert len(expected) == 91 and expected.keys() <= actual.keys()
        extra = actual.keys() - expected.keys()
        prefix = "pretrained_rgb.raw_global." if global_features else "pretrained_rgb.raw_spatial."
        assert len(extra) == (global_tensors if global_features else 23)
        assert all(k.startswith(prefix) for k in extra)
        assert actual[prefix + "project.weight"].count_nonzero() == 0
    else:
        assert actual.keys() == expected.keys()
    assert all(torch.equal(actual[k].cpu(), v) for k, v in expected.items())


def capture_progress(root, arm, checkpoint, *, step, horizon, counts, inputs, tensor_count):
    """Retain a completed checkpoint without stopping or replaying the worker."""
    import torch

    assert 0 < step < horizon
    assert counts["optimizer_steps"] == counts["training_forwards"] == step
    assert len(inputs) == step and [r["step"] for r in inputs] == list(range(1, step + 1))
    checkpoint = Path(checkpoint)
    state = torch.load(checkpoint, map_location="cpu", weights_only=True, mmap=True)
    assert state["step"] == step and state["config"]["steps"] == horizon
    assert len(state["model"]) == len(state["ema"]) == tensor_count
    target = Path(root) / f"{arm}-progress{step}.pt"
    assert not target.exists()
    assert not (Path(root) / f"train-{arm}-progress{step}.json").exists()
    os.link(checkpoint, target)
    receipt = {
        "status": "immutable-progress-checkpoint-within-original-training-budget",
        "arm": arm,
        "step": step,
        "declared_training_horizon": horizon,
        "checkpoint": ref(target),
        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "counts_at_checkpoint": dict(counts),
        "observed_inputs": list(inputs),
        "scope": "Progress only; the same worker continues toward its original full horizon. No extra forward, noise draw, optimizer update or restarted schedule. This is not the completed endpoint.",
    }
    save(Path(root) / f"train-{arm}-progress{step}.json", receipt)
    return receipt


def prepare(root):
    import yaml

    from demosaic.shadow_exposure import POLICY, reviewed_shadow_options
    from demosaic.train import training_domain

    recipes = [REPO / f"configs/quality-v120-reviewed-shadow-pilot-v{v}.yaml" for v in (126, 127)]
    configs = [yaml.safe_load(p.read_text()) for p in recipes]
    ignored = {"run", "experiment_notes", "reviewed_shadow_fraction", "reviewed_shadow_policy"}
    assert {k: v for k, v in configs[0].items() if k not in ignored} == {
        k: v for k, v in configs[1].items() if k not in ignored
    }
    for config, fraction in zip(configs, FRACTIONS.values(), strict=True):
        assert reviewed_shadow_options(config) == (fraction, POLICY if fraction else None)
        assert config["seed"] == 70 and config["steps"] == 1000
        assert config["noise_pair_draws"] == 1 and config["conditional_mean_weight"] == 0
        assert config["reviewed_roi_fraction"] == 0.5
        assert not config["model"].get("raw_frequency_features", False)
    path = prepare_recipes(root, root / "work/artifacts", recipes)
    plan = read(path)
    work = Path(plan["work"])
    script = work / "scripts/train_reviewed_shadow_trial.py"
    shutil.copyfile(__file__, script)
    for arm in plan["arms"]:
        cpu = Path(plan["arms"][arm]["CPU"])
        config = yaml.safe_load(cpu.read_text())
        config["patch_size"] = 128
        cpu.write_text(yaml.safe_dump(config, sort_keys=False))
        for phase in ("CPU", "CUDA"):
            for change in ("fraction", "policy"):
                config = yaml.safe_load(Path(plan["arms"][arm][phase]).read_text())
                if change == "fraction":
                    fraction = 0.5 if FRACTIONS[arm] == 0 else 0.0
                    config.update(
                        reviewed_shadow_fraction=fraction,
                        reviewed_shadow_policy=POLICY if fraction else None,
                    )
                else:
                    config["reviewed_shadow_policy"] = "unknown-shadow-policy"
                config["run"] += f"-rejected-{change}-resume"
                dest = work / "configs" / f"{phase}-{arm}-rejected-{change}.yaml"
                dest.write_text(yaml.safe_dump(config, sort_keys=False))
                plan["arms"][arm][f"{phase}_rejected_{change}"] = str(dest)
    plan.update(
        worker_script=ref(script),
        smoke_updates=16,
        resume_new_updates=2,
        launch_available_RAM_GiB=64,
        runtime_available_RAM_GB=32,
        CUDA_allocator_cap_GiB=16,
        maximum_train_worker_seconds=28800,
        maximum_smoke_worker_seconds=1800,
        prospective_domain_batches=dict(
            Counter(training_domain(s, 70, 0.25, 0.25) for s in range(1, 1001))
        ),
        scope=(
            "Matched fresh1000-update pilot from completedV120, seed70, cleaned90783/23ROIs. "
            "Both reviewed-ROI fractions.5; V126 legacy exposure, V127 shadow fraction.5. "
            "Single sensor view/native256/B16/BF16, LR1e-5/warm100, zeroPSF. "
            "CPU128/B1 and CUDA256/B16 discarded16+2 resumes precede fresh production. "
            "No existing queue/parent/budget edits; no retries or budget extension. "
            "Pilot only, not a completed20k comparison or a quality claim."
        ),
    )
    plan["frozen_files"] = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    save(path, plan)
    guard(plan)
    return path


def worker(path, phase, arm):
    import numpy as np
    import torch
    import yaml
    from profile_raw_kernel_inference import model_hash

    import demosaic.train as training
    from demosaic.shadow_exposure import reviewed_shadow_levels

    plan = read(path)
    guard(plan)
    root, work = Path(plan["root"]), Path(plan["work"])
    assert Path(training.__file__).resolve().is_relative_to(work / "src")
    assert ref(__file__) == plan.get("core_worker_script", plan["worker_script"])
    assert os.environ["CUDA_VISIBLE_DEVICES"] == ("" if phase == "CPU" else "0")
    (root / f"{phase}-{arm}.claim").open("x").close()
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    if phase != "CPU":
        torch.cuda.set_per_process_memory_fraction(
            plan["CUDA_allocator_cap_GiB"]
            * 2**30
            / torch.cuda.get_device_properties(0).total_memory
        )
    config = yaml.safe_load(Path(plan["arms"][arm][phase]).read_text())
    spatial = config["model"].get("raw_spatial_features", False)
    global_features = config["model"].get("raw_global_features", False)
    global_only = training.validate_raw_global_only(config)
    global_tensors = {"memory-only-v3": 15, "patch-memory-v4": 16}.get(
        config["model"].get("raw_global_conditioning"), 18
    )
    assert not (spatial and global_features)
    expected_tensors, expected_states = (
        (91 + global_tensors, 89 + global_tensors)
        if global_features
        else ((114, 112) if spatial else (91, 89))
    )
    if global_only:
        assert global_features
        expected_states = global_tensors
    declared = plan.get("restoration_tensors_by_arm", {}).get(arm, 91)
    assert expected_tensors == declared
    fractions = plan.get("arm_fractions", FRACTIONS)
    assert config["reviewed_shadow_fraction"] == fractions[arm]
    parent = torch.load(plan["parent"]["path"], map_location="cpu", weights_only=True, mmap=True)
    assert parent["step"] == 20000 and len(parent["ema"]) == 91
    counts, domains = Counter(), Counter()
    initials, inputs, gradients = [], [], {}
    gradient_steps, global_gradient_snapshots = [], []
    global_initial_offsets = []
    captured, current, preserved_state = {}, "fresh", None
    constructor, batch_factory, optimizer_factory = (
        training.JointDemosaic,
        training.prepare_training_batch,
        training.make_optimizer,
    )
    destination = root / "retained" / phase / arm
    destination.mkdir(parents=True, exist_ok=False)
    control_binding = plan.get("matched_control_results", {}).get(phase)
    if control_binding:
        assert ref(control_binding["path"]) == control_binding
        control = read(control_binding["path"])
        assert control["phase"] == phase and control["arm"] == plan.get("saved_control_arm", "V126")
        assert control["updates"] == (plan["train_updates"] if phase == "train" else 18)
    elif peer := plan.get("paired_control_arm"):
        control_binding = ref(root / f"{phase}-{peer}-result.json") if arm != peer else None
        control = read(control_binding["path"]) if control_binding else None
        if control:
            from train_v43_quality_trial import live

            assert control["phase"] == phase and control["arm"] == peer
            assert control["updates"] == (plan["train_updates"] if phase == "train" else 18)
            assert not live(control["owner"])
            assert ref(control["checkpoint"]["path"]) == control["checkpoint"]
    else:
        control = read(root / f"{phase}-V126-result.json") if arm == "V127" else None
    prior_inputs = {r["step"]: r for r in control["observed_inputs"]} if control else {}
    smoke = read(root / f"CUDA-{arm}-result.json") if phase == "train" else None
    smoke_inputs = {r["step"]: r for r in smoke["observed_inputs"]} if smoke else {}

    def construct(options):
        assert current != "rejected-resume", "Reject changed shadow options before construction"
        model = constructor(options)
        captured["model"] = model

        def before(module, args):
            counts["training_forwards" if module.training else "validation_forwards"] += 1

        def initial(module, args):
            expected = parent["ema"] if current == "fresh" else preserved_state["model"]
            actual = module.restoration_state_dict()
            verify_initial_restoration(
                actual,
                expected,
                spatial=spatial,
                fresh=current == "fresh",
                global_features=global_features,
                global_tensors=global_tensors,
            )
            assert model_hash(module.context.backbone) == config["expected_dino_sha256"]
            assert all(
                not p.requires_grad and p.grad is None for p in module.context.backbone.parameters()
            )
            assert len([p for p in module.parameters() if p.requires_grad]) == expected_states
            initials.append(
                {
                    "phase": current,
                    "91_parent_or_resume_tensors_exact": True,
                    "model_tensor_count": expected_tensors,
                    "optimizer_state_count": expected_states,
                    "official_encoder_exact": True,
                }
            )
            first.remove()

        model.register_forward_pre_hook(before)
        first = model.register_forward_pre_hook(initial)
        if global_features and current == "fresh":

            def initial_offset(module, args, result):
                assert torch.count_nonzero(result) == 0
                global_initial_offsets.append(
                    {"shape": list(result.shape), "values": result.numel(), "all_zero": True}
                )
                offset_handle.remove()

            offset_handle = model.pretrained_rgb.raw_global.register_forward_hook(initial_offset)
        if plan.get("require_equal_initial_outputs", False) or plan.get(
            "capture_initial_outputs", False
        ):

            def first_output(module, args, result):
                if current == "fresh" and counts["training_forwards"] == 1:
                    arrays = {
                        f"output_{i}": v.detach().float().cpu().numpy()
                        for i, v in enumerate(result)
                    }
                    if control_binding and plan.get("require_equal_initial_outputs", False):
                        assert ref(control["first_outputs"]["path"]) == control["first_outputs"]
                        with np.load(
                            Path(control["first_outputs"]["path"]), allow_pickle=False
                        ) as previous:
                            assert set(arrays) == set(previous.files)
                            assert all(np.array_equal(v, previous[k]) for k, v in arrays.items())
                    np.savez(destination / "first-outputs.npz", **arrays)

            model.register_forward_hook(first_output)
        model.context.backbone.register_forward_hook(
            lambda *args: counts.update(encoder_forwards=1)
        )
        if config.get("dino_feature_weight", 0):
            model.context.backbone.stages[0].register_forward_hook(
                lambda *args: counts.update(stage0_forwards=1)
            )
        return model

    def batch(step, domain, clean, **kwargs):
        if phase == "train" and step - 1 in plan.get("progress_steps", []):
            capture_progress(
                root,
                arm,
                Path(config["run"]) / "last.pt",
                step=step - 1,
                horizon=plan["train_updates"],
                counts=counts,
                inputs=inputs,
                tensor_count=expected_tensors,
            )
        assert domain == training.training_domain(step, 70, 0.25, 0.25)
        clean_hash = training.batch_fingerprint(
            {k: v for k, v in clean.items() if isinstance(v, torch.Tensor)}
        )
        value = batch_factory(step, domain, clean, **kwargs)
        counts.update(prepared_training_batches=1, target_contexts=len(value["packed"]))
        domains[domain] += 1
        assert len(value["packed"]) == config["batch_size"]
        selected = value.get("shadow_exposure_selected")
        n = int(selected.sum()) if selected is not None else 0
        counts["shadow_selected_targets"] += n
        if domain == "commons" and fractions[arm]:
            expected = reviewed_shadow_levels(
                clean, fraction=fractions[arm], seed=70, step=step, device=value["packed"].device
            )
            assert torch.equal(selected, expected > 0)
        else:
            assert selected is None
        digest = training.batch_fingerprint(value)
        row = {
            "step": step,
            "domain": domain,
            "clean_sha256": clean_hash,
            "batch_sha256": digest,
            "selected_shadow_targets": n,
        }
        if step in prior_inputs:
            assert domain == prior_inputs[step]["domain"]
            if plan.get("require_matched_clean_inputs", True) or domain != "commons":
                assert clean_hash == prior_inputs[step]["clean_sha256"]
            if plan.get("require_matched_noisy_inputs", False) or (
                plan.get("require_unchanged_noncommons_inputs", False) and domain != "commons"
            ):
                assert digest == prior_inputs[step]["batch_sha256"]
        if step in smoke_inputs:
            assert digest == smoke_inputs[step]["batch_sha256"]
        if step <= 18:
            output = destination / f"step-{step:02d}.npz"
            np.savez(
                output,
                **{
                    k: v.detach().cpu().contiguous().numpy()
                    for k, v in value.items()
                    if isinstance(v, torch.Tensor)
                },
            )
            row["prepared_tensors"] = ref(output)
        inputs.append(row)
        return value

    def optimizer(model, options):
        result = optimizer_factory(model, options)
        captured["optimizer"] = result
        assert (
            not result.state
            and sum(len(g["params"]) for g in result.param_groups) == expected_states
        )

        def before_step(*args):
            step = counts["optimizer_steps"] + 1
            if global_only:
                assert all(
                    not parameter.requires_grad and parameter.grad is None
                    for name, parameter in model.named_parameters()
                    if not name.startswith("pretrained_rgb.raw_global.")
                )
            declared_steps = plan.get("gradient_observation_steps")
            if phase != "train" or (
                step <= 16 if declared_steps is None else step in declared_steps
            ):
                gradient_steps.append(step)
                snapshot = {}
                for name, parameter in model.named_parameters():
                    if parameter.requires_grad:
                        assert parameter.grad is not None and torch.isfinite(parameter.grad).all()
                        maximum = float(parameter.grad.abs().max())
                        gradients[name] = max(gradients.get(name, 0.0), maximum)
                        if name.startswith("pretrained_rgb.raw_global."):
                            snapshot[name] = maximum
                if global_features:
                    global_gradient_snapshots.append({"step": step, "maxima": snapshot})

        result.register_step_pre_hook(before_step)
        result.register_step_post_hook(lambda *args: counts.update(optimizer_steps=1))
        return result

    try:
        training.JointDemosaic, training.prepare_training_batch, training.make_optimizer = (
            construct,
            batch,
            optimizer,
        )
        expected = plan["train_updates"] if phase == "train" else plan["smoke_updates"]
        last = Path(
            training.train(
                plan["arms"][arm][phase], initialize=plan["parent"]["path"], stop_after=expected
            )
        )
        rejected = {}
        if phase != "train":
            preserved = root / f"{phase}-{arm}-step16.pt"
            os.link(last, preserved)
            preserved_state = torch.load(
                preserved, map_location="cpu", weights_only=True, mmap=True
            )
            assert preserved_state["step"] == 16
            current = "rejected-resume"
            for change in plan.get("resume_rejection_changes", ("fraction", "policy")):
                before = dict(counts)
                try:
                    training.train(
                        plan["arms"][arm][f"{phase}_rejected_{change}"],
                        resume=preserved,
                        stop_after=1,
                    )
                except ValueError as error:
                    assert (
                        plan.get("resume_rejection_error_keyword", "shadow") in str(error).lower()
                    )
                    rejected[change] = str(error)
                else:
                    raise AssertionError("Changed shadow setting accepted on resume")
                assert dict(counts) == before
            current = "resume"
            last = Path(training.train(plan["arms"][arm][phase], resume=preserved, stop_after=2))
            expected += 2
        state = torch.load(last, map_location="cpu", weights_only=True, mmap=True)
        assert (
            state["step"] == expected
            and len(state["model"]) == len(state["ema"]) == expected_tensors
        )
        assert len(state["optimizer"]["state"]) == expected_states
        assert all(float(s["step"]) == expected for s in state["optimizer"]["state"].values())
        assert all(
            torch.isfinite(v).all() for field in ("model", "ema") for v in state[field].values()
        )
        if global_only:
            for field in ("model", "ema"):
                assert all(torch.equal(state[field][k], v) for k, v in parent["ema"].items())
        assert all(
            torch.isfinite(v).all()
            for s in state["optimizer"]["state"].values()
            for v in s.values()
            if isinstance(v, torch.Tensor)
        )
        assert len(gradients) == expected_states and any(v > 0 for v in gradients.values())
        if spatial:
            branch = [
                v for k, v in gradients.items() if k.startswith("pretrained_rgb.raw_spatial.")
            ]
            assert len(branch) == 23 and all(v > 0 for v in branch)
        if global_features:
            assert state["model_config"].get("raw_global_conditioning", "legacy-v1") == config[
                "model"
            ].get("raw_global_conditioning", "legacy-v1")
            branch = [v for k, v in gradients.items() if k.startswith("pretrained_rgb.raw_global.")]
            assert len(branch) == global_tensors and all(v > 0 for v in branch)
            assert len(global_initial_offsets) == 1 and global_initial_offsets[0]["all_zero"]
        assert (
            counts["training_forwards"]
            == counts["optimizer_steps"]
            == counts["prepared_training_batches"]
            == expected
        )
        assert counts["validation_forwards"] == (
            plan.get("expected_train_validation_forwards", 64) if phase == "train" else 0
        )
        assert (
            counts["encoder_forwards"]
            == counts["training_forwards"] + counts["validation_forwards"]
        )
        if config.get("dino_feature_weight", 0):
            assert counts["stage0_forwards"] == counts["encoder_forwards"] + 2 * (
                domains["commons"] + domains["native"]
            )
        assert model_hash(captured["model"].context.backbone) == config["expected_dino_sha256"]
        if phase == "train":
            assert dict(domains) == plan["prospective_domain_batches"]
            if fractions[arm]:
                assert counts["shadow_selected_targets"] > 0
        if plan.get("require_matched_noisy_inputs", False) and arm in plan.get(
            "matched_input_arms", [arm]
        ):
            assert control_binding and len(inputs) == len(control["observed_inputs"])
            assert [r["step"] for r in inputs] == [r["step"] for r in control["observed_inputs"]]
        guard(plan)
        if control_binding:
            assert ref(control_binding["path"]) == control_binding
        save(
            root / f"{phase}-{arm}-result.json",
            {
                "status": plan.get("phase_result_status", "completed-shadow-training-phase"),
                "phase": phase,
                "arm": arm,
                "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
                "checkpoint": ref(last),
                "updates": expected,
                "counts": dict(counts),
                "domain_counts": dict(domains),
                "initial_checks": initials,
                "observed_inputs": inputs,
                "gradient_maxima": gradients,
                "gradient_observation_steps": gradient_steps,
                "global_gradient_snapshots": global_gradient_snapshots,
                plan.get("rejection_result_key", "changed_shadow_resume_rejections"): rejected,
                "model_EMA_Adam_finite": True,
                "source_sha256": state["config"]["source_sha256"],
                "frozen_encoder_no_gradients": all(
                    not p.requires_grad and p.grad is None
                    for p in captured["model"].context.backbone.parameters()
                ),
                "all_AdamW_steps": expected,
                "optimizer_state_count": expected_states,
                "model_EMA_tensor_count": expected_tensors,
                "raw_global_only": global_only,
                "frozen_parent91_model_and_EMA_exact": True if global_only else None,
                "initial_global_offsets": global_initial_offsets,
                "matched_control_result": control_binding,
                "first_outputs": ref(destination / "first-outputs.npz")
                if plan.get("require_equal_initial_outputs", False)
                or plan.get("capture_initial_outputs", False)
                else None,
                "dino_feature_weight": config.get("dino_feature_weight", 0),
                "dino_feature_policy": config.get("dino_feature_policy"),
                "all_observed_inputs_match_saved_control": control is not None
                and len(inputs) == len(control["observed_inputs"])
                and all(
                    all(
                        row[k] == prior_inputs[row["step"]][k]
                        for k in ("domain", "clean_sha256", "batch_sha256")
                    )
                    for row in inputs
                ),
                "CUDA_peak_allocated_bytes": torch.cuda.max_memory_allocated()
                if phase != "CPU"
                else 0,
                "scope": "Discarded implementation check"
                if phase != "train"
                else plan.get(
                    "production_scope",
                    "Bounded1000-update pilot endpoint; image-quality review pending",
                ),
            },
        )
    except BaseException as error:
        save(
            root / f"{phase}-{arm}-failure.json",
            {
                "error": repr(error),
                "counts": dict(counts),
                "current": current,
                "observed_inputs": inputs,
                "status": "failed-preserved-no-automatic-retry",
            },
        )
        raise
    finally:
        training.JointDemosaic, training.prepare_training_batch, training.make_optimizer = (
            constructor,
            batch_factory,
            optimizer_factory,
        )
        captured.clear()
        gc.collect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller", "worker"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--phase", choices=("CPU", "CUDA", "train"))
    parser.add_argument("--arm", choices=tuple(FRACTIONS))
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path.resolve()))
    elif args.mode == "controller":
        controller(args.path.resolve())
    else:
        worker(args.path.resolve(), args.phase, args.arm)
