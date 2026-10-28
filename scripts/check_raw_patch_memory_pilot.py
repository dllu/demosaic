"""Freeze and check V140 neighboring-gradient memory; production is separate."""

import argparse
import shutil
from pathlib import Path

import psutil
from train_directional_bank_trial import guard, read, ref, save
from train_quality_recipes import REPO
from train_quality_recipes import prepare as prepare_recipes
from train_reviewed_shadow_trial import worker
from train_v43_quality_trial import live

CONTROL = REPO / ".cache/current-quality-20261023-v1/raw-global-conditioned-pilot-v1/run"


def prepare(root):
    import yaml

    recipe = REPO / "configs/quality-v120-raw-patch-memory-pilot-v140.yaml"
    baseline = REPO / "configs/quality-v120-raw-global-memory-only-pilot-v139.yaml"
    candidate, original = [yaml.safe_load(p.read_text()) for p in (recipe, baseline)]
    assert candidate["model"]["raw_global_conditioning"] == "patch-memory-v4"
    assert original["model"]["raw_global_conditioning"] == "memory-only-v3"
    comparable = []
    for config in (candidate, original):
        value = {k: v for k, v in config.items() if k not in ("run", "experiment_notes")}
        value["model"] = {k: v for k, v in value["model"].items() if k != "raw_global_conditioning"}
        comparable.append(value)
    assert comparable[0] == comparable[1]
    assert candidate["raw_global_only"] is True and candidate["lr"] == 1e-3
    assert candidate["steps"] == 1000 and candidate["seed"] == 70
    control_plan = read(CONTROL / "plan.json")
    guard(control_plan)
    controls = {}
    for phase in ("CPU", "CUDA", "train"):
        binding = ref(CONTROL / f"{phase}-V137-result.json")
        result = read(binding["path"])
        assert result["status"] == "completed-conditioned-global-pilot-training-phase"
        assert result["arm"] == "V137" and result["phase"] == phase
        assert result["updates"] == (1000 if phase == "train" else 18)
        assert not live(result["owner"]) and result["model_EMA_Adam_finite"]
        assert ref(result["checkpoint"]["path"]) == result["checkpoint"]
        controls[phase] = binding
    path = prepare_recipes(root, root / "work/artifacts", [recipe])
    plan = read(path)
    work = Path(plan["work"])
    script, core = [
        work / "scripts" / n for n in (Path(__file__).name, "train_reviewed_shadow_trial.py")
    ]
    shutil.copyfile(__file__, script)
    shutil.copyfile(REPO / "scripts/train_reviewed_shadow_trial.py", core)
    cpu = Path(plan["arms"]["V140"]["CPU"])
    actual = yaml.safe_load(cpu.read_text())
    actual["patch_size"] = 128
    cpu.write_text(yaml.safe_dump(actual, sort_keys=False))
    changes = (
        ("disabled", False),
        ("nonboolean", 1),
        ("legacy", "legacy-v1"),
        ("conditioned", "cosine-rms-v2"),
        ("memory", "memory-only-v3"),
        ("invalid_mode", "invalid"),
        ("scope", False),
        ("nonboolean_scope", 1),
    )
    for phase in ("CPU", "CUDA"):
        for change, value in changes:
            config = yaml.safe_load(Path(plan["arms"]["V140"][phase]).read_text())
            if change in ("scope", "nonboolean_scope"):
                config["raw_global_only"] = value
            else:
                key = (
                    "raw_global_features"
                    if change in ("disabled", "nonboolean")
                    else "raw_global_conditioning"
                )
                config["model"][key] = value
            config["run"] += f"-rejected-{change}-resume"
            target = work / "configs" / f"{phase}-V140-rejected-{change}.yaml"
            target.write_text(yaml.safe_dump(config, sort_keys=False))
            plan["arms"]["V140"][f"{phase}_rejected_{change}"] = str(target)
    plan.update(
        worker_script=ref(script),
        core_worker_script=ref(core),
        arm_fractions={"V140": 0.0},
        restoration_tensors_by_arm={"V140": 107},
        saved_control_arm="V137",
        matched_control_results=controls,
        require_matched_clean_inputs=True,
        require_matched_noisy_inputs=True,
        capture_initial_outputs=True,
        require_equal_initial_outputs=True,
        phase_result_status="completed-patch-memory-global-implementation-check",
        resume_rejection_changes=[name for name, _ in changes],
        resume_rejection_error_keyword="global",
        rejection_result_key="changed_global_resume_rejections",
        smoke_updates=16,
        resume_new_updates=2,
        train_updates=1000,
        launch_available_RAM_GiB=50,
        launch_available_RAM_GiB_by_phase={"CPU": 40},
        runtime_available_RAM_GB=32,
        CUDA_allocator_cap_GiB=12,
        maximum_smoke_worker_seconds=1800,
        production_launched=False,
        scope=(
            "V140 patch-memory-v4 engineering checks: add eight neighboring signed-gradient vectors "
            "through a zero-initialized2048-parameter projection before memory-only matching. "
            "16tensors16192params;91V120 parent model/EMA frozen. Same data/seed/LR/scope asV139. "
            "Reuse savedV137 clean/noisy streams and initial zero-branch output controls for "
            "CPU128B1FP32/CUDA256B16BF16 discarded16+2 checks;8 changed-mode/scope resumes perdevice "
            "reject beforeconstruction.107modelEMA/16Adam finite. CPU40GiB,CUDACheck50GiB admission, "
            "12GiB allocator cap,32GB floor,30min/check. Original jobs and52GiB policies unchanged. "
            "No old control inference, retry, schedule reset or production/quality launch here. "
            "The1000-update recipe is a future declared horizon; trained quality remains unmeasured. "
            "Any later review must compare V139 with matched inputs and publish nativeGT triplets, "
            "main3879/3880 and corrected3842/3835+JPEGs."
        ),
    )
    plan["inputs"] += [ref(baseline), ref(CONTROL / "plan.json"), *controls.values()]
    plan["frozen_files"] = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    save(path, plan)
    guard(plan)
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "worker"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--phase", choices=("CPU", "CUDA"))
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path.resolve()))
    else:
        if args.phase is None:
            parser.error("worker requires an explicit CPU or CUDA phase")
        plan = read(args.path)
        guard(plan)
        threshold = plan["launch_available_RAM_GiB_by_phase"].get(
            args.phase, plan["launch_available_RAM_GiB"]
        )
        assert psutil.virtual_memory().available >= threshold * 2**30
        assert (
            shutil.disk_usage(args.path.parent).free
            >= plan["phase_start_internal_free_GiB"] * 2**30
        )
        assert (
            shutil.disk_usage("/mnt/external").free >= plan["phase_start_external_free_GiB"] * 2**30
        )
        worker(args.path.resolve(), args.phase, "V140")
