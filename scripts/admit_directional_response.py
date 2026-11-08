"""V195: shared V187 EMA parity and restored head probes for both loss modes."""

import argparse
import copy
import gc
import time

from directional_trial_protocol import (
    ADMISSION as ROOT,
)
from directional_trial_protocol import (
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
    runtime,
    save,
)


def prepare():
    dep = dependency()
    old = read(REPO / ".cache/quality-20261107/V187-pooled-wave-admission-v1/plan-v1.json")
    assert not ROOT.exists()
    ROOT.mkdir()
    (ROOT / "artifacts").mkdir()
    work, sources = freeze(
        ROOT, ["admit_directional_response.py", "inspect_directional_admission.py"]
    )
    plan = {
        "status": "prepared-shared-V187-EMA-parity-and-four-restored-loss-probes-not-quality",
        "created_unix_UTC": time.time(),
        "root": str(ROOT),
        "work": str(work),
        "runner": ref(work / "scripts/admit_directional_response.py"),
        "donor": dep["donor"],
        "initializer": dep["initializer"],
        "dependency": dep,
        "module_config": dep["donor"]["module_config"],
        "cases": old["cases"],
        "sampling_library": old["sampling_library"],
        "pair_units": old["pair_units"],
        "domain_weights": old["domain_weights"],
        "probe_domains": ["mesh", "mixed"],
        "modes": list(MODES),
        "lr": 0.001,
        "weight_decay": 0.01,
        "minimum_GiB": {"local": 40, "RAM": 32},
        "launch_RAM_GiB": 52,
        "CUDA_quota_GiB": 24,
        "local_forecast_GiB": 0.05,
        "gradient_tolerance": {"rtol": 5e-5, "atol": 2e-5},
        "response_gradient_tolerance": {"rtol": 1e-5, "atol": 2e-8},
        "readout_tolerance": {"rtol": 1e-5, "atol": 3e-6},
        "scope": "Same completed V187 EMA full state,508 head parameters/four tensors;189 inherited V183 EMA tensors frozen and all103 neural sources unchanged. Seven native initial parities against a separately strict-loaded V187 EMA model, six nonzero trained-head CPU/GPU readouts. Each loss mode starts identical donor weights with fresh Adam/EMA clocks0 and performs two training-only four-image updates(mesh,mixed), with real Model/Adam/EMA/CPU-CUDA RNG restoration after its first update. Check addition output derivatives on CPU and all508 head parameter derivatives against CPU replay of the GPU upstream gradient. Protected GFX inputs are parity-only. All nine earlier terms/masks retained; add.25domain-weight whole or directional response. Probes never initialize future training. No new source/noise,parent/DINO inference,RAW decode or original/dataz access. Localforecast.05GiB above40GiB reserve; no external writes. Old architecture/CPU geometry contracts reused, not counted as new.",
    }
    plan["inputs"] = [dep[k] for k in ["publication", "verification", "CPU_result", "CPU_tests"]]
    plan["inputs"] += [
        plan["donor"]["export"],
        plan["initializer"]["export"],
        plan["sampling_library"],
        plan["pair_units"],
    ]
    for case in plan["cases"]:
        plan["inputs"] += [case["arrays"], case["parent"]]
    plan["frozen_files"] = sources
    resources(plan)
    save(ROOT / "plan-v1.json", plan)
    print("Prepared shared V187 EMA / 7 parities / two modes x two restored updates")


