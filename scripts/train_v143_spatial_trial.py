"""Matched V144/V145 local-RAW-attention pilot, initialized from V143 EMA."""

import argparse
import shutil
from collections import Counter
from pathlib import Path

import yaml
from train_directional_bank_trial import guard, read, ref, save
from train_quality_recipes import controller
from train_quality_recipes import prepare as prepare_recipes
from train_reviewed_shadow_trial import worker

REPO = Path(__file__).resolve().parents[1]


def prepare(root):
    from demosaic.train import training_domain

    recipes = [
        REPO / f"configs/quality-v143-spatial-{name}-v{version}.yaml"
        for name, version in (("control", 144), ("attention", 145))
    ]
    configs = [yaml.safe_load(p.read_text()) for p in recipes]
    ignored = {"run", "model", "raw_spatial_lr_multiplier"}
    assert {k: v for k, v in configs[0].items() if k not in ignored} == {
        k: v for k, v in configs[1].items() if k not in ignored
    }
    assert configs[1]["model"] == {**configs[0]["model"], "raw_spatial_features": True}
    assert configs[1]["raw_spatial_lr_multiplier"] == 100
    assert configs[0]["steps"] == 1000 and configs[0]["seed"] == 144
    path = prepare_recipes(root, root / "work/artifacts", recipes)
    plan = read(path)
    work = Path(plan["work"])
    for name in ("train_reviewed_shadow_trial.py", Path(__file__).name):
        shutil.copyfile(REPO / "scripts" / name, work / "scripts" / name)
    for arm in plan["arms"]:
        for phase in ("CPU", "CUDA"):
            p = Path(plan["arms"][arm][phase])
            actual = yaml.safe_load(p.read_text())
            if phase == "CPU":
                actual["patch_size"] = 128
                p.write_text(yaml.safe_dump(actual, sort_keys=False))
            changed = {
                **actual,
                "raw_spatial_lr_multiplier": 1 if arm == "V145" else 2,
                "run": actual["run"] + "-rejected-rate",
            }
            destination = work / "configs" / f"{phase}-{arm}-rejected-rate.yaml"
            destination.write_text(yaml.safe_dump(changed, sort_keys=False))
            plan["arms"][arm][f"{phase}_rejected_rate"] = str(destination)
    plan.update(
        worker_script=ref(work / "scripts" / Path(__file__).name),
        core_worker_script=ref(work / "scripts/train_reviewed_shadow_trial.py"),
        parent_step=5000,
        smoke_updates=16,
        resume_new_updates=2,
        arm_fractions={"V144": 0.0, "V145": 0.0},
        restoration_tensors_by_arm={"V144": 91, "V145": 114},
        paired_control_arm="V144",
        capture_initial_outputs=True,
        require_equal_initial_outputs=True,
        require_matched_clean_inputs=True,
        require_matched_noisy_inputs=True,
        matched_input_arms=["V145"],
        resume_rejection_changes=["rate"],
        resume_rejection_error_keyword="spatial",
        rejection_result_key="changed_spatial_rate_resume_rejections",
        phase_result_status="completed-v143-spatial-training-phase",
        CUDA_allocator_cap_GiB=12,
        maximum_smoke_worker_seconds=1800,
        maximum_train_worker_seconds=28800,
        launch_available_RAM_GiB_by_phase={"CPU": 40, "CUDA": 50, "train": 50},
        expected_train_validation_forwards=64,
        prospective_domain_batches=dict(
            Counter(training_domain(i, 144, 0.25, 0.25) for i in range(1, 1001))
        ),
        scope="Matched fresh1000 from V1435k EMA: V144 control, V145 existing local RAW "
        "attention with 100x branch LR. Trunk LR1e-5; same seed144/V143 data and loss. "
        "Combined architecture+rate intervention. CPU128B1/CUDA256B16 discarded16+2, "
        "all input hashes and first outputs matched. Frozen official DINOv3,12GiB CUDA "
        "cap,32GB RAM runtime floor. No dataz. Native/faint/GFX/JPEG/flat quality pending.",
    )
    plan["frozen_files"] = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    save(path, plan)
    guard(plan)
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller", "worker"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--phase", choices=("CPU", "CUDA", "train"))
    parser.add_argument("--arm", choices=("V144", "V145"))
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path.resolve()))
    elif args.mode == "controller":
        controller(args.path.resolve())
    else:
        worker(args.path.resolve(), args.phase, args.arm)
