"""Train V143 for5000 with crossed-line data, smaller gradient epsilon and retained prefixes."""

import argparse
import shutil
from pathlib import Path

import yaml
from train_directional_bank_trial import guard, read, ref, save
from train_quality_recipes import controller
from train_quality_recipes import prepare as prepare_recipes
from train_reviewed_shadow_trial import worker

REPO = Path(__file__).resolve().parents[1]
CONTROL = REPO / ".cache/quality-20261102/V142-crossed-line-v1"


def domain_counts(steps):
    from collections import Counter

    from demosaic.train import training_domain

    return dict(Counter(training_domain(i, 70, 0.25, 0.25) for i in range(1, steps + 1)))


def prepare(root):
    recipe = REPO / "configs/quality-v120-crossed-gradient5000-v143.yaml"
    config = yaml.safe_load(recipe.read_text())
    baseline = yaml.safe_load(
        (REPO / "configs/quality-v120-crossed-line-pilot-v142.yaml").read_text()
    )
    ignore = {"run", "experiment_notes", "gradient_charbonnier_epsilon", "steps"}
    assert {k: v for k, v in config.items() if k not in ignore} == {
        k: v for k, v in baseline.items() if k not in ignore
    }
    assert config["mesh_texture_fraction"] == 0.1
    assert config["gradient_charbonnier_epsilon"] == 0.00003 and config["steps"] == 5000
    path = prepare_recipes(root, root / "work/artifacts", [recipe])
    plan = read(path)
    work = Path(plan["work"])
    for name in ("train_reviewed_shadow_trial.py", Path(__file__).name):
        shutil.copyfile(REPO / "scripts" / name, work / "scripts" / name)
    for phase in ("CPU", "CUDA"):
        p = Path(plan["arms"]["V143"][phase])
        actual = yaml.safe_load(p.read_text())
        if phase == "CPU":
            actual["patch_size"] = 128
        p.write_text(yaml.safe_dump(actual, sort_keys=False))
        for name, value in (("inherited", None), ("invalid", 0)):
            changed = {
                **actual,
                "gradient_charbonnier_epsilon": value,
                "run": actual["run"] + "-rejected-" + name,
            }
            destination = work / "configs" / f"{phase}-V143-rejected-{name}.yaml"
            destination.write_text(yaml.safe_dump(changed, sort_keys=False))
            plan["arms"]["V143"][f"{phase}_rejected_{name}"] = str(destination)
    controls = {phase: ref(CONTROL / f"{phase}-V142-result.json") for phase in ("CPU", "CUDA")}
    plan.update(
        worker_script=ref(work / "scripts" / Path(__file__).name),
        core_worker_script=ref(work / "scripts/train_reviewed_shadow_trial.py"),
        smoke_updates=16,
        resume_new_updates=2,
        arm_fractions={"V143": 0.0},
        restoration_tensors_by_arm={"V143": 91},
        saved_control_arm="V142",
        matched_control_results=controls,
        require_matched_clean_inputs=True,
        require_matched_noisy_inputs=True,
        matched_input_arms=[],
        require_unchanged_noncommons_inputs=True,
        capture_initial_outputs=True,
        require_equal_initial_outputs=True,
        resume_rejection_changes=["inherited", "invalid"],
        resume_rejection_error_keyword="epsilon",
        rejection_result_key="changed_gradient_resume_rejections",
        phase_result_status="completed-crossed-gradient5000-training-phase",
        CUDA_allocator_cap_GiB=12,
        maximum_smoke_worker_seconds=1800,
        maximum_train_worker_seconds=28800,
        launch_available_RAM_GiB_by_phase={"CPU": 40, "CUDA": 50, "train": 50},
        expected_train_validation_forwards=320,
        progress_steps=[1000, 2500],
        prospective_domain_batches=domain_counts(5000),
        prefix_control_result=ref(CONTROL / "train-V142-result.json"),
        scope="V143 fresh5000 from V120: V142 crossed-line/empty data.10 within.15 weak quota, "
        "gradient epsilon3e-5 from V141, pixel3e-4. Keep90782/27seed70/quota.5/zeroPSF/native256B16BF16/"
        "LR1e-5/warm100. Combined horizon+gradient intervention versus V1421k, not equal-budget/isolated causality. "
        "Genuine CPU128B1/CUDA256B16 discarded16+2 must match V142 clean/noisy inputs and first outputs. "
        "Train first18 must match CUDA check; compare first1000 input hashes with V142 at progress binding. "
        "Original5000 budget, retained1000/2500 prefixes,12GiB CUDA cap/32GB runtime floor/8h bound, no retry/reset. "
        "Fixed native/faint/bothGFX/mesh-priors/JPEG/exact-flat reviews required; no gain claimed.",
    )
    plan["inputs"] += [
        *controls.values(),
        ref(CONTROL / "plan.json"),
        plan["prefix_control_result"],
    ]
    plan["frozen_files"] = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    save(path, plan)
    guard(plan)
    return path


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("prepare", "controller", "worker"))
    p.add_argument("path", type=Path)
    p.add_argument("--phase", choices=("CPU", "CUDA", "train"))
    p.add_argument("--arm", default="V143")
    args = p.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path.resolve()))
    elif args.mode == "controller":
        controller(args.path.resolve())
    else:
        assert args.arm == "V143"
        worker(args.path.resolve(), args.phase, args.arm)
