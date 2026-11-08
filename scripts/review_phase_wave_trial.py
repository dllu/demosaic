"""Review both new readout endpoints and replay inherited V183/V169 exactly."""

import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import psutil
from phase_admission_protocol import owner_live, read, ref
from train_phase_wave_trial import METHODS, REPO, ROOT, common_engine, factory, guard, save


def ready(plan):
    launch = read(ROOT / "wave-train-launch-v1.json")
    if owner_live(launch["owner"]):
        raise RuntimeError("Original readout training is still live; no Torch import")
    assert not (ROOT / "wave-train-failure-v1.json").exists()
    result = read(ROOT / "wave-train-result-v1.json")
    assert result["owner"] == launch["owner"] and result["status"].startswith("completed-")
    audit = read(ROOT / "training-audit-v1.json")
    assert (
        audit["status"]
        == "pass-isolated-readout-full-trace-five-checkpoints-inherited189-and-new-Adam-EMA"
    )
    assert audit["training"] == ref(ROOT / "wave-train-result-v1.json")
    assert audit["plan"] == ref(ROOT / "plan-v1.json")
    assert result["plan"] == ref(ROOT / "plan-v1.json")
    return result


def source_guard(plan):
    guard(plan)
    seal = read(ROOT / "review-source-v1.json")
    assert ref(__file__) == seal["reviewer"] and seal["plan"] == ref(ROOT / "plan-v1.json")
    for binding in seal["helpers"]:
        assert ref(binding["path"]) == binding


def prepare():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    assert not (ROOT / "review-source-v1.json").exists()
    work = ROOT / "review-work-v1/scripts"
    work.mkdir(parents=True)
    shutil.copyfile(Path(__file__), work / Path(__file__).name)
    save(
        ROOT / "review-source-v1.json",
        {
            "plan": ref(ROOT / "plan-v1.json"),
            "reviewer": ref(work / Path(__file__).name),
            "helpers": [
                ref(Path(plan["work"]) / "scripts" / name)
                for name in ["phase_wave_training_state.py", "balanced_spatial_metrics.py"]
            ],
            "scope": "Actual two-endpoint review only after terminal original training and independent full training audit. Exact V183 EMA and V169 replay plus ordered baseline+wave closure.",
        },
    )
    print("Prepared sealed two-endpoint review; no quality or Torch call")


