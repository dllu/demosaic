"""Train a frozen-parent global branch against the retained V137 control."""

import argparse
import shutil
from collections import Counter
from pathlib import Path

from train_directional_bank_trial import guard, read, ref, save
from train_quality_recipes import REPO, controller
from train_quality_recipes import prepare as prepare_recipes
from train_reviewed_shadow_trial import worker
from train_v43_quality_trial import live

CONTROL = REPO / ".cache/current-quality-20261023-v1/raw-global-conditioned-pilot-v1/run"


def prepare(root):
    import yaml

    from demosaic.train import training_domain

    recipe = REPO / "configs/quality-v120-raw-global-only-pilot-v138.yaml"
    original = REPO / "configs/quality-v120-raw-global-conditioned-pilot-v137.yaml"
    candidate, baseline = [yaml.safe_load(p.read_text()) for p in (recipe, original)]
    ignored = {"run", "experiment_notes", "raw_global_only", "lr"}
    assert {k: v for k, v in candidate.items() if k not in ignored} == {
        k: v for k, v in baseline.items() if k not in ignored
    }
    assert candidate["model"] == baseline["model"]
    assert candidate["raw_global_only"] is True
    assert candidate["lr"] == 1e-3 and baseline["lr"] == 1e-5
    assert candidate["model"]["raw_global_conditioning"] == "cosine-rms-v2"
    assert candidate["steps"] == 1000 and candidate["seed"] == 70
    control_plan = read(CONTROL / "plan.json")
    guard(control_plan)
    status = read(CONTROL / "status.json")
    assert status["status"] == "completed-training-awaiting-model-comparisons"
    assert not live(status["controller"])
    assert status.get("child") is None or not live(status["child"])
    controls = {}
    for phase in ("CPU", "CUDA", "train"):
        binding = ref(CONTROL / f"{phase}-V137-result.json")
        result = read(binding["path"])
        assert result["status"] == "completed-conditioned-global-pilot-training-phase"
        assert result["arm"] == "V137" and result["phase"] == phase
        assert result["updates"] == (1000 if phase == "train" else 18)
        assert not live(result["owner"])
        assert len(result["observed_inputs"]) == result["updates"]
        assert result["model_EMA_Adam_finite"] and result["optimizer_state_count"] == 107
        assert ref(result["checkpoint"]["path"]) == result["checkpoint"]
        controls[phase] = binding
    path = prepare_recipes(root, root / "work/artifacts", [recipe])
    plan = read(path)
    work = Path(plan["work"])
    script, core = [
        work / "scripts" / n for n in [Path(__file__).name, "train_reviewed_shadow_trial.py"]
    ]
    shutil.copyfile(__file__, script)
    shutil.copyfile(REPO / "scripts/train_reviewed_shadow_trial.py", core)
    cpu = Path(plan["arms"]["V138"]["CPU"])
    actual = yaml.safe_load(cpu.read_text())
    actual["patch_size"] = 128
    cpu.write_text(yaml.safe_dump(actual, sort_keys=False))
    for phase in ("CPU", "CUDA"):
        for change, value in (
            ("disabled", False),
            ("nonboolean", 1),
            ("legacy", "legacy-v1"),
            ("invalid_mode", "invalid"),
            ("scope", False),
            ("nonboolean_scope", 1),
        ):
            config = yaml.safe_load(Path(plan["arms"]["V138"][phase]).read_text())
            if change in ("scope", "nonboolean_scope"):
                config["raw_global_only"] = value
            else:
                config["model"][
                    "raw_global_features"
                    if change in ("disabled", "nonboolean")
                    else "raw_global_conditioning"
                ] = value
            config["run"] += f"-rejected-{change}-resume"
            target = work / "configs" / f"{phase}-V138-rejected-{change}.yaml"
            target.write_text(yaml.safe_dump(config, sort_keys=False))
            plan["arms"]["V138"][f"{phase}_rejected_{change}"] = str(target)
    plan.update(
        worker_script=ref(script),
        core_worker_script=ref(core),
        arm_fractions={"V138": 0.0},
        restoration_tensors_by_arm={"V138": 109},
        saved_control_arm="V137",
        matched_control_results=controls,
        require_matched_clean_inputs=True,
        require_matched_noisy_inputs=True,
        capture_initial_outputs=True,
        require_equal_initial_outputs=True,
        gradient_observation_steps=sorted({*range(1, 17), *range(25, 1001, 25)}),
        phase_result_status="completed-global-only-pilot-training-phase",
        resume_rejection_changes=[
            "disabled",
            "nonboolean",
            "legacy",
            "invalid_mode",
            "scope",
            "nonboolean_scope",
        ],
        resume_rejection_error_keyword="global",
        rejection_result_key="changed_global_resume_rejections",
        smoke_updates=16,
        resume_new_updates=2,
        train_updates=1000,
        launch_available_RAM_GiB=52,
        launch_available_RAM_GiB_by_phase={"CPU": 40},
        runtime_available_RAM_GB=32,
        CUDA_allocator_cap_GiB=16,
        maximum_train_worker_seconds=28800,
        maximum_smoke_worker_seconds=1800,
        prospective_domain_batches=dict(
            Counter(training_domain(s, 70, 0.25, 0.25) for s in range(1, 1001))
        ),
        before_train_admission=dict(
            read(
                REPO / ".cache/current-quality-20261023-v1/"
                "raw-spatial-training-admission-v2/run/plan.json"
            )["before_train_admission"],
            require_completed=True,
        ),
        scope=(
            "Fresh1000-update V138 from V120: train only18 global tensors18272parameters "
            "atLR1e-3; all91 common model andEMA tensors stay exactV120. Samecosine-rms-v2 "
            "branch/initialization asV137, seed70/90782photos/27regions/quota.5/256B16BF16/"
            "singleview/zeroPSF/warm100. Compare savedV137jointLR1e-5; combined scope+LR "
            "intervention, not an isolatedLR ablation. All1000 clean/noisy hashes andfirstactual "
            "outputs must match control. FreshCPU128B1/CUDA256B16 discarded16+2 with12 "
            "scope/operator rejections before construction;109modelEMA/18Adam finite. "
            "CPU40GiB,CUDATrain52GiB admission/16GiBcap/32GBfloor,30mincheck/8hproduction. "
            "Production waits for originalV125 completion. No oldcontrols rerun, retries, "
            "schedule reset,20k run or quality claim. Existingplans/budgets/data unchanged."
        ),
    )
    plan["inputs"] += [
        ref(original),
        ref(CONTROL / "plan.json"),
        *controls.values(),
        ref(
            REPO / ".cache/current-quality-20261023-v1/"
            "raw-spatial-training-admission-v2/run/plan.json"
        ),
    ]
    plan["frozen_files"] = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    save(path, plan)
    guard(plan)
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller", "worker"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--phase", choices=("CPU", "CUDA", "train"))
    parser.add_argument("--arm", choices=("V138",))
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path.resolve()))
    elif args.mode == "controller":
        controller(args.path.resolve())
    else:
        worker(args.path.resolve(), args.phase, args.arm)
