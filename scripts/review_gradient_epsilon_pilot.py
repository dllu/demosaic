"""Prepare fixed V141 native/flat review and bind its actual completed endpoint."""

import argparse
import os
from pathlib import Path

from bind_patch_memory_review import matching_batches
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
        comparison_scope="V141 complete1k small-gradient-epsilon pilot versus savedV129 matched control. "
        "Same V120/data90782/27/seed70/quota.5/zeroPSF/B16/native256/BF16/LR1e-5/warm100. "
        "Only spatial-gradient epsilon3e-4→3e-5; actual1000 clean/noisy matches required. "
        "102 fixed IEEE-FP32 calls:64shadow/16ordinary/16faintADC/4mainGFX512/2mesh768. "
        "Reuse408 V120/V129/V136/V137 predictions, same ROIs/noise/displays/source masks. "
        "Native160 exact-syntheticGT triplets; binned and separateISO100 references notGT. "
        "Both corrected protectedGFX pairs, both extra-mesh priors and cameraJPEGs. "
        "No new noise/RAW or old-model inference. Not full427/camera/color/fullframe/speed quality.",
    )
    # Label-only variants preserve V140's published operator bytes and bindings.
    # Freeze each new operator here before it prepares or reads any predictions.
    for original, destination in [
        ("report_pilot_flat_safety.py", "flat-operator-v1.py"),
        ("audit_pilot_flat_safety.py", "flat-auditor-v1.py"),
    ]:
        text = (REPO / "scripts" / original).read_text().replace("V140", "V141")
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
            "changes": "Only V140→V141 labels and an explicit repository root for relocated operator. "
            "No scoring, source selection, ROI, transform, noise, pixel or audit-tolerance changes.",
        },
    )


def bind(root):
    queue = read(root / "queue-plan-v1.json")
    guard(queue)
    training = read(queue["training_plan"]["path"])
    guard(training)
    status = read(Path(training["root"]) / "status.json")
    assert status["plan"] == queue["training_plan"]
    assert status["status"] == "completed-gradient-epsilon-training-awaiting-quality-review"
    assert not live(status["owner"]) and status["child"] is None
    binding = status["completed"]["train"]
    assert ref(binding["path"]) == binding
    actual = read(binding["path"])
    assert actual["status"] == "completed-small-gradient-epsilon-pilot-phase"
    assert actual["arm"] == "V141" and actual["phase"] == "train" and not live(actual["owner"])
    assert actual["updates"] == actual["all_AdamW_steps"] == 1000
    assert actual["model_EMA_tensor_count"] == 91 and actual["optimizer_state_count"] == 89
    assert actual["model_EMA_Adam_finite"] and actual["all_observed_inputs_match_saved_control"]
    assert actual["counts"]["training_forwards"] == actual["counts"]["optimizer_steps"] == 1000
    assert (
        actual["counts"]["validation_forwards"] == 64
        and actual["counts"]["encoder_forwards"] == 1064
    )
    control = actual["matched_control_result"]
    assert ref(control["path"]) == control
    matching_batches(actual, read(control["path"]))
    import torch

    torch.set_num_threads(2)
    checkpoint = actual["checkpoint"]
    assert ref(checkpoint["path"]) == checkpoint
    state = torch.load(checkpoint["path"], weights_only=True, map_location="cpu", mmap=True)
    assert state["step"] == state["config"]["steps"] == 1000
    assert state["config"]["gradient_charbonnier_epsilon"] == 0.00003
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
    target = root / "V141-step1000-inference.pt"
    os.link(checkpoint["path"], target)
    target.chmod(0o444)
    save(
        root / "endpoint-verification-v1.json",
        {
            "training_result": binding,
            "checkpoint": ref(target),
            "all1000_clean_and_noisy_batches_match_saved_V129": True,
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
