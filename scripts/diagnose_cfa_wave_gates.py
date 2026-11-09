"""Fixed V198 input/basis gate interventions; CPU-only, no retraining or promotion."""

import argparse
import ast
import gzip
import json
import os
import time
from pathlib import Path

import numpy as np
from directional_trial_protocol import (
    REPO,
    freeze,
    guard,
    launch,
    read,
    ref,
    require_launch,
    resources,
    save,
)
from phase_admission_protocol import owner_live
from readout_gate_interventions import POLICIES

ROOT = REPO / ".cache/quality-20261108/V199-readout-gate-diagnostic-v1"
DISPLAY_INDICES = [0, 3, 4, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 23, 26, 32, 33, 34, 37]


def prepare():
    assert not ROOT.exists()
    import sys

    assert "torch" not in sys.modules
    publication = REPO / "docs/results/v198-cfa-innovation-wave-final-v1.json"
    proof = REPO / "docs/results/v198-cfa-innovation-wave-publication-verification-v1.json"
    assert read(proof)["publication"] == ref(publication)
    closure = read(REPO / "docs/results/v198-completed-execution-v1.json")
    assert all(not owner_live(v["owner"]) for v in closure["all_registered_owners_terminal"])
    neural = closure["all105_neural_hashes_unchanged"]
    assert len(neural) == 105
    for name, digest in neural.items():
        assert ref(REPO / "src/demosaic" / name)["sha256"] == digest
    tests = REPO / ".cache/v199-readout-gate-CPU-tests-v1.log"
    assert "21 passed" in tests.read_text()
    prior_root = REPO / ".cache/quality-20261108/V198-cfa-innovation-wave-trial-v1"
    old = read(prior_root / "plan-v1.json")
    gallery = REPO / "docs/images/v198-cfa-innovation-wave-v1/manifest-v1.json"
    manifest = read(gallery)
    displays = [dict(index=i, **manifest["images"][i]) for i in DISPLAY_INDICES]
    assert len(displays) == 19 and all(not x["triplet"] for x in displays)
    cases = list({x["case"]["id"]: x["case"] for x in displays}.values())
    assert len(cases) == 14
    extra = set()
    for binding in old["metrics_sources"]:
        for node in ast.walk(ast.parse(Path(binding["path"]).read_text())):
            names = (
                [a.name for a in node.names]
                if isinstance(node, ast.Import)
                else (
                    [node.module]
                    if isinstance(node, ast.ImportFrom) and node.module and not node.level
                    else []
                )
            )
            for name in names:
                candidate = name.split(".")[0] + ".py"
                if (REPO / "scripts" / candidate).exists():
                    extra.add(candidate)
    ROOT.mkdir()
    (ROOT / "artifacts").mkdir()
    work, sources = freeze(
        ROOT,
        [
            "diagnose_cfa_wave_gates.py",
            "audit_cfa_gate_diagnostic.py",
            "render_cfa_gate_diagnostic.py",
            *sorted(extra),
        ],
    )
    plan = {
        "status": "prepared-fixed-input-CFA-gate-diagnostic-no-quality-promotion",
        "created_unix_UTC": time.time(),
        "root": str(ROOT),
        "work": str(work),
        "runner": ref(work / "scripts/diagnose_cfa_wave_gates.py"),
        "auditor": ref(work / "scripts/audit_cfa_gate_diagnostic.py"),
        "renderer": ref(work / "scripts/render_cfa_gate_diagnostic.py"),
        "publication": ref(publication),
        "verification": ref(proof),
        "prior_plan": ref(prior_root / "plan-v1.json"),
        "source_scores": ref(prior_root / "scores-v1.json"),
        "source_journal": ref(prior_root / "quality-observations-v1.jsonl.gz"),
        "baseline_scores": read(prior_root / "review-source-v1.json")["quality_context"][
            "baseline_scores"
        ],
        "gallery": ref(gallery),
        "checkpoints": read(publication)["checkpoints"],
        "module_config": old["module_config"],
        "metrics_sources": old["metrics_sources"],
        "cases": cases,
        "displays": displays,
        "policies": list(POLICIES),
        "CPU_tests": ref(tests),
        "all105_neural_hashes": neural,
        "minimum_GiB": {"local": 40, "RAM": 32},
        "launch_RAM_GiB": 48,
        "forecast_local_MiB": 192,
        "maximum_local_MiB": 256,
        "wave_tolerance": {"rtol": 2e-5, "atol": 3e-8},
        "scope": "Fixed14preselectedV198qualitycontexts/19native displays,bothrawEMAheads,sevenpredeclaredgateinterventions. Only451parameterreadoutforwardsonCPU:28head+28context+28gatecalls;no fullanchor/matching/parent/DINOforward,training,optimizer ornoise/source draws. Savedinput-derivedbins andcachedV195anchor fixed;allsourcefieldschecked. Independentlyreconstructnativebasisandactualheadoutput. RemoveRGBspecificity/spatialvariation,positive-onlygates,andwhole-contextRMSmatchedsharedcontrolswithouttargets. RMSmatchingcanexceedtrainedgatebounds;notadeployableboundedarchitecture. Targetsonlyafterfeatures/interventionsformeasurement. Realreferencesindependent/notexactGT;bothfamilies/JPEGs/siblingsheldout. Diagnosticinterventionsarenotretrainedcandidatesandpreselectedcasesarenotpopulationquality. Existingfullstudyevidenceunchanged. No RAWdecode,original/datazaccess or externalwrites;localbudget256MiBabove40GiBfloor.",
    }
    plan["inputs"] = [
        plan[k]
        for k in [
            "publication",
            "verification",
            "prior_plan",
            "source_scores",
            "source_journal",
            "baseline_scores",
            "gallery",
            "CPU_tests",
        ]
    ] + plan["metrics_sources"]
    plan["inputs"] += [v["export"] for v in plan["checkpoints"].values()]
    for c in cases:
        plan["inputs"] += [c["arrays"], c["parent"]]
    plan["frozen_files"] = sources
    resources(plan)
    save(ROOT / "plan-v1.json", plan)
    print("Prepared14contexts/28CPUheads/7gatepolicies/19native displays")