def review():
    plan = read(ROOT / "plan-v1.json")
    source_guard(plan)
    training = ready(plan)
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    for _ in range(60):
        path = ROOT / "review-launch-v1.json"
        if path.exists() and read(path)["owner"] == owner:
            break
        time.sleep(0.2)
    else:
        raise RuntimeError("Missing actual review launch; no Torch initialized")
    (ROOT / "review.claim").open("x").close()
    import numpy as np
    import torch
    from balanced_spatial_metrics import DetailMetrics, summarize
    from phase_wave_training_state import inherited_hash, load_ema
    from profile_raw_kernel_inference import model_hash

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
    rows = []
    native = {}
    hashes = {}
    ADC = closure_channels = 0
    cpu_rng, cuda_rng = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
    state = torch.load(training["final_checkpoint"]["path"], map_location="cpu", weights_only=True)
    with (
        (ROOT / "quality-events-v1.jsonl").open("x") as events,
        (ROOT / "quality-observations-v1.jsonl").open("x") as journal,
    ):
        for endpoint, method in METHODS.items():
            module = common.instrument(factory(plan["module_config"]).cuda(), counts).eval()
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
                torch.cuda.synchronize()
                value = output.cpu().numpy()
                inherited = aux["inherited_output"].cpu().numpy()
                v169 = aux["frozen_output"].cpu().numpy()
                wave = aux["wave_correction"].cpu().numpy()
                assert fingerprint(inherited) == baseline[case["id"]]["values"]
                assert fingerprint(v169) == frozen[case["id"]]["values"]
                np.testing.assert_array_equal(value, inherited + wave)
                closure_channels += value.size
                if not aux["matching_evaluated"]:
                    assert np.array_equal(value, v169) and np.array_equal(value, inherited)
                    assert not np.any(arrays["variance"]) and not np.any(wave)
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
                    wave_correction_RMS_DN16=float(np.sqrt(np.mean(wave.astype(np.float64) ** 2)))
                    * 65535,
                )
                if case["id"] in plan["native_cases"]:
                    for label, array in [(method, value), (method + "-wave", wave)]:
                        path = Path(plan["artifacts"]) / "native" / f"{label}-{index:03d}.npy"
                        assert not path.exists()
                        np.save(path, array, allow_pickle=False)
                        native.setdefault(case["id"], {})[label] = ref(path)
                    row["prediction"] = native[case["id"]][method]
                rows.append(row)
                evidence = (
                    None
                    if aux["phase_evidence"] is None
                    else {k: v.detach().cpu().tolist() for k, v in aux["phase_evidence"].items()}
                )
                record = {
                    "method": method,
                    "index": index,
                    "id": case["id"],
                    "arrays": case["arrays"],
                    "parent": case["parent"],
                    "inputs": {k: fingerprint(arrays[k]) for k in batch},
                    "row": row,
                    "evidence": evidence,
                    "inherited_replay_exact": True,
                    "frozen_replay_exact": True,
                    "baseline_plus_wave_closure_exact": True,
                }
                journal.write(json.dumps(record, allow_nan=False) + "\n")
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
    assert counts == plan["expected_quality_counts"] and head_calls["calls"] == 1500
    assert len(rows) == 1644 and len(native) == 36 and ADC == 144
    assert torch.equal(cpu_rng, torch.get_rng_state()) and torch.equal(
        cuda_rng, torch.cuda.get_rng_state()
    )
    rows.sort(key=lambda r: (r["index"], r["method"]))
    source_guard(plan)
    save(
        ROOT / "scores-v1.json",
        {
            "status": "completed-two-endpoint-wave-readout-fixed-quality-awaiting-native-viewing",
            "owner": owner,
            "plan": ref(ROOT / "plan-v1.json"),
            "checkpoint": training["final_checkpoint"],
            "rows": rows,
            "summary": summarize(rows),
            "counts": counts,
            "readout_calls": 1500,
            "native_predictions": native,
            "module_hashes": hashes,
            "weights_unchanged": True,
            "RNG_unchanged": True,
            "exact_V183_EMA_replays": 1644,
            "exact_V169_replays": 1644,
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
        {
            "status": "completed-quality-awaiting-render-and-viewing",
            "owner": owner,
            "counts": counts,
            "readout_calls": 1500,
        },
    )


def launch():
    plan = read(ROOT / "plan-v1.json")
    source_guard(plan)
    ready(plan)
    assert not (ROOT / "review-launch-v1.json").exists() and not (ROOT / "review.claim").exists()
    assert psutil.virtual_memory().available > plan["launch_RAM_GiB"] * 2**30
    assert shutil.disk_usage(REPO).free > (48.5 + 0.20) * 2**30
    assert shutil.disk_usage("/mnt/external").free > (111.5 + 0.43) * 2**30
    env = dict(
        os.environ,
        PYTHONPATH=f"{ROOT}/review-work-v1/scripts:{plan['work']}/src:{plan['work']}/scripts",
        CUDA_VISIBLE_DEVICES="0",
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="2",
        MKL_NUM_THREADS="1",
        CUBLAS_WORKSPACE_CONFIG=":4096:8",
    )
    with (ROOT / "review-v1.log").open("xb") as log:
        child = subprocess.Popen(
            [str(REPO / ".venv/bin/python"), str(Path(__file__)), "review"],
            cwd=REPO,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
    save(ROOT / "review-launch-v1.json", {"owner": owner, "plan": ref(ROOT / "plan-v1.json")})
    print(json.dumps(owner))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "launch", "review"])
    args = parser.parse_args()
    if args.phase != "review":
        {"prepare": prepare, "launch": launch}[args.phase]()
    else:
        try:
            review()
        except BaseException as exc:
            save(ROOT / "review-failure-v1.json", {"error": repr(exc), "time_UTC": time.time()})
            raise
