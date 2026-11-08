"""Matched whole/directional response stages from the identical V187 EMA donor."""

import argparse
import gc
import json
import math
import shutil
import time
from functools import partial
from pathlib import Path

from directional_trial_protocol import (
    ADMISSION,
    MODES,
    REPO,
    dependency,
    factory,
    freeze,
    guard,
    launch,
    objective_total,
    read,
    ref,
    require_launch,
    resources,
    save,
)
from directional_trial_protocol import (
    TRIAL as ROOT,
)
from phase_admission_protocol import owner_live

ARTIFACTS = ROOT / "artifacts"
METHODS = {
    mode: {endpoint: f"V195-{mode}-response-{endpoint}" for endpoint in ["raw", "EMA"]}
    for mode in MODES
}


def common_engine():
    import train_coherent_pair_evidence_engine as common

    common.ROOT = ROOT
    return common


def load_donor(config, state):
    module = factory(config)
    module.load_state_dict(state, strict=True)
    return module


def ready():
    result = read(ADMISSION / "admission-result-v1.json")
    assert result["status"].startswith("pass-V195-V187-EMA-parity")
    assert not owner_live(result["owner"])
    inspection = read(ADMISSION / "CPU-inspection-v1.json")
    assert inspection["status"] == "pass-V195-four-probes-eight-CPU-raw-EMA-loads-and-Adam"
    assert inspection["admission"] == ref(ADMISSION / "admission-result-v1.json")


