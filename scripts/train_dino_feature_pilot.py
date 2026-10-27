"""Test frozen early DINO supervision against the saved matched V126 control."""

import argparse
import shutil
from collections import Counter
from pathlib import Path

from train_directional_bank_trial import guard, read, ref, save
from train_quality_recipes import REPO, controller
from train_quality_recipes import prepare as prepare_recipes
from train_reviewed_shadow_trial import worker
from train_v43_quality_trial import live

CONTROL = REPO / ".cache/current-quality-20261023-v1/reviewed-shadow-training-pilot-v1/run"


def prepare(root):
    import yaml

    from demosaic.dino_supervision import POLICY, feature_options
    from demosaic.train import training_domain

    recipe = REPO / "configs/quality-v120-dino-feature-pilot-v128.yaml"
    original = REPO / "configs/quality-v120-reviewed-shadow-pilot-v126.yaml"
    config, baseline = [yaml.safe_load(p.read_text()) for p in (recipe, original)]
    ignored = {"run", "experiment_notes", "dino_feature_weight", "dino_feature_policy"}
    assert {k: v for k, v in config.items() if k not in ignored} == {
        k: v for k, v in baseline.items() if k not in ignored
    }
    assert feature_options(config) == (0.1, POLICY)
    assert feature_options(baseline) == (0, None)
    control_plan = read(CONTROL / "plan.json")
    guard(control_plan)
    controls = {}
    for phase in ("CPU", "CUDA", "train"):
        binding = ref(CONTROL / f"{phase}-V126-result.json")
        result = read(binding["path"])
        assert result["status"] == "completed-shadow-training-phase"
        assert result["phase"] == phase and result["arm"] == "V126"
        assert not live(result["owner"])
        assert result["updates"] == (1000 if phase == "train" else 18)
        assert len(result["observed_inputs"]) == result["updates"]
        assert ref(result["checkpoint"]["path"]) == result["checkpoint"]
        controls[phase] = binding
    path = prepare_recipes(root, root / "work/artifacts", [recipe])
    plan = read(path)
    work = Path(plan["work"])
    script = work / "scripts/train_dino_feature_pilot.py"
    core = work / "scripts/train_reviewed_shadow_trial.py"
    shutil.copyfile(__file__, script)
    shutil.copyfile(REPO / "scripts/train_reviewed_shadow_trial.py", core)
    cpu = Path(plan["arms"]["V128"]["CPU"])
    actual = yaml.safe_load(cpu.read_text())
    actual["patch_size"] = 128
    cpu.write_text(yaml.safe_dump(actual, sort_keys=False))
    for phase in ("CPU", "CUDA"):
        for change in ("weight", "policy"):
            actual = yaml.safe_load(Path(plan["arms"]["V128"][phase]).read_text())
            actual["dino_feature_" + change] = (
                0.2 if change == "weight" else "unknown-feature-policy"
            )
            actual["run"] += f"-rejected-{change}-resume"
            dest = work / "configs" / f"{phase}-V128-rejected-{change}.yaml"
            dest.write_text(yaml.safe_dump(actual, sort_keys=False))
            plan["arms"]["V128"][f"{phase}_rejected_{change}"] = str(dest)
    plan.update(
        worker_script=ref(script),
        core_worker_script=ref(core),
        arm_fractions={"V128": 0.0},
        matched_control_results=controls,
        require_matched_noisy_inputs=True,
        phase_result_status="completed-dino-feature-training-phase",
        resume_rejection_changes=["weight", "policy"],
        resume_rejection_error_keyword="feature",
        rejection_result_key="changed_feature_resume_rejections",
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
            "One new V1281000-update candidate, matched to completed V1261000 control. "
            "V120 EMA parent/seed70/90783photos/23ROIs/fraction.5; native256/B16/BF16/"
            "single noise view/zeroPSF/LR1e-5/warm100/paired32/native128 unchanged. "
            "Only addition: weight.1 frozen spatial stage0 feature MSE on sensor-valid "
            "Commons/native cameraRGB, never paired or validation. No new inference "
            "parameters. Discarded CPU128/B1 and CUDA256/B16 16+2 resume checks; "
            "all1000 clean/noisy batch hashes must match saved V126. Reuse control "
            "checks and endpoint; no repeated training/old neural predictions. "
            "Budget:36 new check updates plus1000 fresh pilot updates,8h production,"
            "30min/check,16GiB CUDAcap+4GiB host+32GiB available reserve. No automatic "
            "retry, reset, or budget extension. Quality remains unproven."
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
    parser.add_argument("--arm", choices=("V128",))
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path.resolve()))
    elif args.mode == "controller":
        controller(args.path.resolve())
    else:
        worker(args.path.resolve(), args.phase, args.arm)
