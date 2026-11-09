"""V200: physical multiscale support engineering, actual anchor parity and restored GPU probes."""

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

ROOT = REPO / ".cache/quality-20261108/V200-scale-supported-CFA-admission-v1"
MODES = ("scale",)


def factory(plan, mode="scale"):
    from demosaic.late_scale_supported_cfa_wave import LateScaleSupportedCFAWaveDetail

    if mode != "scale":
        raise ValueError("Expected the scale-supported CFA prototype")
    return LateScaleSupportedCFAWaveDetail(lower=1 / 64, **plan["anchor"]["module_config"])


def prepare():
    from phase_admission_protocol import owner_live

    assert not ROOT.exists()
    previous_path = REPO / ".cache/quality-20261108/V198-cfa-innovation-admission-v1/plan-v1.json"
    previous = read(previous_path)
    final_path = REPO / "docs/results/v199-cfa-gate-diagnostic-completed-v1.json"
    proof_path = REPO / "docs/results/v199-cfa-gate-diagnostic-publication-verification-v1.json"
    proof = read(proof_path)
    assert proof["status"].startswith("pass-") and proof["publication"] == ref(final_path)
    completed = read(final_path)
    assert not owner_live(completed["owner_terminal"]["owner"])
    neural = completed["all105_neural_hashes_unchanged"]
    assert len(neural) == 105
    for name, digest in neural.items():
        assert ref(REPO / "src/demosaic" / name)["sha256"] == digest
    tests = REPO / ".cache/v200-scale-supported-CFA-CPU-tests-v2.log"
    assert "34 passed" in tests.read_text()
    cases = previous["cases"]
    assert len(cases) == 8
    ROOT.mkdir()
    (ROOT / "artifacts").mkdir()
    work, sources = freeze(
        ROOT, ["admit_scale_supported_cfa_wave.py", "inspect_scale_supported_cfa_admission.py"]
    )
    plan = {
        "status": "prepared-physical-cross-scale-CFA-support-engineering-not-quality",
        "created_unix_UTC": time.time(),
        "root": str(ROOT),
        "work": str(work),
        "runner": ref(work / "scripts/admit_scale_supported_cfa_wave.py"),
        "inspector": ref(work / "scripts/inspect_scale_supported_cfa_admission.py"),
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
        "covariance_tolerance": {"rtol": 5e-5, "atol": 2e-14},
        "local_forecast_GiB": 0.08,
        "external_new_bytes": 0,
        "CPU_tests": ref(tests),
        "neural105": neural,
        "new_sources": [
            ref(REPO / "src/demosaic" / name)
            for name in ["cfa_scale_support.py", "late_scale_supported_cfa_wave.py"]
        ],
        "prior_publication": ref(final_path),
        "prior_verification": ref(proof_path),
        "scope": "Engineering-only V200 physical cross-scale support above all193 frozen trainedV195WholeEMA tensors. Four fresh tensors/643parameters,197fullstate;freshAdamEMA0. V198 input-only innovation eightbins1/64..1/3,old24contexts and measured65RGBwavebasis remain. Twelve new coordinates describe physical complex amplitude agreement of65with33and17 forRGB. Per-CFA LS nominal covariance is Gdagger H Gdagger,including offdiagonal projected noise;green center trace averages independent nominal RAW phases with factor1/4. Interpolated squared mean sqrt-trace is a conservative nominal bound for overlapping fits,not exact interpolation variance or innovation confidence. Bothscales reuse noise;no independent holdout. Existing24 head columns retain initialweights,new12columns zero,finalgates zero;36->16->3 realtanh gains with explicit unchanged nativecolor synthesis. Numerical Gram rank cutoff1e-10*area is not confidence. Addedfeatures and192parameters change together;futurequality is combinedarchitecture,not isolatedcovariance causality. Eightactualanchorparities,sevenCPU/GPU context+physicalwave+allthreecovariance checks,seven nonzero heads with active extra columns,two training-only mesh/mixedupdates with strictmodelAdamEMACPU/CUDARNG restore afterrow1before2. Protectedsky/cab/building parity-only,nevergradients;bothGFXfamilies/JPEGs/siblings heldout. No newsource/noisedraws,parentDINOinference,RAWdecode,original/datazaccess,externalwrites or improvedqualityclaim. All105previous neural sources unchanged. No training run launched by admission;probe snapshots never future initializers.",
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
    plan["inputs"] += [
        ref(REPO / "tests" / n)
        for n in ["test_cfa_scale_support.py", "test_late_scale_supported_cfa_wave.py"]
    ]
    plan["inputs"] += plan["new_sources"]
    for case in cases:
        plan["inputs"] += [case["arrays"], case["parent"]]
    plan["frozen_files"] = sources
    resources(plan)
    save(ROOT / "plan-v1.json", plan)
    print("Prepared8anchorparities/7CPU-GPU-physical-supportchecks/2restoredtraining-onlyupdates")


def probe():
    plan = read(ROOT / "plan-v1.json")
    guard(plan, __file__)
    owner = require_launch(ROOT, "probe")
    (ROOT / "probe.claim").open("x").close()
    try:
        import numpy as np
        import torch
        from cfa_scale_state import (
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

        from demosaic.cfa_scale_support import cfa_cross_scale_support
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
                        agreement, scale_aux = cfa_cross_scale_support(
                            cpu_field,
                            cpu_noise,
                            cpu_colors,
                            bins,
                            valid,
                            windows=(model.evidence_window, *model.support_windows),
                            strides=(
                                model.evidence_stride,
                                model.support_stride,
                                model.support_stride,
                            ),
                        )
                        contextual = torch.cat(
                            (large[:, :, :6], small, large[:, :, 6:], agreement), 2
                        )
                        covariance_values = 0
                        covariance_difference = 0.0
                        for cpu_scale, gpu_scale in zip(
                            scale_aux["scale_geometry"],
                            aux["scale_support"]["scale_geometry"],
                            strict=True,
                        ):
                            c = cpu_scale["nominal_untransported_center_covariance"]
                            g = gpu_scale["nominal_untransported_center_covariance"].cpu()
                            torch.testing.assert_close(c, g, **plan["covariance_tolerance"])
                            assert torch.equal(
                                cpu_scale["wave_gram_rank"], gpu_scale["wave_gram_rank"].cpu()
                            )
                            covariance_values += c.numel()
                            covariance_difference = max(
                                covariance_difference, float(abs(c - g).max())
                            )
                        record["independently_checked_nominal_covariance_values"] = (
                            covariance_values
                        )
                        record["CPU_GPU_nominal_covariance_maximum_difference"] = (
                            covariance_difference
                        )
                        record["extra_support_coordinates"] = agreement.numel()
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
                            agreement,
                            scale_aux,
                        )
                        head = copy.deepcopy(model.cfa_readout).cpu()
                        head.context.weight[:, 24:].fill_(0.02)
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
                extra_nonzero = int(model.cfa_readout.context.weight.grad[:, 24:].count_nonzero())
                if update == 2:
                    assert extra_nonzero > 0
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
                    "extra_support_weight_nonzero_gradient_coordinates": extra_nonzero,
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
                "status": "pass-V200-scale-supported-CFA-eight-anchor-parities-seven-CPU-GPU-maps-heads-two-restored-updates",
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
