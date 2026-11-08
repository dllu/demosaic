"""V198: color-grounded wave engineering, actual anchor parity and restored GPU probes."""

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

ROOT = REPO / ".cache/quality-20261108/V198-cfa-innovation-admission-v1"
MODES = ("CFA",)


def factory(plan, mode="CFA"):
    from demosaic.late_cfa_innovation_wave import LateCFAInnovationWaveDetail

    if mode != "CFA":
        raise ValueError("Expected the CFA-grounded prototype")
    return LateCFAInnovationWaveDetail(lower=1 / 64, **plan["anchor"]["module_config"])


def prepare():
    assert not ROOT.exists()
    previous_path = REPO / ".cache/quality-20261108/V197-innovation-wave-admission-v1/plan-v1.json"
    previous = read(previous_path)
    final_path = REPO / "docs/results/v197-innovation-wave-final-v1.json"
    proof_path = REPO / "docs/results/v197-innovation-wave-publication-verification-v1.json"
    proof = read(proof_path)
    assert proof["status"].startswith("pass-") and proof["publication"] == ref(final_path)
    closure = read(REPO / "docs/results/v197-completed-execution-v1.json")
    neural = closure["all104_neural_hashes_unchanged"]
    assert len(neural) == 104
    for name, digest in neural.items():
        assert ref(REPO / "src/demosaic" / name)["sha256"] == digest
    tests = REPO / ".cache/v198-cfa-innovation-CPU-tests-v1.log"
    assert "23 passed" in tests.read_text()
    training = read(REPO / ".cache/quality-20261108/V197-innovation-wave-trial-v1/plan-v1.json")
    building = next(
        c
        for c in read(training["design"]["path"])["observations"]
        if c["id"] == "main-building-detail"
    )
    cases = [
        *previous["cases"],
        {
            "id": building["id"],
            "arrays": building["arrays"],
            "parent": building["parent"],
            "domain": "protected-real",
            "training_step": None,
            "noisy": True,
        },
    ]
    ROOT.mkdir()
    (ROOT / "artifacts").mkdir()
    work, sources = freeze(
        ROOT, ["admit_cfa_innovation_wave.py", "inspect_cfa_innovation_admission.py"]
    )
    plan = {
        "status": "prepared-CFA-grounded-head-engineering-only-no-quality",
        "created_unix_UTC": time.time(),
        "root": str(ROOT),
        "work": str(work),
        "runner": ref(work / "scripts/admit_cfa_innovation_wave.py"),
        "inspector": ref(work / "scripts/inspect_cfa_innovation_admission.py"),
        "anchor": previous["anchor"],
        "modes": list(MODES),
        "lower_native_frequency": 1 / 64,
        "cases": cases,
        "sampling_library": previous["sampling_library"],
        "pair_units": previous["pair_units"],
        "domain_weights": previous["domain_weights"],
        "lr": 0.001,
        "weight_decay": 0.01,
        "CUDA_quota_GiB": 24,
        "minimum_GiB": {"local": 40, "RAM": 32},
        "launch_RAM_GiB": 52,
        "gradient_tolerance": {"rtol": 5e-5, "atol": 2e-9},
        "readout_tolerance": {"rtol": 1e-5, "atol": 3e-9},
        "map_tolerance": {"rtol": 2e-5, "atol": 2e-6},
        "physical_wave_tolerance": {"rtol": 2e-5, "atol": 3e-9},
        "local_forecast_GiB": 0.08,
        "external_new_bytes": 0,
        "CPU_tests": ref(tests),
        "neural104": neural,
        "new_source": ref(REPO / "src/demosaic/late_cfa_innovation_wave.py"),
        "prior_publication": ref(final_path),
        "prior_verification": ref(proof_path),
        "scope": "Engineering-only V198 CFA-grounded prototype above all193 frozen trainedV195WholeEMA tensors. Four new tensors/451parameters,197fullstate;freshAdamEMA0. Same input-only innovation eightbins1/64..1/3,large65/small33/17 contexts. Largewave Gram solves local affine+detrended realcos/sin coefficients at actualfour CFAphases;R/B synthesis uses own measurements,G averages its two phases. Same old18 green contexts plus6 R/B nominalpower/cross coordinates feed24->16->3 realtanhgates bounded[-1,1],zero output initially;explicit native phase transport and sum acrossbins,no output-sigma multiplication. Numerical rank1e-10*boxarea is not a confidence gate. Other phases can condition gates but cannot supply R/B synthesis waves. Correlatedinnovation andnominalRAWvariance are not calibration;leakage/noisy falsepatterns stillpossible. Eightactualanchorparities,seven independentCPU/GPU feature/head checks,two training-only mesh/mixedupdates with actualrow1 strictmodelAdamEMACPU/CUDARNG restorebefore row2. No improved-quality claim;probes never futureinitializers. Sky,cab,building parity-only,never gradients;bothstandingGFX scenes/JPEGs/siblings heldout. No newsource/noisedraws,parentDINOinference,RAWdecode,original/datazaccess;104previousneuralfilesunchanged. Additional channels,LSunits,realbounded gates and summedmodes change together;futureanchor/V197 comparison tests combinedarchitecture,not color-grounding-alone causality. Forecast.08GiB local,40GiBreserve,zeroexternalwrites.",
    }
    plan["inputs"] = [
        ref(previous_path),
        ref(final_path),
        ref(proof_path),
        ref(tests),
        previous["anchor"]["export"],
        previous["sampling_library"],
        previous["pair_units"],
    ]
    for case in cases:
        plan["inputs"] += [case["arrays"], case["parent"]]
    plan["frozen_files"] = sources
    resources(plan)
    save(ROOT / "plan-v1.json", plan)
    print("Prepared8anchorparities/7CPU-GPU-feature-headchecks/2restoredtraining-onlyupdates")


