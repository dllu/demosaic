"""Four V197 endpoints on all822 cases; exact V195/V183/V169 replays."""

import argparse
import ast
import gc
import json
import time
from pathlib import Path

from admit_innovation_wave import MODES, factory
from directional_trial_protocol import (
    freeze,
    guard,
    read,
    ref,
    require_launch,
    save,
)
from phase_admission_protocol import owner_live
from train_innovation_wave import ROOT


def source_guard(plan):
    guard(plan)
    seal = read(ROOT / "review-source-v1.json")
    guard(seal)
    return seal


def review_plan():
    plan = read(ROOT / "plan-v1.json")
    plan.update(read(ROOT / "review-source-v1.json")["quality_context"])
    return plan


def load_new_ema(module, ema):
    expected = {n for n in module.state_dict() if n.startswith("innovation_readout.")}
    assert len(expected) == 4 and set(ema) == expected
    module.load_state_dict(dict(module.state_dict(), **ema), strict=True)


def ready(plan):
    for mode in MODES:
        owner = read(ROOT / f"{mode}-launch-v1.json")["owner"]
        assert not owner_live(owner)
        assert not (ROOT / f"{mode}-train-failure-v1.json").exists()
        result = read(ROOT / f"{mode}-train-result-v1.json")
        assert result["owner"] == owner and result["status"].startswith("completed-V197-")
    audit = read(ROOT / "training-audit-v1.json")
    assert (
        audit["status"]
        == "pass-V197-two-full-matched-traces-ten-factored-checkpoints-3860anchor-tensors"
    )
    assert audit["plan"] == ref(ROOT / "plan-v1.json")


def prepare():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    assert not (ROOT / "review-source-v1.json").exists()
    import shutil

    from directional_trial_protocol import REPO

    contracts = REPO / ".cache/v197-evidence-CPU-tests-v1.log"
    assert "5 passed" in contracts.read_text()

    previous = read(plan["previous_plan"]["path"])
    quality_context = {
        "baseline_scores": ref(Path(plan["previous_plan"]["path"]).parent / "scores-v1.json"),
        "V183_scores": previous["baseline_scores"],
        "V187_scores": previous["V187_scores"],
        "prior_figures": ref(Path(plan["previous_plan"]["path"]).parent / "figures-v1.json"),
        "anchor_journal": ref(
            Path(plan["previous_plan"]["path"]).parent / "quality-observations-v1.jsonl.gz"
        ),
        "orientation_plan": ref(
            REPO / ".cache/quality-20261108/V194-orientation-response-v1/plan-v2.json"
        ),
        "previous_breakdown": ref(
            Path(plan["previous_plan"]["path"]).parent / "directional-breakdown-v2/result-v1.json"
        ),
        "expected_quality_counts": {
            "wrapper": 3288,
            "frozen": 3288,
            "network": 3000,
            "sampler": 15000,
            "projection": 3000,
        },
    }
    extra = set()
    for binding in plan["metrics_sources"]:
        for node in ast.walk(ast.parse(Path(binding["path"]).read_text())):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                names = [node.module]
            for name in names:
                filename = name.split(".")[0] + ".py"
                if (REPO / "scripts" / filename).is_file():
                    extra.add(filename)
    work, sources = freeze(
        ROOT / "review-frozen-v1",
        [
            "review_innovation_wave.py",
            "audit_innovation_quality.py",
            "render_innovation_wave.py",
            "reduce_innovation_wave.py",
            "export_innovation_checkpoints.py",
            "breakdown_innovation_wave.py",
            *sorted(extra),
        ],
    )
    test_copy = work / "tests/test_innovation_wave_evidence_receipt.py"
    test_copy.parent.mkdir()
    shutil.copyfile(REPO / "tests/test_innovation_wave_evidence_receipt.py", test_copy)
    sources[str(test_copy)] = ref(test_copy)["sha256"]
    (Path(plan["artifacts"]) / "native").mkdir()
    save(
        ROOT / "review-source-v1.json",
        {
            "created_unix_UTC": time.time(),
            "plan": ref(ROOT / "plan-v1.json"),
            "work": str(work),
            "reviewer": ref(work / "scripts/review_innovation_wave.py"),
            "auditor": ref(work / "scripts/audit_innovation_quality.py"),
            "renderer": ref(work / "scripts/render_innovation_wave.py"),
            "reducer": ref(work / "scripts/reduce_innovation_wave.py"),
            "exporter": ref(work / "scripts/export_innovation_checkpoints.py"),
            "breakdown": ref(work / "scripts/breakdown_innovation_wave.py"),
            "frozen_files": sources,
            "dynamic_metric_import_roots": sorted(extra),
            "inputs": [
                *plan["metrics_sources"],
                plan["prior_scores"],
                ref(ROOT / "plan-v1.json"),
                *[b for k, b in quality_context.items() if k != "expected_quality_counts"],
            ],
            "quality_context": quality_context,
            "CPU_contracts": ref(contracts),
            "scope": "Prepare code while training may run; review requires both original owners terminal and full CPU training audit. Four endpoints x822cases,144native RGB+144wave encodings,exact V195/V183/V169 replays,all protected scenes. Reuse inputs/baselines; compact seven-method current figures/tables instead of recopying historical galleries. No quality claim at preparation.",
        },
    )
    print("Prepared four-endpoint review; training completion/audit required before launch")