def prepare():
    dep = dependency()
    ready()
    assert not ROOT.exists()
    baseline = read(dep["V187_plan"]["path"])
    import torch
    from phase_wave_training_state import clocks, fresh_state, inherited_hash
    from profile_raw_kernel_inference import model_hash

    assert not torch.cuda.is_initialized()
    donor = torch.load(dep["donor"]["export"]["path"], map_location="cpu", weights_only=True)
    module = load_donor(dep["donor"]["module_config"], donor["state_dict"])
    optimizer, ema = fresh_state(module, lr=0.001, weight_decay=0.01)
    assert model_hash(module) == dep["donor"]["module_hash"]
    assert inherited_hash(module) == dep["initializer"]["module_hash"]
    assert clocks(module, optimizer) == {"tensors": 4, "states": 0, "steps": []}
    assert all(torch.equal(p, ema[n]) for n, p in module.named_parameters() if p.requires_grad)
    assert module.wave_readout.mixing.weight.count_nonzero() > 0
    assert sum(p.numel() for p in module.parameters() if p.requires_grad) == 508
    proof = {
        "full_module_hash": model_hash(module),
        "inherited_hash": inherited_hash(module),
        "fresh_Adam": clocks(module, optimizer),
        "EMA_equals_trained_donor_head": True,
        "head_parameters": 508,
        "head_tensors": 4,
        "strict_full_state_tensors": 193,
        "head_final_weights_nonzero": True,
        "CPU_only_no_forward": True,
    }
    ROOT.mkdir()
    for mode in MODES:
        (ARTIFACTS / mode / "checkpoints").mkdir(parents=True)
    (ARTIFACTS / "native").mkdir()
    work, sources = freeze(ROOT, ["train_directional_response.py", "audit_directional_training.py"])
    plan = {
        k: baseline[k]
        for k in [
            "cache",
            "pair_units",
            "training_provenance",
            "frozen_component",
            "design",
            "prior_scores",
            "metrics_sources",
            "native_cases",
            "processing_order",
            "sampling_library",
            "domain_weights",
            "steps",
            "warmup",
            "gradient_clip",
            "CUDA_quota_GiB",
            "launch_RAM_GiB",
        ]
    }
    plan.update(
        status="prepared-matched-response-head-training-from-completed-V187-EMA",
        created_unix_UTC=time.time(),
        root=str(ROOT),
        work=str(work),
        artifacts=str(ARTIFACTS),
        runner=ref(work / "scripts/train_directional_response.py"),
        auditor=ref(work / "scripts/audit_directional_training.py"),
        seed=202611080195,
        modes=list(MODES),
        methods=METHODS,
        module_config=dep["donor"]["module_config"],
        donor=dep["donor"],
        initializer=dep["initializer"],
        dependency=dep,
        CPU_initialization=proof,
        lr=0.001,
        weight_decay=0.01,
        EMA_decay=0.999,
        head_initial_updates=0,
        prior_donor_head_updates=900,
        inherited_network_updates=1800,
        inherited_adapter_updates=900,
        minimum_GiB={"local": 40, "RAM": 32},
        total_new_local_forecast_GiB=2.0,
        total_new_external_forecast_GiB=0,
        admission=ref(ADMISSION / "admission-result-v1.json"),
        admission_inspection=ref(ADMISSION / "CPU-inspection-v1.json"),
        V187_plan=dep["V187_plan"],
        V187_scores=ref(Path(dep["V187_plan"]["path"]).parent / "scores-v1.json"),
        baseline_plan=baseline["baseline_plan"],
        baseline_scores=baseline["baseline_scores"],
        loss_source=ref(work / "scripts/directional_pair_objective.py"),
        expected_training_counts_per_arm={
            "wrapper": 900,
            "frozen": 900,
            "network": 900,
            "sampler": 4500,
            "projection": 900,
        },
        expected_quality_counts={
            "wrapper": 3288,
            "frozen": 3288,
            "network": 3000,
            "sampler": 15000,
            "projection": 3000,
        },
        storage_scope="Reuse immutable datasets, cached parents, manifests and baseline native encodings without copying them. Selective code import closure only. Total new local budget2GiB covers four endpoints' native RGB+wave encodings(uncompressed worst<1GiB),ten factored checkpoints,four strict exports,compressed receipts,compact current-comparator figures/browser captures and Git. No regeneration or recopy of all historical panels. No external writes. Check local40/RAM32 before every forward; launchRAM52/CUDAquota24.",
        scope="Matched whole versus directional response pressure. Both start the same completed V187 EMA full193state, trained508parameter head and fresh identical head Adam/EMA clocks0;189 inherited V183 EMA tensors remain frozen. Each uses the same1000 cached rows,900 noisy updates,3600 images,100 ADC skips,five checkpoints and genuine row8restore with no prefix replay. Nine old terms/masks,loss order,domain weights,LR,schedule,clip,EMA unchanged. Add.25domain-weight whole response(control,totalwhole.50)or eight-region response(directional,oldwhole.25). Equal added weights do not imply equal gradient norms. This is a new matched retraining stage,not resumed old Adam history. Probe checkpoints forbidden as initializers. Both states of both arms require all822quality cases,quiet/absent/fresh flats,natural detail and both protected GFX families with native100percent triplets. All103 neural sources unchanged. Cached scenes/JPEGs/siblings remain heldout; real references are qualitative,not exact GT. No new source/noise draw,parent/DINO inference,RAW decode or original/dataz access. No quality claim at launch.",
    )
    plan["inputs"] = [
        plan[k]
        for k in [
            "cache",
            "pair_units",
            "training_provenance",
            "design",
            "prior_scores",
            "sampling_library",
            "admission",
            "admission_inspection",
            "V187_plan",
            "V187_scores",
            "baseline_plan",
            "baseline_scores",
        ]
    ]
    plan["inputs"] += plan["metrics_sources"] + [
        dep[k] for k in ["publication", "verification", "CPU_result", "CPU_tests"]
    ]
    plan["inputs"] += [dep["donor"]["export"], dep["initializer"]["export"]]
    plan["frozen_files"] = sources
    resources(plan)
    assert shutil.disk_usage(REPO).free > (40 + 2) * 2**30
    save(ROOT / "plan-v1.json", plan)
    print(
        "Prepared matched arms from V187 EMA; 2x900 updates; fresh head clocks0; local budget2GiB"
    )


