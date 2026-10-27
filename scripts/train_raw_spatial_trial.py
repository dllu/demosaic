"""Train matched full-horizon V131/V132 spatial-detail continuations."""

import argparse
import shutil
from collections import Counter
from pathlib import Path

from train_directional_bank_trial import guard, read, ref, save
from train_quality_recipes import REPO, controller
from train_quality_recipes import prepare as prepare_recipes
from train_reviewed_shadow_trial import worker
from train_v43_quality_trial import live

ARMS = ("V131", "V132")


def validate_recipes(configs):
    """Allow only the declared architecture difference within the matched pair."""
    import copy

    normalized = []
    for config, spatial in zip(configs, (False, True), strict=True):
        value = copy.deepcopy(config)
        assert value["model"].pop("raw_spatial_features") is spatial
        for key in ("run", "experiment_notes"):
            value.pop(key)
        normalized.append(value)
    assert normalized[0] == normalized[1], "Matched training recipes differ beyond the spatial flag"
    config = configs[0]
    assert config["steps"] == 20000 and config["seed"] == 70
    assert config["checkpoint_every"] == 1000
    assert config["precision"] == "bfloat16" and config["batch_size"] == 16
    assert config["patch_size"] == 256 and config["reviewed_roi_fraction"] == 0.5
    assert config["paired_fraction"] == config["raw_clean_fraction"] == 0.25
    assert config["noise_pair_draws"] == 1 and config["conditional_mean_weight"] == 0
    assert config["reviewed_shadow_fraction"] == 0 and config["reviewed_shadow_policy"] is None
    assert config.get("dino_feature_weight", 0) == config["normalized_band_weight"] == 0
    assert config["optical_blur_probability"] == config["raw_clean_optical_blur_probability"] == 0
    assert config["reviewed_roi_catalogue"] == str(
        REPO / "configs/low-contrast-training-rois-cleaned90781-v1.json"
    )


def prepare(root):
    import yaml

    from demosaic.shadow_exposure import POLICY
    from demosaic.train import training_domain

    recipes = [REPO / f"configs/quality-v120-raw-spatial-v{v}.yaml" for v in (131, 132)]
    configs = [yaml.safe_load(p.read_text()) for p in recipes]
    validate_recipes(configs)
    catalogue = read(configs[0]["reviewed_roi_catalogue"])
    assert len(catalogue["examples"]) == 29
    assert ref(configs[0]["manifest"]) == catalogue["source_manifest"]
    path = prepare_recipes(root, root / "work/artifacts", recipes)
    plan = read(path)
    work = Path(plan["work"])
    script = work / "scripts/train_raw_spatial_trial.py"
    core = work / "scripts/train_reviewed_shadow_trial.py"
    shutil.copyfile(__file__, script)
    shutil.copyfile(REPO / "scripts/train_reviewed_shadow_trial.py", core)
    for arm in ARMS:
        cpu = Path(plan["arms"][arm]["CPU"])
        config = yaml.safe_load(cpu.read_text())
        config["patch_size"] = 128
        cpu.write_text(yaml.safe_dump(config, sort_keys=False))
        for phase in ("CPU", "CUDA"):
            for change in ("fraction", "policy"):
                config = yaml.safe_load(Path(plan["arms"][arm][phase]).read_text())
                if change == "fraction":
                    config.update(reviewed_shadow_fraction=0.5, reviewed_shadow_policy=POLICY)
                else:
                    config["reviewed_shadow_policy"] = "unknown-shadow-policy"
                config["run"] += f"-rejected-{change}-resume"
                dest = work / "configs" / f"{phase}-{arm}-rejected-{change}.yaml"
                dest.write_text(yaml.safe_dump(config, sort_keys=False))
                plan["arms"][arm][f"{phase}_rejected_{change}"] = str(dest)
    plan.update(
        worker_script=ref(script),
        core_worker_script=ref(core),
        training_format="matched-raw-spatial-v1",
        arm_fractions=dict.fromkeys(ARMS, 0.0),
        paired_control_arm="V131",
        require_matched_clean_inputs=True,
        require_matched_noisy_inputs=True,
        matched_input_arms=["V132"],
        require_equal_initial_outputs=True,
        restoration_tensors_by_arm={"V131": 91, "V132": 114},
        phase_result_status="completed-raw-spatial-training-phase",
        smoke_updates=16,
        resume_new_updates=2,
        expected_train_validation_forwards=640,
        progress_steps=[1000],
        launch_available_RAM_GiB=52,
        runtime_available_RAM_GB=32,
        CUDA_allocator_cap_GiB=16,
        maximum_train_worker_seconds=172800,
        maximum_smoke_worker_seconds=1800,
        prospective_domain_batches=dict(
            Counter(training_domain(s, 70, 0.25, 0.25) for s in range(1, 20001))
        ),
        production_scope="Completed full20000-update endpoint; independent numerical and native photographic/GFX review pending.",
        scope=(
            "Fresh matched V120-EMA continuations, V131 control and V132 spatial branch. "
            "Both cleaned90781/29ROIs, seed70/native256/B16/BF16/single-view, LR1e-5/"
            "warm100/cosine20000, zeroPSF, paired32/native128. Only raw_spatial_features "
            "differs. Enforce all20000 clean/noisy input hashes and exact first outputs "
            "per device. CPU128/B1 and CUDA256/B16 actual16+2 discarded checks for each "
            "arm precede40000 fresh production updates. Each arm has640 validation and "
            "20640 encoder calls,320000 target contexts. Retain step1000 within the same "
            "live worker and original20k horizon; it is progress, not a completed endpoint. "
            "Sequential arms, one extra worker beside original V124/V125.30min percheck,"
            "48h perproduction worker,52GiB admission/16GiB CUDAcap/32GB runtime floor; "
            "no automatic retry/reset/budget extension or existing-source/control replay."
        ),
    )
    plan["frozen_files"] = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    save(path, plan)
    guard(plan)
    return path