def preflight():
    plan = review_plan()
    seal = source_guard(plan)
    assert ref(__file__) == seal["reviewer"]
    import numpy as np
    import torch
    from balanced_spatial_metrics import DetailMetrics
    from lossless_native import load_native

    assert not torch.cuda.is_initialized()
    torch.set_num_threads(1)

    def reject_forward(*args, **kwargs):
        raise RuntimeError("Metric preflight must never run a neural module")

    torch.nn.Module._call_impl = reject_forward
    metric = DetailMetrics(plan["metrics_sources"])
    baseline = read(plan["baseline_scores"]["path"])
    old = {r["id"]: r for r in baseline["rows"] if r["method"] == "V195-whole-response-EMA"}
    cases = [
        c for c in read(plan["design"]["path"])["observations"] if c["id"] in plan["native_cases"]
    ]
    checks = 0
    kinds = set()
    for case in cases:
        with np.load(case["arrays"]["path"], allow_pickle=False) as archive:
            arrays = dict(archive)
        base = np.load(case["parent"]["path"], allow_pickle=False)
        value = load_native(baseline["native_predictions"][case["id"]]["V195-whole-response-EMA"])
        measured = metric.measure(case, arrays, base, value)
        for key, observed in measured.items():
            if isinstance(observed, (int, float)) and not isinstance(observed, bool):
                assert abs(observed - old[case["id"]][key]) < 1e-10
                checks += 1
            else:
                assert observed == old[case["id"]][key]
        kinds.add(case["kind"])
    assert len(cases) == 36 and len(kinds) == 5 and not torch.cuda.is_initialized()
    save(
        ROOT / "metric-preflight-v1.json",
        {
            "status": "pass36saved-V195-native-metrics-five-kinds-no-neural-forwards",
            "review_source": ref(ROOT / "review-source-v1.json"),
            "numeric_scalars_within_1e-10": checks,
            "cases": 36,
            "kinds": sorted(kinds),
            "new_module_forwards": 0,
            "CUDA_initialized": False,
        },
    )
    print("PASS36savedanchor-native-metric-replays/", checks, "numeric scalars/no neural forwards")


