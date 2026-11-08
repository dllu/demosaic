"""V197: two fresh measurement heads, real anchor parity and restored GPU probes."""

import argparse
import copy
import gc
import time

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
    runtime,
    save,
)

ROOT = REPO / ".cache/quality-20261108/V197-innovation-wave-admission-v1"
MODES = ("RAW", "innovation")


def factory(plan, mode):
    from demosaic.late_innovation_wave import LateInnovationWaveDetail

    return LateInnovationWaveDetail(
        measurement=mode, lower=1 / 64, **plan["anchor"]["module_config"]
    )


def prepare():
    assert not ROOT.exists()
    previous = read(
        REPO / ".cache/quality-20261108/V195-directional-response-admission-v1/plan-v1.json"
    )
    gallery = REPO / "docs/images/v195-directional-response-v1/manifest-v1.json"
    anchor = read(gallery)["method_checkpoints"]["V195-whole-response-EMA"]
    diagnostic = REPO / ".cache/quality-20261108/V196-innovation-selection-v1/audit-v1.json"
    assert read(diagnostic)["status"] == "pass144selectors72fullQRscoremaps16nativegeometryrows"
    tests = REPO / ".cache/v197-innovation-wave-CPU-tests-v1.log"
    assert "25 passed" in tests.read_text()
    ROOT.mkdir()
    (ROOT / "artifacts").mkdir()
    work, sources = freeze(ROOT, ["admit_innovation_wave.py", "inspect_innovation_admission.py"])
    plan = {
        "status": "prepared-two-fresh-heads-above-frozen-V195-WholeEMA-no-quality",
        "created_unix_UTC": time.time(),
        "root": str(ROOT),
        "work": str(work),
        "runner": ref(work / "scripts/admit_innovation_wave.py"),
        "inspector": ref(work / "scripts/inspect_innovation_admission.py"),
        "anchor": anchor,
        "modes": list(MODES),
        "lower_native_frequency": 1 / 64,
        "cases": previous["cases"],
        "sampling_library": previous["sampling_library"],
        "pair_units": previous["pair_units"],
        "domain_weights": previous["domain_weights"],
        "lr": 0.001,
        "weight_decay": 0.01,
        "CUDA_quota_GiB": 24,
        "minimum_GiB": {"local": 40, "RAM": 32},
        "launch_RAM_GiB": 52,
        "gradient_tolerance": {"rtol": 5e-5, "atol": 2e-5},
        "readout_tolerance": {"rtol": 1e-5, "atol": 3e-6},
        "local_forecast_GiB": 0.06,
        "external_new_bytes": 0,
        "CPU_tests": ref(tests),
        "diagnostic": ref(diagnostic),
        "new_source": ref(REPO / "src/demosaic/late_innovation_wave.py"),
        "neural103": read(REPO / "docs/results/v195-completed-execution-v1.json")[
            "previous103_neural_hashes_unchanged"
        ],
        "scope": "Two matched new508parameter heads above all193 frozen V195WholeEMA tensors,197 fullstate tensors. RAW vs RAW-minus-sampled-anchor changes global selection AND localwave/support measurements together; both use1/64..1/3 band,eight bins,65/33/17 contexts andsameMLP. Both initial new heads outputzero,strict trainedanchor preserved;freshAdamEMA0. Seven cachedcontexts compare eachmode toseparatelyloaded anchor,12nonzeroCPU/GPU readouts,two modes xmesh/mixed training-onlyupdates withrealrow1 modelAdamEMACPU/CUDARNG restorebefore row2. Existingnine terms+wholeaddition retained(.50totalcoherentweight);new probesnevertraininginitializers. Targets onlyafterforward;protected sky/cab parity-only,no gradients. RAWvariance remainsnominalunits forcorrelatedinnovation,notcalibration. Noquality/improvementclaims,newnoise/source,parentDINOinference,RAWdecode,original/datazaccess. Old103neuralfilesunchanged;onlynew104tharchitecturefile. Localbudget.06GiB,reserve40GiB;zeroexternalwrites.",
    }
    plan["inputs"] = [
        ref(gallery),
        ref(diagnostic),
        ref(tests),
        anchor["export"],
        previous["sampling_library"],
        previous["pair_units"],
    ]
    for case in plan["cases"]:
        plan["inputs"] += [case["arrays"], case["parent"]]
    for name, digest in plan["neural103"].items():
        assert ref(REPO / "src/demosaic" / name)["sha256"] == digest
    plan["frozen_files"] = sources
    resources(plan)
    save(ROOT / "plan-v1.json", plan)
    print("Prepared14initialparities/12nonzeroheadparities/4restoredtraining-onlyupdates")


