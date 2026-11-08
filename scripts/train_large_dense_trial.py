"""Train only the new wave readout above the completed frozen V183 EMA model."""

import argparse
import gc
import json
import math
import os
import shutil
import subprocess
import time
from pathlib import Path

import psutil
from phase_admission_protocol import owner_live, read, ref
from profile_large_dense_spectrum import CONFIG, completed_base

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261107/V193-large-dense-trial-v1"
ARTIFACTS = Path("/mnt/external/demosaic/quality-20261107/V193-large-dense-trial-v1")
ADMISSION = ROOT.parent / "V193-large-dense-admission-v1"
METHODS = {e: f"V193-large-dense-{e}" for e in ["raw", "EMA"]}


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def guard(plan):
    assert ref(__file__) == plan["runner"], "Use the sealed training entry"
    for binding in plan["inputs"]:
        assert ref(binding["path"]) == binding
    for path, digest in plan["frozen_files"].items():
        assert ref(path)["sha256"] == digest


def prerequisites(plan, name):
    result = read(plan["admission"]["path"])
    assert result["status"].startswith("pass-V193-frozen-baseline") and not owner_live(
        result["owner"]
    )
    assert read(plan["admission_inspection"]["path"])["status"].startswith(
        "pass-V193-readout-probe-CPU"
    )
    assert name == "wave-train"


def common_engine():
    import train_coherent_pair_evidence_engine as common

    common.ROOT, common.guard, common.prerequisites = ROOT, guard, prerequisites
    return common


def factory(config):
    from demosaic.late_dense_local_spectrum import LateDenseLocalSpectrumDetail

    return LateDenseLocalSpectrumDetail(**config)


