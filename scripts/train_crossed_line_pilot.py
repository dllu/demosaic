"""Run V142's data-only pilot with actual prefix and non-Commons witnesses."""

import argparse
import shutil
from pathlib import Path

import yaml
from train_directional_bank_trial import guard, read, ref, save
from train_quality_recipes import controller
from train_quality_recipes import prepare as prepare_recipes
from train_reviewed_shadow_trial import worker

REPO = Path(__file__).resolve().parents[1]
CONTROL = REPO / ".cache/current-quality-20261023-v1/reviewed-detail-training-pilot-v1/run"


def prepare(root):
    recipe = REPO / "configs/quality-v120-crossed-line-pilot-v142.yaml"
    config = yaml.safe_load(recipe.read_text())
    baseline = yaml.safe_load(
        (REPO / "configs/quality-v120-reviewed-detail-pilot-v129.yaml").read_text()
    )
    ignore = {"run", "experiment_notes", "mesh_texture_fraction"}
    assert {k: v for k, v in config.items() if k not in ignore} == {
        k: v for k, v in baseline.items() if k not in ignore
    }
    assert config["mesh_texture_fraction"] == 0.1
    path = prepare_recipes(root, root / "work/artifacts", [recipe])
    plan = read(path)
    work = Path(plan["work"])
    for name in ("train_reviewed_shadow_trial.py", Path(__file__).name):
        shutil.copyfile(REPO / "scripts" / name, work / "scripts" / name)
    for phase in ("CPU", "CUDA"):
        p = Path(plan["arms"]["V142"][phase])
        actual = yaml.safe_load(p.read_text())
        if phase == "CPU":
            actual["patch_size"] = 128
        p.write_text(yaml.safe_dump(actual, sort_keys=False))
        for name, value in (("disabled", 0), ("invalid", 2)):
            changed = {
                **actual,
                "mesh_texture_fraction": value,
                "run": actual["run"] + "-rejected-" + name,
            }
            destination = work / "configs" / f"{phase}-V142-rejected-{name}.yaml"
            destination.write_text(yaml.safe_dump(changed, sort_keys=False))
            plan["arms"]["V142"][f"{phase}_rejected_{name}"] = str(destination)
    controls = {
        phase: ref(CONTROL / f"{phase}-V129-result.json") for phase in ("CPU", "CUDA", "train")
    }
    plan.update(
        worker_script=ref(work / "scripts" / Path(__file__).name),
        core_worker_script=ref(work / "scripts/train_reviewed_shadow_trial.py"),
        smoke_updates=16,
        resume_new_updates=2,
        arm_fractions={"V142": 0.0},
        restoration_tensors_by_arm={"V142": 91},
        saved_control_arm="V129",
        matched_control_results=controls,
        require_matched_clean_inputs=False,
        require_matched_noisy_inputs=False,
        require_unchanged_noncommons_inputs=True,
        capture_initial_outputs=True,
        require_equal_initial_outputs=False,
        resume_rejection_changes=["disabled", "invalid"],
        resume_rejection_error_keyword="mesh",
        rejection_result_key="changed_mesh_resume_rejections",
        phase_result_status="completed-crossed-line-data-pilot-phase",
        CUDA_allocator_cap_GiB=12,
        maximum_smoke_worker_seconds=1800,
        maximum_train_worker_seconds=28800,
        launch_available_RAM_GiB_by_phase={"CPU": 40, "CUDA": 50, "train": 50},
        prospective_domain_batches=read(CONTROL / "plan.json")["prospective_domain_batches"],
        scope="V142 fresh1000 data-only from V120 versus savedV129: same90782/27seed70/quota.5/"
        "zeroPSF/native256B16BF16/LR1e-5/warm100/pixel+gradient epsilon3e-4. Replace.10 "
        "of existing.15 weak quota with crossed-line/empty sources; half absent. All native/paired "
        "clean/noisy batches must match V129; Commons intentionally changes. CPU128B1/CUDA256B16 "
        "discarded16+2 first,12GiB CUDA cap/32GB runtime floor/8h original1k bound, no retry/reset. "
        "Matched native/GFX/uniform-field quality still required; no gain claimed.",
    )
    plan["inputs"] += [*controls.values(), ref(CONTROL / "plan.json")]
    plan["frozen_files"] = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    save(path, plan)
    guard(plan)
    return path


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("prepare", "controller", "worker"))
    p.add_argument("path", type=Path)
    p.add_argument("--phase", choices=("CPU", "CUDA", "train"))
    p.add_argument("--arm", default="V142")
    args = p.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path.resolve()))
    elif args.mode == "controller":
        controller(args.path.resolve())
    else:
        assert args.arm == "V142"
        worker(args.path.resolve(), args.phase, args.arm)