def review():
    plan = review_plan()
    seal = source_guard(plan)
    assert ref(__file__) == seal["reviewer"]
    ready(plan)
    owner = require_launch(ROOT, "review")
    (ROOT / "review.claim").open("x").close()
    import numpy as np
    import torch
    from balanced_spatial_metrics import DetailMetrics, summarize
    from frequency_coverage import sample_camera_rgb
    from innovation_wave_state import anchor_hash
    from innovation_wave_state import expand as expand_checkpoint
    from lossless_native import write_native
    from pooled_wave_evidence_receipt import describe_pooled, describe_support
    from profile_raw_kernel_inference import model_hash
    from spatial_trial_protocol import open_text
    from train_coherent_pair_evidence_engine import instrument
    from train_innovation_wave import common_engine

    from demosaic.prediction_archive import fingerprint

    common = common_engine()
    common.runtime(plan)
    baseline_scores = read(plan["baseline_scores"]["path"])
    baseline_method = "V195-whole-response-EMA"
    baseline = {r["id"]: r for r in baseline_scores["rows"] if r["method"] == baseline_method}
    frozen = {
        r["id"]: r
        for r in read(plan["prior_scores"]["path"])["rows"]
        if r["method"] == "balanced-EMA"
    }
    v183 = {
        r["id"]: r
        for r in read(plan["V183_scores"]["path"])["rows"]
        if r["method"] == "V183-coherent-pair-EMA"
    }
    assert len(baseline) == len(frozen) == len(v183) == 822
    metric = DetailMetrics(plan["metrics_sources"])
    design = read(plan["design"]["path"])["observations"]
    counts = dict.fromkeys(["wrapper", "frozen", "network", "sampler", "projection"], 0)
    head_calls = {"calls": 0}
    anchor_calls = {"calls": 0}
    rows, native, hashes, checkpoints = [], {}, {}, {}
    ADC = closure_channels = 0
    cpu_rng, cuda_rng = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
    with (
        (ROOT / "quality-events-v1.jsonl").open("x") as events,
        open_text(ROOT / "quality-observations-v1.jsonl.gz", "xt") as journal,
    ):
        for mode in MODES:
            training = read(ROOT / f"{mode}-train-result-v1.json")
            checkpoint = training["final_checkpoint"]
            assert ref(checkpoint["path"]) == checkpoint
            checkpoints[mode] = checkpoint
            state = expand_checkpoint(
                torch.load(checkpoint["path"], map_location="cpu", weights_only=True)
            )
            for endpoint, method in plan["methods"][mode].items():
                module = instrument(factory(plan, mode).cuda(), counts).eval()
                module.load_state_dict(state["models"], strict=True)
                if endpoint == "EMA":
                    load_new_ema(module, state["ema"])
                assert anchor_hash(module) == plan["initializer"]["module_hash"]
                before = model_hash(module)
                module.innovation_readout.register_forward_pre_hook(
                    lambda *args: head_calls.__setitem__("calls", head_calls["calls"] + 1)
                )
                module.wave_readout.register_forward_pre_hook(
                    lambda *args: anchor_calls.__setitem__("calls", anchor_calls["calls"] + 1)
                )
                hashes[method] = {
                    "before": before,
                    "inherited": anchor_hash(module),
                    "frozen": model_hash(module.frozen),
                }
                for ordinal, index in enumerate(plan["processing_order"]):
                    common.resources(plan, "review", owner)
                    case = design[index]
                    assert (
                        ref(case["arrays"]["path"]) == case["arrays"]
                        and ref(case["parent"]["path"]) == case["parent"]
                    )
                    arrays = dict(np.load(case["arrays"]["path"], allow_pickle=False))
                    base = np.load(case["parent"]["path"], allow_pickle=False)
                    batch = {
                        k: torch.from_numpy(arrays[k]).cuda()
                        for k in ["packed", "variance", "colors", "wb"]
                    }
                    with torch.inference_mode():
                        output, aux = module(
                            torch.from_numpy(base).cuda(),
                            *(batch[k] for k in ["packed", "variance", "colors", "wb"]),
                            return_aux=True,
                        )
                    value = output.cpu().numpy()
                    inherited = aux["anchor_output"].cpu().numpy()
                    v169 = aux["anchor_aux"]["frozen_output"].cpu().numpy()
                    v183_value = aux["anchor_aux"]["inherited_output"].cpu().numpy()
                    assert fingerprint(v183_value) == v183[case["id"]]["values"]
                    wave = aux["wave_correction"].cpu().numpy()
                    assert fingerprint(inherited) == baseline[case["id"]]["values"]
                    assert fingerprint(v169) == frozen[case["id"]]["values"]
                    np.testing.assert_array_equal(value, inherited + wave)
                    closure_channels += value.size
                    if not aux["matching_evaluated"]:
                        assert np.array_equal(value, v169) and not np.any(wave)
                        assert not np.any(arrays["variance"])
                        ADC += 1
                    field_values = None
                    if aux["matching_evaluated"]:
                        expected_field = arrays["packed"].copy()
                        if mode == "innovation":
                            expected_field = np.subtract(
                                expected_field,
                                sample_camera_rgb(inherited, arrays["colors"]),
                                dtype=np.float32,
                            )
                        field_values = aux["measurement_field"].cpu().numpy()
                        assert fingerprint(field_values) == fingerprint(expected_field)
                    row = metric.measure(case, arrays, base, value)
                    row.update(
                        method=method,
                        index=index,
                        values=fingerprint(value),
                        inherited_values=fingerprint(inherited),
                        frozen_values=fingerprint(v169),
                        anchor_V195_EMA_replay_exact=True,
                        V183_replay_exact=True,
                        V183_values=fingerprint(v183_value),
                        frozen_V169_replay_exact=True,
                        ADC_exact=not aux["matching_evaluated"],
                        wave_correction_values=fingerprint(wave),
                        wave_correction_RMS_DN16=float(
                            np.sqrt(np.mean(wave.astype(np.float64) ** 2))
                        )
                        * 65535,
                    )
                    if case["id"] in plan["native_cases"]:
                        directory = Path(plan["artifacts"]) / "native"
                        delta = write_native(
                            directory / f"{method}-wave-{index:03d}.native.json", wave
                        )
                        encoded = write_native(
                            directory / f"{method}-{index:03d}.native.json",
                            value,
                            baseline=baseline_scores["native_predictions"][case["id"]][
                                baseline_method
                            ],
                            wave=delta,
                        )
                        native.setdefault(case["id"], {}).update(
                            {method: encoded, method + "-wave": delta}
                        )
                        row["prediction"] = encoded
                    rows.append(row)
                    evidence = (
                        None
                        if aux["anchor_aux"]["phase_evidence"] is None
                        else {
                            k: v.detach().cpu().tolist()
                            for k, v in aux["anchor_aux"]["phase_evidence"].items()
                        }
                    )
                    journal.write(
                        json.dumps(
                            {
                                "method": method,
                                "index": index,
                                "id": case["id"],
                                "arrays": case["arrays"],
                                "parent": case["parent"],
                                "inputs": {k: fingerprint(arrays[k]) for k in batch},
                                "row": row,
                                "evidence": evidence,
                                "mode": mode,
                                "measurement_field": None
                                if field_values is None
                                else fingerprint(field_values),
                                "measurement_field_CPU_checked": aux["matching_evaluated"],
                                "anchor_pooled": describe_pooled(aux["anchor_aux"]),
                                "anchor_support": describe_support(aux["anchor_aux"]),
                                "support": describe_support(aux),
                                "pooled": describe_pooled(aux),
                                "inherited_replay_exact": True,
                                "frozen_replay_exact": True,
                                "baseline_plus_wave_closure_exact": True,
                            },
                            allow_nan=False,
                        )
                        + "\n"
                    )
                    journal.flush()
                    events.write(
                        json.dumps(
                            {
                                "method": method,
                                "index": index,
                                "ordinal": ordinal,
                                "id": case["id"],
                                "counts": dict(counts),
                                "readout_calls": head_calls["calls"],
                                "anchor_readout_calls": anchor_calls["calls"],
                                "matching_evaluated": aux["matching_evaluated"],
                            }
                        )
                        + "\n"
                    )
                    events.flush()
                    if ordinal % 16 == 0:
                        common.progress(
                            "review",
                            {
                                "status": "reviewing",
                                "owner": owner,
                                "method": method,
                                "ordinal": ordinal,
                                "index": index,
                                "counts": dict(counts),
                                "readout_calls": head_calls["calls"],
                                "anchor_readout_calls": anchor_calls["calls"],
                                "peak_CUDA_bytes": torch.cuda.max_memory_allocated(),
                            },
                        )
                    del (
                        arrays,
                        base,
                        batch,
                        output,
                        aux,
                        value,
                        inherited,
                        v169,
                        v183_value,
                        wave,
                        evidence,
                        field_values,
                    )
                assert (
                    model_hash(module) == before
                    and anchor_hash(module) == plan["initializer"]["module_hash"]
                )
                hashes[method]["after"] = model_hash(module)
                del module
                gc.collect()
            del state
    assert (
        counts == plan["expected_quality_counts"]
        and head_calls["calls"] == anchor_calls["calls"] == 3000
    )
    assert len(rows) == 3288 and len(native) == 36 and ADC == 288
    assert torch.equal(cpu_rng, torch.get_rng_state()) and torch.equal(
        cuda_rng, torch.cuda.get_rng_state()
    )
    rows.sort(key=lambda r: (r["index"], r["method"]))
    source_guard(plan)
    save(
        ROOT / "scores-v1.json",
        {
            "status": "completed-V197-four-endpoint-quality-awaiting-native-viewing",
            "owner": owner,
            "plan": ref(ROOT / "plan-v1.json"),
            "checkpoints": checkpoints,
            "rows": rows,
            "summary": summarize(rows),
            "counts": counts,
            "readout_calls": 3000,
            "native_predictions": native,
            "module_hashes": hashes,
            "weights_unchanged": True,
            "RNG_unchanged": True,
            "exact_V195_EMA_replays": 3288,
            "exact_V183_EMA_replays": 3288,
            "anchor_readout_calls": 3000,
            "exact_V169_replays": 3288,
            "ADC_outputs_exact_V169": ADC,
            "independent_inprocess_baseline_plus_wave_addition_channels": closure_channels,
            "new_parent_DINO_forwards": 0,
            "new_source_noise_draws": 0,
            "peak_CUDA_allocated_bytes": torch.cuda.max_memory_allocated(),
            "scope": plan["scope"],
        },
    )
    common.progress(
        "review",
        {"status": "completed-quality-awaiting-native-viewing", "owner": owner, "counts": counts},
    )
    print(
        "Completed 4x822cases / inherited replays /144native RGB+144wave; actual viewing pending",
        flush=True,
    )