def prepare():
    dependency = completed_base()
    comparison = read(dependency["previous_plan"]["path"])
    assert not ROOT.exists() and not ARTIFACTS.exists()
    admission = read(ADMISSION / "admission-result-v1.json")
    inspection = read(ADMISSION / "CPU-inspection-v1.json")
    assert not owner_live(admission["owner"]) and admission["status"].startswith(
        "pass-V193-frozen-baseline"
    )
    assert inspection["status"].startswith("pass-V193-readout-probe-CPU")
    assert inspection["admission"] == ref(ADMISSION / "admission-result-v1.json")
    assert shutil.disk_usage(REPO).free > (40 + 0.25) * 2**30
    assert shutil.disk_usage("/mnt/external").free > (110 + 0.70) * 2**30
    assert psutil.virtual_memory().available > 52 * 2**30
    baseline_path = ROOT.parent / "V183-coherent-pair-evidence-trial-v1/plan-v1.json"
    baseline = read(baseline_path)
    import torch
    from phase_wave_training_state import clocks, fresh_state, inherited_hash
    from profile_raw_kernel_inference import model_hash

    assert not torch.cuda.is_initialized()
    initial = torch.load(
        dependency["initializer"]["export"]["path"], map_location="cpu", weights_only=True
    )
    config = dict(CONFIG)
    module = factory(config).initialize_from_evidence(initial["state_dict"])
    optimizer, ema = fresh_state(module, lr=0.001, weight_decay=0.01)
    assert inherited_hash(module) == dependency["initializer"]["module_hash"]
    assert clocks(module, optimizer) == {"tensors": 4, "states": 0, "steps": []}
    assert len(ema) == 4 and len(module.state_dict()) == 193
    proof = {
        "inherited_tensors_exact": 189,
        "inherited_hash": inherited_hash(module),
        "full_module_hash": model_hash(module),
        "new_head_parameters": 508,
        "new_head_tensors": 4,
        "Adam": clocks(module, optimizer),
        "head_final_layer_exact_zero": bool(
            module.wave_readout.mixing.weight.count_nonzero() == 0
            and module.wave_readout.mixing.bias.count_nonzero() == 0
        ),
        "CPU_only_no_forward": True,
    }
    ROOT.mkdir()
    ARTIFACTS.mkdir()
    for name in ["checkpoints", "native"]:
        (ARTIFACTS / name).mkdir()
    work = ROOT / "work"
    for name in ["src", "scripts"]:
        shutil.copytree(
            REPO / name, work / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
        )
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
            "expected_quality_counts",
            "minimum_GiB",
        ]
    }
    plan["minimum_GiB"] = {"RAM": 32, "local": 40, "external": 110}
    plan.update(
        status="prepared-isolated-readout-training-after-native-CPU-CUDA-proofs",
        created_unix_UTC=time.time(),
        root=str(ROOT),
        work=str(work),
        artifacts=str(ARTIFACTS),
        runner=ref(work / "scripts/train_large_dense_trial.py"),
        component=type(module).__name__,
        module_config=config,
        methods=METHODS,
        initializer=dependency["initializer"],
        completed_dependency=dependency,
        CPU_initialization=proof,
        admission=ref(ADMISSION / "admission-result-v1.json"),
        admission_inspection=ref(ADMISSION / "CPU-inspection-v1.json"),
        baseline_plan=ref(baseline_path),
        baseline_scores=ref(baseline_path.parent / "scores-v1.json"),
        prior_figures=ref(Path(dependency["V191_plan"]["path"]).parent / "figures-v1.json"),
        V191_plan=dependency["V191_plan"],
        V191_scores=ref(Path(dependency["V191_plan"]["path"]).parent / "scores-v1.json"),
        support_diagnostic=dependency["support_diagnostic"],
        support_diagnostic_verification=dependency["support_diagnostic_verification"],
        V189_plan=dependency["V189_plan"],
        V189_scores=ref(Path(dependency["V189_plan"]["path"]).parent / "scores-v1.json"),
        V187_plan=comparison["V187_plan"],
        V185_plan=comparison["V185_plan"],
        V187_scores=comparison["V187_scores"],
        V185_scores=comparison["V185_scores"],
        lr=0.001,
        weight_decay=0.01,
        EMA_decay=0.999,
        head_initial_updates=0,
        inherited_network_updates=1800,
        inherited_adapter_updates=900,
        loss_source=ref(work / "scripts/coherent_pair_objective.py"),
        new_local_forecast_GiB=0.25,
        new_external_forecast_GiB=0.70,
        storage_forecast="New native RGB/wave, factored checkpoints/exports and browser captures on external SSD, forecast.70GiB above110GiB floor. Local sealed sources/receipts/figures/publication/Git forecast.25GiB above40GiB floor. Actual RAM32/local40/external110 checked before every forward; launchRAM52/CUDAquota24 unchanged. Prospective allocation only, prior plans/evidence preserved.",
        storage_forecast_receipt=ref(ROOT.parent / "V193-large-dense-storage-forecast-v1.json"),
        scope="V193 tests larger coherent support in the same completed V191 dense spectral implementation: dense129/stride64 replaces65/32, changing window, carrier grid and stride together; support33/17 and frozen matching65/32 unchanged. All103 neural source files unchanged. Same508parameters/fourheadtensors/193state/freshinitialhash/189frozenV183EMA. V192 noiseless analytical support diagnostic motivates the trial but establishes neither trained quality, calibrated confidence nor flat-sky safety. Fresh V183EMA, never a V191/V187 trained head or admission probe. Same1000cachedrows/900updates/3600images/100ADCskips/nine losses/masks/domainweights/LR.001/schedule/clip1/headAdamEMA0; true row8 restoration to9 andfivefactoredcheckpoints. Primary same-state V191, retaining preferred V187 and V189 negative control and all earlier useful methods. Both822case endpoints, independent complete audits,60nativefigures/12triplets/480browser crops before quality claim. Protected3879/3880 andcab3842/3835/JPEGs/siblingsheldout; references qualitative notGT. No originals/dataz/new source/noise/RAWdecode/parent-DINOinference. New allocations local.25GiB and external.70GiB above40/110GiB floors; existing evidence preserved.",
    )
    plan["inputs"] = (
        [
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
                "baseline_plan",
                "baseline_scores",
                "prior_figures",
                "V185_plan",
                "V185_scores",
                "V187_plan",
                "V187_scores",
                "V189_plan",
                "V189_scores",
                "V191_plan",
                "V191_scores",
                "support_diagnostic",
                "support_diagnostic_verification",
                "storage_forecast_receipt",
            ]
        ]
        + [
            dependency["publication"],
            dependency["verification"],
            dependency["previous_publication"],
            dependency["previous_verification"],
            dependency["native_geometry"],
            dependency["native_geometry_verification"],
            dependency["initializer"]["export"],
        ]
        + plan["metrics_sources"]
    )
    plan["frozen_files"] = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    save(ROOT / "plan-v1.json", plan)
    print("Prepared900headupdates/508parameters/frozenV183EMA/all9losses;noCUDA/forward")


