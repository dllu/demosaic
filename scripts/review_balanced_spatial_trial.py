"""V169: fixed V168 weights, isolate direct RGB and remove its broad component."""

import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np
import psutil
from train_directional_bank_trial import guard, read, ref, save

REPO = Path("/home/dllu/proj/demosaic")
PRIOR = REPO / ".cache/quality-20261107/V168-fine-mesh-ladder-v3"
ROOT = REPO / ".cache/quality-20261107/V169-balanced-spatial-v3"
EXTERNAL = Path("/mnt/external/demosaic/quality-20261107/V169-balanced-spatial-v3")


def resources(plan):
    available = {
        "RAM": psutil.virtual_memory().available,
        "local": shutil.disk_usage(REPO).free,
        "external": shutil.disk_usage("/mnt/external").free,
    }
    return available, all(available[k] > v * 2**30 for k, v in plan["minimum_GiB"].items())


def prepare():
    assert not ROOT.exists() and not EXTERNAL.exists()
    available, ok = resources({"minimum_GiB": {"RAM": 32, "local": 56, "external": 117.5}})
    assert ok, available
    ROOT.mkdir()
    EXTERNAL.mkdir()
    prior = read(PRIOR / "review-result-v1.json")
    design = read(PRIOR / "quality-design-v1.json")
    figures = read(PRIOR / "figures-v1.json")
    selected = sorted({item["case"]["id"] for item in figures["images"]})
    assert len(selected) == 36 and len(design["observations"]) == 822
    sources = list((REPO / "src/demosaic").glob("*.py")) + [
        REPO / "scripts" / name
        for name in [
            "review_balanced_spatial_trial.py",
            "balanced_spatial_metrics.py",
            "train_directional_bank_trial.py",
            "profile_raw_kernel_inference.py",
            "report_checkpoint_pilot.py",
            "train_v43_quality_trial.py",
            "report_late_spectral_mixed_quiet.py",
            "render_balanced_spatial_trial.py",
        ]
    ]
    sources += [REPO / "tests/test_late_balanced_spatial.py"]
    frozen = {}
    for source in sources:
        target = ROOT / "work" / source.relative_to(REPO)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        assert source.read_bytes() == target.read_bytes()
        frozen[str(target)] = ref(target)["sha256"]
    metrics = [
        ref(REPO / ".cache/quality-20261103" / name)
        for name in [
            "collaborative-detail-v1/transfer-v1.py",
            "V144-V145-photo-supplement-v1/operator-v2.py",
        ]
    ]
    exports = {end: prior["collections"][f"fine-mesh-{end}-step1000"] for end in ["raw", "EMA"]}
    plan = {
        "root": str(ROOT),
        "external": str(EXTERNAL),
        "work": str(ROOT / "work"),
        "prior_review": ref(PRIOR / "review-result-v1.json"),
        "prior_scores": ref(PRIOR / "scores-v1.json"),
        "design": ref(PRIOR / "quality-design-v1.json"),
        "prior_figures": ref(PRIOR / "figures-v1.json"),
        "collections": exports,
        "frozen_files": frozen,
        "inputs": metrics
        + [
            ref(PRIOR / p)
            for p in [
                "review-result-v1.json",
                "scores-v1.json",
                "quality-design-v1.json",
                "figures-v1.json",
            ]
        ],
        "metrics_sources": metrics,
        "native_cases": selected,
        "minimum_GiB": {"RAM": 32, "local": 56, "external": 116},
        "kernel": {
            "sigma_native_pixels": 8,
            "radius_native_pixels": 24,
            "padding": "replicate",
            "centering": "per-image-channel first pixel before filtering",
        },
        "methods": ["V168", "balanced", "spectral-only", "spatial-only"],
        "endpoints": ["raw", "EMA"],
        "planned_component_forwards": 1644,
        "planned_new_parent_DINO_forwards": 0,
        "planned_new_noise_draws": 0,
        "saved_full_prediction_cases_per_method_endpoint": 36,
        "scope": "Fixed-weight inference intervention,not retraining. Same V168 raw/EMA weights,822 frozen inputs and source conditioning. One outer neural forward per case/endpoint returns original and separated corrections; original output must replay its actual archived prediction bitexact. Balanced output keeps spectral correction and subtracts sigma8/radius24 Gaussian lowpass from direct RGB correction. Spectral-only and spatial-only are branch diagnostics. Target/reference never enters inference. All822 cases get streamed metrics and prediction fingerprints;only36 preselected native cases retain full branch arrays/new predictions,not a full new prediction archive. In-process independent Gaussian checks cover all pixels and independent scalar/error decomposition checks accompany metrics. Fixed48 native boards plus24 triplets follow V168 ROIs/transforms;both protected GFX scenes/priors/JPEGs remain qualitative,notGT. No original/dataz reads,source/noise redraws,parent/DINO calls,training updates or claim of blind generalization. New module plus90 prior neural files remain frozen;two strict CPU transferred-weight loads/47tensors/124909params each. CUDA quota12GiB,32GiB RAM and56/116GiB local/external reserves;resource pressure waits before another forward. No full-output archive or training-quality claim.",
    }
    sizes = sum(
        np.load(c["parent"]["path"], mmap_mode="r").nbytes + 128
        for c in design["observations"]
        if c["id"] in selected
    )
    plan["projected_new_array_bytes"] = 8 * sizes
    assert plan["projected_new_array_bytes"] < 0.81 * 2**30
    available, ok = resources(plan)
    assert ok and available["external"] > 116.5 * 2**30 + plan["projected_new_array_bytes"], (
        available
    )
    plan["admission_available_bytes"] = available
    save(ROOT / "plan-v1.json", plan)
    print(
        "Prepared1644 root forwards,36 fixed native cases,projected arrays GiB",
        plan["projected_new_array_bytes"] / 2**30,
    )


