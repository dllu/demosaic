"""All822 cases for each V195 endpoint, with exact inherited baseline replay."""

import argparse
import gc
import json
import time
from pathlib import Path

from directional_trial_protocol import (
    MODES,
    factory,
    freeze,
    guard,
    read,
    ref,
    require_launch,
    save,
)
from directional_trial_protocol import (
    TRIAL as ROOT,
)
from phase_admission_protocol import owner_live


def source_guard(plan):
    guard(plan)
    seal = read(ROOT / "review-source-v1.json")
    for name, digest in seal["frozen_files"].items():
        assert ref(name)["sha256"] == digest
    return seal


def ready(plan):
    for mode in MODES:
        owner = read(ROOT / f"{mode}-launch-v1.json")["owner"]
        assert not owner_live(owner)
        assert not (ROOT / f"{mode}-train-failure-v1.json").exists()
        result = read(ROOT / f"{mode}-train-result-v1.json")
        assert result["owner"] == owner and result["status"].startswith("completed-V195-")
    audit = read(ROOT / "training-audit-v1.json")
    assert (
        audit["status"] == "pass-V195-two-matched-traces-ten-checkpoints-Adam-EMA-and-inherited189"
    )
    assert audit["plan"] == ref(ROOT / "plan-v1.json")


def prepare():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    assert not (ROOT / "review-source-v1.json").exists()
    work, sources = freeze(
        ROOT / "review-frozen-v1",
        [
            "review_directional_response.py",
            "audit_directional_quality.py",
            "render_directional_response.py",
            "reduce_directional_response.py",
        ],
    )
    save(
        ROOT / "review-source-v1.json",
        {
            "created_unix_UTC": time.time(),
            "plan": ref(ROOT / "plan-v1.json"),
            "work": str(work),
            "reviewer": ref(work / "scripts/review_directional_response.py"),
            "auditor": ref(work / "scripts/audit_directional_quality.py"),
            "renderer": ref(work / "scripts/render_directional_response.py"),
            "reducer": ref(work / "scripts/reduce_directional_response.py"),
            "frozen_files": sources,
            "scope": "Prepare code while training may run; review requires both original owners terminal and full CPU training audit. Four endpoints x822cases,144native RGB+144wave encodings,exact V183/V169 replays,all protected scenes. Reuse inputs/baselines; compact six-method current figures/tables instead of recopying historical galleries. No quality claim at preparation.",
        },
    )
    print("Prepared four-endpoint review; training completion/audit required before launch")


def review():
    plan = read(ROOT / "plan-v1.json")
    seal = source_guard(plan)
    assert ref(__file__) == seal["reviewer"]
    ready(plan)
    owner = require_launch(ROOT, "review")
    (ROOT / "review.claim").open("x").close()
    import numpy as np
    import torch
    from balanced_spatial_metrics import DetailMetrics, summarize
    from lossless_native import write_native
    from phase_wave_training_state import inherited_hash, load_ema
    from pooled_wave_evidence_receipt import describe_pooled, describe_support
    from profile_raw_kernel_inference import model_hash
    from spatial_trial_protocol import open_text
    from spatial_wave_training_state import expand_checkpoint
    from train_coherent_pair_evidence_engine import instrument
    from train_directional_response import common_engine

    from demosaic.prediction_archive import fingerprint

    common = common_engine()
    common.runtime(plan)
    baseline_scores = read(plan["baseline_scores"]["path"])
    baseline_method = "V183-coherent-pair-EMA"
    baseline = {r["id"]: r for r in baseline_scores["rows"] if r["method"] == baseline_method}
    frozen = {
        r["id"]: r
        for r in read(plan["prior_scores"]["path"])["rows"]
        if r["method"] == "balanced-EMA"
    }
    assert len(baseline) == len(frozen) == 822
    metric = DetailMetrics(plan["metrics_sources"])
    design = read(plan["design"]["path"])["observations"]
    counts = dict.fromkeys(["wrapper", "frozen", "network", "sampler", "projection"], 0)
    head_calls = {"calls": 0}
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
                module = instrument(factory(plan["module_config"]).cuda(), counts).eval()
                module.load_state_dict(state["models"], strict=True)
                if endpoint == "EMA":
                    load_ema(module, state["ema"])
                assert inherited_hash(module) == plan["initializer"]["module_hash"]
                before = model_hash(module)
                module.wave_readout.register_forward_pre_hook(
                    lambda *args: head_calls.__setitem__("calls", head_calls["calls"] + 1)
                )
                hashes[method] = {
                    "before": before,
                    "inherited": inherited_hash(module),
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
                    inherited = aux["inherited_output"].cpu().numpy()
                    v169 = aux["frozen_output"].cpu().numpy()
                    wave = aux["wave_correction"].cpu().numpy()
                    assert fingerprint(inherited) == baseline[case["id"]]["values"]
                    assert fingerprint(v169) == frozen[case["id"]]["values"]
                    np.testing.assert_array_equal(value, inherited + wave)
                    closure_channels += value.size
                    if not aux["matching_evaluated"]:
                        assert np.array_equal(value, v169) and not np.any(wave)
                        assert not np.any(arrays["variance"])
                        ADC += 1
                    row = metric.measure(case, arrays, base, value)
                    row.update(
                        method=method,
                        index=index,
                        values=fingerprint(value),
                        inherited_values=fingerprint(inherited),
                        frozen_values=fingerprint(v169),
                        inherited_V183_EMA_replay_exact=True,
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
                        if aux["phase_evidence"] is None
                        else {
                            k: v.detach().cpu().tolist() for k, v in aux["phase_evidence"].items()
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
                                "peak_CUDA_bytes": torch.cuda.max_memory_allocated(),
                            },
                        )
                    del arrays, base, batch, output, aux, value, inherited, v169, wave, evidence
                assert (
                    model_hash(module) == before
                    and inherited_hash(module) == plan["initializer"]["module_hash"]
                )
                hashes[method]["after"] = model_hash(module)
                del module
                gc.collect()
            del state
    assert counts == plan["expected_quality_counts"] and head_calls["calls"] == 3000
    assert len(rows) == 3288 and len(native) == 36 and ADC == 288
    assert torch.equal(cpu_rng, torch.get_rng_state()) and torch.equal(
        cuda_rng, torch.cuda.get_rng_state()
    )
    rows.sort(key=lambda r: (r["index"], r["method"]))
    source_guard(plan)
    save(
        ROOT / "scores-v1.json",
        {
            "status": "completed-V195-four-endpoint-quality-awaiting-native-viewing",
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
            "exact_V183_EMA_replays": 3288,
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
    plan = read(ROOT / "plan-v1.json")
    seal = source_guard(plan)
    ready(plan)
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
    parser.add_argument("phase", choices=["prepare", "launch", "review"])
    phase = parser.parse_args().phase
    if phase == "prepare":
        prepare()
    elif phase == "launch":
        launch_review()
    else:
        try:
            review()
        except BaseException as exc:
            save(ROOT / "review-failure-v1.json", {"error": repr(exc), "time_UTC": time.time()})
            raise
