"""Prepare fixed V142 native/flat review and bind its actual data-only endpoint."""

import argparse
import os
from pathlib import Path

from review_standalone_patch_memory_pilot import prepare as prepare_native
from review_standalone_patch_memory_pilot import run as run_native
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import live

REPO = Path(__file__).resolve().parents[1]


def prepare(root, training_path):
    prepare_native(
        root,
        training_path,
        camera_control="V129",
        comparison_scope="V142 complete1k crossed-line/empty data-only pilot versus savedV129. "
        "Same V120/data90782/27/seed70/quota.5/zeroPSF/B16/native256/BF16/LR1e-5/warm100, "
        "pixel+gradient epsilon3e-4. Only .10 of .15 weak quota replaced by crossed lines/empty. "
        "All native/paired training inputs must match; Commons intentionally changes. "
        "102 fixed IEEE-FP32 calls:64shadow/16ordinary/16faintADC/4mainGFX512/2mesh768. "
        "Reuse408 V120/V129/V136/V137 predictions; same ROIs/noise/displays/source masks. "
        "Native160 exact-syntheticGT triplets; binned and separateISO100 references notGT. "
        "Both corrected protectedGFX pairs, both extra-mesh priors and cameraJPEGs. "
        "No new noise/RAW or old-model inference in primary review. Not full427/camera/color/"
        "fullframe/speed or proof against hallucinations.",
    )
    # Label-only variants preserve V140's published operator bytes and bindings.
    # Freeze each new operator here before it prepares or reads any predictions.
    for original, destination in [
        ("report_pilot_flat_safety.py", "flat-operator-v1.py"),
        ("audit_pilot_flat_safety.py", "flat-auditor-v1.py"),
    ]:
        text = (REPO / "scripts" / original).read_text().replace("V140", "V142")
        text = text.replace(
            "REPO = Path(__file__).resolve().parents[1]", f"REPO = Path({str(REPO)!r})"
        )
        (root / destination).write_text(text)
    save(
        root / "flat-operator-bindings-v1.json",
        {
            "operator": ref(root / "flat-operator-v1.py"),
            "auditor": ref(root / "flat-auditor-v1.py"),
            "original_operator": ref(REPO / "scripts/report_pilot_flat_safety.py"),
            "original_auditor": ref(REPO / "scripts/audit_pilot_flat_safety.py"),
            "changes": "Only V140→V142 labels and an explicit repository root for relocated operator. "
            "No scoring, source selection, ROI, transform, noise, pixel or audit-tolerance changes.",
        },
    )


def check_training_batches(actual, control, count):
    """Require unchanged domains and all non-Commons inputs; count intentional changes."""
    assert len(actual["observed_inputs"]) == len(control["observed_inputs"]) == count
    domains, changed = {}, {}
    for step, (a, b) in enumerate(
        zip(actual["observed_inputs"], control["observed_inputs"], strict=True), 1
    ):
        assert a["step"] == b["step"] == step and a["domain"] == b["domain"]
        domain = a["domain"]
        assert domain in ("commons", "native", "paired")
        domains[domain] = domains.get(domain, 0) + 1
        equal = all(a[k] == b[k] for k in ("clean_sha256", "batch_sha256"))
        if domain != "commons":
            assert equal, (step, domain)
        elif not equal:
            changed[domain] = changed.get(domain, 0) + 1
    assert domains == actual["domain_counts"] == control["domain_counts"]
    assert changed.get("commons", 0) > 0
    return {
        "domain_batches": domains,
        "changed_input_batches": changed,
        "all_native_paired_clean_and_noisy_match": True,
    }