def probe():
    plan = read(ROOT / "plan-v1.json")
    guard(plan, __file__)
    owner = require_launch(ROOT, "probe")
    (ROOT / "probe.claim").open("x").close()
    try:
        import numpy as np
        import torch
        from cfa_innovation_state import (
            anchor_hash,
            clocks,
            fresh,
            pack,
            parameters,
            restore,
            update_ema,
        )
        from directional_pair_objective import objective
        from profile_raw_kernel_inference import model_hash
        from train_coherent_pair_evidence_engine import instrument

        from demosaic.late_cfa_innovation_wave import cfa_innovation_wave_maps
        from demosaic.late_pooled_phase_wave import LatePooledPhaseWaveDetail
        from demosaic.late_spatial_context_wave import fixed_bin_support_context
        from demosaic.prediction_archive import fingerprint

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
                        cpu_field = aux["measurement_field"].cpu()
                        cpu_noise, cpu_colors = batch["variance"].cpu(), batch["colors"].cpu()
                        bins = aux["wave_selection"]["bin_yx"].cpu()
                        valid = aux["wave_selection"]["valid"].cpu()
                        large, measured, geometry = cfa_innovation_wave_maps(
                            cpu_field,
                            cpu_noise,
                            cpu_colors,
                            bins,
                            valid,
                            window=model.evidence_window,
                            stride=model.evidence_stride,
                        )
                        small, _ = fixed_bin_support_context(
                            cpu_field,
                            cpu_noise,
                            cpu_colors,
                            bins,
                            valid,
                            windows=model.support_windows,
                            stride=model.support_stride,
                        )
                        contextual = torch.cat((large[:, :, :6], small, large[:, :, 6:]), 2)
                        torch.testing.assert_close(
                            contextual, aux["cfa_context"].cpu(), **plan["map_tolerance"]
                        )
                        torch.testing.assert_close(
                            measured, aux["cfa_waves"].cpu(), **plan["physical_wave_tolerance"]
                        )
                        assert torch.equal(
                            geometry["wave_gram_rank"], aux["cfa_evidence"]["wave_gram_rank"].cpu()
                        )
                        record.update(
                            independently_checked_context_values=contextual.numel(),
                            independently_checked_physical_wave_values=measured.numel(),
                            CPU_GPU_context_maximum_difference=float(
                                abs(contextual - aux["cfa_context"].cpu()).max()
                            ),
                            CPU_GPU_physical_wave_maximum_difference=float(
                                abs(measured - aux["cfa_waves"].cpu()).max()
                            ),
                            physical_wave_values=fingerprint(measured.numpy()),
                            physical_wave_RMS_DN16=float(measured.double().square().mean().sqrt())
                            * 65535,
                            numerical_rank_counts={
                                str(rank): int((geometry["wave_gram_rank"] == rank).sum())
                                for rank in [0, 1, 2]
                            },
                        )
                        del (
                            cpu_field,
                            cpu_noise,
                            cpu_colors,
                            large,
                            measured,
                            small,
                            contextual,
                            geometry,
                        )
                        head = copy.deepcopy(model.cfa_readout).cpu()
                        head.gates.weight.fill_(0.01)
                        head.gates.bias.fill_(0.1)
                        cpu = head(
                            aux["cfa_context"].cpu(),
                            aux["cfa_waves"].cpu(),
                            aux["wave_selection"]["bin_yx"].cpu(),
                        )
                        gpu = (
                            copy.deepcopy(head)
                            .cuda()(
                                aux["cfa_context"],
                                aux["cfa_waves"],
                                aux["wave_selection"]["bin_yx"],
                            )
                            .cpu()
                        )
                        torch.testing.assert_close(gpu, cpu, **plan["readout_tolerance"])
                        record["nonzero_CPU_GPU_head_maximum_difference"] = float(
                            abs(gpu - cpu).max()
                        )
                        del head, cpu, gpu
                    else:
                        assert aux["wave_selection"] is aux["cfa_context"] is None
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
                head = copy.deepcopy(model.cfa_readout).cpu()
                cpu_wave = head(
                    aux["cfa_context"].cpu(),
                    aux["cfa_waves"].cpu(),
                    aux["wave_selection"]["bin_yx"].cpu(),
                )
                cpu_gradients = torch.autograd.grad(
                    (cpu_wave * upstream).sum(), tuple(head.parameters())
                )
                loss.backward()
                differences, nonzero = [], {}
                for (name, p), expected in zip(
                    model.cfa_readout.named_parameters(), cpu_gradients, strict=True
                ):
                    assert p.grad is not None and torch.isfinite(p.grad).all()
                    torch.testing.assert_close(p.grad.cpu(), expected, **plan["gradient_tolerance"])
                    differences.append(float(abs(p.grad.cpu() - expected).max()))
                    nonzero[name] = int(p.grad.count_nonzero())
                assert any(nonzero.values())
                assert all(
                    p.grad is None
                    for n, p in model.named_parameters()
                    if not n.startswith("cfa_readout.")
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
        assert len(initial_hashes) == 1
        assert counts == {
            "wrapper": 18,
            "frozen": 18,
            "network": 16,
            "sampler": 80,
            "projection": 16,
        }, counts
        guard(plan, __file__)
        save(
            ROOT / "admission-result-v1.json",
            {
                "status": "pass-V198-CFA-eight-anchor-parities-seven-CPU-GPU-maps-heads-two-restored-updates",
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
        print("PASS8parities/7CPU-GPUmaps-heads/2updates/1restoration", flush=True)
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
