"""Discarded genuine-parent mixed-domain optimizer replay of execution policies."""

import argparse
import gc
import json
import os
import shutil
from contextlib import redirect_stdout
from pathlib import Path

import psutil
import torch
import yaml
from audit_flat_palette import identical, train_rows
from profile_raw_kernel_inference import model_hash
from train_directional_interval_trial import guard, read, ref, save

import demosaic.train as training
from demosaic.safety import writable_path

FIELDS = (
    "model_config",
    "model",
    "ema",
    "optimizer",
    "python_rng",
    "torch_rng",
    "cuda_rng",
    "best",
    "step",
)
CASES = ("cpu-default", "cpu-strict", "cpu-resumed", "cuda-strict-a", "cuda-strict-b")
DINO_SHA = "370a84c2d9e1d216757422c0a25ceb82a0a106083ba8ca545d9b267e704540fd"


def prepare(root):
    root = writable_path(root)
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    files = [*Path("src/demosaic").glob("*.py"), *Path("scripts").glob("*.py")]
    files += [
        Path(p)
        for p in (
            "pyproject.toml",
            "uv.lock",
            "configs/evaluation.yaml",
            "third_party/gaussian/Noise2VST-LICENSE",
            "third_party/gaussian/KAIR-LICENSE",
            "third_party/dinov3/LICENSE.md",
        )
    ]
    for source in files:
        target = work / source
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    template = Path("configs/dino-convnext-directional-control-v78.yaml")
    cfg = yaml.safe_load(template.read_text())
    cfg.update(
        log_every=1, checkpoint_every=6, val_batches=1, validation_images=1, min_available_gb=24
    )
    configs = {}
    for case in CASES:
        options = dict(cfg)
        options["run"] = str(work / "runs" / case)
        if case != "cpu-default":
            options["training_execution"] = "deterministic-v1"
        if case.startswith("cpu"):
            options.update(
                device="cpu",
                precision="float32",
                amp=False,
                channels_last=False,
                batch_size=1,
                patch_size=64,
                cpu_threads=2,
                workers=0,
                paired_workers=0,
                raw_clean_workers=0,
                seed=48,
                checkpoint_every=4,
            )
        path = work / "configs" / (case + ".yaml")
        path.write_text(yaml.safe_dump(options))
        configs[case] = str(path)
    parent = Path(
        "/mnt/external/demosaic/models/dino-convnext-wide-long-control-b16-v63-step20000.pt"
    )
    assert (
        ref(parent)["sha256"] == "ed70952dd33c5d7da39199bf1306b58b579862920fb0cccd6b222f19871bc9b5"
    )
    legacy_receipt = Path(".cache/experiments/directional-CPU-preflight-v1/receipt.json")
    legacy = read(legacy_receipt)["cases"]["control"]["checkpoint"]
    assert ref(legacy["path"]) == legacy
    inputs = [template, parent, legacy_receipt, Path(legacy["path"])]
    inputs += [
        Path(cfg[k])
        for k in ("manifest", "validation_manifest", "raw_clean_manifest", "paired_manifest")
    ]
    plan = {
        "root": str(root),
        "work": str(work),
        "parent": ref(parent),
        "python": str(Path(".venv/bin/python3").absolute()),
        "configs": configs,
        "legacy_CPU": legacy,
        "inputs": [ref(p) for p in inputs],
        "frozen_files": {str(p): ref(p)["sha256"] for p in sorted(work.rglob("*")) if p.is_file()},
        "scope": "Discarded genuine V63 EMA training, original4000 LR horizon. CPU B1/native64/FP32 four updates, default compatibility and strict2+2 resume. Two fresh CUDA B16/native256/BF16 strict six-update processes cover Commons/native/paired. Tiny real validation; no quality or throughput claim, no model promotion.",
    }
    save(root / "plan.json", plan)
    print(json.dumps({"plan": ref(root / "plan.json"), "frozen_files": len(plan["frozen_files"])}))


def flags():
    return {
        "matmul_fp32": torch.backends.cuda.matmul.fp32_precision,
        "conv_fp32": torch.backends.cudnn.conv.fp32_precision,
        "benchmark": torch.backends.cudnn.benchmark,
        "deterministic": torch.backends.cudnn.deterministic,
        "algorithms": torch.are_deterministic_algorithms_enabled(),
        "warn_only": torch.is_deterministic_algorithms_warn_only_enabled(),
    }


