"""Compare replacement and epoch ordering on the cleaned 90778/33 corpus."""

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path

from train_directional_bank_trial import guard, read, ref, save
from train_quality_recipes import REPO
from train_quality_recipes import prepare as prepare_recipes
from train_reviewed_shadow_trial import worker as core_worker
from train_v43_quality_trial import live

ARMS = ("V134", "V135")
BASE = REPO / ".cache/current-quality-20261023-v1"
QUOTA = BASE / "reviewed-quota-training-recovery-v2/run"
REVIEW = BASE / "V133-reviewed-quota-green-mesh-v1"


def validate_recipes(configs):
    ignored = {"run", "experiment_notes", "photo_epoch_order", "photo_epoch_order_sha256"}
    normalized = [{k: v for k, v in c.items() if k not in ignored} for c in configs]
    assert len(configs) == 2 and normalized[0] == normalized[1], (
        "Epoch comparison differs beyond source order"
    )
    a, b = configs
    assert not a.get("photo_epoch_order") and b.get("photo_epoch_order")
    assert b.get("photo_epoch_order_sha256")
    for c in configs:
        assert c["steps"] == 20000 and c["seed"] == 70
        assert c["batch_size"] == 16 and c["patch_size"] == 256
        assert c["reviewed_roi_fraction"] == 0.05
        assert c["precision"] == "bfloat16" and c["checkpoint_every"] == 1000
        assert c["paired_fraction"] == c["raw_clean_fraction"] == 0.25
        assert c["noise_pair_draws"] == 1 and c["conditional_mean_weight"] == 0
        assert c["reviewed_shadow_fraction"] == c["normalized_band_weight"] == 0
        assert c["optical_blur_probability"] == c["raw_clean_optical_blur_probability"] == 0
        assert c["model"]["raw_spatial_features"] is False


def review_ready(state, dependency):
    assert state["plan"] == dependency["plan"] and state["owner"] == dependency["owner"]
    assert not state["status"].startswith("failed"), state.get("error", state["status"])
    terminal = "completed-new-mesh-predictions-native-viewing-pending"
    if state["status"] != terminal:
        assert live(state["owner"]), "Prior review owner exited before completion"
        return False
    if live(state["owner"]) or (state.get("child") is not None and live(state["child"])):
        return False
    assert ref(state["result"]["path"]) == state["result"]
    result = read(state["result"]["path"])
    assert result["owner"] == dependency["owner"] and result["queue_plan"] == dependency["plan"]
    return True


def controller(path):
    import train_quality_recipes as common

    original = common.training_admission_ready

    def ready(state, dependency):
        if not original(state, dependency):
            return False
        review = dependency["after_original_review"]
        return review_ready(read(review["status"]), review)

    common.training_admission_ready = ready
    try:
        common.controller(path)
    finally:
        common.training_admission_ready = original