def probe():
    plan = read(ROOT / "plan-v1.json")
    guard(plan, __file__)
    owner = require_launch(ROOT, "probe")
    (ROOT / "probe.claim").open("x").close()
    try:
        import numpy as np
        import torch
        from directional_pair_objective import objective
        from innovation_wave_state import (
            anchor_hash,
            clocks,
            fresh,
            pack,
            parameters,
            restore,
            update_ema,
        )
        from profile_raw_kernel_inference import model_hash
        from train_coherent_pair_evidence_engine import instrument

        from demosaic.late_pooled_phase_wave import LatePooledPhaseWaveDetail

        runtime(plan)
        donor = torch.load(plan["anchor"]["export"]["path"], map_location="cpu", weights_only=True)
        counts = dict.fromkeys(["wrapper", "frozen", "network", "sampler", "projection"], 0)

        def new(mode):
            m = factory(plan, mode).initialize_anchor(donor["state_dict"])
            assert anchor_hash(m) == plan["anchor"]["module_hash"]
            return instrument(m.cuda(), counts).train()

        baseline = LatePooledPhaseWaveDetail(**plan["anchor"]["module_config"])
        baseline.load_state_dict(donor["state_dict"], strict=True)
        baseline = instrument(baseline.cuda(), counts).eval().requires_grad_(False)
        models = {mode: new(mode) for mode in MODES}
        parities = []
        for case in plan["cases"]:
            resources(plan)
            with np.load(case["arrays"]["path"], allow_pickle=False) as archive:
                batch = {
                    k: torch.from_numpy(archive[k]).cuda()
                    for k in ["packed", "variance", "colors", "wb"]
                }
            base = torch.from_numpy(np.load(case["parent"]["path"], allow_pickle=False)).cuda()
            args = [batch[k] for k in ["packed", "variance", "colors", "wb"]]
            with torch.no_grad():
                expected = baseline(base, *args)
                for mode, model in models.items():
                    actual, aux = model(base, *args, return_aux=True)
                    assert torch.equal(actual.view(torch.int32), expected.view(torch.int32))
                    record = {
                        "case": case["id"],
                        "mode": mode,
                        "native_values": actual.numel(),
                        "anchor_initial_bit_exact": True,
                        "ADC_only": not case["noisy"],
                    }
                    if case["noisy"]:
                        head = copy.deepcopy(model.innovation_readout).cpu()
                        head.mixing.weight.fill_(0.01)
                        head.mixing.bias.fill_(0.1)
                        cpu = head(
                            aux["wave_evidence_features"].cpu(),
                            aux["wave_selection"]["bin_yx"].cpu(),
                            aux["wave_support_context"].cpu(),
                        )
                        gpu = (
                            copy.deepcopy(head)
                            .cuda()(
                                aux["wave_evidence_features"],
                                aux["wave_selection"]["bin_yx"],
                                aux["wave_support_context"],
                            )
                            .cpu()
                        )
                        torch.testing.assert_close(gpu, cpu, **plan["readout_tolerance"])
                        record["nonzero_CPU_GPU_head_maximum_difference"] = float(
                            abs(gpu - cpu).max()
                        )
                        del head, cpu, gpu
                    else:
                        assert aux["wave_selection"] is aux["wave_evidence_features"] is None
                    parities.append(record)
                    del actual, aux
            print("parity", case["id"], flush=True)
            del batch, base, args, expected
        del baseline, models
        gc.collect()
        units = read(plan["pair_units"]["path"])["rows"]
        records, checkpoints, restorations = [], [], []
        initial_hashes = []
        for mode in MODES:
            model = new(mode)
            initial_hashes.append(model_hash(model))
            optimizer, ema = fresh(model)
            assert clocks(model, optimizer) == {"tensors": 4, "states": 0, "steps": []}
            for update, domain in enumerate(["mesh", "mixed"], 1):
                resources(plan)
                case = next(c for c in plan["cases"] if c["domain"] == domain)
                with np.load(case["arrays"]["path"], allow_pickle=False) as archive:
                    batch = {k: torch.from_numpy(archive[k]).cuda() for k in archive.files}
                base = torch.from_numpy(np.load(case["parent"]["path"], allow_pickle=False)).cuda()
                pair_units = torch.tensor(
                    units[case["training_step"] - 1]["candidate_units_FP32"],
                    device="cuda",
                    dtype=torch.float32,
                ).reshape(-1, 1, 1, 1)
                optimizer.zero_grad(set_to_none=True)
                output, aux = model(
                    base,
                    *(batch[k] for k in ["packed", "variance", "colors", "wb"]),
                    return_aux=True,
                )
                loss, terms, mask = objective(
                    output,
                    aux["anchor_aux"]["frozen_output"],
                    batch,
                    pair_units,
                    plan["domain_weights"][domain],
                    mode="whole",
                )
                scalars = {k: float(v.detach()) for k, v in terms.items()}
                assert float(loss.detach()) == objective_total(
                    scalars, plan["domain_weights"][domain]
                )
                upstream = torch.autograd.grad(loss, output, retain_graph=True)[0].detach().cpu()
                head = copy.deepcopy(model.innovation_readout).cpu()
                cpu_wave = (
                    head(
                        aux["wave_evidence_features"].cpu(),
                        aux["wave_selection"]["bin_yx"].cpu(),
                        aux["wave_support_context"].cpu(),
                    )
                    * aux["sigma"].cpu()
                )
                cpu_gradients = torch.autograd.grad(
                    (cpu_wave * upstream).sum(), tuple(head.parameters())
                )
                loss.backward()
                differences, nonzero = [], {}
                for (name, p), expected in zip(
                    model.innovation_readout.named_parameters(), cpu_gradients, strict=True
                ):
                    assert p.grad is not None and torch.isfinite(p.grad).all()
                    torch.testing.assert_close(p.grad.cpu(), expected, **plan["gradient_tolerance"])
                    differences.append(float(abs(p.grad.cpu() - expected).max()))
                    nonzero[name] = int(p.grad.count_nonzero())
                assert any(nonzero.values())
                assert all(
                    p.grad is None
                    for n, p in model.named_parameters()
                    if not n.startswith("innovation_readout.")
                )
                norm = torch.nn.utils.clip_grad_norm_(
                    parameters(model).values(), 1, error_if_nonfinite=True
                )
                optimizer.step()
                decay = update_ema(model, ema, update)
                assert anchor_hash(model) == plan["anchor"]["module_hash"]
                record = {
                    "mode": mode,
                    "update": update,
                    "domain": domain,
                    "loss": float(loss.detach()),
                    "terms": scalars,
                    "mask_pixels": int(mask.sum()),
                    "gradient_norm": float(norm),
                    "nonzero_gradient_coordinates": nonzero,
                    "CPU_GPU_head_gradient_maximum_difference": max(differences),
                    "EMA_decay": decay,
                    "Adam": clocks(model, optimizer),
                    "module_hash": model_hash(model),
                    "anchor193_unchanged": True,
                }
                path = ROOT / "artifacts" / f"{mode}-probe-step{update}.pt"
                payload = {
                    "models": model.state_dict(),
                    "optimizer": optimizer.state_dict(),
                    "ema": ema,
                    "updates": update,
                    "measurement": mode,
                    "anchor_hash": anchor_hash(model),
                    "CPU_RNG": torch.get_rng_state(),
                    "CUDA_RNG": torch.cuda.get_rng_state(),
                    "component": type(model).__name__,
                    "plan": ref(ROOT / "plan-v1.json"),
                    "scope": "Engineering probe only;nevertraininginitializer",
                }
                with path.open("xb") as stream:
                    torch.save(pack(payload, plan["anchor"]["export"]), stream)
                checkpoints.append(ref(path))
                records.append(record)
                save(ROOT / f"{mode}-update{update}-v1.json", record)
                del (
                    output,
                    aux,
                    loss,
                    terms,
                    mask,
                    batch,
                    base,
                    pair_units,
                    upstream,
                    head,
                    cpu_wave,
                    cpu_gradients,
                    payload,
                )
                if update == 1:
                    saved = torch.load(path, map_location="cpu", weights_only=True)
                    del model, optimizer
                    gc.collect()
                    model = instrument(factory(plan, mode).cuda(), counts).train()
                    optimizer, ema = restore(model, saved)
                    assert model_hash(model) == record["module_hash"]
                    restorations.append(
                        {
                            "mode": mode,
                            "checkpoint": ref(path),
                            "strict_model_Adam_EMA_CPU_CUDA_RNG_exact": True,
                            "repeated_forwards": 0,
                        }
                    )
                    del saved
                print("probe", mode, update, record["loss"], flush=True)
            del model, optimizer, ema
            gc.collect()
        assert initial_hashes[0] == initial_hashes[1]
        assert counts == {
            "wrapper": 25,
            "frozen": 25,
            "network": 22,
            "sampler": 110,
            "projection": 22,
        }, counts
        guard(plan, __file__)
        save(
            ROOT / "admission-result-v1.json",
            {
                "status": "pass-V197-two-fresh-heads-14anchor-parities-12nonzero-head-checks-4restoredupdates",
                "created_unix_UTC": time.time(),
                "owner": owner,
                "plan": ref(ROOT / "plan-v1.json"),
                "parities": parities,
                "records": records,
                "checkpoints": checkpoints,
                "restorations": restorations,
                "identical_initial_full_hash": initial_hashes[0],
                "counts": counts,
                "peak_CUDA_allocated_bytes": torch.cuda.max_memory_allocated(),
                "new_source_noise_draws": 0,
                "protected_optimizer_inputs": 0,
                "scope": plan["scope"],
            },
        )
        print("PASS14parities/12nonzeroheadchecks/4updates/2restorations", flush=True)
    except BaseException as exc:
        save(
            ROOT / "admission-failure-v1.json",
            {"owner": owner, "error": repr(exc), "time_UTC": time.time()},
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "launch", "probe"])
    phase = parser.parse_args().phase
    if phase == "prepare":
        prepare()
    elif phase == "launch":
        print(launch(ROOT, "probe"))
    else:
        probe()