def adopt_checks_after_admission(root, original_path, dependency_path):
    """Reuse completed checks and protect the original mean-loss admission window."""
    import train_quality_recipes

    root, original_path, dependency_path = (
        Path(p).resolve() for p in (root, original_path, dependency_path)
    )
    assert root.is_relative_to(REPO / ".cache") and not root.exists()
    original, dependency = read(original_path), read(dependency_path)
    guard(original)
    guard(dependency)
    previous_root = Path(original["root"])
    handoff = read(previous_root / "admission-handoff-v1.json")
    assert handoff["original_plan"] == ref(original_path)
    assert handoff["new_production_updates"] == 0
    assert not live(handoff["original_controller"])
    expected = {f"{phase}-{arm}" for phase in ("CPU", "CUDA") for arm in ARMS}
    assert set(handoff["completed"]) == expected
    assert not any((previous_root / f"train-{arm}.claim").exists() for arm in ARMS)
    for key, binding in handoff["completed"].items():
        assert ref(binding["path"]) == binding
        result = read(binding["path"])
        phase, arm = key.split("-")
        assert result["status"] == "completed-raw-spatial-training-phase"
        assert (result["phase"], result["arm"], result["updates"]) == (phase, arm, 18)
        assert result["model_EMA_Adam_finite"] and result["all_AdamW_steps"] == 18
        assert not live(result["owner"])
        assert ref(result["checkpoint"]["path"]) == result["checkpoint"]
        if arm == "V132":
            assert result["all_observed_inputs_match_saved_control"]
    state = read(Path(dependency["root"]) / "status.json")
    assert state["plan"] == ref(dependency_path) and live(state["controller"])
    assert not state["status"].startswith("failed")
    assert list(dependency["arms"]) == ["V124", "V125"]
    root.mkdir(parents=True)
    source = root / "controller.py"
    shutil.copyfile(train_quality_recipes.__file__, source)
    plan = {
        **original,
        "root": str(root),
        "controller_source": ref(source),
        "replaced_controller": handoff["original_controller"],
        "adopted_phase_results": handoff["completed"],
        "adopted_worker_plan": ref(original_path),
        "output_worker_root": str(previous_root),
        "before_train_admission": {
            "plan": ref(dependency_path),
            "status": str(Path(dependency["root"]) / "status.json"),
            "controller": state["controller"],
            "arm": "V125",
            "running_status": "running-noise-pair-training",
            "completed_phases": [
                f"{phase}-{arm}" for phase in ("CPU", "CUDA", "train") for arm in ("V124", "V125")
            ],
            "maximum_wait_seconds": 345600,
        },
        "inputs": [
            *original["inputs"],
            ref(original_path),
            ref(previous_root / "launch.json"),
            ref(previous_root / "admission-handoff-v1.json"),
            ref(dependency_path),
            *handoff["completed"].values(),
        ],
        "frozen_files": {**original["frozen_files"], str(source): ref(source)["sha256"]},
        "scope": original["scope"]
        + (
            " Controller-only admission handoff: adopt all72 completed discarded check "
            "updates without replay. Keep the original worker plan/source/output paths, "
            "20k budgets, LR horizons and48h per-arm bounds. Start production only after "
            "the exact original V125 owner has obtained its64GiB admission, or the "
            "entire original mean trial has completed successfully. No original job signals."
        ),
    }
    path = root / "plan.json"
    save(path, plan)
    guard(plan)
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "adopt-checks", "controller", "worker"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--phase", choices=("CPU", "CUDA", "train"))
    parser.add_argument("--arm", choices=ARMS)
    parser.add_argument("--original-plan", type=Path)
    parser.add_argument("--admission-plan", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path.resolve()))
    elif args.mode == "adopt-checks":
        print(adopt_checks_after_admission(args.path, args.original_plan, args.admission_plan))
    elif args.mode == "controller":
        controller(args.path.resolve())
    else:
        worker(args.path.resolve(), args.phase, args.arm)