def bind(root):
    queue = read(root / "queue-plan-v1.json")
    guard(queue)
    training = read(queue["training_plan"]["path"])
    guard(training)
    status = read(Path(training["root"]) / "status.json")
    assert status["plan"] == queue["training_plan"]
    assert status["status"] == "completed-training-awaiting-model-comparisons"
    assert not live(status["controller"])
    assert status.get("child") is None or not live(status["child"])
    for phase in ("CPU", "CUDA"):
        checked = status["completed"][phase + "-V142"]
        assert ref(checked["path"]) == checked
        smoke = read(checked["path"])
        assert smoke["status"] == "completed-crossed-line-data-pilot-phase"
        assert smoke["phase"] == phase and smoke["arm"] == "V142" and not live(smoke["owner"])
        assert smoke["updates"] == smoke["all_AdamW_steps"] == 18
        assert smoke["model_EMA_Adam_finite"] and smoke["frozen_encoder_no_gradients"]
        assert set(smoke["changed_mesh_resume_rejections"]) == {"disabled", "invalid"}
        control = smoke["matched_control_result"]
        assert ref(control["path"]) == control
        check_training_batches(smoke, read(control["path"]), 18)
    binding = status["completed"]["train-V142"]
    assert ref(binding["path"]) == binding
    actual = read(binding["path"])
    assert actual["status"] == "completed-crossed-line-data-pilot-phase"
    assert actual["arm"] == "V142" and actual["phase"] == "train" and not live(actual["owner"])
    assert actual["updates"] == actual["all_AdamW_steps"] == 1000
    assert actual["model_EMA_tensor_count"] == 91 and actual["optimizer_state_count"] == 89
    assert actual["model_EMA_Adam_finite"] and actual["frozen_encoder_no_gradients"]
    assert actual["counts"]["training_forwards"] == actual["counts"]["optimizer_steps"] == 1000
    assert (
        actual["counts"]["validation_forwards"] == 64
        and actual["counts"]["encoder_forwards"] == 1064
    )
    control = actual["matched_control_result"]
    assert ref(control["path"]) == control
    batches = check_training_batches(actual, read(control["path"]), 1000)
    import torch

    torch.set_num_threads(2)
    checkpoint = actual["checkpoint"]
    assert ref(checkpoint["path"]) == checkpoint
    state = torch.load(checkpoint["path"], weights_only=True, map_location="cpu", mmap=True)
    assert state["step"] == state["config"]["steps"] == 1000
    assert state["config"]["gradient_charbonnier_epsilon"] == 0.0003
    assert state["config"]["mesh_texture_fraction"] == 0.1
    assert state["config"]["reconstruction_charbonnier_epsilon"] == 0.0003
    assert state["config"]["initialized_from"] == queue["expected_lineage"]
    assert len(state["model"]) == len(state["ema"]) == 91
    assert len(state["optimizer"]["state"]) == 89
    assert all(float(s["step"]) == 1000 for s in state["optimizer"]["state"].values())
    values = [*state["model"].values(), *state["ema"].values()]
    values += [
        v
        for s in state["optimizer"]["state"].values()
        for v in s.values()
        if isinstance(v, torch.Tensor)
    ]
    assert all(torch.isfinite(v).all() for v in values)
    sources = list((Path(queue["work"]) / "src/demosaic").glob("*.py"))
    trained = Path(state["config"]["source_snapshot"])
    assert len(sources) == 69 and all(
        p.read_bytes() == (trained / p.name).read_bytes() for p in sources
    )
    assert not torch.cuda.is_initialized()
    target = root / "V142-step1000-inference.pt"
    os.link(checkpoint["path"], target)
    target.chmod(0o444)
    save(
        root / "endpoint-verification-v1.json",
        {
            "training_result": binding,
            "checkpoint": ref(target),
            "training_input_comparison": batches,
            "EMA_tensors": 91,
            "Adam_states": 89,
            "Adam_steps": 1000,
            "finite_state_values": sum(v.numel() for v in values),
            "trained_source_modules_exact": 69,
            "new_neural_forwards": 0,
        },
    )
    plan = {
        **queue,
        "checkpoint": ref(target),
        "inputs": [
            *queue["inputs"],
            binding,
            ref(target),
            ref(root / "endpoint-verification-v1.json"),
        ],
    }
    save(root / "plan-v1.json", plan)
    guard(plan)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("prepare", "bind", "run"))
    p.add_argument("root", type=Path)
    p.add_argument("--training-plan", type=Path)
    args = p.parse_args()
    if args.mode == "prepare":
        prepare(args.root.resolve(), args.training_plan.resolve())
    elif args.mode == "bind":
        bind(args.root.resolve())
    else:
        run_native(args.root.resolve())