def launch_review():
    plan = review_plan()
    seal = source_guard(plan)
    ready(plan)
    assert read(ROOT / "metric-preflight-v1.json")["status"].startswith(
        "pass36saved-V195-native-metrics"
    )
    # The shared launcher binds a runner; leave the original training plan intact.
    import os
    import subprocess

    import psutil

    assert not (ROOT / "review-launch-v1.json").exists()
    assert psutil.virtual_memory().available > plan["launch_RAM_GiB"] * 2**30
    env = dict(
        os.environ,
        PYTHONPATH=f"{seal['work']}/src:{seal['work']}/scripts",
        CUDA_VISIBLE_DEVICES="0",
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="2",
        MKL_NUM_THREADS="1",
        CUBLAS_WORKSPACE_CONFIG=":4096:8",
    )
    from directional_trial_protocol import REPO

    with (ROOT / "review-v1.log").open("xb") as log:
        child = subprocess.Popen(
            [str(REPO / ".venv/bin/python"), seal["reviewer"]["path"], "review"],
            cwd=REPO,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
    save(
        ROOT / "review-launch-v1.json",
        {
            "owner": owner,
            "plan": ref(ROOT / "plan-v1.json"),
            "review_source": ref(ROOT / "review-source-v1.json"),
        },
    )
    print(owner)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "preflight", "launch", "review"])
    phase = parser.parse_args().phase
    if phase == "prepare":
        prepare()
    elif phase == "preflight":
        preflight()
    elif phase == "launch":
        launch_review()
    else:
        try:
            review()
        except BaseException as exc:
            save(ROOT / "review-failure-v1.json", {"error": repr(exc), "time_UTC": time.time()})
            raise
