"""V182: local training-gradient geometry at completed raw V180/V181 states.

No optimizer update, new noise/source observation or protected-scene inference.
The two first/middle noisy batches in each training domain are fixed before
any diagnostic forward. Saved Adam denominators define a fixed positive metric,
not an Adam step or a prediction of finite training/image-quality changes.
"""

import argparse
import gc
import json
import os
import shutil
import time
from pathlib import Path

import psutil
from phase_admission_protocol import owner_live, read, ref

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261107/V182-flat-spatial-loss-geometry-v1"
EXTERNAL = Path("/mnt/external/demosaic/quality-20261107/V182-flat-spatial-loss-geometry-v1")
STUDIES = ["V180-local-phase-trial-v1", "V181-flat-spatial-evidence-trial-v1"]


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def progress(value):
    path = ROOT / "status-v1.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(dict(value, observed_unix_UTC=time.time()), indent=2) + "\n")
    temporary.replace(path)


def guard(plan):
    assert ref(__file__) == plan["runner"], "Use the frozen diagnostic entry"
    for binding in plan["inputs"]:
        assert not binding["path"].startswith("/mnt/dataz")
        assert ref(binding["path"]) == binding
    for path, digest in plan["frozen_files"].items():
        assert ref(path)["sha256"] == digest


def completed_states():
    states = []
    for study, stem in zip(STUDIES, ["v180-local-phase", "v181-flat-spatial"], strict=True):
        root = ROOT.parent / study
        publication = REPO / f"docs/results/{stem}-evidence-final-v1.json"
        verification = REPO / f"docs/results/{stem}-evidence-publication-verification-v1.json"
        index, proof = read(publication), read(verification)
        assert proof["status"].startswith("pass-exact-evidence-")
        assert proof["publication"] == ref(publication)
        assert (
            index["status"]
            == "completed-matched-trial-audited-actually-viewed-and-two-strict-exports"
        )
        for phase in ["evidence-train", "review", "completion"]:
            owner = read(root / f"{phase}-launch-v1.json")["owner"]
            assert not owner_live(owner)
            assert not (root / f"{phase}-failure-v1.json").exists()
        result = read(root / "evidence-train-result-v1.json")
        assert result["status"] == "completed-matched-warmstart-one-pass"
        method = {
            "v180-local-phase": "V180-local-phase-raw",
            "v181-flat-spatial": "V181-flat-spatial-raw",
        }[stem]
        entry = index["checkpoints"][method]
        assert entry["source_checkpoint"] == result["final_checkpoint"]
        states.append(
            {
                "method": method,
                "checkpoint": result["final_checkpoint"],
                "module_hash": entry["module_hash"],
                "publication": ref(publication),
                "verification": ref(verification),
                "plan": ref(root / "plan-v1.json"),
                "training": ref(root / "evidence-train-result-v1.json"),
            }
        )
    return states