def train(mode):
    plan = read(ROOT / "plan-v1.json")
    guard(plan, __file__)
    common = common_engine()
    owner = require_launch(ROOT, mode)
    (ROOT / f"{mode}-train.claim").open("x").close()
    import numpy as np
    import torch
    from directional_pair_objective import objective as objective_impl

    objective = partial(objective_impl, mode=mode)
    from phase_wave_training_state import (
        clocks,
        fresh_state,
        inherited_hash,
        readout_parameters,
        update_ema,
    )
    from profile_raw_kernel_inference import model_hash
    from spatial_wave_training_state import pack_checkpoint, restore_factored

    from demosaic.prediction_archive import fingerprint

    common.runtime(plan)
    torch.manual_seed(plan["seed"])
    counts = dict.fromkeys(["wrapper", "frozen", "network", "sampler", "projection"], 0)
    initial = torch.load(plan["donor"]["export"]["path"], map_location="cpu", weights_only=True)
    module = common.instrument(
        load_donor(plan["module_config"], initial["state_dict"]).cuda(),
        counts,
    ).train()
    assert model_hash(module) == plan["donor"]["module_hash"]
    del initial
    optimizer, ema = fresh_state(module, lr=plan["lr"], weight_decay=plan["weight_decay"])
    inherited = plan["initializer"]["module_hash"]
    assert inherited_hash(module) == inherited
    cpu_rng, cuda_rng = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
    save(
        ROOT / f"{mode}-initial-state-v1.json",
        {
            "mode": mode,
            "donor": plan["donor"]["export"],
            "module_hash": model_hash(module),
            "inherited_hash": inherited,
            "Adam": clocks(module, optimizer),
            "EMA_equals_donor_head": all(
                torch.equal(p, ema[n]) for n, p in module.named_parameters() if p.requires_grad
            ),
            "CPU_RNG": fingerprint(cpu_rng.numpy()),
            "CUDA_RNG": fingerprint(cuda_rng.cpu().numpy()),
            "seed": plan["seed"],
            "new_module_forwards": 0,
        },
    )
    rows = read(plan["cache"]["path"])["batches"]
    units = read(plan["pair_units"]["path"])["rows"]
    updates = skipped = images = 0
    trace = []
    checkpoints = []
    restoration = None
    maxima = {n: 0.0 for n in readout_parameters(module)}
    with (ROOT / f"{mode}-train-trace-v1.jsonl").open("x") as journal:
        for step, item in enumerate(rows, 1):
            common.resources(plan, mode, owner)
            assert (
                ref(item["arrays"]["path"]) == item["arrays"]
                and ref(item["parent"]["path"]) == item["parent"]
            )
            arrays = dict(np.load(item["arrays"]["path"], allow_pickle=False))
            parent = np.load(item["parent"]["path"], allow_pickle=False)
            assert {k: fingerprint(v) for k, v in arrays.items()} == item["inputs"] and fingerprint(
                parent
            ) == item["parent_values"]
            assert units[step - 1]["step"] == step and units[step - 1]["batch"] == item["arrays"]
            phase = max(0, step - plan["warmup"]) / (plan["steps"] - plan["warmup"])
            lr = (
                plan["lr"]
                * min(1, step / plan["warmup"])
                * (0.1 + 0.9 * (1 + math.cos(math.pi * phase)) / 2)
            )
            row = {
                "step": step,
                "batch": item["arrays"],
                "parent": item["parent"],
                "domain": item["metadata"]["domain"],
                "noisy": bool(np.any(arrays["variance"] > 0)),
                "lr": lr,
            }
            if row["noisy"]:
                batch = {k: torch.from_numpy(v).cuda() for k, v in arrays.items()}
                base = torch.from_numpy(parent).cuda()
                pair_units = torch.tensor(
                    units[step - 1]["candidate_units_FP32"], device="cuda", dtype=torch.float32
                ).reshape(-1, 1, 1, 1)
                optimizer.zero_grad(set_to_none=True)
                for group in optimizer.param_groups:
                    group["lr"] = lr
                output, aux = module(
                    base,
                    *(batch[k] for k in ["packed", "variance", "colors", "wb"]),
                    return_aux=True,
                )
                loss, terms, mask = objective(
                    output,
                    aux["frozen_output"],
                    batch,
                    pair_units,
                    plan["domain_weights"][row["domain"]],
                )
                assert torch.isfinite(loss)
                loss.backward()
                zero = []
                for name, p in readout_parameters(module).items():
                    assert p.grad is not None and torch.isfinite(p.grad).all(), name
                    maxima[name] = max(maxima[name], float(p.grad.abs().max()))
                    if p.grad.count_nonzero() == 0:
                        zero.append(name)
                assert all(
                    p.grad is None
                    for n, p in module.named_parameters()
                    if not n.startswith("wave_readout.")
                )
                norm = torch.nn.utils.clip_grad_norm_(
                    readout_parameters(module).values(),
                    plan["gradient_clip"],
                    error_if_nonfinite=True,
                )
                optimizer.step()
                updates += 1
                images += len(base)
                decay = update_ema(module, ema, updates=updates)
                row.update(
                    loss=float(loss.detach()),
                    terms={k: float(v.detach()) for k, v in terms.items()},
                    gradient_norm=float(norm),
                    zero_gradient_tensors=zero,
                    flat_mask=fingerprint(mask.cpu().numpy()),
                    flat_eligible_pixels=int(mask.sum()),
                    wave_RMS_DN16=float(aux["wave_correction"].detach().square().mean().sqrt())
                    * 65535,
                    EMA_decay=decay,
                )
                assert row["loss"] == objective_total(
                    row["terms"], plan["domain_weights"][row["domain"]]
                )
                del batch, base, pair_units, output, aux, loss, terms, mask
            else:
                skipped += 1
                row["skipped"] = "zero variance;no matching,readout or optimizer call"
            row.update(updates=updates, counts=dict(counts))
            trace.append(row)
            journal.write(json.dumps(row, allow_nan=False) + "\n")
            journal.flush()
            if step == 1 or step % 10 == 0:
                common.progress(
                    mode,
                    {
                        "status": "training",
                        "owner": owner,
                        "step": step,
                        "updates": updates,
                        "counts": dict(counts),
                        "peak_CUDA_bytes": torch.cuda.max_memory_allocated(),
                    },
                )
            if step in [8, 250, 500, 750, 1000]:
                assert inherited_hash(module) == inherited and clocks(module, optimizer) == {
                    "tensors": 4,
                    "states": 4,
                    "steps": [float(updates)],
                }
                path = ARTIFACTS / mode / "checkpoints" / f"wave-step{step:04d}.pt"
                payload = {
                    "models": module.state_dict(),
                    "mode": mode,
                    "ema": ema,
                    "optimizer": optimizer.state_dict(),
                    "step": step,
                    "updates": updates,
                    "inherited_hash": inherited,
                    "CPU_RNG": torch.get_rng_state(),
                    "CUDA_RNG": torch.cuda.get_rng_state(),
                    "counts": dict(counts),
                    "component": type(module).__name__,
                    "module_config": plan["module_config"],
                    "plan": ref(ROOT / "plan-v1.json"),
                }
                with path.open("xb") as stream:
                    torch.save(pack_checkpoint(payload, plan["initializer"]["export"]), stream)
                checkpoints.append(ref(path))
                del payload
                if step == 8:
                    before = model_hash(module)
                    saved = torch.load(path, map_location="cpu", weights_only=True)
                    del module, optimizer
                    gc.collect()
                    module = common.instrument(
                        factory(plan["module_config"]).cuda(), counts
                    ).train()
                    optimizer, ema = restore_factored(
                        module, saved, lr=plan["lr"], weight_decay=plan["weight_decay"]
                    )
                    assert model_hash(module) == before and inherited_hash(module) == inherited
                    restoration = {
                        "checkpoint": ref(path),
                        "model_Adam_EMA_CPU_CUDA_RNG_exact": True,
                        "continued_at_row": 9,
                        "repeated_prefix_forwards": 0,
                    }
                    save(ROOT / f"{mode}-restoration-v1.json", restoration)
                    del saved
            del arrays, parent
    assert len(trace) == 1000 and updates == 900 and skipped == 100 and images == 3600
    assert counts == {
        "wrapper": 900,
        "frozen": 900,
        "network": 900,
        "sampler": 4500,
        "projection": 900,
    }
    assert inherited_hash(module) == inherited and all(v > 0 for v in maxima.values())
    assert torch.equal(cpu_rng, torch.get_rng_state()) and torch.equal(
        cuda_rng, torch.cuda.get_rng_state()
    )
    guard(plan, __file__)
    save(
        ROOT / f"{mode}-train-result-v1.json",
        {
            "status": "completed-V195-matched-response-head-from-V187-EMA",
            "mode": mode,
            "donor": plan["donor"]["export"],
            "owner": owner,
            "plan": ref(ROOT / "plan-v1.json"),
            "trace": trace,
            "checkpoints": checkpoints,
            "final_checkpoint": checkpoints[-1],
            "updates": updates,
            "ADC_skips": skipped,
            "training_images": images,
            "counts": counts,
            "final_Adam": clocks(module, optimizer),
            "inherited189_tensors_unchanged": True,
            "inherited_hash": inherited,
            "RNG_unchanged": True,
            "restoration": restoration,
            "parameter_maximum_gradients": maxima,
            "peak_CUDA_allocated_bytes": torch.cuda.max_memory_allocated(),
            "new_parent_DINO_forwards": 0,
            "new_source_noise_draws": 0,
            "scope": plan["scope"],
        },
    )
    common.progress(
        mode,
        {
            "status": "completed-training",
            "owner": owner,
            "step": 1000,
            "updates": 900,
            "counts": counts,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "launch", "train"])
    parser.add_argument("--mode", choices=MODES)
    args = parser.parse_args()
    if args.phase == "prepare":
        prepare()
    else:
        assert args.mode in MODES
        ready()
        if args.phase == "launch":
            print(launch(ROOT, "train", mode=args.mode))
        else:
            try:
                train(args.mode)
            except BaseException as exc:
                save(
                    ROOT / f"{args.mode}-train-failure-v1.json",
                    {"error": repr(exc), "time_UTC": time.time()},
                )
                raise