def worker(plan_path, case):
    os.nice(5)
    plan = read(plan_path)
    guard(plan)
    cpu, strict = case.startswith("cpu"), case != "cpu-default"
    root, work = Path(plan["root"]), Path(plan["work"])
    output = writable_path(work / "results" / case)
    output.mkdir(parents=True, exist_ok=False)
    assert psutil.virtual_memory().available > 40 * 2**30
    assert shutil.disk_usage(root).free > 128 * 2**30
    assert shutil.disk_usage("/mnt/external").free > 500 * 2**30
    if cpu:
        assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not torch.cuda.is_initialized()
    else:
        assert read(root / "cpu-audit.json")["status"] == "passed-CPU-execution-preflight"
        device = torch.device("cuda", torch.cuda.current_device())
        torch.cuda.set_per_process_memory_fraction(
            24 * 2**30 / torch.cuda.get_device_properties(device).total_memory, device
        )
    before = flags()
    parent = torch.load(plan["parent"]["path"], map_location="cpu", weights_only=True, mmap=True)
    assert parent["step"] == 20000 and len(parent["ema"]) == 91
    constructor, prepare_batch, make_optimizer = (
        training.JointDemosaic,
        training.prepare_training_batch,
        training.make_optimizer,
    )
    current = {"expected": parent["ema"], "resuming": False}
    starts, observations, gradients = [], [], []

    def active_policy():
        assert torch.backends.cudnn.benchmark is not strict
        assert torch.backends.cudnn.deterministic is strict
        assert torch.are_deterministic_algorithms_enabled() is strict
        assert not torch.is_deterministic_algorithms_warn_only_enabled()

    def instrument(options):
        active_policy()
        net = constructor(options)
        current["model"] = net

        def first_forward(module, args):
            active_policy()
            actual = module.restoration_state_dict()
            assert len(actual) == 99
            assert all(torch.equal(actual[k].cpu(), v) for k, v in current["expected"].items())
            if not current["resuming"]:
                extra = actual.keys() - parent["ema"].keys()
                assert len(extra) == 8 and all(
                    k.startswith("pretrained_rgb.raw_directional.") for k in extra
                )
                assert all(
                    p.count_nonzero() == 0
                    for n, p in module.pretrained_rgb.raw_directional.named_parameters()
                    if not n.startswith("local.")
                )
            assert model_hash(module.context.backbone) == DINO_SHA
            starts.append(
                {
                    "resume": current["resuming"],
                    "common_weights_exact": True,
                    "branch_sha256": model_hash(module.pretrained_rgb.raw_directional),
                    "DINO_sha256": DINO_SHA,
                }
            )
            handle.remove()

        handle = net.register_forward_pre_hook(first_forward)
        return net

    def observe(*args, **kwargs):
        active_policy()
        batch = prepare_batch(*args, **kwargs)
        observations.append(
            {
                "step": args[0],
                "domain": args[1],
                "full_sha256": training.batch_fingerprint(batch),
                "legacy_sha256": training.batch_fingerprint(
                    {k: v for k, v in batch.items() if k != "sensor_target"}
                ),
            }
        )
        return batch

    def optimizer_for(net, options):
        optimizer = make_optimizer(net, options)
        assert [g["lr_multiplier"] for g in optimizer.param_groups] == [1, 20]

        def before_step(*args):
            active_policy()
            active = [p for p in net.parameters() if p.requires_grad]
            assert len(active) == 97 and all(
                p.grad is not None and torch.isfinite(p.grad).all() for p in active
            )
            assert all(
                p.grad is None and not p.requires_grad for p in net.context.backbone.parameters()
            )
            gradients.append(97)

        optimizer.register_step_pre_hook(before_step)
        return optimizer

    def finish():
        net = current.pop("model")
        assert model_hash(net.context.backbone) == DINO_SHA
        assert all(
            not p.requires_grad and p.grad is None for p in net.context.backbone.parameters()
        )

    steps = 4 if cpu else 6
    training.JointDemosaic, training.prepare_training_batch, training.make_optimizer = (
        instrument,
        observe,
        optimizer_for,
    )
    try:
        with (output / "train.log").open("x") as log, redirect_stdout(log):
            checkpoint = training.train(
                plan["configs"][case],
                initialize=plan["parent"]["path"],
                stop_after=2 if case == "cpu-resumed" else steps,
            )
            finish()
            gc.collect()
            if case == "cpu-resumed":
                middle = output / "step2.pt"
                shutil.copyfile(checkpoint, middle)
                partial = torch.load(middle, map_location="cpu", weights_only=True, mmap=True)
                current.update(expected=partial["model"], resuming=True)
                checkpoint = training.train(plan["configs"][case], resume=middle, stop_after=2)
                finish()
    finally:
        training.JointDemosaic, training.prepare_training_batch, training.make_optimizer = (
            constructor,
            prepare_batch,
            make_optimizer,
        )
    assert flags() == before
    assert len(gradients) == steps
    state = torch.load(checkpoint, map_location="cpu", weights_only=True, mmap=True)
    assert state["step"] == steps and state["config"]["steps"] == 4000
    assert len(state["model"]) == len(state["ema"]) == 99 and len(state["optimizer"]["state"]) == 97
    for field in ("model", "ema"):
        assert all(torch.isfinite(v).all() for v in state[field].values())
    for values in state["optimizer"]["state"].values():
        assert int(values["step"]) == steps
        assert all(torch.isfinite(v).all() for v in values.values() if isinstance(v, torch.Tensor))
    rows = train_rows(Path(checkpoint).parent)
    assert [r["step"] for r in rows] == list(range(1, steps + 1))
    assert {r["domain"] for r in observations} == {"commons", "native", "paired"}
    if cpu:
        assert not torch.cuda.is_initialized()
    guard(plan)
    save(
        output / "receipt.json",
        {
            "status": "passed-discarded-mixed-domain-execution-case",
            "case": case,
            "plan": ref(plan_path),
            "config": ref(plan["configs"][case]),
            "checkpoint": ref(checkpoint),
            "runtime": state["config"]["training_execution_runtime"],
            "starts": starts,
            "observations": observations,
            "rows": rows,
            "finite_gradients_each_step": gradients,
            "finite_states": {"model": 99, "EMA": 99, "AdamW": 97},
            "caller_flags_restored": True,
            "peak_CUDA_bytes": 0 if cpu else torch.cuda.max_memory_allocated(),
            "scope": plan["scope"],
        },
    )
    print(json.dumps({"case": case, "receipt": ref(output / "receipt.json")}))