def prepare():
    states = completed_states()
    baseline = read(states[1]["plan"]["path"])
    assert not ROOT.exists() and not EXTERNAL.exists()
    assert psutil.virtual_memory().available > 52 * 2**30
    assert shutil.disk_usage(REPO).free > (48.5 + 0.1) * 2**30
    assert shutil.disk_usage("/mnt/external").free > (111.5 + 0.5) * 2**30
    original = baseline["frozen_files"]
    neural = {Path(p).name: h for p, h in original.items() if "/src/demosaic/" in p}
    assert len(neural) == len(list((REPO / "src/demosaic").glob("*.py"))) == 98
    for name, digest in neural.items():
        assert ref(REPO / "src/demosaic" / name)["sha256"] == digest
    cache = read(baseline["cache"]["path"])["batches"]
    cases = []
    for domain in ["mesh", "weak", "photo", "mixed", "flat"]:
        rows = [
            c
            for c in cache
            if c["metadata"]["domain"] == domain and c["metadata"]["noise"]["shot"] > 0
        ]
        cases += [
            dict(rows[i], selection=label)
            for i, label in [(0, "first-noisy"), (len(rows) // 2, "middle-noisy")]
        ]
    assert [c["step"] for c in cases] == [1, 505, 5, 433, 2, 478, 4, 529, 8, 553]
    tests = REPO / ".cache/v182-loss-gradient-CPU-tests-v2.log"
    assert "22 passed" in tests.read_text()
    ROOT.mkdir()
    EXTERNAL.mkdir()
    work = ROOT / "work"
    for name in ["src", "scripts"]:
        shutil.copytree(
            REPO / name, work / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
        )
    (work / "tests").mkdir()
    shutil.copyfile(
        REPO / "tests/test_loss_gradient_geometry.py", work / "tests/test_loss_gradient_geometry.py"
    )
    plan = {
        "status": "prepared-training-only-gradient-diagnostic-no-quality-claim",
        "created_unix_UTC": time.time(),
        "runner": ref(work / "scripts" / Path(__file__).name),
        "root": str(ROOT),
        "external": str(EXTERNAL),
        "work": str(work),
        "states": states,
        "cases": cases,
        "cache": baseline["cache"],
        "pair_units": baseline["pair_units"],
        "module_config": baseline["module_config"],
        "sampling_library": baseline["sampling_library"],
        "domain_weights": baseline["domain_weights"],
        "frozen_component": baseline["frozen_component"],
        "unchanged98neuralfiles": neural,
        "CPU_tests": dict(ref(tests), text=tests.read_text()),
        "expected_forwards": {
            "wrapper": 20,
            "frozen": 20,
            "network": 20,
            "sampler": 100,
            "projection": 20,
        },
        "expected_parameter_backwards": 76,
        "retained_full_parameter_case_indices": [0],
        "scope": "Twenty new native4image diagnostic forwards,ten first/middle cached training batches at each completed raw V180/V181 checkpoint. Five local gradient functionals:original weighted7term total,weightednewspatial,weightedpairdifference,weightedpaircommon,and mean normalized full-target pair response. Output/parameter Gram matrices with independent NumPy/Torch FP64 reductions;also fixed saved-Adam inverseRMS metric,excluding first/newsecondmoments,clipping,decay and finite updates. First mesh parameter vectors/diagonal retained for both checkpoints;other vectors have fingerprints/in-process independent checks. All20RGB batches retained. No optimizer update,new source/noise,parent/DINO,RAWdecode or protectedinput. Not trainedquality,seeduncertainty,blindvalidation or an actual Adam step. Existing V180/V181 quality remains authoritative.",
    }
    plan["inputs"] = [plan[k] for k in ["cache", "pair_units", "sampling_library"]]
    plan["inputs"] += [
        s[k]
        for s in states
        for k in ["checkpoint", "publication", "verification", "plan", "training"]
    ]
    plan["inputs"] += [c[k] for c in cases for k in ["arrays", "parent"]]
    plan["frozen_files"] = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    save(ROOT / "plan-v1.json", plan)
    print("Prepared20nativeforwards/76parameterbackwards/zero updates;fixed10trainingrows")


def checked_gram(vectors, diagonal=None):
    import numpy as np
    import torch
    from loss_gradient_geometry import gram

    result = gram(vectors, diagonal)
    matrix = torch.tensor(np.asarray(vectors), dtype=torch.float64)
    weighted = matrix if diagonal is None else matrix * torch.tensor(diagonal, dtype=torch.float64)
    alternate = (weighted @ matrix.T).numpy()
    bound = 1e-11 * np.sqrt(np.outer(result.diagonal(), result.diagonal())) + 1e-12
    assert np.all(np.abs(result - alternate) <= bound)
    return result, float(np.max(np.abs(result - alternate) / bound))


def probe():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    for _ in range(60):
        if (ROOT / "launch-v1.json").exists() and read(ROOT / "launch-v1.json")["owner"] == owner:
            break
        time.sleep(0.2)
    else:
        raise RuntimeError("Missing exact launch identity;no Torch import")
    (ROOT / "probe.claim").open("x").close()
    os.nice(max(0, 10 - psutil.Process().nice()))
    os.sched_setaffinity(0, [4, 5])
    counts = dict.fromkeys(["wrapper", "frozen", "network", "sampler", "projection"], 0)
    try:
        import numpy as np
        import torch
        from audit_flat_spatial_evidence_trial import loss_from_terms
        from flat_spatial_objective import flat_spatial_error_loss
        from loss_gradient_geometry import LABELS, adam_diagonal, geometry, paired_target_response
        from nonlocal_residual_objective import objective
        from phase_evidence_training_state import adam_clocks, matching_parameters, optimizer_for
        from profile_raw_kernel_inference import model_hash
        from train_flat_spatial_evidence_trial import factory
        from train_phase_evidence_trial import instrument

        from demosaic.prediction_archive import fingerprint

        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        torch.set_float32_matmul_precision("highest")
        torch.backends.cuda.matmul.allow_tf32 = torch.backends.cudnn.allow_tf32 = False
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        torch.use_deterministic_algorithms(True, warn_only=True)
        torch.cuda.set_per_process_memory_fraction(
            24 * 2**30 / torch.cuda.get_device_properties(0).total_memory
        )
        torch.ops.load_library(plan["sampling_library"]["path"])
        save(
            ROOT / "runtime-v1.json",
            {
                "Torch": torch.__version__,
                "CUDA": torch.version.cuda,
                "device": torch.cuda.get_device_name(),
                "sampling_library": plan["sampling_library"],
            },
        )
        units = read(plan["pair_units"]["path"])["rows"]
        rows, backwards, gram_checks, max_ratio = [], 0, 0, 0.0
        with (ROOT / "events-v1.jsonl").open("x") as journal:
            for state in plan["states"]:
                cp = torch.load(state["checkpoint"]["path"], map_location="cpu", weights_only=True)
                module = factory("evidence", plan["module_config"])
                module.load_state_dict(cp["models"], strict=True)
                assert model_hash(module) == state["module_hash"]
                optimizer = optimizer_for(module, lr=1e-4, weight_decay=0.01)
                optimizer.load_state_dict(cp["optimizer"])
                clocks = adam_clocks(module, optimizer)
                assert clocks["network"]["steps"] == [1800.0] and clocks["adapter"]["steps"] == [
                    900.0
                ]
                parameters = matching_parameters(module)
                assert len(parameters) == 142
                diagonals, denominator_state = {}, {}
                for name, parameter in parameters.items():
                    s = optimizer.state[parameter]
                    group = next(
                        g
                        for g in optimizer.param_groups
                        if any(p is parameter for p in g["params"])
                    )
                    diagonals[name] = adam_diagonal(
                        s["exp_avg_sq"].numpy(), float(s["step"]), group["betas"][1], group["eps"]
                    )
                    denominator_state[name] = {
                        "step": float(s["step"]),
                        "beta2": group["betas"][1],
                        "epsilon": group["eps"],
                        "exp_avg_sq": fingerprint(s["exp_avg_sq"].numpy()),
                    }
                del optimizer, cp, parameters
                module = instrument(module.cuda(), counts).train()
                parameters = matching_parameters(module)
                frozen = model_hash(module.frozen)
                assert frozen == plan["frozen_component"]["module_hash"]
                CPU_RNG, CUDA_RNG = (
                    torch.get_rng_state().clone(),
                    torch.cuda.get_rng_state().clone(),
                )
                for index, case in enumerate(plan["cases"]):
                    assert psutil.virtual_memory().available > 32 * 2**30
                    assert shutil.disk_usage(REPO).free > 48.5 * 2**30
                    assert shutil.disk_usage("/mnt/external").free > 111.5 * 2**30
                    arrays = dict(np.load(case["arrays"]["path"], allow_pickle=False))
                    parent = np.load(case["parent"]["path"], allow_pickle=False)
                    assert {k: fingerprint(v) for k, v in arrays.items()} == case["inputs"]
                    assert fingerprint(parent) == case["parent_values"]
                    batch = {k: torch.from_numpy(v).cuda() for k, v in arrays.items()}
                    u = units[case["step"] - 1]
                    assert u["step"] == case["step"] and u["batch"] == case["arrays"]
                    pair_units = torch.tensor(
                        u["candidate_units_FP32"], device="cuda", dtype=torch.float32
                    ).reshape(-1, 1, 1, 1)
                    start = dict(counts)
                    output, aux = module(
                        torch.from_numpy(parent).cuda(),
                        *(batch[k] for k in ["packed", "variance", "colors", "wb"]),
                        return_aux=True,
                    )
                    weight = plan["domain_weights"][case["metadata"]["domain"]]
                    baseline, terms, mask = objective(
                        output, aux["frozen_output"], batch, pair_units, weight
                    )
                    spatial = flat_spatial_error_loss(output, batch["target"], mask)
                    total = baseline + (0.25 * weight) * spatial
                    values = dict(terms, flat_spatial=spatial)
                    term_values = {k: float(v.detach()) for k, v in values.items()}
                    assert float(total.detach()) == loss_from_terms(term_values, weight)
                    scalars = [
                        baseline,
                        (0.25 * weight) * spatial,
                        weight * terms["pair_difference"],
                        weight * terms["pair_common"],
                    ]
                    response = output.new_zeros(())
                    energies = []
                    if len(batch["pair_indices"]):
                        response, power = paired_target_response(
                            output, batch["target"], batch["pair_indices"]
                        )
                        energies = power.cpu().tolist()
                    scalars.append(response)
                    gradients = []
                    for value in scalars:
                        if value.requires_grad:
                            computed = torch.autograd.grad(
                                value,
                                (output, *parameters.values()),
                                retain_graph=True,
                                allow_unused=True,
                            )
                            backwards += 1
                            current = [
                                g.detach().cpu().numpy().copy()
                                if g is not None
                                else np.zeros(tuple(p.shape), np.float32)
                                for p, g in zip(
                                    (output, *parameters.values()), computed, strict=True
                                )
                            ]
                            del computed
                        else:
                            current = [
                                np.zeros(tuple(p.shape), np.float32)
                                for p in (output, *parameters.values())
                            ]
                        assert all(np.isfinite(g).all() for g in current)
                        gradients.append(current)
                    groups = {name: np.zeros((5, 5)) for name in ["all", "network", "adapter"]}
                    weighted_groups = {name: np.zeros((5, 5)) for name in groups}
                    layers = []
                    for j, (name, parameter) in enumerate(parameters.items(), 1):
                        vectors = np.stack([g[j].ravel() for g in gradients])
                        ordinary, ratio = checked_gram(vectors)
                        metric, ratio2 = checked_gram(vectors, diagonals[name].ravel())
                        gram_checks += 2
                        max_ratio = max(max_ratio, ratio, ratio2)
                        for group in [
                            "all",
                            "network" if name.startswith("network.") else "adapter",
                        ]:
                            groups[group] += ordinary
                            weighted_groups[group] += metric
                        layers.append(
                            {
                                "name": name,
                                "shape": list(parameter.shape),
                                "gradients": [fingerprint(g[j]) for g in gradients],
                                "Gram": ordinary.tolist(),
                                "fixed_Adam_Gram": metric.tolist(),
                            }
                        )
                    output_gram, ratio = checked_gram(np.stack([g[0].ravel() for g in gradients]))
                    gram_checks += 1
                    max_ratio = max(max_ratio, ratio)
                    retained = None
                    if index in plan["retained_full_parameter_case_indices"]:
                        path = (
                            EXTERNAL / f"{state['method']}-case{index:02d}-parameter-gradients.npz"
                        )
                        vectors = np.stack(
                            [np.concatenate([v.ravel() for v in g[1:]]) for g in gradients]
                        )
                        diagonal = np.concatenate([v.ravel() for v in diagonals.values()])
                        with path.open("xb") as stream:
                            np.savez(stream, gradients=vectors, fixed_Adam_diagonal=diagonal)
                        retained = ref(path)
                    prediction = EXTERNAL / f"{state['method']}-case{index:02d}-RGB.npy"
                    value = output.detach().cpu().numpy()
                    with prediction.open("xb") as stream:
                        np.save(stream, value, allow_pickle=False)
                    row = {
                        "method": state["method"],
                        "case_index": index,
                        "step": case["step"],
                        "domain": case["metadata"]["domain"],
                        "selection": case["selection"],
                        "batch": case["arrays"],
                        "parent": case["parent"],
                        "inputs": case["inputs"],
                        "parent_values": case["parent_values"],
                        "pair_units": u,
                        "loss_terms": term_values,
                        "old_loss": float(baseline.detach()),
                        "eight_term_total": float(total.detach()),
                        "domain_weight": weight,
                        "flat_mask": fingerprint(mask.cpu().numpy()),
                        "flat_coverage": float(mask.float().mean()),
                        "pair_response": float(response.detach()),
                        "pair_target_energies": energies,
                        "output": dict(ref(prediction), values=fingerprint(value)),
                        "labels": LABELS,
                        "output_Gram": output_gram.tolist(),
                        "output_geometry": geometry(output_gram),
                        "parameter_Grams": {k: v.tolist() for k, v in groups.items()},
                        "fixed_Adam_Grams": {k: v.tolist() for k, v in weighted_groups.items()},
                        "parameter_geometry": {k: geometry(v) for k, v in groups.items()},
                        "fixed_Adam_geometry": {k: geometry(v) for k, v in weighted_groups.items()},
                        "layers": layers,
                        "retained_full_parameter_gradients": retained,
                        "denominator_state": denominator_state,
                        "saved_Adam_clocks": clocks,
                        "output_gradient_fingerprints": [fingerprint(g[0]) for g in gradients],
                        "counts_before": start,
                        "counts_after": dict(counts),
                        "parameter_backward_evaluations": sum(v.requires_grad for v in scalars),
                    }
                    save(ROOT / f"{state['method']}-case{index:02d}-v1.json", row)
                    rows.append(row)
                    journal.write(
                        json.dumps(
                            {
                                "method": state["method"],
                                "case_index": index,
                                "step": case["step"],
                                "row": ref(ROOT / f"{state['method']}-case{index:02d}-v1.json"),
                                "counts": dict(counts),
                                "backwards": backwards,
                            }
                        )
                        + "\n"
                    )
                    journal.flush()
                    assert all(p.grad is None for p in module.parameters())
                    assert torch.equal(CPU_RNG, torch.get_rng_state()) and torch.equal(
                        CUDA_RNG, torch.cuda.get_rng_state()
                    )
                    progress(
                        {
                            "status": "probing-training-gradient-geometry",
                            "owner": owner,
                            "method": state["method"],
                            "case_index": index,
                            "counts": dict(counts),
                            "backwards": backwards,
                        }
                    )
                    del (
                        gradients,
                        current,
                        vectors,
                        output,
                        aux,
                        baseline,
                        spatial,
                        total,
                        terms,
                        values,
                        scalars,
                        response,
                        batch,
                        arrays,
                        parent,
                    )
                    gc.collect()
                assert (
                    model_hash(module) == state["module_hash"]
                    and model_hash(module.frozen) == frozen
                )
                del module, parameters, diagonals
                gc.collect()
                torch.cuda.empty_cache()
        assert (
            counts == plan["expected_forwards"]
            and backwards == plan["expected_parameter_backwards"]
        )
        guard(plan)
        save(
            ROOT / "result-v1.json",
            {
                "status": "completed-training-gradient-geometry-zero-updates-awaiting-independent-inspection",
                "owner": owner,
                "plan": ref(ROOT / "plan-v1.json"),
                "rows": rows,
                "counts": counts,
                "parameter_backward_evaluations": backwards,
                "independent_Torch_NumPy_Gram_checks": gram_checks,
                "maximum_Gram_error_fraction_of_tolerance": max_ratio,
                "peak_CUDA_bytes": torch.cuda.max_memory_allocated(),
                "all_model_frozen_state_and_RNG_unchanged": True,
                "optimizer_updates": 0,
                "new_sensor_source_draws": 0,
                "new_parent_DINO_forwards": 0,
                "RAW_decodes": 0,
                "scope": plan["scope"],
            },
        )
        progress(
            {
                "status": "completed-awaiting-independent-inspection",
                "owner": owner,
                "counts": counts,
                "backwards": backwards,
            }
        )
    except BaseException as error:
        save(
            ROOT / "failure-v1.json",
            {
                "status": "failed-preserved-no-automatic-retry",
                "owner": owner,
                "counts": counts,
                "error": repr(error),
            },
        )
        progress(
            {"status": "failed-preserved-no-automatic-retry", "owner": owner, "error": repr(error)}
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "probe"])
    args = parser.parse_args()
    prepare() if args.phase == "prepare" else probe()
