"""Run a precision-only V130 candidate against completed V129 training receipts."""

import argparse
import shutil
from collections import Counter
from pathlib import Path

from train_directional_bank_trial import guard, read, ref, save
from train_quality_recipes import REPO, controller
from train_quality_recipes import prepare as prepare_recipes
from train_reviewed_shadow_trial import worker
from train_v43_quality_trial import live

CONTROL = REPO / ".cache/current-quality-20261023-v1/reviewed-detail-training-pilot-v1/run"


def prepare(root):
    import yaml

    from demosaic.shadow_exposure import POLICY, reviewed_shadow_options
    from demosaic.train import training_domain

    recipe = REPO / "configs/quality-v120-fp32-pilot-v130.yaml"
    original = REPO / "configs/quality-v120-reviewed-detail-pilot-v129.yaml"
    config, baseline = [yaml.safe_load(p.read_text()) for p in (recipe, original)]
    ignored = {"run", "experiment_notes", "precision"}
    assert {k: v for k, v in config.items() if k not in ignored} == {
        k: v for k, v in baseline.items() if k not in ignored
    }
    assert config["precision"] == "float32" and baseline["precision"] == "bfloat16"
    assert reviewed_shadow_options(config) == reviewed_shadow_options(baseline) == (0, None)
    assert config.get("dino_feature_weight", 0) == 0 and config["seed"] == 70
    control_plan = read(CONTROL / "plan.json")
    guard(control_plan)
    status = read(CONTROL / "status.json")
    assert status["plan"] == ref(CONTROL / "plan.json")
    assert status["status"] == "completed-training-awaiting-model-comparisons"
    assert not live(status["controller"])
    assert status.get("child") is None or not live(status["child"])
    controls = {}
    for phase in ("CPU", "CUDA", "train"):
        binding = ref(CONTROL / f"{phase}-V129-result.json")
        result = read(binding["path"])
        assert result["status"] == "completed-reviewed-detail-training-phase"
        assert result["phase"] == phase and result["arm"] == "V129"
        assert not live(result["owner"])
        assert result["updates"] == (1000 if phase == "train" else 18)
        assert len(result["observed_inputs"]) == result["updates"]
        assert result["model_EMA_Adam_finite"] and result["optimizer_state_count"] == 89
        assert ref(result["checkpoint"]["path"]) == result["checkpoint"]
        controls[phase] = binding
    path = prepare_recipes(root, root / "work/artifacts", [recipe])
    plan = read(path)
    work = Path(plan["work"])
    script = work / "scripts/train_precision_pilot.py"
    core = work / "scripts/train_reviewed_shadow_trial.py"
    shutil.copyfile(__file__, script)
    shutil.copyfile(REPO / "scripts/train_reviewed_shadow_trial.py", core)
    cpu = Path(plan["arms"]["V130"]["CPU"])
    actual = yaml.safe_load(cpu.read_text())
    actual["patch_size"] = 128
    cpu.write_text(yaml.safe_dump(actual, sort_keys=False))
    previous_cpu = Path(control_plan["arms"]["V129"]["CPU"])
    previous = yaml.safe_load(previous_cpu.read_text())
    cpu_ignored = {"run", "experiment_notes", "validation_protocol"}
    assert {k: v for k, v in actual.items() if k not in cpu_ignored} == {
        k: v for k, v in previous.items() if k not in cpu_ignored
    }
    assert (
        ref(actual["validation_protocol"])["sha256"]
        == ref(previous["validation_protocol"])["sha256"]
    )
    previous_src = Path(control_plan["work"]) / "src"
    src_proof = {}
    for p in (work / "src").rglob("*.py"):
        relative = p.relative_to(work / "src")
        old = previous_src / relative
        assert ref(p)["sha256"] == ref(old)["sha256"]
        src_proof[str(relative)] = ref(p)["sha256"]
    assert set(src_proof) == {str(p.relative_to(previous_src)) for p in previous_src.rglob("*.py")}
    # CPU recipes both force IEEE FP32. Adopt the already completed, identical
    # CPU implementation check, preserving its original arm/receipt unchanged.
    proof = work / "CPU-adoption-proof-v1.json"
    save(
        proof,
        {
            "status": "identical-CPU-config-and-training-source-adopted-without-neural-replay",
            "candidate_config": ref(cpu),
            "original_config": ref(previous_cpu),
            "ignored_fields": sorted(cpu_ignored),
            "validation_protocol_bytes_exact": True,
            "training_source_hashes": src_proof,
            "original_CPU_result": controls["CPU"],
            "new_CPU_forwards": 0,
        },
    )
    for change in ("fraction", "policy"):
        rejected = yaml.safe_load(Path(plan["arms"]["V130"]["CUDA"]).read_text())
        if change == "fraction":
            rejected.update(reviewed_shadow_fraction=0.5, reviewed_shadow_policy=POLICY)
        else:
            rejected["reviewed_shadow_policy"] = "unknown-shadow-policy"
        rejected["run"] += f"-rejected-{change}-resume"
        dest = work / "configs" / f"CUDA-V130-rejected-{change}.yaml"
        dest.write_text(yaml.safe_dump(rejected, sort_keys=False))
        plan["arms"]["V130"][f"CUDA_rejected_{change}"] = str(dest)
    plan.update(
        worker_script=ref(script),
        core_worker_script=ref(core),
        arm_fractions={"V130": 0.0},
        saved_control_arm="V129",
        matched_control_results=controls,
        adopted_phase_results={"CPU-V130": controls["CPU"]},
        CPU_adoption_proof=ref(proof),
        require_matched_clean_inputs=True,
        require_matched_noisy_inputs=True,
        require_unchanged_noncommons_inputs=True,
        phase_result_status="completed-precision-training-phase",
        resume_rejection_changes=["fraction", "policy"],
        resume_rejection_error_keyword="shadow",
        rejection_result_key="changed_shadow_resume_rejections",
        smoke_updates=16,
        resume_new_updates=2,
        launch_available_RAM_GiB=52,
        runtime_available_RAM_GB=32,
        CUDA_allocator_cap_GiB=16,
        maximum_train_worker_seconds=28800,
        maximum_smoke_worker_seconds=1800,
        prospective_domain_batches=dict(
            Counter(training_domain(s, 70, 0.25, 0.25) for s in range(1, 1001))
        ),
        scope=(
            "New V130 IEEE FP32 precision-only1000-update candidate versus saved V129 "
            "BF16 control; same V120 EMA parent/seed70/90782photos/27ROIs/quota.5/"
            "native256/B16/singleview/zeroPSF/LR1e-5/warm100/paired32/native128. "
            "All1000 clean/noisy batch hashes must match. CPU128/B1 FP32 check reused "
            "only after config/training-source-byte identity proof; original V129 receipt "
            "unchanged.18 new discarded CUDA256/B16 updates including valid16+2 resume "
            "and1000 fresh production updates;30min check/8h production,52GiB admission/"
            "16GiB CUDAcap/32GB runtime floor. Zero automatic retry/reset. No old "
            "training/inference replay and no precision/quality/speed promotion claim."
        ),
    )
    plan["inputs"] += [ref(original), ref(CONTROL / "plan.json"), *controls.values()]
    plan["frozen_files"] = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    save(path, plan)
    guard(plan)
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller", "worker"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--phase", choices=("CPU", "CUDA", "train"))
    parser.add_argument("--arm", choices=("V130",))
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path.resolve()))
    elif args.mode == "controller":
        controller(args.path.resolve())
    else:
        worker(args.path.resolve(), args.phase, args.arm)