def run():
    import torch
    from balanced_spatial_metrics import DetailMetrics, summarize
    from profile_raw_kernel_inference import model_hash

    from demosaic.late_balanced_spatial import LateBalancedSpatialDetail
    from demosaic.prediction_archive import fingerprint

    def independent_blur(value, kernel):
        result = value.astype(np.float64)
        for axis in [-1, -2]:
            padding = [(0, 0)] * 4
            padding[axis] = (24, 24)
            padded = np.pad(result, padding, mode="edge")
            result = np.apply_along_axis(
                lambda line: np.convolve(line, kernel, mode="valid"), axis, padded
            )
        return result

    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    assert not (ROOT / "review.claim").exists()
    (ROOT / "review.claim").write_text(str(os.getpid()))
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[2:4])
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.set_float32_matmul_precision("highest")
    torch.backends.cuda.matmul.allow_tf32 = torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    torch.cuda.set_per_process_memory_fraction(
        12 * 2**30 / torch.cuda.get_device_properties(0).total_memory
    )
    cpu_rng = torch.get_rng_state().clone()
    cuda_rng = torch.cuda.get_rng_state().clone()
    design = read(plan["design"]["path"])
    old_scores = read(plan["prior_scores"]["path"])
    old_rows = {(r["id"], r["method"]): r for r in old_scores["rows"]}
    metric = DetailMetrics(plan["metrics_sources"])
    rows = []
    native = {}
    forward_count = [0]
    exact = scalar_checks = filter_pixels = ADC_constants = 0
    maximum_filter_error = 0.0
    save(ROOT / "status-v1.json", {"status": "running", "owner": owner, "returned_forwards": 0})
    with (
        (ROOT / "forward-events-v1.jsonl").open("x") as forwards,
        (ROOT / "observations-v1.jsonl").open("x") as observations,
    ):
        for endpoint, binding in plan["collections"].items():
            assert ref(binding["path"]) == binding
            collection = read(binding["path"])
            export = collection["export"]
            assert ref(export["path"]) == export
            state = torch.load(export["path"], map_location="cpu", weights_only=True)
            module = LateBalancedSpatialDetail(**state["module_config"]).cuda().eval()
            assert Path(module.forward.__code__.co_filename).is_relative_to(
                Path(plan["work"]) / "src"
            )
            module.load_state_dict(state["state_dict"], strict=True)
            assert (
                len(module.state_dict()) == 47
                and sum(p.numel() for p in module.parameters()) == 124909
            )
            before = model_hash(module)
            assert before == collection["module_before"] == collection["module_after"]
            module.register_forward_hook(
                lambda *args: forward_count.__setitem__(0, forward_count[0] + 1)
            )
            point = EXTERNAL / endpoint
            point.mkdir()
            kernel = np.exp(-0.5 * (np.arange(-24, 25, dtype=np.float64) / 8) ** 2)
            kernel /= kernel.sum()
            for index, (case, previous) in enumerate(
                zip(design["observations"], collection["observations"], strict=True)
            ):
                assert (
                    case["id"] == previous["id"]
                    and ref(case["arrays"]["path"]) == case["arrays"]
                    and ref(case["parent"]["path"]) == case["parent"]
                )
                arrays = dict(np.load(case["arrays"]["path"]))
                base = np.load(case["parent"]["path"])
                for name, f in previous["inputs"].items():
                    assert fingerprint(arrays[name]) == f
                while True:
                    available, ok = resources(plan)
                    if ok:
                        break
                    save(
                        ROOT / "status-v1.json",
                        {
                            "status": "waiting-resource-before-next-forward",
                            "owner": owner,
                            "returned_forwards": forward_count[0],
                            "available_bytes": available,
                        },
                    )
                    time.sleep(5)
                batch = {
                    k: torch.from_numpy(arrays[k]).cuda()
                    for k in ["packed", "variance", "colors", "wb"]
                }
                with torch.inference_mode():
                    output, aux = module(torch.from_numpy(base).cuda(), **batch, return_aux=True)
                forwards.write(
                    json.dumps(
                        {
                            "endpoint": endpoint,
                            "index": index,
                            "id": case["id"],
                            "returned_forwards": forward_count[0],
                        }
                    )
                    + "\n"
                )
                forwards.flush()
                original = aux["unbalanced_output"].cpu().numpy()
                balanced = output.cpu().numpy()
                assert ref(previous["prediction"]["path"]) == previous["prediction"]
                np.testing.assert_array_equal(original, np.load(previous["prediction"]["path"]))
                exact += 1
                spatial = aux["unbalanced_spatial_correction"].cpu().numpy()
                new_spatial = aux["spatial_correction"].cpu().numpy()
                oracle = spatial.astype(np.float64) - independent_blur(spatial, kernel)
                difference = float(np.max(np.abs(new_spatial - oracle)))
                maximum_filter_error = max(maximum_filter_error, difference)
                np.testing.assert_allclose(new_spatial, oracle, atol=2e-10, rtol=2e-5)
                filter_pixels += oracle.size
                spectral = aux["spectral_correction"].cpu().numpy()
                values = {
                    "V168": original,
                    "balanced": balanced,
                    "spectral-only": base + spectral,
                    "spatial-only": base + spatial,
                }
                case_records = []
                for method, value in values.items():
                    row = metric.measure(case, arrays, base, value)
                    row.update(
                        method=f"{method}-{endpoint}",
                        endpoint=endpoint,
                        values=fingerprint(value),
                        index=index,
                    )
                    if method == "V168":
                        old = old_rows[case["id"], f"fine-mesh-{endpoint}-step1000"]
                        for k, v in row.items():
                            if k in old and isinstance(v, (int, float)) and not isinstance(v, bool):
                                assert abs(v - old[k]) < 1e-10, (k, v, old[k])
                                scalar_checks += 1
                    if (
                        case["kind"] == "flat"
                        and case["noise"]["name"] == "adc-only"
                        and case.get("cohort") != "adc-sloped512"
                    ):
                        assert np.array_equal(value, base)
                        ADC_constants += 1
                    if case["id"] in plan["native_cases"]:
                        if method == "V168":
                            row["prediction"] = previous["prediction"]
                        else:
                            path = point / f"{method}-{index:03d}.npy"
                            assert not path.exists()
                            np.save(path, value, allow_pickle=False)
                            row["prediction"] = ref(path)
                        native.setdefault(case["id"], {})[row["method"]] = row["prediction"]
                    rows.append(row)
                    case_records.append(row)
                if case["id"] in plan["native_cases"]:
                    path = point / f"original-spatial-{index:03d}.npy"
                    np.save(path, spatial, allow_pickle=False)
                    native[case["id"]][f"original-spatial-{endpoint}"] = ref(path)
                observations.write(
                    json.dumps(
                        {
                            "endpoint": endpoint,
                            "index": index,
                            "id": case["id"],
                            "parent": case["parent"],
                            "arrays": case["arrays"],
                            "original_prediction": previous["prediction"],
                            "original_replayed_exact": True,
                            "rows": case_records,
                            "spectral_values": fingerprint(spectral),
                            "spatial_values": fingerprint(spatial),
                            "balanced_spatial_values": fingerprint(new_spatial),
                            "filter_maximum_absolute_error": difference,
                        }
                    )
                    + "\n"
                )
                observations.flush()
                if index % 32 == 0:
                    save(
                        ROOT / "status-v1.json",
                        {
                            "status": "running",
                            "owner": owner,
                            "endpoint": endpoint,
                            "index": index,
                            "returned_forwards": forward_count[0],
                        },
                    )
                    print(endpoint, index, "roots", forward_count[0], flush=True)
                del output, aux, batch
            assert before == model_hash(module)
            del module
            torch.cuda.empty_cache()
    assert forward_count[0] == exact == 1644 and len(rows) == 6576 and len(native) == 36
    assert torch.equal(cpu_rng, torch.get_rng_state()) and torch.equal(
        cuda_rng, torch.cuda.get_rng_state()
    )
    save(
        ROOT / "scores-v1.json",
        {
            "status": "completed-streamed-all822-fixed-cases",
            "plan": ref(ROOT / "plan-v1.json"),
            "rows": rows,
            "summary": summarize(rows),
            "native_predictions": native,
            "owner": owner,
            "component_forwards": forward_count[0],
            "original_predictions_replayed_exact": exact,
            "inherited_metric_scalar_checks": scalar_checks,
            "independent_filter_pixels": filter_pixels,
            "maximum_filter_error": maximum_filter_error,
            "exact_ADC_constant_outputs": ADC_constants,
            "RNG_unchanged": True,
            "model_weights_unchanged": True,
            "new_parent_DINO_forwards": 0,
            "new_noise_draws": 0,
            "new_training_updates": 0,
            "sources": plan["frozen_files"],
            "scope": plan["scope"],
        },
    )
    save(
        ROOT / "status-v1.json",
        {
            "status": "completed-streamed-quality-awaiting-native-render-and-viewing",
            "owner": owner,
            "returned_forwards": forward_count[0],
        },
    )
    print(
        "Completed1644 actual roots/exact replays,6576 streamed rows;36 native cases saved",
        flush=True,
    )


def launch():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    assert not (ROOT / "launch-v1.json").exists() and not (ROOT / "review.claim").exists()
    log = (ROOT / "review-v1.log").open("xb")
    env = dict(os.environ, PYTHONPATH=str(ROOT / "work/src") + ":" + str(ROOT / "work/scripts"))
    command = [
        str(REPO / ".venv/bin/python"),
        str(ROOT / "work/scripts/review_balanced_spatial_trial.py"),
        "run",
    ]
    child = subprocess.Popen(
        command, stdout=log, stderr=subprocess.STDOUT, env=env, cwd=REPO, start_new_session=True
    )
    save(
        ROOT / "launch-v1.json",
        {
            "owner": {"pid": child.pid, "created": psutil.Process(child.pid).create_time()},
            "command": command,
            "plan": ref(ROOT / "plan-v1.json"),
            "log": str(ROOT / "review-v1.log"),
        },
    )
    print("Launched", child.pid)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "run", "launch"])
    args = parser.parse_args()
    {"prepare": prepare, "run": run, "launch": launch}[args.mode]()