def probe():
    plan = read(ROOT / "plan-v1.json")
    guard(plan, __file__)
    owner = require_launch(ROOT, "probe")
    (ROOT / "probe.claim").open("x").close()
    try:
        import numpy as np
        import torch
        from coherent_pair_objective import paired_coherent_response_loss
        from directional_pair_objective import objective
        from directional_pair_reference import independent
        from phase_wave_training_state import clocks, fresh_state, inherited_hash, update_ema
        from profile_raw_kernel_inference import model_hash
        from spatial_wave_training_state import pack_checkpoint, restore_factored
        from train_coherent_pair_evidence_engine import instrument

        runtime(plan)
        donor = torch.load(plan["donor"]["export"]["path"], map_location="cpu", weights_only=True)
        inherited = plan["initializer"]["module_hash"]
        counts = dict.fromkeys(["wrapper", "frozen", "network", "sampler", "projection"], 0)

        def new_model():
            m = factory(plan["module_config"])
            m.load_state_dict(donor["state_dict"], strict=True)
            assert model_hash(m) == plan["donor"]["module_hash"]
            assert inherited_hash(m) == inherited
            return instrument(m.cuda(), counts).train()

        model = new_model()
        baseline = factory(plan["module_config"])
        baseline.load_state_dict(donor["state_dict"], strict=True)
        baseline = instrument(baseline.cuda(), counts).eval().requires_grad_(False)
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
                old = baseline(base, *args)
                actual, aux = model(base, *args, return_aux=True)
                assert torch.equal(old.view(torch.int32), actual.view(torch.int32))
                row = {
                    "case": case["id"],
                    "native_values": actual.numel(),
                    "V187_EMA_initial_bit_exact": True,
                    "noisy": case["noisy"],
                }
                if aux["wave_evidence_features"] is not None:
                    head = copy.deepcopy(model.wave_readout).cpu()
                    expected = head(
                        aux["wave_evidence_features"].cpu(),
                        aux["wave_selection"]["bin_yx"].cpu(),
                        aux["wave_support_context"].cpu(),
                    )
                    actual_head = model.wave_readout(
                        aux["wave_evidence_features"],
                        aux["wave_selection"]["bin_yx"],
                        aux["wave_support_context"],
                    ).cpu()
                    torch.testing.assert_close(actual_head, expected, **plan["readout_tolerance"])
                    row.update(
                        nonzero_head_values=expected.numel(),
                        CPU_GPU_head_maximum_difference=float((actual_head - expected).abs().max()),
                    )
                    del head, expected, actual_head
            parities.append(row)
            save(ROOT / f"parity-{len(parities)}-v1.json", row)
            print("parity", case["id"], flush=True)
            del batch, base, args, old, actual, aux
            gc.collect()
        del baseline, model
        units = read(plan["pair_units"]["path"])["rows"]
        all_records, checkpoints, restorations = [], [], []
        for mode in MODES:
            model = new_model()
            optimizer, ema = fresh_state(model, lr=plan["lr"], weight_decay=plan["weight_decay"])
            assert clocks(model, optimizer) == {"tensors": 4, "states": 0, "steps": []}
            assert all(
                torch.equal(p, ema[n]) for n, p in model.named_parameters() if p.requires_grad
            )
            for update, domain in enumerate(plan["probe_domains"], 1):
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
                weight = plan["domain_weights"][domain]
                loss, terms, mask = objective(
                    output, aux["frozen_output"], batch, pair_units, weight, mode=mode
                )
                scalars = {k: float(v.detach()) for k, v in terms.items()}
                assert float(loss.detach()) == objective_total(scalars, weight)
                addition_grad = (
                    torch.autograd.grad(terms["response_addition"], output, retain_graph=True)[0]
                    .detach()
                    .cpu()
                )
                cpu_value = output.detach().cpu()
                if mode == "directional":
                    expected_loss, expected_grad = independent(
                        cpu_value.double().numpy(),
                        batch["target"].cpu().double().numpy(),
                        batch["pair_indices"].cpu().numpy(),
                        1,
                    )
                    expected_grad = torch.from_numpy(expected_grad).float()
                else:
                    cpu_value.requires_grad_(True)
                    cpu_loss = paired_coherent_response_loss(
                        cpu_value, batch["target"].cpu(), batch["pair_indices"].cpu()
                    )
                    expected_loss = float(cpu_loss.detach())
                    expected_grad = torch.autograd.grad(cpu_loss, cpu_value)[0]
                assert abs(expected_loss - scalars["response_addition"]) < 3e-6
                torch.testing.assert_close(
                    addition_grad, expected_grad, **plan["response_gradient_tolerance"]
                )
                upstream = torch.autograd.grad(loss, output, retain_graph=True)[0].detach().cpu()
                head = copy.deepcopy(model.wave_readout).cpu()
                cpu_correction = (
                    head(
                        aux["wave_evidence_features"].cpu(),
                        aux["wave_selection"]["bin_yx"].cpu(),
                        aux["wave_support_context"].cpu(),
                    )
                    * aux["sigma"].cpu()
                )
                cpu_gradients = torch.autograd.grad(
                    (cpu_correction * upstream).sum(), tuple(head.parameters())
                )
                loss.backward()
                differences, nonzero = [], {}
                for (name, p), expected in zip(
                    model.wave_readout.named_parameters(), cpu_gradients, strict=True
                ):
                    assert p.grad is not None and torch.isfinite(p.grad).all()
                    torch.testing.assert_close(p.grad.cpu(), expected, **plan["gradient_tolerance"])
                    differences.append(float((p.grad.cpu() - expected).abs().max()))
                    nonzero[name] = int(p.grad.count_nonzero())
                    assert nonzero[name] > 0
                assert all(
                    p.grad is None
                    for n, p in model.named_parameters()
                    if not n.startswith("wave_readout.")
                )
                norm = torch.nn.utils.clip_grad_norm_(
                    model.wave_readout.parameters(), 1, error_if_nonfinite=True
                )
                optimizer.step()
                decay = update_ema(model, ema, updates=update)
                assert inherited_hash(model) == inherited
                assert clocks(model, optimizer) == {
                    "tensors": 4,
                    "states": 4,
                    "steps": [float(update)],
                }
                record = {
                    "mode": mode,
                    "update": update,
                    "domain": domain,
                    "case": case["id"],
                    "loss": float(loss.detach()),
                    "terms": scalars,
                    "ten_term_FP32_total_exact": True,
                    "mask_pixels": int(mask.sum()),
                    "gradient_norm": float(norm),
                    "parameter_gradient_coordinates": 508,
                    "nonzero_gradients": nonzero,
                    "CPU_GPU_parameter_gradient_maximum_difference": max(differences),
                    "response_gradient_coordinates": addition_grad.numel(),
                    "response_gradient_maximum_difference": float(
                        (addition_grad - expected_grad).abs().max()
                    ),
                    "independent_response_loss": expected_loss,
                    "EMA_decay": decay,
                    "Adam": clocks(model, optimizer),
                    "module_hash": model_hash(model),
                    "counts": dict(counts),
                }
                all_records.append(record)
                path = ROOT / "artifacts" / f"{mode}-probe-step{update}.pt"
                payload = {
                    "models": model.state_dict(),
                    "ema": ema,
                    "optimizer": optimizer.state_dict(),
                    "updates": update,
                    "mode": mode,
                    "inherited_hash": inherited,
                    "CPU_RNG": torch.get_rng_state(),
                    "CUDA_RNG": torch.cuda.get_rng_state(),
                    "component": type(model).__name__,
                    "module_config": plan["module_config"],
                    "plan": ref(ROOT / "plan-v1.json"),
                    "scope": "Probe only; never a training initializer",
                }
                with path.open("xb") as stream:
                    torch.save(pack_checkpoint(payload, plan["initializer"]["export"]), stream)
                checkpoints.append(ref(path))
                save(ROOT / f"{mode}-update-{update}-v1.json", record)
                del (
                    output,
                    aux,
                    loss,
                    terms,
                    mask,
                    batch,
                    base,
                    pair_units,
                    payload,
                    upstream,
                    head,
                    cpu_correction,
                    cpu_gradients,
                )
                del cpu_value, expected_grad, addition_grad
                if mode == "whole":
                    del cpu_loss
                if update == 1:
                    saved = torch.load(path, map_location="cpu", weights_only=True)
                    del model, optimizer
                    gc.collect()
                    model = instrument(factory(plan["module_config"]).cuda(), counts).train()
                    optimizer, ema = restore_factored(
                        model, saved, lr=plan["lr"], weight_decay=plan["weight_decay"]
                    )
                    assert (
                        model_hash(model) == record["module_hash"]
                        and inherited_hash(model) == inherited
                    )
                    restorations.append(
                        {
                            "mode": mode,
                            "checkpoint": ref(path),
                            "model_Adam_EMA_CPU_CUDA_RNG_exact": True,
                            "repeated_prefix_forwards": 0,
                        }
                    )
                    del saved
                print("update", mode, update, "loss", record["loss"], flush=True)
            del model, optimizer, ema
            gc.collect()
        assert counts == {
            "wrapper": 18,
            "frozen": 18,
            "network": 16,
            "sampler": 80,
            "projection": 16,
        }
        guard(plan, __file__)
        save(
            ROOT / "admission-result-v1.json",
            {
                "status": "pass-V195-V187-EMA-parity-both-response-gradients-and-restoration",
                "owner": owner,
                "plan": ref(ROOT / "plan-v1.json"),
                "parities": parities,
                "records": all_records,
                "checkpoints": checkpoints,
                "restorations": restorations,
                "counts": counts,
                "peak_CUDA_allocated_bytes": torch.cuda.max_memory_allocated(),
                "inherited189_unchanged": True,
                "new_source_noise_draws": 0,
                "protected_optimizer_inputs": 0,
                "scope": plan["scope"],
            },
        )
        print(
            "PASS: seven shared parities, six head parities, four updates, two restorations",
            flush=True,
        )
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