def train():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    common = common_engine()
    owner = common.own()
    common.require_worker_launch(plan, "wave-train", owner)
    (ROOT / "wave-train.claim").open("x").close()
    import numpy as np
    import torch
    from coherent_pair_objective import objective
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
    counts = dict.fromkeys(["wrapper", "frozen", "network", "sampler", "projection"], 0)
    initial = torch.load(
        plan["initializer"]["export"]["path"], map_location="cpu", weights_only=True
    )
    module = common.instrument(
        factory(plan["module_config"]).initialize_from_evidence(initial["state_dict"]).cuda(),
        counts,
    ).train()
    del initial
    optimizer, ema = fresh_state(module, lr=plan["lr"], weight_decay=plan["weight_decay"])
    inherited = plan["initializer"]["module_hash"]
    assert inherited_hash(module) == inherited
    cpu_rng, cuda_rng = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
    rows = read(plan["cache"]["path"])["batches"]
    units = read(plan["pair_units"]["path"])["rows"]
    updates = skipped = images = 0
    trace = []
    checkpoints = []
    restoration = None
    maxima = {n: 0.0 for n in readout_parameters(module)}
    with (ROOT / "wave-train-trace-v1.jsonl").open("x") as journal:
        for step, item in enumerate(rows, 1):
            common.resources(plan, "wave-train", owner)
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
                    "wave-train",
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
                path = ARTIFACTS / "checkpoints" / f"wave-step{step:04d}.pt"
                payload = {
                    "models": module.state_dict(),
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
                    save(ROOT / "wave-restoration-v1.json", restoration)
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
    guard(plan)
    save(
        ROOT / "wave-train-result-v1.json",
        {
            "status": "completed-isolated-readout-one-pass-frozen-V183-EMA",
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
        "wave-train",
        {
            "status": "completed-training",
            "owner": owner,
            "step": 1000,
            "updates": 900,
            "counts": counts,
        },
    )


def launch():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    prerequisites(plan, "wave-train")
    assert (
        not (ROOT / "wave-train-launch-v1.json").exists()
        and not (ROOT / "wave-train.claim").exists()
    )
    assert psutil.virtual_memory().available > plan["launch_RAM_GiB"] * 2**30
    env = dict(
        os.environ,
        PYTHONPATH=f"{plan['work']}/src:{plan['work']}/scripts",
        CUDA_VISIBLE_DEVICES="0",
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="2",
        MKL_NUM_THREADS="1",
        CUBLAS_WORKSPACE_CONFIG=":4096:8",
    )
    with (ROOT / "wave-train-v1.log").open("xb") as log:
        child = subprocess.Popen(
            [str(REPO / ".venv/bin/python"), plan["runner"]["path"], "train"],
            cwd=REPO,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
    save(ROOT / "wave-train-launch-v1.json", {"owner": owner, "plan": ref(ROOT / "plan-v1.json")})
    print(json.dumps(owner))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "launch", "train"])
    args = parser.parse_args()
    if args.phase != "train":
        {"prepare": prepare, "launch": launch}[args.phase]()
    else:
        try:
            train()
        except BaseException as exc:
            save(ROOT / "wave-train-failure-v1.json", {"error": repr(exc), "time_UTC": time.time()})
            raise