def audit(plan_path, device):
    plan = read(plan_path)
    guard(plan)
    root, work = Path(plan["root"]), Path(plan["work"])
    names = CASES[:3] if device == "cpu" else CASES[3:]
    receipts = {k: read(work / "results" / k / "receipt.json") for k in names}
    for item in receipts.values():
        assert item["status"] == "passed-discarded-mixed-domain-execution-case"
        assert ref(item["checkpoint"]["path"]) == item["checkpoint"]
    states = {
        k: torch.load(r["checkpoint"]["path"], map_location="cpu", weights_only=True, mmap=True)
        for k, r in receipts.items()
    }
    pairs = [(names[1], names[2])] if device == "cpu" else [(names[0], names[1])]
    if device == "cpu":
        states["archived-default"] = torch.load(
            plan["legacy_CPU"]["path"], map_location="cpu", weights_only=True, mmap=True
        )
        pairs += [(names[0], "archived-default")]
    for a, b in pairs:
        for field in FIELDS:
            identical(states[a][field], states[b][field])
    reference = receipts[names[0]]
    for receipt in receipts.values():
        identical(receipt["observations"], reference["observations"])
    if device == "cuda":
        assert [r["domain"] for r in reference["observations"]] == [
            "commons",
            "native",
            "commons",
            "commons",
            "native",
            "paired",
        ]
        assert (
            reference["observations"][0]["full_sha256"]
            == "b0ac985abbfa82a415e731e5094cb4f5ff31452e7ed7fbb4a7c39e870babcc7f"
        )
        for a, b in zip(receipts[names[0]]["rows"], receipts[names[1]]["rows"], strict=True):
            identical(
                {k: v for k, v in a.items() if k not in ("seconds_per_step", "cuda_gb")},
                {k: v for k, v in b.items() if k not in ("seconds_per_step", "cuda_gb")},
            )
    save(
        root / (device + "-audit.json"),
        {
            "status": "passed-" + device.upper() + "-execution-preflight",
            "plan": ref(plan_path),
            "receipts": [ref(work / "results" / k / "receipt.json") for k in names],
            "exact_pairs": pairs,
            "exact_fields": list(FIELDS),
            "actual_updates": 4 if device == "cpu" else 6,
            "all_selected_inputs_exact": True,
            "scope": plan["scope"],
        },
    )
    print(json.dumps({"audit": ref(root / (device + "-audit.json"))}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "worker", "audit"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--case", choices=CASES)
    parser.add_argument("--device", choices=("cpu", "cuda"))
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.path)
    elif args.action == "worker":
        parser.error("worker requires --case") if not args.case else worker(args.path, args.case)
    else:
        parser.error("audit requires --device") if not args.device else audit(
            args.path, args.device
        )