def run():
    plan = read(ROOT / "plan-v1.json")
    guard(plan, __file__)
    owner = require_launch(ROOT, "run")
    (ROOT / "run.claim").open("x").close()
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    import resource

    import psutil
    import torch
    from balanced_spatial_metrics import DetailMetrics
    from frequency_coverage import sample_camera_rgb
    from lossless_native import fingerprint, load_native
    from profile_raw_kernel_inference import model_hash
    from readout_gate_interventions import (
        amplitude_match,
        correction_stats,
        crop_gates,
        native_basis,
        policy_gate,
        synthesize,
    )

    from demosaic.late_cfa_innovation_wave import CFAInnovationWaveReadout, cfa_innovation_wave_maps
    from demosaic.late_spatial_context_wave import fixed_bin_support_context

    assert not torch.cuda.is_initialized()
    os.nice(max(0, 10 - psutil.Process().nice()))
    os.sched_setaffinity(0, [4, 5])
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    rng = torch.get_rng_state().clone()
    counts = {"head": 0, "context": 0, "gates": 0}
    allowed, heads, captures, hashes = {}, {}, {}, {}
    methods = {e: f"V198-CFA-wave-{e}" for e in ["raw", "EMA"]}
    for endpoint, method in methods.items():
        payload = torch.load(
            plan["checkpoints"][method]["export"]["path"], map_location="cpu", weights_only=True
        )
        head = CFAInnovationWaveReadout().eval().requires_grad_(False)
        head.load_state_dict(
            {
                n.removeprefix("cfa_readout."): v
                for n, v in payload["state_dict"].items()
                if n.startswith("cfa_readout.")
            },
            strict=True,
        )
        assert sum(p.numel() for p in head.parameters()) == 451
        heads[endpoint], hashes[endpoint] = head, model_hash(head)
        for name, module in [("head", head), ("context", head.context), ("gates", head.gates)]:
            allowed[id(module)] = name
        head.gates.register_forward_hook(
            lambda module, args, output, e=endpoint: captures.__setitem__(
                e, output.detach().clone()
            )
        )
        del payload
    original = torch.nn.Module._call_impl

    def only_readout(module, *args, **kwargs):
        if id(module) not in allowed:
            raise RuntimeError("Only isolated readout modules may execute")
        counts[allowed[id(module)]] += 1
        return original(module, *args, **kwargs)

    torch.nn.Module._call_impl = only_readout
    source = read(plan["source_scores"]["path"])
    baseline = read(plan["baseline_scores"]["path"])
    indexed = {(r["id"], r["method"]): r for r in source["rows"]}
    selected = {c["id"] for c in plan["cases"]}
    with gzip.open(plan["source_journal"]["path"], "rt") as stream:
        journal = {
            (r["id"], r["method"]): r for r in map(json.loads, stream) if r["id"] in selected
        }
    metric = DetailMetrics(plan["metrics_sources"])
    rows, observations, artifacts = [], [], []
    replay_scalars = synthesis_channels = 0
    try:
        with (ROOT / "events-v1.jsonl").open("x") as events:
            for case_number, case in enumerate(plan["cases"]):
                resources(plan)
                case_id = case["id"]
                assert ref(case["arrays"]["path"]) == case["arrays"]
                with np.load(case["arrays"]["path"], allow_pickle=False) as archive:
                    inputs = {k: archive[k] for k in ["packed", "variance", "colors"]}
                inherited_binding = baseline["native_predictions"][case_id][
                    "V195-whole-response-EMA"
                ]
                inherited = load_native(inherited_binding)
                field = np.subtract(
                    inputs["packed"],
                    sample_camera_rgb(inherited, inputs["colors"]),
                    dtype=np.float32,
                )
                old = journal[case_id, methods["EMA"]]
                assert fingerprint(field) == old["measurement_field"]
                bins = torch.tensor(old["cfa"]["selection"]["bin_yx"], dtype=torch.int64)
                valid = torch.tensor(old["cfa"]["selection"]["valid"], dtype=torch.bool)
                raw, noise, colors = [
                    torch.from_numpy(v) for v in [field, inputs["variance"], inputs["colors"]]
                ]
                config = plan["module_config"]
                large, waves, geometry = cfa_innovation_wave_maps(
                    raw,
                    noise,
                    colors,
                    bins,
                    valid,
                    window=config["evidence_window"],
                    stride=config["evidence_stride"],
                )
                small, _ = fixed_bin_support_context(
                    raw,
                    noise,
                    colors,
                    bins,
                    valid,
                    windows=config["support_windows"],
                    stride=config["support_stride"],
                )
                context = torch.cat((large[:, :, :6], small, large[:, :, 6:]), 2)
                basis = native_basis(waves.numpy(), bins.numpy())
                mask = (
                    (inputs["variance"].clip(0).mean(1, keepdims=True) > 0)
                    .repeat(2, -2)
                    .repeat(2, -1)
                )
                actual_waves, gates_by_state = {}, {}
                head_checks = {}
                for endpoint, head in heads.items():
                    with torch.no_grad():
                        output = head(context, waves, bins).numpy()
                    output = np.where(mask, output, 0)
                    gates = (
                        captures.pop(endpoint)
                        .tanh()
                        .reshape(*context.shape[:2], 3, *context.shape[-2:])
                        .numpy()
                    )
                    gates_by_state[endpoint] = gates
                    actual = load_native(
                        source["native_predictions"][case_id][methods[endpoint] + "-wave"]
                    )
                    predicted = synthesize(basis, gates, mask)
                    np.testing.assert_allclose(predicted, output, **plan["wave_tolerance"])
                    np.testing.assert_allclose(output, actual, **plan["wave_tolerance"])
                    synthesis_channels += actual.size
                    actual_waves[endpoint] = actual
                    head_checks[endpoint] = {
                        "CPU_head_maximum_difference_from_evaluated_GPU": float(
                            abs(output - actual).max()
                        ),
                        "NumPy_synthesis_maximum_difference_from_CPU_head": float(
                            abs(predicted - output).max()
                        ),
                        "gate_values": fingerprint(gates),
                        "negative_gate_fractions_RGB": [
                            float((gates[:, :, c] < 0).mean()) for c in range(3)
                        ],
                        "gate_minimum_RGB": [float(gates[:, :, c].min()) for c in range(3)],
                        "gate_maximum_RGB": [float(gates[:, :, c].max()) for c in range(3)],
                    }
                # Targets and metric-only parent values are first read after feature/head extraction.
                with np.load(case["arrays"]["path"], allow_pickle=False) as archive:
                    arrays = dict(archive)
                parent = np.load(case["parent"]["path"], allow_pickle=False)
                displays = [d for d in plan["displays"] if d["case"]["id"] == case_id]
                for d in displays:
                    x, y, w, h = d["ROI_xywh"]
                    path = (
                        ROOT / "artifacts" / f"case-{case_number:02d}-display-{d['index']:02d}.npz"
                    )
                    data = {
                        "basis": basis[..., y : y + h, x : x + w],
                        "mask": mask[..., y : y + h, x : x + w],
                    }
                    data.update(
                        {
                            "gate_" + e: crop_gates(g, d["ROI_xywh"])
                            for e, g in gates_by_state.items()
                        }
                    )
                    with path.open("xb") as stream:
                        np.savez_compressed(stream, **data)
                    artifacts.append(
                        {
                            "display": d["index"],
                            "arrays": ref(path),
                            "fingerprints": {k: fingerprint(v) for k, v in data.items()},
                            "inherited_prediction": inherited_binding,
                        }
                    )
                for endpoint, gates in gates_by_state.items():
                    constants = {
                        "color": gates.mean((-2, -1), keepdims=True).tolist(),
                        "shared": gates.mean((2, 3, 4), keepdims=True).tolist(),
                    }
                    for policy in POLICIES:
                        gate = policy_gate(gates, policy)
                        if policy == "actual":
                            wave = actual_waves[endpoint]
                        else:
                            wave = synthesize(basis, gate, mask)
                        matching = {
                            "scale": 1.0,
                            "possible": True,
                            "bounded_gate_architecture": True,
                        }
                        if policy.endswith("-RMS"):
                            wave, matching = amplitude_match(wave, actual_waves[endpoint])
                        value = (inherited + wave).astype(np.float32)
                        measured = metric.measure(case, arrays, parent, value)
                        if policy == "actual":
                            expected = indexed[case_id, methods[endpoint]]
                            for key, observed in measured.items():
                                if isinstance(observed, (int, float)) and not isinstance(
                                    observed, bool
                                ):
                                    assert abs(observed - expected[key]) < 1e-10
                                    replay_scalars += 1
                                else:
                                    assert observed == expected[key]
                        roi_rows = []
                        for d in displays:
                            x, y, w, h = d["ROI_xywh"]
                            roi_rows.append(
                                {
                                    "display": d["index"],
                                    **correction_stats(wave[..., y : y + h, x : x + w]),
                                }
                            )
                        row = {
                            "case": case_id,
                            "state": endpoint,
                            "policy": policy,
                            "normalization": matching,
                            "effective_maximum_gate_abs": float(abs(gate).max())
                            * matching["scale"],
                            "whole_correction": correction_stats(wave),
                            "metrics": measured,
                            "rois": roi_rows,
                        }
                        rows.append(row)
                        events.write(
                            json.dumps(
                                {
                                    "case": case_id,
                                    "state": endpoint,
                                    "policy": policy,
                                    "counts": dict(counts),
                                },
                                allow_nan=False,
                            )
                            + "\n"
                        )
                        events.flush()
                        del wave, value
                    observations.append(
                        {
                            "case": case_id,
                            "state": endpoint,
                            "head_check": head_checks[endpoint],
                            "constants": constants,
                            "actual_wave": source["native_predictions"][case_id][
                                methods[endpoint] + "-wave"
                            ],
                            "actual_prediction": source["native_predictions"][case_id][
                                methods[endpoint]
                            ],
                            "field": fingerprint(field),
                            "fixed_bins": bins.tolist(),
                            "numerical_rank_counts": {
                                str(k): int((geometry["wave_gram_rank"] == k).sum())
                                for k in [0, 1, 2]
                            },
                        }
                    )
                print("case", case_number, case_id, counts, flush=True)
                del (
                    basis,
                    context,
                    large,
                    small,
                    waves,
                    raw,
                    noise,
                    colors,
                    arrays,
                    parent,
                    gates_by_state,
                    actual_waves,
                )
    finally:
        torch.nn.Module._call_impl = original
    assert counts == {"head": 28, "context": 28, "gates": 28}
    assert len(rows) == 196 and len(observations) == 28 and len(artifacts) == 19
    assert all(model_hash(head) == hashes[e] for e, head in heads.items())
    assert all(p.grad is None for head in heads.values() for p in head.parameters())
    assert torch.equal(rng, torch.get_rng_state()) and not torch.cuda.is_initialized()
    guard(plan, __file__)
    save(
        ROOT / "result-v1.json",
        {
            "status": "completed-fixed14context-CFA-gate-interventions-awaiting-audit-and-viewing",
            "created_unix_UTC": time.time(),
            "owner": owner,
            "plan": ref(ROOT / "plan-v1.json"),
            "rows": rows,
            "observations": observations,
            "crop_artifacts": artifacts,
            "isolated_module_calls": counts,
            "independently_reconstructed_native_channels": synthesis_channels,
            "actual_V198_metric_scalars_replayed": replay_scalars,
            "head_hashes_unchanged": hashes,
            "maximum_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            "CUDA_initialized": False,
            "RNG_unchanged": True,
            "optimizer_steps": 0,
            "full_anchor_matching_parent_DINO_forwards": 0,
            "new_source_noise_draws": 0,
            "scope": plan["scope"],
        },
    )
    print(
        "Completed28CPUheads/196case-policy rows/19native-crop bundles; audit/viewing pending",
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "launch", "run"])
    args = parser.parse_args()
    if args.phase == "prepare":
        prepare()
    elif args.phase == "launch":
        print(launch(ROOT, "run"))
    else:
        try:
            run()
        except BaseException as exc:
            save(ROOT / "run-failure-v1.json", {"error": repr(exc), "time_UTC": time.time()})
            raise
