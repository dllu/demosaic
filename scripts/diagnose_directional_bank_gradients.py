"""Read-only gradient routing at trained weights; no optimizer or EMA updates."""

import argparse
import gc
import hashlib
import json
import math
import os
import time
from pathlib import Path

import psutil
import torch
import yaml
from profile_raw_kernel_inference import model_hash
from torch.utils.data import default_collate

from demosaic.data import CleanDataset
from demosaic.inference import load_checkpoint
from demosaic.losses import reconstruction_loss
from demosaic.paired_training import PairedDataset, paired_reconstruction_loss
from demosaic.precision import amp_context, ieee_fp32
from demosaic.raw_clean import RawCleanDataset
from demosaic.suite import observation
from demosaic.train import batch_fingerprint, prepare_training_batch


def read(path):
    return json.loads(Path(path).read_text())


def ref(path):
    path = Path(path).resolve()
    with path.open("rb") as stream:
        sha = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path), "sha256": sha}


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def compare(a, b):
    """Scalar FP64 norm/dot accumulation from CPU copies of FP32 gradients."""
    assert a.keys() == b.keys()
    aa, bb, dd, ab, maximum, changed = [], [], [], [], 0.0, 0
    for key in a:
        x, y = a[key].double(), b[key].double()
        delta = x - y
        aa.append(float(x.square().sum()))
        bb.append(float(y.square().sum()))
        dd.append(float(delta.square().sum()))
        ab.append(float((x * y).sum()))
        maximum = max(maximum, float(delta.abs().max()))
        changed += not torch.equal(a[key], b[key])
    an, bn, dn = (math.sqrt(math.fsum(v)) for v in (aa, bb, dd))
    return {
        "tensors": len(a),
        "changed_tensors": changed,
        "connected_l2": an,
        "detached_l2": bn,
        "difference_l2": dn,
        "difference_over_connected_l2": dn / max(an, 1e-30),
        "cosine": math.fsum(ab) / max(an * bn, 1e-30),
        "maximum_abs_difference": maximum,
    }


def route(model, batch, domain, device, precision, detach):
    model.zero_grad(set_to_none=True)
    branch, captured = model.pretrained_rgb.raw_directional, {}

    def capture(_module, args, _output):
        for name, value in [("base", args[0]), ("features", args[4])]:
            value.retain_grad()
            captured[name] = value

    handles = [branch.register_forward_hook(capture)]
    if detach:
        handles.append(
            branch.bank.register_forward_pre_hook(lambda _module, args: (args[0].detach(),))
        )
    try:
        with amp_context(device, dtype=precision):
            prediction, auxiliary = model(
                *(batch[k] for k in ("packed", "variance", "colors", "wb", "matrix")),
                auxiliary=True,
            )
            if domain == "paired":
                loss, terms = paired_reconstruction_loss(prediction, batch, auxiliary)
            else:
                loss, terms = reconstruction_loss(
                    prediction, batch, auxiliary, camera_supervision="sensor-valid-v1"
                )
        assert torch.isfinite(loss)
        with ieee_fp32():
            loss.backward()
        gradients = {
            name: p.grad.detach().cpu().clone()
            for name, p in model.named_parameters()
            if p.requires_grad and p.grad is not None
        }
        assert len(gradients) == 103
        assert all(torch.isfinite(value).all() for value in gradients.values())
        assert all(p.grad is None for p in model.context.backbone.parameters())
        cut = {name: value.grad.detach().cpu().clone() for name, value in captured.items()}
        with ieee_fp32():
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1, error_if_nonfinite=True)
        clipped = {
            name: p.grad.detach().cpu().clone()
            for name, p in model.named_parameters()
            if p.requires_grad and p.grad is not None
        }
        return {
            "prediction": prediction.detach().cpu(),
            "auxiliary": auxiliary.detach().cpu(),
            "loss": float(loss.detach()),
            "terms": {k: float(v.detach()) for k, v in terms.items()},
            "preclip_norm": float(norm),
            "raw": gradients,
            "clipped": clipped,
            "cut": cut,
        }
    finally:
        for handle in handles:
            handle.remove()
        assert not branch._forward_hooks and not branch.bank._forward_pre_hooks


