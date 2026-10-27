"""Train one conditioned global candidate against the retained V137 control."""

import argparse
import shutil
from collections import Counter
from pathlib import Path

from train_directional_bank_trial import guard, read, ref, save
from train_quality_recipes import REPO, controller
from train_quality_recipes import prepare as prepare_recipes
from train_reviewed_shadow_trial import worker
from train_v43_quality_trial import live

CONTROL = REPO / ".cache/current-quality-20261023-v1/raw-global-attention-pilot-v1/run"


def prepare(root):
    import yaml

    from demosaic.train import training_domain

    recipe = REPO / "configs/quality-v120-raw-global-conditioned-pilot-v137.yaml"
    original = REPO / "configs/quality-v120-raw-global-pilot-v136.yaml"
    candidate, baseline = [yaml.safe_load(p.read_text()) for p in (recipe, original)]
    ignored = {"run", "experiment_notes", "model"}
    assert {k: v for k, v in candidate.items() if k not in ignored} == {
        k: v for k, v in baseline.items() if k not in ignored
    }
    assert candidate["model"]["raw_global_features"] is True
    assert {
        k: v for k, v in candidate["model"].items() if k != "raw_global_conditioning"
    } == baseline["model"]
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
        binding = ref(CONTROL / f"{phase}-V136-result.json")
        result = read(binding["path"])
        assert result["status"] == "completed-global-attention-pilot-training-phase"
        assert result["arm"] == "V136" and result["phase"] == phase
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
    cpu = Path(plan["arms"]["V137"]["CPU"])
    actual = yaml.safe_load(cpu.read_text())
    actual["patch_size"] = 128
    cpu.write_text(yaml.safe_dump(actual, sort_keys=False))
    for phase in ("CPU", "CUDA"):
        for change, value in (
            ("disabled", False),
            ("nonboolean", 1),
            ("legacy", "legacy-v1"),
            ("invalid_mode", "invalid"),
        ):
            config = yaml.safe_load(Path(plan["arms"]["V137"][phase]).read_text())
            config["model"][
                "raw_global_features"
                if change in ("disabled", "nonboolean")
                else "raw_global_conditioning"
            ] = value
            config["run"] += f"-rejected-{change}-resume"
            target = work / "configs" / f"{phase}-V137-rejected-{change}.yaml"
            target.write_text(yaml.safe_dump(config, sort_keys=False))
            plan["arms"]["V137"][f"{phase}_rejected_{change}"] = str(target)
    plan.update(
        worker_script=ref(script),
        core_worker_script=ref(core),
        arm_fractions={"V137": 0.0},
        restoration_tensors_by_arm={"V137": 109},
        saved_control_arm="V136",
        matched_control_results=controls,
        require_matched_clean_inputs=True,
        require_matched_noisy_inputs=True,
        capture_initial_outputs=True,
        require_equal_initial_outputs=True,
        gradient_observation_steps=sorted({*range(1, 17), *range(25, 1001, 25)}),
        phase_result_status="completed-conditioned-global-pilot-training-phase",
        resume_rejection_changes=["disabled", "nonboolean", "legacy", "invalid_mode"],
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
        scope=(
            "One fresh1000-update V137 conditioned-global candidate versus saved completed V136. "
            "Exact V120 Small EMA/seed70/90782photos/27regions/quota.5/native256/B16/BF16/"
            "singleview/zeroPSF/LR1e-5/warm100; onlycosine-rms-v2 mixing differs; same18tensors18272params and initialvalues. "
            "All1000 clean/noisy hashes must match before candidate root calls; existing control "
            "never rerun. Fresh CPU128/B1 and CUDA256/B16 discarded16+2 checks with retained "
            "prefixes and disabled/nonboolean/legacy/invalid-mode resumes rejected before model construction.  "
            "109model/EMA107Adam; all18 branch gradients finite and nonzero. Firstactual root outputs match V136 exactly; record gradient steps1-16 plus every25 through1000.  CPU40GiB,CUDA/"
            "train52GiB admission,16GiBcap,32GB floor,30min/check,8h production. "
            "No automatic retry, schedule reset, new queued20k run or quality claim. "
            "All existing training/evaluation owners and frozen inputs remain unchanged."
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
    parser.add_argument("--arm", choices=("V137",))
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path.resolve()))
    elif args.mode == "controller":
        controller(args.path.resolve())
    else:
        worker(args.path.resolve(), args.phase, args.arm)