def prepare(root):
    import yaml
    from prepare_photo_epoch_order import prepare as prepare_order

    from demosaic.train import training_domain

    recipes = [REPO / f"configs/quality-v120-photo-epoch-v{v}.yaml" for v in (134, 135)]
    configs = [yaml.safe_load(p.read_text()) for p in recipes]
    validate_recipes(configs)
    catalogue = read(configs[0]["reviewed_roi_catalogue"])
    assert len(catalogue["examples"]) == 33
    assert ref(configs[0]["manifest"]) == catalogue["source_manifest"]
    quota_path = QUOTA / "controller-plan-v1.json"
    quota_plan, quota_state = read(quota_path), read(QUOTA / "status.json")
    guard(quota_plan)
    assert quota_state["plan"] == ref(quota_path) and live(quota_state["controller"])
    assert not quota_state["status"].startswith("failed")
    review_path = REVIEW / "queue-plan-v1.json"
    review_plan, review_state = read(review_path), read(REVIEW / "status.json")
    guard(review_plan)
    assert review_state["plan"] == ref(review_path) and live(review_state["owner"])
    path = prepare_recipes(root, root / "work/artifacts", recipes)
    plan = read(path)
    work = Path(plan["work"])
    names = [
        "train_photo_epoch_trial.py",
        "train_reviewed_shadow_trial.py",
        "prepare_photo_epoch_order.py",
    ]
    for name in names:
        shutil.copyfile(REPO / "scripts" / name, work / "scripts" / name)
    # Production and CUDA use the already audited B16 order. CPU requires B1.
    source_header = Path(configs[1]["photo_epoch_order"])
    header = read(source_header)
    assert ref(source_header)["sha256"] == configs[1]["photo_epoch_order_sha256"]
    plan["inputs"] += [ref(source_header), ref(source_header.parent / header["order"]["path"])]
    for phase in ("CPU", "CUDA", "train"):
        for arm in ARMS:
            recipe = Path(plan["arms"][arm][phase])
            config = yaml.safe_load(recipe.read_text())
            if phase == "CPU":
                config["patch_size"] = 128
            if arm == "V135" and phase == "CPU":
                config.pop("photo_epoch_order")
                config.pop("photo_epoch_order_sha256")
                recipe.write_text(yaml.safe_dump(config, sort_keys=False))
                cpu_header = prepare_order(recipe, work / "photo-order-CPU")
                config["photo_epoch_order"] = str(cpu_header)
                config["photo_epoch_order_sha256"] = ref(cpu_header)["sha256"]
            recipe.write_text(yaml.safe_dump(config, sort_keys=False))
        if phase == "train":
            continue
        epoch = yaml.safe_load(Path(plan["arms"]["V135"][phase]).read_text())
        for arm in ARMS:
            for change in ("mode", "binding"):
                config = yaml.safe_load(Path(plan["arms"][arm][phase]).read_text())
                if change == "mode":
                    if arm == "V134":
                        config.update(
                            {k: epoch[k] for k in ("photo_epoch_order", "photo_epoch_order_sha256")}
                        )
                    else:
                        config.pop("photo_epoch_order")
                        config.pop("photo_epoch_order_sha256")
                else:
                    config["photo_epoch_order_sha256"] = "0" * 64
                config["run"] += f"-rejected-order-{change}"
                target = work / "configs" / f"{phase}-{arm}-rejected-{change}.yaml"
                target.write_text(yaml.safe_dump(config, sort_keys=False))
                plan["arms"][arm][f"{phase}_rejected_{change}"] = str(target)
    plan.update(
        worker_script=ref(work / "scripts/train_photo_epoch_trial.py"),
        core_worker_script=ref(work / "scripts/train_reviewed_shadow_trial.py"),
        training_format="matched-photographic-epoch-v1",
        paired_control_arm="V134",
        arm_fractions=dict.fromkeys(ARMS, 0.0),
        require_matched_clean_inputs=False,
        require_matched_noisy_inputs=False,
        require_unchanged_noncommons_inputs=True,
        require_equal_initial_outputs=False,
        restoration_tensors_by_arm=dict.fromkeys(ARMS, 91),
        phase_result_status="completed-photo-epoch-training-phase",
        resume_rejection_changes=["mode", "binding"],
        resume_rejection_error_keyword="epoch order",
        rejection_result_key="changed_photo_epoch_resume_rejections",
        smoke_updates=16,
        resume_new_updates=2,
        expected_train_validation_forwards=640,
        progress_steps=[1000],
        launch_available_RAM_GiB=52,
        launch_available_RAM_GiB_by_phase={"CPU": 40, "CUDA": 52, "train": 52},
        runtime_available_RAM_GB=32,
        CUDA_allocator_cap_GiB=16,
        maximum_train_worker_seconds=172800,
        maximum_smoke_worker_seconds=1800,
        prospective_domain_batches=dict(
            Counter(training_domain(s, 70, 0.25, 0.25) for s in range(1, 20001))
        ),
        before_train_admission={
            "plan": ref(quota_path),
            "status": str(QUOTA / "status.json"),
            "controller": quota_state["controller"],
            "arm": "V133",
            "running_status": "running-quality-training",
            "require_completed": True,
            "completed_phases": [f"{phase}-V133" for phase in ("CPU", "CUDA", "train")],
            "maximum_wait_seconds": 691200,
            "after_original_review": {
                "plan": ref(review_path),
                "status": str(REVIEW / "status.json"),
                "owner": review_state["owner"],
            },
        },
        production_scope="Completed full20000 source-order endpoint; numerical and actual native quality review pending.",
        scope="Fresh matched V120-Small EMA continuations on cleaned90778/33,seed70,native256/B16/BF16,singleview,zeroPSF,.05reviewed,paired32/native128,LR1e-5/warm100/cosine20000. V134 replacement versus V135 ordinary-photo epochs; only order differs. Four new CPU128/B1 or CUDA256/B16 checks execute16fresh+2valid resumed updates; reject mode/binding drift before model construction. Retain first18 prepared tensors and all native/paired batch fingerprints; compare unaffected procedural/reviewed tensors before candidate neural calls. Fresh20k production perarm,640validation/20640encoder calls,retained1000 progress inside same horizon. Production waits for original V133 training and complete endpoint review/mesh owners to exit. CPU40GiB/CUDA-production52GiB headroom,16GiB CUDAcap,32GB runtime floor,30min/check,48h/production,8day dependency wait. No old model replay, automatic retry, schedule reset or existing-input changes. Quality unmeasured.",
    )
    plan["inputs"] += [ref(quota_path), ref(review_path)]
    plan["frozen_files"] = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    save(path, plan)
    guard(plan)
    return path