def cases(plan, cfg, model, device, preflight):
    size, batch_size = (64, 1) if preflight else (256, 16)
    datasets = {
        "commons": CleanDataset(
            cfg["manifest"],
            patch_size=size,
            seed=51,
            synthetic_fraction=0.2,
            flat_fraction=0.1,
            flat_chroma_stops=8,
            augmentation_downsample=2,
        ),
        "native": RawCleanDataset(
            cfg["raw_clean_manifest"],
            patch_size=size,
            seed=51,
            augmentation_downsample=2,
        ),
        "paired": PairedDataset(cfg["paired_manifest"], patch_size=size, seed=51),
    }
    for item in plan["training_batches"]:
        step, domain = item["step"], item["domain"]
        # Preserve global B16 source indices even in the separate B1 CPU check.
        indices = list(range((step - 1) * 16, (step - 1) * 16 + batch_size))
        clean = default_collate([datasets[domain][i] for i in indices])
        batch = prepare_training_batch(
            step, domain, clean, model=model, device=device, config=cfg, seed=51
        )
        digest = batch_fingerprint(
            {k: batch[k] for k in ("packed", "variance", "colors", "wb", "matrix", "shot", "read")}
        )
        if not preflight:
            assert digest == item["input_sha256"], (step, digest, item["input_sha256"])
            assert (
                batch_fingerprint({k: v for k, v in batch.items() if k != "sensor_target"})
                == item["legacy_batch_sha256"]
            )
        yield {"kind": "training", "step": step, "domain": domain, "indices": indices}, batch
    del datasets
    protocol = yaml.safe_load(Path(plan["protocol"]["path"]).read_text())
    for item in plan["analytic_cases"]:
        level, contrast, period = (item[k] for k in ("level", "contrast", "period"))
        draws = 1 if preflight else 4
        coords = torch.arange(size, dtype=torch.float32)
        rgb = (
            (level * (1 + contrast * (coords * (2 * math.pi / period)).cos()))[None, None, None]
            .expand(draws, 3, size, size)
            .clone()
        )
        ids = [f"carrier-l{level}-c{contrast}-p{period}-draw{i}" for i in range(draws)]
        condition = next(x for x in protocol["conditions"] if x["name"] == item["condition"])
        for pattern in protocol["patterns"]:
            cpu = observation(
                rgb,
                ids,
                condition,
                pattern,
                protocol["white_balance"],
                protocol["camera_to_srgb"],
                20261016,
            )
            # These low-level gray fixtures do not clip in the camera/display
            # target conversion, so both clean targets coincide exactly.
            assert cpu["target"].min() >= 0 and cpu["target"].max() < 0.98
            cpu["sensor_target"] = cpu["target"].clone()
            cpu["shot"] = torch.full((draws,), condition["shot"])
            cpu["read"] = torch.full((draws,), condition["read"])
            yield (
                {"kind": "analytic", **item, "pattern": pattern},
                {k: v.to(device) for k, v in cpu.items()},
            )


