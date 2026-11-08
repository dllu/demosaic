"""Matched RAW/innovation fresh heads above frozen V195 Whole EMA."""

import argparse
import gc
import json
import math
import time
from functools import partial

from admit_innovation_wave import MODES, factory
from admit_innovation_wave import ROOT as ADMISSION
from directional_trial_protocol import (
    REPO,
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
from phase_admission_protocol import owner_live

ROOT = REPO / ".cache/quality-20261108/V197-innovation-wave-trial-v1"
ARTIFACTS = ROOT / "artifacts"


def common_engine():
    import train_coherent_pair_evidence_engine as common

    common.ROOT = ROOT
    return common


def load_anchor(plan, mode, state):
    return factory(plan, mode).initialize_anchor(state)


def ready():
    probe = read(ADMISSION / "admission-result-v1.json")
    inspection = read(ADMISSION / "CPU-inspection-v1.json")
    assert probe["status"].startswith("pass-V197-two-fresh-heads")
    assert not owner_live(probe["owner"])
    assert inspection["admission"] == ref(ADMISSION / "admission-result-v1.json")
    assert inspection["status"].startswith("pass-V197-eight-strict-CPU")
    admission = read(ADMISSION / "plan-v1.json")
    assert admission["new_source"] == ref(REPO / "src/demosaic/late_innovation_wave.py")


def prepare():
    ready()
    assert not ROOT.exists()
    import torch
    from innovation_wave_state import anchor_hash, clocks, fresh
    from profile_raw_kernel_inference import model_hash

    assert not torch.cuda.is_initialized()
    admission = read(ADMISSION / "plan-v1.json")
    previous_path = REPO / ".cache/quality-20261108/V195-directional-response-trial-v1/plan-v1.json"
    previous = read(previous_path)
    anchor = admission["anchor"]
    donor = torch.load(anchor["export"]["path"], map_location="cpu", weights_only=True)
    proofs = []
    for mode in MODES:
        model = load_anchor(admission, mode, donor["state_dict"])
        optimizer, ema = fresh(model)
        assert anchor_hash(model) == anchor["module_hash"]
        assert clocks(model, optimizer) == {"tensors": 4, "states": 0, "steps": []}
        assert len(model.state_dict()) == 197
        assert sum(p.numel() for p in model.parameters() if p.requires_grad) == 508
        assert model.innovation_readout.mixing.weight.count_nonzero() == 0
        assert model.innovation_readout.mixing.bias.count_nonzero() == 0
        proofs.append(
            {
                "full_module_hash": model_hash(model),
                "anchor_hash": anchor_hash(model),
                "fresh_Adam": clocks(model, optimizer),
                "EMA_equals_fresh_head": all(
                    torch.equal(p, ema[n]) for n, p in model.named_parameters() if p.requires_grad
                ),
                "head_parameters": 508,
                "head_tensors": 4,
                "strict_full_state_tensors": 197,
                "CPU_only_no_forward": True,
            }
        )
    assert proofs[0] == proofs[1]
    ROOT.mkdir()
    for mode in MODES:
        (ARTIFACTS / mode / "checkpoints").mkdir(parents=True)
    work, sources = freeze(ROOT, ["train_innovation_wave.py", "audit_innovation_training.py"])
    plan = {
        k: previous[k]
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
        status="prepared-matched-fresh-RAW-innovation-heads-above-V195-WholeEMA",
        created_unix_UTC=time.time(),
        root=str(ROOT),
        work=str(work),
        artifacts=str(ARTIFACTS),
        runner=ref(work / "scripts/train_innovation_wave.py"),
        auditor=ref(work / "scripts/audit_innovation_training.py"),
        seed=202611080197,
        modes=list(MODES),
        methods={
            mode: {endpoint: f"V197-{mode}-wave-{endpoint}" for endpoint in ["raw", "EMA"]}
            for mode in MODES
        },
        module_config=anchor["module_config"],
        anchor=anchor,
        donor=anchor,
        initializer=anchor,
        CPU_initialization=proofs[0],
        lr=0.001,
        weight_decay=0.01,
        EMA_decay=0.999,
        head_initial_updates=0,
        prior_anchor_wave_training_updates=1800,
        minimum_GiB={"local": 40, "RAM": 32},
        total_new_local_forecast_GiB=2.0,
        total_new_external_forecast_GiB=0,
        admission=ref(ADMISSION / "admission-result-v1.json"),
        admission_inspection=ref(ADMISSION / "CPU-inspection-v1.json"),
        previous_plan=ref(previous_path),
        previous_trace=ref(previous_path.parent / "whole-train-result-v1.json"),
        lower_native_frequency=1 / 64,
        expected_training_counts_per_arm={
            "wrapper": 900,
            "frozen": 900,
            "network": 900,
            "sampler": 4500,
            "projection": 900,
        },
        planned_quality_cases_per_endpoint=822,
        planned_endpoints=4,
        scope="Matched two fresh508parameter wave heads above all193 frozen trainedV195WholeEMA tensors;197fullstate. RAW/innovation changes BOTH selection and localwave/support field,notselectionalone. Both wider1/64..1/3 band,eightbins,65/33/17support,identicalnewheadparameters/freshAdamEMA0,seed,1000cachedrows/900noisyupdates/3600images/100ADCskips,LRschedule/WD/clip andsameV195whole ten-termobjective(.50totalcoherent). Additionalheadcapacity/training vsanchor confounded;matchedRAWvsinnovation isolatesmeasurementarm. Preserveanchordonor's separateV187900+V195900wavehistory;neverclaimuninterruptednewheadAdamEMA. Truefactoredrow8restoreto9,fivecheckpointspermodes. Engineeringprobesneverinitializers. Targetsafterforwardonly;allprotectedmain3879/3880 andcab3842/3835/JPEGs/siblingsheldout. FuturequalitymustscoreallfourrawEMA822endpoints,actualquiet/absent/freshflats,naturalphotos,bothrealcapturefamilies,>=2native100%tripletsperimprovedmodel/checkpoint/noise/exposuremetadata;noqualityclaimsfromtrainingloss. Old103neuralfilesunchanged;104thnewsource. No newsource/noisedraws,parentDINOinference,RAWdecode,original/datazaccess. Compactcheckpointsbind193tensoranchor;reuseoldarraysinplace. Totalnewtrialbudget2GiBlocal above40GiBfloor,zeroexternalwrites.",
    )
    plan["inputs"] = [
        plan[k]
        for k in [
            "cache",
            "pair_units",
            "design",
            "sampling_library",
            "admission",
            "admission_inspection",
            "previous_plan",
            "previous_trace",
        ]
    ] + [anchor["export"], admission["new_source"]]
    plan["frozen_files"] = sources
    resources(plan)
    save(ROOT / "plan-v1.json", plan)
    print("Prepared identical fresh197state/508parameter arms;900updates each;2GiB local forecast")


def train(mode):
    plan = read(ROOT / "plan-v1.json")
    guard(plan, __file__)
    common = common_engine()
    owner = require_launch(ROOT, mode)
    (ROOT / f"{mode}-train.claim").open("x").close()
    import numpy as np
    import torch
    from directional_pair_objective import objective as objective_impl

    objective = partial(objective_impl, mode="whole")
    from innovation_wave_state import (
        anchor_hash,
        clocks,
        update_ema,
    )
    from innovation_wave_state import (
        fresh as fresh_state,
    )
    from innovation_wave_state import pack as pack_checkpoint
    from innovation_wave_state import (
        parameters as readout_parameters,
    )
    from innovation_wave_state import restore as restore_factored
    from profile_raw_kernel_inference import model_hash

    from demosaic.prediction_archive import fingerprint

    common.runtime(plan)
    torch.manual_seed(plan["seed"])
    counts = dict.fromkeys(["wrapper", "frozen", "network", "sampler", "projection"], 0)
    initial = torch.load(plan["donor"]["export"]["path"], map_location="cpu", weights_only=True)
    module = common.instrument(
        load_anchor(plan, mode, initial["state_dict"]).cuda(),
        counts,
    ).train()
    assert model_hash(module) == plan["CPU_initialization"]["full_module_hash"]
    del initial
    optimizer, ema = fresh_state(module, lr=plan["lr"], weight_decay=plan["weight_decay"])
    inherited = plan["initializer"]["module_hash"]
    assert anchor_hash(module) == inherited
    cpu_rng, cuda_rng = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
    save(
        ROOT / f"{mode}-initial-state-v1.json",
        {
            "mode": mode,
            "donor": plan["donor"]["export"],
            "module_hash": model_hash(module),
            "anchor_hash": inherited,
            "Adam": clocks(module, optimizer),
            "EMA_equals_fresh_head": all(
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
                    aux["anchor_aux"]["frozen_output"],
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
                    if not n.startswith("innovation_readout.")
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
                assert anchor_hash(module) == inherited and clocks(module, optimizer) == {
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
                    "anchor_hash": inherited,
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
                    module = common.instrument(factory(plan, mode).cuda(), counts).train()
                    optimizer, ema = restore_factored(
                        module, saved, lr=plan["lr"], weight_decay=plan["weight_decay"]
                    )
                    assert model_hash(module) == before and anchor_hash(module) == inherited
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
    assert anchor_hash(module) == inherited and all(v > 0 for v in maxima.values())
    assert torch.equal(cpu_rng, torch.get_rng_state()) and torch.equal(
        cuda_rng, torch.cuda.get_rng_state()
    )
    guard(plan, __file__)
    save(
        ROOT / f"{mode}-train-result-v1.json",
        {
            "status": "completed-V197-fresh-wave-head-above-frozen-V195-WholeEMA",
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
            "anchor193_tensors_unchanged": True,
            "anchor_hash": inherited,
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
