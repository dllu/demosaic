"""Source-frozen V143 frequency-only pilot with larger coherent context."""

import argparse
import os
import shutil
from collections import Counter
from pathlib import Path

import yaml
from train_directional_bank_trial import guard, read, ref, save
from train_quality_recipes import controller
from train_quality_recipes import prepare as prepare_recipes
from train_raw_frequency_trial import worker

REPO = Path(__file__).resolve().parents[1]


def prepare(root):
    from demosaic.train import training_domain

    recipe = REPO / "configs/quality-v143-coherent-frequency-v146.yaml"
    config = yaml.safe_load(recipe.read_text())
    assert config["steps"] == 500 and config["seed"] == 146
    assert config["model"]["raw_frequency_window"] == 128
    assert config["raw_frequency_only"] is True and config["lr"] == 0.001
    assert config["mesh_texture_fraction"] == 0.6
    path = prepare_recipes(root, root / "work/artifacts", [recipe])
    plan = read(path)
    work = Path(plan["work"])
    for name in (Path(__file__).name, "train_raw_frequency_trial.py"):
        shutil.copyfile(REPO / "scripts" / name, work / "scripts" / name)
    for phase in ("CPU", "CUDA"):
        p = Path(plan["arms"]["V146"][phase])
        actual = yaml.safe_load(p.read_text())
        if phase == "CPU":
            actual["patch_size"] = 128
            p.write_text(yaml.safe_dump(actual, sort_keys=False))
        for change in ("resume", "window"):
            altered = yaml.safe_load(p.read_text())
            altered["run"] += f"-rejected-{change}"
            if change == "resume":
                altered["raw_frequency_only"] = False
            else:
                altered["model"]["raw_frequency_window"] = 64
            dest = work / "configs" / f"{phase}-V146-rejected-{change}.yaml"
            dest.write_text(yaml.safe_dump(altered, sort_keys=False))
            plan["arms"]["V146"][phase + "_rejected_" + change] = str(dest)
    plan.update(
        worker_script=ref(work / "scripts" / Path(__file__).name),
        core_worker_script=ref(work / "scripts/train_raw_frequency_trial.py"),
        arm_scopes={"V146": True},
        parent_step=5000,
        smoke_updates=16,
        resume_new_updates=2,
        trace_all_batches=True,
        expected_train_validation_forwards=32,
        launch_available_RAM_GiB=52,
        runtime_available_RAM_GB=32,
        CUDA_allocator_cap_GiB=12,
        maximum_smoke_worker_seconds=1800,
        maximum_train_worker_seconds=7200,
        prospective_domain_batches=dict(
            Counter(training_domain(i, 146, 0.25, 0.25) for i in range(1, 501))
        ),
        scope="Fresh500-update feasibility pilot from V1435k EMA; only3264 frequency "
        "parameters train. Native256/B16/BF16, packed Fourierwindow128(native256), "
        "mesh/weak/synthetic fractions.60/.65/.70 inside Commons,50% matched-empty "
        "mesh recipes. Paired/native domains remain.25 each. LR.001/warm100. "
        "Combined parent/context/data/LR intervention versus historicalV122; no "
        "isolated attribution. Official DINOv3 and all91 parent restoration tensors "
        "frozen. CPU128B1/CUDA256B16 discarded16+2, rejected scope/window resumes. "
        "No dataz. Quality pending on cached mesh/photo/flat/both real GFX scenes.",
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
    parser.add_argument("--arm", choices=("V146",))
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path.resolve()))
    elif args.mode == "controller":
        controller(args.path.resolve())
    else:
        os.nice(10)
        os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
        worker(args.path.resolve(), args.phase, args.arm)