def main(plan_path, output, device_name, preflight):
    plan = read(plan_path)
    output = output.resolve()
    assert output.is_relative_to(Path(plan["root"]))
    output.mkdir(parents=True, exist_ok=False)
    for item in plan["inputs"]:
        assert ref(item["path"]) == item
    for name, digest in plan["frozen_files"].items():
        assert ref(name)["sha256"] == digest
    assert ref(__file__) == plan["worker"]
    os.nice(10)
    torch.set_num_threads(2 if preflight else 4)
    assert psutil.virtual_memory().available > 40 * 2**30
    device = torch.device(device_name)
    if device.type == "cuda":
        prior = read(Path(plan["root"]) / "cpu-preflight/summary.json")
        assert prior["status"] == "completed-CPU-gradient-routing-preflight"
        assert prior["driver"] == plan["worker"]
        device = torch.device("cuda", torch.cuda.current_device())
        torch.cuda.set_per_process_memory_fraction(
            24 * 2**30 / torch.cuda.get_device_properties(device).total_memory, device
        )
    else:
        assert not torch.cuda.is_initialized() and os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    torch.set_float32_matmul_precision("high")
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    model, state = load_checkpoint(plan["checkpoint"]["path"], device)
    assert state["loaded_sha256"] == plan["checkpoint"]["sha256"]
    del state
    if device.type == "cuda":
        model.to(memory_format=torch.channels_last)
    model.train()
    initial, dino = model_hash(model), model_hash(model.context.backbone)
    assert dino == plan["DINO_sha256"]
    cfg = yaml.safe_load(Path(plan["template"]["path"]).read_text())
    records, started = [], time.monotonic()
    branch_prefix = "pretrained_rgb.raw_directional."
    for label, batch in cases(plan, cfg, model, device, preflight):
        assert time.monotonic() - started < 1800
        assert psutil.virtual_memory().available > 24 * 2**30
        model.set_noise(batch["shot"], batch["read"])
        precision = "float32" if preflight or label["kind"] == "analytic" else "bfloat16"
        rng = torch.get_rng_state()
        cuda_rng = torch.cuda.get_rng_state_all() if device.type == "cuda" else []
        a = route(model, batch, label.get("domain"), device, precision, False)
        torch.set_rng_state(rng)
        if cuda_rng:
            torch.cuda.set_rng_state_all(cuda_rng)
        b = route(model, batch, label.get("domain"), device, precision, True)
        assert torch.equal(a["prediction"], b["prediction"])
        assert torch.equal(a["auxiliary"], b["auxiliary"])
        assert a["loss"] == b["loss"] and a["terms"] == b["terms"]
        assert torch.equal(a["cut"]["features"], b["cut"]["features"])
        assert all(
            torch.equal(v, b["raw"][n]) for n, v in a["raw"].items() if n.startswith(branch_prefix)
        )
        groups = {
            "common": lambda n: not n.startswith(branch_prefix),
            "local_directional": lambda n: (
                n.startswith(branch_prefix) and not n.startswith(branch_prefix + "bank.")
            ),
            "bank": lambda n: n.startswith(branch_prefix + "bank."),
        }
        record = {
            "case": label,
            "examples": len(batch["packed"]),
            "precision": precision,
            "batch_sha256": batch_fingerprint(batch),
            "predictions_auxiliary_loss_terms_exact": True,
            "branch_raw_parameter_gradients_exact": True,
            "feature_cut_gradients_exact": True,
            "loss": a["loss"],
            "terms": a["terms"],
            "preclip_norm": {"connected": a["preclip_norm"], "detached": b["preclip_norm"]},
            "base_cut_gradient": compare({"base": a["cut"]["base"]}, {"base": b["cut"]["base"]}),
            "parameter_gradients": {
                stage: {
                    group: compare(
                        {n: v for n, v in a[stage].items() if select(n)},
                        {n: v for n, v in b[stage].items() if select(n)},
                    )
                    for group, select in groups.items()
                }
                for stage in ["raw", "clipped"]
            },
            "variance_floor_fraction": float((batch["variance"] <= 1e-8).float().mean()),
        }
        records.append(record)
        save(output / "partial.json", records)
        print(
            json.dumps(
                {
                    "case": label,
                    "common_gradient_relative_change": record["parameter_gradients"]["raw"][
                        "common"
                    ]["difference_over_connected_l2"],
                }
            ),
            flush=True,
        )
        del a, b, batch
        gc.collect()
    assert len(records) == 15
    assert model_hash(model) == initial and model_hash(model.context.backbone) == dino
    for name, digest in plan["frozen_files"].items():
        assert ref(name)["sha256"] == digest
    for item in plan["inputs"]:
        assert ref(item["path"]) == item
    save(
        output / "summary.json",
        {
            "status": "completed-CPU-gradient-routing-preflight"
            if preflight
            else "completed-read-only-bank-gradient-routing",
            "plan": ref(plan_path),
            "driver": ref(__file__),
            "device": str(device),
            "model_state_sha256_before_and_after": initial,
            "DINO_sha256": dino,
            "records": records,
            "new_training_updates": 0,
            "new_checkpoint_or_default": False,
            "scope": "Connected versus bank-input-detached gradients at fixed V81 EMA. Identical forward values, losses, feature-cut gradients and raw branch parameter gradients are required. Training inputs replay original source/domain/noise identities; CPU preflight uses separate B1/native64 inputs. Analytic cases are explicit loss Jacobian fixtures, not new quality scores. No attribution of historical training causes, independent retraining effect, convergence or promotion.",
        },
    )
    print(json.dumps({"completed": True, "cases": len(records)}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", choices=["cpu", "cuda"], required=True)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    main(args.plan, args.output, args.device, args.preflight)