def compare_prepared_arrays(actual, previous, mask):
    import numpy as np

    assert actual.keys() == previous.keys()
    count = 0
    for key, a in actual.items():
        b = previous[key]
        assert a.shape == b.shape and a.dtype == b.dtype, key
        if a.ndim and a.shape[0] == len(mask):
            a, b = a[mask], b[mask]
        assert np.array_equal(a, b), (key, "unchanged photo-epoch examples")
        count += a.size
    return count


def worker(path, phase, arm):
    import numpy as np
    import torch
    import yaml

    import demosaic.train as training
    from demosaic.photo_epoch_order import bind_photo_epoch_order

    plan = read(path)
    guard(plan)
    assert arm in ARMS
    config = yaml.safe_load(Path(plan["arms"][arm][phase]).read_text())
    proof = Counter()
    original = training.prepare_training_batch
    if arm == "V135":
        prior_ref = ref(Path(plan["root"]) / f"{phase}-V134-result.json")
        prior = read(prior_ref["path"])
        assert not live(prior["owner"]) and prior["model_EMA_Adam_finite"]
        records = [json.loads(line) for line in Path(config["manifest"]).read_text().splitlines()]
        order = bind_photo_epoch_order(config, records)
        previous = {r["step"]: r for r in prior["observed_inputs"]}

        def checked(step, domain, clean, **kwargs):
            batch = original(step, domain, clean, **kwargs)
            if step <= 18:
                prior_arrays = previous[step]["prepared_tensors"]
                assert ref(prior_arrays["path"]) == prior_arrays
                mask = (
                    order.values[(step - 1) * config["batch_size"] : step * config["batch_size"]]
                    < 0
                    if domain == "commons"
                    else np.ones(config["batch_size"], dtype=bool)
                )
                with np.load(prior_arrays["path"], allow_pickle=False) as retained:
                    actual = {
                        k: v.detach().cpu().contiguous().numpy()
                        for k, v in batch.items()
                        if isinstance(v, torch.Tensor)
                    }
                    proof["exact_unaffected_prepared_values"] += compare_prepared_arrays(
                        actual, {k: retained[k] for k in retained.files}, mask
                    )
                proof["unaffected_first18_examples"] += int(mask.sum())
                proof["checked_batches_before_model_forward"] += 1
            return batch

        training.prepare_training_batch = checked
    try:
        core_worker(path, phase, arm)
    finally:
        training.prepare_training_batch = original
    result_ref = ref(Path(plan["root"]) / f"{phase}-{arm}-result.json")
    result = read(result_ref["path"])
    if arm == "V135":
        assert proof["checked_batches_before_model_forward"] == 18
        assert len(result["observed_inputs"]) == len(prior["observed_inputs"])
        for a, b in zip(result["observed_inputs"], prior["observed_inputs"], strict=True):
            assert (a["step"], a["domain"]) == (b["step"], b["domain"])
            if a["domain"] != "commons":
                assert (
                    a["clean_sha256"] == b["clean_sha256"]
                    and a["batch_sha256"] == b["batch_sha256"]
                )
                proof["exact_native_paired_whole_batches"] += 1
        save(
            Path(plan["root"]) / f"{phase}-{arm}-input-comparison-v1.json",
            {
                "status": "passed-photo-epoch-unaffected-input-proof",
                "candidate": result_ref,
                "control": prior_ref,
                "counts": dict(proof),
                "new_forwards_for_comparison": 0,
            },
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller", "worker"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--phase", choices=("CPU", "CUDA", "train"))
    parser.add_argument("--arm", choices=ARMS)
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path))
    elif args.mode == "controller":
        controller(args.path)
    else:
        worker(args.path, args.phase, args.arm)
