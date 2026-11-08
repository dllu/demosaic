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
from profile_spatial_context_wave import completed_base

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261107/V185-spatial-context-trial-v1"
EXTERNAL = Path("/mnt/external/demosaic/quality-20261107/V185-spatial-context-trial-v1")
ADMISSION = ROOT.parent / "V185-spatial-context-admission-v1"
METHODS = {e: f"V185-spatial-context-{e}" for e in ["raw", "EMA"]}


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
    assert result["status"].startswith("pass-V185-frozen-baseline") and not owner_live(
        result["owner"]
    )
    assert read(plan["admission_inspection"]["path"])["status"].startswith(
        "pass-V185-readout-probe-CPU"
    )
    assert name == "wave-train"


def common_engine():
    import train_coherent_pair_evidence_engine as common

    common.ROOT, common.guard, common.prerequisites = ROOT, guard, prerequisites
    return common


def factory(config):
    from demosaic.late_spatial_context_wave import LateSpatialContextWaveDetail

    return LateSpatialContextWaveDetail(**config)


def prepare():
    dependency = completed_base()
    assert not ROOT.exists() and not EXTERNAL.exists()
    admission = read(ADMISSION / "admission-result-v1.json")
    inspection = read(ADMISSION / "CPU-inspection-v1.json")
    assert not owner_live(admission["owner"]) and admission["status"].startswith(
        "pass-V185-frozen-baseline"
    )
    assert inspection["status"].startswith("pass-V185-readout-probe-CPU")
    assert inspection["admission"] == ref(ADMISSION / "admission-result-v1.json")
    assert shutil.disk_usage(REPO).free > (48.5 + 0.075) * 2**30
    assert shutil.disk_usage("/mnt/external").free > (111.5 + 0.20) * 2**30
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
    config = dict(baseline["module_config"], support_windows=[33, 17], support_stride=8)
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
    EXTERNAL.mkdir()
    for name in ["checkpoints", "native"]:
        (EXTERNAL / name).mkdir()
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
    plan.update(
        status="prepared-isolated-readout-training-after-native-CPU-CUDA-proofs",
        created_unix_UTC=time.time(),
        root=str(ROOT),
        work=str(work),
        artifacts=str(EXTERNAL),
        runner=ref(work / "scripts/train_spatial_context_trial.py"),
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
        prior_figures=ref(baseline_path.parent / "figures-v1.json"),
        lr=0.001,
        weight_decay=0.01,
        EMA_decay=0.999,
        head_initial_updates=0,
        inherited_network_updates=1800,
        inherited_adapter_updates=900,
        loss_source=ref(work / "scripts/coherent_pair_objective.py"),
        new_local_forecast_GiB=0.075,
        new_external_forecast_GiB=0.20,
        storage_forecast="Read-only V184 forecast:72wave byteplanes-zlib135859290bytes;72RGBexactFP32addrecipes,all53772288bitschecked. Native35percentmargin+manifests183704953bytes. Fivefactoredheadcheckpoints<1MiB,twofullstrictCPUexports~18MiB;externalforecast.20GiB. FutureRGB fallsbacktoXORifadditionbitdigestdiffers; actualfreecheckedperrow. Newqualityjournal andpairedtable use losslessgzip; no oldreceiptmodified. Localforecast.075GiB includesfrozenwork andcompressedreceipts/nativePNGs.",
        storage_forecast_receipt=ref(
            ROOT.parent / "V185-addition-storage-forecast-v1/result-v1.json"
        ),
        scope="V185 tests smallerRAWsupport for V184wavegate: same large65packedwavebasis and fixedbins, two additional33/17packedwindows atstride8 provide12contextinputs. Head18to16to12has508params(vs316),old6hiddenweights/biascopiedexact,new12inputweightszero,finalmixingzero. All189V183EMA inherited tensors exact/eval. Freshhead900updates/3600images/1000oldcachedrows/100ADCskips,all9losses/mask/data/domains/LR.001/schedule/clip1/EMAclock0 matchV184. PrimaryrawvsV184raw,EMAvsV184EMA; extra192paramsandmultiscalefinercontextchange together. Contexts reusecorrelatednoise,notcalibratedSNR orindependentconfidence. Genuine row8restore resumes9,zero prefixreplay;5factoredcheckpoints/headAdam900/inheritednetwork1800adapter900. InitializercompletedV183EMA,neverV184head/probes. Both endpoints/all822fixedcases,allretainedstrongmethods;include protectedmain3879/3880sky/building/foliage/coarsefence andfinecab3842/3835JPEGs. These/siblingsheldout andindependentrefsnotexactGT. Allquality/nativeviewing stillrequired; noimprovementclaimed. Originals/datazunused.",
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
                "storage_forecast_receipt",
            ]
        ]
        + [
            dependency["publication"],
            dependency["verification"],
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
                path = EXTERNAL / "checkpoints" / f"wave-step{step:04d}.pt"
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
