"""Freeze and queue retained-prediction quality evaluation after matched training."""

import argparse
import ast
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import psutil
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import live

REPO = Path(__file__).resolve().parents[1]
STAGES = {
    "photo": (3108, 12404),
    "known": (24, 72),
    "unseen": (30, 90),
    "texture": (112, 448),
    "color": (1176, 1176),
    "gfx": (4, 4),
    "gfx-highlights": (2, 2),
    "full-gfx": (130, 520),
}
HELPERS = [
    "collect_quality_predictions.py",
    "queue_matched_quality_predictions.py",
    "frozen_backbone_identity.py",
    "train_directional_bank_trial.py",
    "train_v43_quality_trial.py",
    "profile_raw_kernel_inference.py",
    "evaluate_texture_candidates.py",
    "diagnose_texture_response.py",
    "evaluate_color_grid_cuda.py",
    "prepare_color_grid.py",
    "audit_colored_flats.py",
    "report_raw_pair.py",
]


def function_ast(path, name):
    tree = ast.parse(Path(path).read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    return ast.dump(node, include_attributes=False)


def execution_arms(execution, binding, training_format):
    if training_format == "matched-photographic-epoch-v1":
        assert list(execution["arms"]) == ["V134", "V135"]
        assert execution["restoration_tensors_by_arm"] == {"V134": 91, "V135": 91}
        assert execution["paired_control_arm"] == "V134"
        return [{"arm": arm, "training_plan": binding} for arm in execution["arms"]]
    if training_format == "reviewed-photographic-quota-v1":
        assert list(execution["arms"]) == ["V133"]
        assert execution["restoration_tensors_by_arm"] == {"V133": 91}
        assert execution["saved_control_arm"] == "V131"
        return [{"arm": "V133", "training_plan": binding}]
    if training_format == "matched-raw-spatial-v1":
        assert execution["restoration_tensors_by_arm"] == {"V131": 91, "V132": 114}
        assert list(execution["arms"]) == ["V131", "V132"]
        assert execution["paired_control_arm"] == "V131"
        return [{"arm": arm, "training_plan": binding} for arm in execution["arms"]]
    if training_format == "independent-noise-mean-v1":
        assert execution["arm_weights"] == {"V124": 0.0, "V125": 0.25}
        assert set(execution["arms"]) == set(execution["arm_weights"])
        return [{"arm": arm, "training_plan": binding} for arm in execution["arms"]]
    if training_format == "learned-frequency-scopes-v1":
        assert execution["arm_scopes"] == {"V122": True, "V123": False}
        assert set(execution["arms"]) == set(execution["arm_scopes"])
        return [{"arm": arm, "training_plan": binding} for arm in execution["arms"]]
    assert training_format == "matched-execution-v1"
    return execution["arms"]


def verify_noise_pair_training_state(actual, snapshot, weight):
    """Reject partial runs or changed supervision using retained state only."""
    import torch

    from demosaic.noise_pairs import noise_pair_options

    assert actual["status"] == "completed-noise-pair-training-phase"
    assert actual["phase"] == "train" and actual["updates"] == snapshot["step"] == 20000
    assert noise_pair_options(snapshot["config"]) == (2, weight)
    assert actual["conditional_mean_weight"] == weight and actual["noise_pair_draws"] == 2
    assert all(
        actual["counts"][key] == 20000
        for key in ("training_forwards", "optimizer_steps", "prepared_training_batches")
    )
    assert actual["counts"]["unique_target_contexts"] == 320000
    domains = actual["domain_counts"]
    assert sum(domains.values()) == 20000
    assert actual["counts"]["sensor_observations"] == 16 * (
        2 * (domains["commons"] + domains["native"]) + domains["paired"]
    )
    assert actual["initial_checks"][0]["official_encoder_exact"]
    assert actual["model_EMA_Adam_finite"] and actual["frozen_encoder_no_gradients"]
    assert len(snapshot["model"]) == len(snapshot["ema"]) == 91
    states = snapshot["optimizer"]["state"]
    assert len(states) == 89 and all(float(s["step"]) == 20000 for s in states.values())
    assert all(torch.isfinite(v).all() for key in ("model", "ema") for v in snapshot[key].values())
    assert all(
        torch.isfinite(v).all()
        for s in states.values()
        for v in s.values()
        if isinstance(v, torch.Tensor)
    )


def verify_frequency_training_state(actual, snapshot, parent, only):
    """Check completed retained training state without any model construction."""
    import torch

    assert actual["status"] == "completed-frequency-training-phase"
    assert actual["phase"] == "train" and actual["updates"] == snapshot["step"] == 20000
    assert snapshot["config"]["raw_frequency_only"] is only
    assert all(
        actual["counts"][key] == 20000
        for key in ("training_forwards", "optimizer_steps", "prepared_training_batches")
    )
    assert actual["initial_checks"][0]["official_encoder_exact"]
    assert actual["common91_model_and_EMA_exact_to_parent"] is only
    states = snapshot["optimizer"]["state"]
    assert len(states) == (5 if only else 94)
    assert all(float(s["step"]) == 20000 for s in states.values())
    assert all(torch.isfinite(v).all() for key in ("model", "ema") for v in snapshot[key].values())
    assert all(
        torch.isfinite(v).all()
        for s in states.values()
        for v in s.values()
        if isinstance(v, torch.Tensor)
    )
    if only:
        for key, value in parent["ema"].items():
            assert torch.equal(snapshot["model"][key], value)
            assert torch.equal(snapshot["ema"][key], value)


def verify_spatial_training_state(
    actual, snapshot, spatial, *, expected_status="completed-raw-spatial-training-phase"
):
    """Require the full matched horizon and the declared 91/114-tensor state."""
    import torch

    tensors, adam_states = (114, 112) if spatial else (91, 89)
    assert actual["status"] == expected_status
    assert actual["phase"] == "train" and actual["updates"] == snapshot["step"] == 20000
    assert snapshot["config"]["steps"] == 20000
    assert snapshot["model_config"]["raw_spatial_features"] is spatial
    counts = actual["counts"]
    assert all(
        counts[k] == 20000
        for k in ("training_forwards", "optimizer_steps", "prepared_training_batches")
    )
    assert counts["validation_forwards"] == 640 and counts["encoder_forwards"] == 20640
    assert counts["target_contexts"] == 320000
    assert actual["initial_checks"][0]["official_encoder_exact"]
    assert actual["initial_checks"][0]["91_parent_or_resume_tensors_exact"]
    assert actual["model_EMA_Adam_finite"] and actual["frozen_encoder_no_gradients"]
    assert actual["model_EMA_tensor_count"] == tensors
    assert snapshot["model"].keys() == snapshot["ema"].keys()
    assert len(snapshot["model"]) == tensors
    assert sum(k.startswith("pretrained_rgb.raw_spatial.") for k in snapshot["model"]) == (
        23 if spatial else 0
    )
    states = snapshot["optimizer"]["state"]
    assert len(states) == adam_states and all(float(s["step"]) == 20000 for s in states.values())
    assert all(torch.isfinite(v).all() for key in ("model", "ema") for v in snapshot[key].values())
    assert all(
        torch.isfinite(v).all()
        for state in states.values()
        for v in state.values()
        if isinstance(v, torch.Tensor)
    )
    rows = actual["observed_inputs"]
    assert len(rows) == 20000 and [r["step"] for r in rows] == list(range(1, 20001))
    if spatial:
        assert actual["all_observed_inputs_match_saved_control"]


def verify_quota_training_state(actual, snapshot, comparison, expected_config=None):
    """Require a complete quota-only endpoint and its finished input proof."""
    verify_spatial_training_state(
        actual, snapshot, False, expected_status="completed-reviewed-quota-training-phase"
    )
    assert actual["arm"] == "V133"
    config = snapshot["config"]
    assert config["reviewed_roi_fraction"] == 0.05 and config["seed"] == 70
    assert config["noise_pair_draws"] == 1 and config["conditional_mean_weight"] == 0
    assert config["reviewed_shadow_fraction"] == config.get("dino_feature_weight", 0) == 0
    assert config["normalized_band_weight"] == 0
    if expected_config is not None:
        ignored = {"run", "experiment_notes", "validation_protocol"}
        assert all(
            config.get(key) == value for key, value in expected_config.items() if key not in ignored
        )
        if "validation_protocol" in expected_config:
            assert (
                config["validation_protocol_sha256"]
                == ref(expected_config["validation_protocol"])["sha256"]
            )
    assert comparison["status"] == "passed-quota-only-unaffected-batch-and-example-proof"
    assert comparison["control"] == actual["matched_control_result"]
    counts = comparison["counts"]
    assert counts["native_steps"] == counts["native_whole_batches_exact"] == 4965
    assert counts["paired_steps"] == counts["paired_whole_batches_exact"] == 4989
    assert counts["commons_steps"] == 10046
    assert (
        counts.get("commons_whole_batches_exact", 0)
        + counts["Commons_batches_with_expected_selection_changes"]
        == 10046
    )
    assert counts["exact_unaffected_prepared_values"] > 0


def verify_photo_epoch_training_state(actual, snapshot, comparison, expected_config):
    """Require full endpoints, the frozen order policy and its input proof."""
    verify_spatial_training_state(
        actual, snapshot, False, expected_status="completed-photo-epoch-training-phase"
    )
    arm, config = actual["arm"], snapshot["config"]
    assert arm in {"V134", "V135"}
    assert config["seed"] == 70 and config["reviewed_roi_fraction"] == 0.05
    assert config["noise_pair_draws"] == 1 and config["conditional_mean_weight"] == 0
    assert config["reviewed_shadow_fraction"] == config["normalized_band_weight"] == 0
    ignored = {"run", "experiment_notes", "validation_protocol"}
    assert all(config.get(k) == v for k, v in expected_config.items() if k not in ignored)
    if "validation_protocol" in expected_config:
        assert (
            config["validation_protocol_sha256"]
            == ref(expected_config["validation_protocol"])["sha256"]
        )
    assert bool(config.get("photo_epoch_order")) == (arm == "V135")
    if arm == "V134":
        assert comparison is None and actual["matched_control_result"] is None
        assert config.get("photo_epoch_order_sha256") is None
    else:
        assert config["photo_epoch_order_sha256"]
        assert comparison["status"] == "passed-photo-epoch-unaffected-input-proof"
        assert comparison["control"] == actual["matched_control_result"]
        counts = comparison["counts"]
        assert counts["checked_batches_before_model_forward"] == 18
        assert counts["unaffected_first18_examples"] > 0
        assert counts["exact_unaffected_prepared_values"] > 0
        assert counts["exact_native_paired_whole_batches"] == 9954


def training_execution_binding(training_root, status):
    """Follow the exact live controller's receipt, including nondefault filenames."""
    shared = "execution_plan" not in status and "plan" in status
    field = "plan" if shared else "execution_plan"
    binding = status[field]
    assert Path(binding["path"]).resolve().parent == Path(training_root).resolve()
    assert ref(binding["path"]) == binding
    return binding, shared


def prepare(root, artifacts, training_root, witness_plan, gfx_selections, controls=()):
    root, artifacts, training_root = root.resolve(), artifacts.resolve(), training_root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    internal_artifacts = artifacts.is_relative_to(root / "work")
    assert internal_artifacts or artifacts.is_relative_to(Path("/mnt/external/demosaic"))
    status = read(training_root / "status.json")
    execution, shared_plan = training_execution_binding(training_root, status)
    training = read(execution["path"])
    training_format = (
        training.get("training_format", "learned-frequency-scopes-v1")
        if shared_plan
        else "matched-execution-v1"
    )
    guard(training)
    owner_field, execution_field = (
        ("controller", "plan") if shared_plan else ("owner", "execution_plan")
    )
    assert status[execution_field] == execution and live(status[owner_field])
    assert not status["status"].startswith("failed")
    arms = execution_arms(training, execution, training_format)
    arm_names = [a["arm"] for a in arms]
    assert arm_names and len(arm_names) == len(set(arm_names))
    original = read(witness_plan)
    guard(original)
    assert function_ast(REPO / "src/demosaic/suite.py", "observation") == function_ast(
        original["historical_suite"]["path"], "observation"
    )
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    files = list((REPO / "src/demosaic").glob("*.py")) + [REPO / "scripts" / p for p in HELPERS]
    files += [REPO / p for p in ["pyproject.toml", "uv.lock", "third_party/dinov3/LICENSE.md"]]
    for source in files:
        target = work / source.relative_to(REPO)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    protocol = work / "configs/evaluation.yaml"
    protocol.parent.mkdir(exist_ok=True)
    shutil.copyfile(original["stages"]["photo"]["protocol"]["path"], protocol)
    stages, inputs = {}, [execution, ref(witness_plan)]
    for stage, (calls, observations) in STAGES.items():
        spec = {
            "calls_per_model": calls,
            "observations_per_model": observations,
            "output": str(artifacts / stage),
        }
        if stage in {"photo", "known", "unseen"}:
            spec["manifest"] = original["stages"][stage]["manifest"]
            inputs.append(spec["manifest"])
        if stage == "photo":
            spec["protocol"] = ref(protocol)
        if stage in original["stages"]:
            spec["future_input_witness"] = str(
                Path(original["stages"][stage]["output"]) / "retained-means.jsonl"
            )
            spec["future_original_result"] = str(
                Path(original["stages"][stage]["output"]) / "result.json"
            )
        else:
            source = Path(gfx_selections[stage])
            selection = read(source)
            for key in ["noisy", "reference"]:
                p = Path(selection[key])
                if not p.is_absolute():
                    p = REPO / p
                assert p.resolve().is_relative_to(REPO / ".cache/gfx-qualitative-20231231")
                selection[key] = str(p.resolve())
                inputs.append(ref(p))
            target = work / "configs" / (stage + ".json")
            save(target, selection)
            spec["selection"] = ref(target)
            inputs.append(ref(source))
        stages[stage] = spec
    inputs.append(original["color_inputs"])
    control_files = [ref(p) for p in controls]
    inputs.extend(control_files)
    # Evaluation-only callbacks/retention may change; the physical model and
    # observation generator must agree with the actually frozen training source.
    source_checks = []
    for arm in arms:
        plan = read(arm["training_plan"]["path"])
        guard(plan)
        changed = []
        for source in (Path(plan["work"]) / "src/demosaic").glob("*.py"):
            if source.read_bytes() != (work / "src/demosaic" / source.name).read_bytes():
                changed.append(source.name)
        assert set(changed) <= {"suite.py", "real_suite.py"}, changed
        source_checks.append(
            {
                "arm": arm["arm"],
                "training_plan": arm["training_plan"],
                "evaluation_only_changed_modules": changed,
            }
        )
    snapshot = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    plan = {
        "root": str(root),
        "work": str(work),
        "artifact_root": str(artifacts),
        "python": sys.executable,
        "training_execution": execution,
        "training_owner": status[owner_field],
        "training_status": str(training_root / "status.json"),
        "training_format": training_format,
        "full_gfx_common_grid_alignment": 32
        if training_format
        in {
            "matched-raw-spatial-v1",
            "reviewed-photographic-quota-v1",
            "matched-photographic-epoch-v1",
        }
        else None,
        "training_owner_field": owner_field,
        "training_execution_field": execution_field,
        "expected_training_terminal": "completed-training-awaiting-model-comparisons"
        if shared_plan
        else training.get(
            "terminal_status", "completed-matched-V114-V115-training-awaiting-quality-comparisons"
        ),
        "expected_training_phases": [
            f"{phase}-{arm}"
            for phase in (["CPU", "CUDA", "train"] if shared_plan else ["CUDA", "train"])
            for arm in arm_names
        ],
        "expected_model_count": len(arm_names),
        "original_witness_plan": ref(witness_plan),
        "stages": stages,
        "color_inputs": original["color_inputs"],
        "material_photo_ids": [
            "0ae232278265dabbdd54f52c34045a3d03323aa7",
            "14d8ea6cea4a27346a643e6d767f800729fb4693",
            "212ae12913effa23268af953b4c8f8e8b7ab4ef5",
            "2b5a51667b9906eecead8f82e08c7ba11750f8c6",
        ],
        "shared_checkpoint_cache": str(artifacts / ".checkpoint-cache"),
        "existing_control_files": control_files,
        "estimated_retained_and_export_budget_GiB": 15 * len(arm_names),
        "collector_source": ref(work / "scripts/collect_quality_predictions.py"),
        "controller_source": ref(work / "scripts/queue_matched_quality_predictions.py"),
        "maximum_training_wait_seconds": (
            691200
            if training_format
            in {"reviewed-photographic-quota-v1", "matched-photographic-epoch-v1"}
            else 432000
            if training_format == "matched-raw-spatial-v1"
            else 259200
        ),
        "first_stage_external_free_GiB": 208 if internal_artifacts else 248,
        "phase_start_external_free_GiB": 208 if internal_artifacts else 216,
        "runtime_external_reserve_GiB": 208,
        "phase_start_internal_free_GiB": 128 if internal_artifacts else 32,
        "runtime_internal_reserve_GiB": 96 if internal_artifacts else 16,
        "core_training_sources_unchanged": source_checks,
        "photo_observation_AST_identical_to_original": True,
        "inputs": inputs,
        "frozen_files": snapshot,
        "scope": "Declared new endpoints only, eight single-view FP32 stages after exact training-owner success. Retain native predictions/exact supervision and compare all numerical-panel inputs to original completed eight-view witnesses. Existing controls are reused without neural reruns. Six full-frame native floats and two RGB16 exports per new model. No automatic model promotion or retry; numeric/native review follows.",
    }
    save(root / "queue-plan-v1.json", plan)
    guard(plan)
    return root / "queue-plan-v1.json"


def endpoint_plan(plan, state):
    import torch

    from demosaic.checkpoint_cache import freeze_checkpoint

    execution = read(plan["training_execution"]["path"])
    training_format = plan.get("training_format", "matched-execution-v1")
    arms = execution_arms(execution, plan["training_execution"], training_format)
    assert len(arms) == plan.get("expected_model_count", len(arms))
    assert set(state["completed"]) == set(plan["expected_training_phases"])
    checkpoints, inputs = [], list(plan["inputs"])
    artifacts = Path(plan["artifact_root"])
    artifacts.mkdir(exist_ok=False)
    for arm in arms:
        name = arm["arm"]
        accounting = state["completed"][f"train-{name}"]
        assert ref(accounting["path"]) == accounting
        actual = read(accounting["path"])
        assert not live(actual["owner"])
        assert actual["counts"]["training_forwards"] == actual["counts"]["optimizer_steps"] == 20000
        if training_format == "matched-execution-v1":
            assert actual["all_AdamW_steps"] == 20000
            assert actual["model_EMA_Adam_finite"] and actual["frozen_encoder_no_gradients"]
        if name == "V115":
            assert actual["matched_logged_inputs_steps_domains_LRs"] == 801
        training = read(arm["training_plan"]["path"])
        assert ref(actual["checkpoint"]["path"]) == actual["checkpoint"]
        path, digest = freeze_checkpoint(
            actual["checkpoint"]["path"],
            artifacts / "weights",
            cache_dir=plan["shared_checkpoint_cache"],
        )
        assert digest == actual["checkpoint"]["sha256"]
        snapshot = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
        if training_format == "learned-frequency-scopes-v1":
            parent = torch.load(
                training["parent"]["path"], map_location="cpu", weights_only=True, mmap=True
            )
            verify_frequency_training_state(actual, snapshot, parent, execution["arm_scopes"][name])
            del parent
        if training_format == "independent-noise-mean-v1":
            verify_noise_pair_training_state(actual, snapshot, execution["arm_weights"][name])
        if training_format == "matched-raw-spatial-v1":
            verify_spatial_training_state(actual, snapshot, name == "V132")
        if training_format == "reviewed-photographic-quota-v1":
            import yaml

            comparison_path = Path(training["root"]) / "train-V133-input-comparison-v1.json"
            comparison = read(comparison_path)
            assert comparison["candidate"] == accounting
            expected_config = yaml.safe_load(Path(training["arms"][name]["train"]).read_text())
            verify_quota_training_state(actual, snapshot, comparison, expected_config)
            inputs.append(ref(comparison_path))
        if training_format == "matched-photographic-epoch-v1":
            import yaml

            comparison = None
            if name == "V135":
                comparison_path = Path(training["root"]) / "train-V135-input-comparison-v1.json"
                comparison = read(comparison_path)
                assert comparison["candidate"] == accounting
                inputs.append(ref(comparison_path))
            expected_config = yaml.safe_load(Path(training["arms"][name]["train"]).read_text())
            verify_photo_epoch_training_state(actual, snapshot, comparison, expected_config)
        lineage = {**training["parent"], "step": 20000}
        assert snapshot["step"] == 20000 and snapshot["config"]["initialized_from"] == lineage
        checkpoints.append(
            {
                "arm": name,
                "EMA_tensors": len(snapshot["ema"]),
                **ref(path),
                "expected_lineage": {"step": 20000, "initialized_from": lineage},
                "expected_backbone": training["backbones"][name],
            }
        )
        inputs.extend([accounting, actual["checkpoint"], ref(path)])
    stages = {}
    for name, specification in plan["stages"].items():
        spec = dict(specification)
        if "future_input_witness" in spec:
            binding = ref(spec["future_input_witness"])
            result_binding = ref(spec["future_original_result"])
            result = read(result_binding["path"])
            assert result["averaged_observations"] == spec["observations_per_model"]
            assert (
                result["retained_means"] == binding
                and result["all_streamed_numpy64_means_bit_exact"]
            )
            assert len(Path(binding["path"]).read_text().splitlines()) == spec["calls_per_model"]
            spec["input_witness"] = binding
            inputs.extend([binding, result_binding])
        stages[name] = spec
    result = {**plan, "checkpoints": checkpoints, "stages": stages, "inputs": inputs}
    save(Path(plan["root"]) / "evaluation-plan-v1.json", result)
    return Path(plan["root"]) / "evaluation-plan-v1.json"


def controller(path):
    plan = read(path)
    guard(plan)
    root = Path(plan["root"])
    assert ref(__file__) == plan["controller_source"]
    (root / "controller.claim").open("x").close()
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    state = {"owner": owner, "queue_plan": ref(path), "completed": {}}
    child = child_owner = None
    owner_field = plan.get("training_owner_field", "owner")
    execution_field = plan.get("training_execution_field", "execution_plan")

    def record(status, **fields):
        state.update(status=status, updated_unix=time.time(), **fields)
        save(root / "status.json", state)

    try:
        record("waiting-for-exact-matched-training-owner", dependency=plan["training_owner"])
        began = time.monotonic()
        while live(plan["training_owner"]):
            observed = read(plan["training_status"])
            assert (
                observed[owner_field] == plan["training_owner"]
                and observed[execution_field] == plan["training_execution"]
            )
            assert not observed["status"].startswith("failed"), observed["status"]
            assert time.monotonic() - began < plan["maximum_training_wait_seconds"]
            time.sleep(10)
        observed = read(plan["training_status"])
        assert (
            observed[owner_field] == plan["training_owner"]
            and observed[execution_field] == plan["training_execution"]
        )
        assert observed["status"] == plan["expected_training_terminal"]
        assert observed.get("child") is None or not live(observed["child"])
        guard(plan)
        evaluation_path = endpoint_plan(plan, observed)
        evaluation = read(evaluation_path)
        for index, stage in enumerate(plan["stages"]):
            record("waiting-for-quality-headroom", stage=stage, child=None)
            began, stable = time.monotonic(), None
            while True:
                if deadline := plan.get("absolute_stage_headroom_deadlines", {}).get(stage):
                    assert time.time() < deadline
                enough = (
                    psutil.virtual_memory().available >= 48 * 2**30
                    and shutil.disk_usage(root).free
                    >= plan.get("phase_start_internal_free_GiB", 32) * 2**30
                    and shutil.disk_usage("/mnt/external").free
                    >= plan[
                        "first_stage_external_free_GiB"
                        if index == 0
                        else "phase_start_external_free_GiB"
                    ]
                    * 2**30
                )
                stable = (time.monotonic() if stable is None else stable) if enough else None
                if stable is not None and time.monotonic() - stable >= 15:
                    break
                assert time.monotonic() - began < 7200
                time.sleep(2)
            guard(evaluation)
            work = Path(plan["work"])
            env = dict(
                os.environ,
                PYTHONPATH=f"{work / 'src'}:{work / 'scripts'}",
                CUDA_VISIBLE_DEVICES="0",
                HF_HUB_OFFLINE="1",
                TRANSFORMERS_OFFLINE="1",
                OPENBLAS_NUM_THREADS="1",
                OMP_NUM_THREADS="4",
            )
            with (root / (stage + "-v1.log")).open("x") as log:
                child = subprocess.Popen(
                    [
                        plan["python"],
                        "-P",
                        plan["collector_source"]["path"],
                        str(evaluation_path),
                        stage,
                    ],
                    cwd=work,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                child_owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                record("running-frozen-endpoint-quality-stage", stage=stage, child=child_owner)
                began = time.monotonic()
                while child.poll() is None:
                    if deadline := plan.get("absolute_stage_deadlines", {}).get(stage):
                        assert time.time() < deadline
                    assert time.monotonic() - began < 43200
                    assert psutil.virtual_memory().available >= 24 * 2**30
                    assert (
                        shutil.disk_usage(root).free
                        >= plan.get("runtime_internal_reserve_GiB", 16) * 2**30
                    )
                    assert (
                        shutil.disk_usage("/mnt/external").free
                        >= plan["runtime_external_reserve_GiB"] * 2**30
                    )
                    time.sleep(2)
                assert child.wait() == 0, (stage, child.returncode)
            result_path = Path(plan["stages"][stage]["output"]) / "result.json"
            result = read(result_path)
            assert result["owner"] == child_owner and not live(child_owner)
            state["completed"][stage] = ref(result_path)
            record("completed-quality-stage", child=None)
        record(
            "completed-matched-endpoint-evaluation-awaiting-independent-and-native-review",
            child=None,
        )
    except BaseException as error:
        if child is not None and child.poll() is None and live(child_owner):
            os.killpg(child.pid, signal.SIGINT)
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                if live(child_owner):
                    os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=30)
        record("failed-quality-evaluation-preserved-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "controller"])
    parser.add_argument("root", type=Path)
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--training-root", type=Path)
    parser.add_argument("--witness-plan", type=Path)
    parser.add_argument("--gfx", type=Path)
    parser.add_argument("--gfx-highlights", type=Path)
    parser.add_argument("--full-gfx", type=Path)
    parser.add_argument("--controls", type=Path, nargs="*", default=[])
    args = parser.parse_args()
    if args.mode == "prepare":
        print(
            prepare(
                args.root,
                args.artifacts,
                args.training_root,
                args.witness_plan,
                {"gfx": args.gfx, "gfx-highlights": args.gfx_highlights, "full-gfx": args.full_gfx},
                args.controls,
            )
        )
    else:
        controller(args.root)
