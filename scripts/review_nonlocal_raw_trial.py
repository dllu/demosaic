"""Fixed released RAW matching network, direct and DINO-parent reconstructions."""

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
ROOT = REPO / ".cache/quality-20261107/V170-nonlocal-raw-v2"
UPSTREAM = ROOT.parent / "V170-nonlocal-raw-v1"
PRIOR = REPO / ".cache/quality-20261107/V169-balanced-spatial-v3"


def resources(plan):
    free = {
        "RAM": psutil.virtual_memory().available,
        "local": shutil.disk_usage(REPO).free,
        "external": shutil.disk_usage("/mnt/external").free,
    }
    return free, all(free[k] > v * 2**30 for k, v in plan["minimum_GiB"].items())


def prepare():
    assert not (ROOT / "plan-v1.json").exists() and not (ROOT / "work").exists()
    prior_plan = read(PRIOR / "plan-v1.json")
    design_path = Path(prior_plan["design"]["path"])
    design = read(design_path)
    native = read(PRIOR / "figures-v1.json")
    selected = sorted({item["case"]["id"] for item in native["images"]})
    assert len(design["observations"]) == 822 and len(selected) == 36
    assert read(UPSTREAM / "parity-admission-v1.json")["original_and_ported_CPU_output_bitexact"]
    assert "13 passed" in (REPO / ".cache/v170-cpu-tests-v1.log").read_text()
    external = Path("/mnt/external/demosaic/quality-20261107/V170-nonlocal-raw-v1")
    assert not external.exists()
    files = list((REPO / "src/demosaic").glob("*.py")) + [
        REPO / "scripts" / n
        for n in [
            "review_nonlocal_raw_trial.py",
            "balanced_spatial_metrics.py",
            "report_checkpoint_pilot.py",
            "report_late_spectral_mixed_quiet.py",
            "train_directional_bank_trial.py",
            "train_v43_quality_trial.py",
            "profile_raw_kernel_inference.py",
            "fetch_nonlocal_raw.py",
            "render_nonlocal_raw_trial.py",
        ]
    ]
    files += [REPO / "tests/test_nonlocal_raw.py"]
    frozen = {}
    for path in files:
        target = ROOT / "work" / path.relative_to(REPO)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        assert path.read_bytes() == target.read_bytes()
        frozen[str(target)] = ref(target)["sha256"]
    old_neural = {
        Path(p).name: h for p, h in prior_plan["frozen_files"].items() if "/src/demosaic/" in p
    }
    assert len(old_neural) == 91
    for name, h in old_neural.items():
        assert ref(REPO / "src/demosaic" / name)["sha256"] == h
    projected = 0
    for case in design["observations"]:
        if case["id"] not in selected:
            continue
        parent = np.load(case["parent"]["path"], mmap_mode="r")
        batch, _, height, width = parent.shape
        projected += 2 * parent.nbytes + batch * 4 * (height // 2) * (width // 2) * 4 + 384
    assert projected < 0.27 * 2**30
    order = [0, 692] + [i for i in range(822) if i not in [0, 692]]
    assert (
        design["observations"][692]["id"] == "mesh-nominal"
        and design["observations"][692]["output_shape"][-1] == 768
    )
    adopted = read(UPSTREAM / "fetch-adoption-v1.json")
    weights = adopted["tensor_weights"]
    library = adopted["library"]
    metric_sources = prior_plan["metrics_sources"]
    plan = {
        "root": str(ROOT),
        "work": str(ROOT / "work"),
        "external": str(external),
        "design": ref(design_path),
        "prior_scores": ref(PRIOR / "scores-v1.json"),
        "parent_scores": prior_plan["prior_scores"],
        "prior_figures": ref(PRIOR / "figures-v1.json"),
        "released_weights": weights,
        "library": library,
        "admission": ref(UPSTREAM / "parity-admission-v1.json"),
        "fetch": ref(UPSTREAM / "fetch-adoption-v1.json"),
        "methods": ["NLRaw-Malvar", "NLRaw-DINO"],
        "processing_order": order,
        "native_cases": selected,
        "minimum_GiB": {"RAM": 32, "local": 52, "external": 114},
        "CUDA_quota_GiB": 12,
        "projected_new_array_bytes": int(projected),
        "projection_margin_GiB": 0.5,
        "prior_neural_hashes": old_neural,
        "metrics_sources": metric_sources,
        "frozen_files": frozen,
        "inputs": [
            weights,
            library,
            ref(design_path),
            ref(PRIOR / "scores-v1.json"),
            ref(PRIOR / "figures-v1.json"),
        ]
        + metric_sources,
        "scope": "External pretrained RAW-to-RAW NLFeMF v1.0.0 comparison,not a matched architecture/training test or a model newly trained on our free-image corpus. Selected original7 class ASTs/141 tensors/15282866 values match release;native CPU/CUDA sampling sources pinned and independently checked. Model input is canonical RGGB-oriented RGBG RAW clipped0..1 plus sqrt of supplied noisy-input variance. Output RAW clips0..1 as upstream. Two fixed RGB reconstructions share one network call:Malvar;and frozen V143 DINO-parent plus Malvar(denoisedRAW-CFA(parent)). No target/reference enters forward. Same822 cached cases,CFA/noise/parents/GT/ROIs/exposure asV169. Real references qualitative,notGT,unscored. No new photo source/noise draw,training,parent/DINO call or original/dataz read. All822 get streamed metrics/fingerprints;36 fixed native cases retain2 fullRGB outputs+RAW. Fixed48 native boards/12 triplets,60 figures,no resizing. Processing order firsttests512 and768 geometries without repeating those calls. New bounded trial reserves52GiB local/114GiB external+.5GiB projectionmargin;prior trialguards/receipts remainunchanged. Runtime32GiB RAM/12GiB CUDA;wait before nextforward on resource pressure. Prior91 neural files unchanged;two new source modules. Admission2CPU+1CUDA synthetic fullmodelcalls are separate;quality822 newGPUroots,with5 nested samplercalls perroot. No full new prediction archive/posthoc all-array or blind-generalization claim.",
    }
    free, ok = resources(plan)
    assert ok and free["external"] > (114.5 * 2**30 + projected), free
    plan["admission_free_bytes"] = free
    external.mkdir(parents=True)
    save(ROOT / "plan-v1.json", plan)
    print(
        "Prepared822 new quality roots/1644 RGB method rows,36 native cases,array GiB",
        projected / 2**30,
    )


def run():
    import torch
    from balanced_spatial_metrics import DetailMetrics, summarize
    from profile_raw_kernel_inference import model_hash

    from demosaic.nonlocal_raw import NonlocalRawDemosaic
    from demosaic.prediction_archive import fingerprint

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
    torch.ops.load_library(plan["library"]["path"])
    module = (
        NonlocalRawDemosaic().load_released_state(plan["released_weights"]["path"]).cuda().eval()
    )
    assert Path(module.forward.__code__.co_filename).is_relative_to(Path(plan["work"]) / "src")
    before = model_hash(module)
    counts = {"root": 0, "network": 0, "sampler": 0}
    module.register_forward_hook(lambda *a: counts.__setitem__("root", counts["root"] + 1))
    module.network.register_forward_hook(
        lambda *a: counts.__setitem__("network", counts["network"] + 1)
    )
    for submodule in [
        module.network.down1[0],
        module.network.down2[0],
        module.network.body[0],
        module.network.up2[1],
        module.network.up1[1],
    ]:
        submodule.register_forward_hook(
            lambda *a: counts.__setitem__("sampler", counts["sampler"] + 1)
        )
    CPU_RNG = torch.get_rng_state().clone()
    CUDA_RNG = torch.cuda.get_rng_state().clone()
    design = read(plan["design"]["path"])
    metric = DetailMetrics(plan["metrics_sources"])
    rows = []
    native = {}
    raw_rows = []
    save(ROOT / "status-v1.json", {"status": "running", "owner": owner, "counts": counts})
    with (
        (ROOT / "forward-events-v1.jsonl").open("x") as forwards,
        (ROOT / "observations-v1.jsonl").open("x") as observations,
    ):
        for ordinal, index in enumerate(plan["processing_order"]):
            case = design["observations"][index]
            assert (
                ref(case["arrays"]["path"]) == case["arrays"]
                and ref(case["parent"]["path"]) == case["parent"]
            )
            arrays = dict(np.load(case["arrays"]["path"]))
            base = np.load(case["parent"]["path"])
            batch = {
                k: torch.from_numpy(arrays[k]).cuda()
                for k in ["packed", "variance", "colors", "wb"]
            }
            while True:
                free, ok = resources(plan)
                if ok:
                    break
                save(
                    ROOT / "status-v1.json",
                    {
                        "status": "waiting-resource-before-next-forward",
                        "owner": owner,
                        "counts": counts,
                        "next_index": index,
                        "free_bytes": free,
                    },
                )
                time.sleep(5)
            torch.cuda.synchronize()
            started = time.monotonic()
            with torch.inference_mode():
                hybrid, aux = module(torch.from_numpy(base).cuda(), **batch, return_aux=True)
            torch.cuda.synchronize()
            elapsed = time.monotonic() - started
            forwards.write(
                json.dumps(
                    {
                        "index": index,
                        "id": case["id"],
                        "ordinal": ordinal,
                        "returned_forwards": counts["root"],
                        "network_forwards": counts["network"],
                        "nested_sampler_calls": counts["sampler"],
                        "seconds": elapsed,
                    }
                )
                + "\n"
            )
            forwards.flush()
            assert counts == {
                "root": ordinal + 1,
                "network": ordinal + 1,
                "sampler": 5 * (ordinal + 1),
            }
            raw = aux["denoised_packed"].cpu().numpy()
            values = {
                "NLRaw-Malvar": aux["direct_rgb"].cpu().numpy(),
                "NLRaw-DINO": hybrid.cpu().numpy(),
            }
            assert (
                raw.dtype == np.float32
                and np.isfinite(raw).all()
                and raw.min() >= 0
                and raw.max() <= 1
            )
            checks = {}
            for method, value in values.items():
                selected = np.stack(
                    [
                        value[0, int(arrays["colors"][0, p]), p // 2 :: 2, p % 2 :: 2]
                        for p in range(4)
                    ]
                )[None]
                maximum = float(np.max(np.abs(selected - raw)))
                assert maximum < 5e-7
                checks[method] = maximum
            case_rows = []
            for method, value in values.items():
                row = metric.measure(case, arrays, base, value)
                row.update(method=method, index=index, values=fingerprint(value))
                if case["id"] in plan["native_cases"]:
                    path = Path(plan["external"]) / f"{method}-{index:03d}.npy"
                    assert not path.exists()
                    np.save(path, value, allow_pickle=False)
                    row["prediction"] = ref(path)
                    native.setdefault(case["id"], {})[method] = row["prediction"]
                rows.append(row)
                case_rows.append(row)
            raw_record = {
                "index": index,
                "id": case["id"],
                "values": fingerprint(raw),
                "measured_sample_maximum_error": checks,
            }
            if case["kind"] != "real":
                target = arrays["target"]
                target_raw = np.stack(
                    [
                        target[0, int(arrays["colors"][0, p]), p // 2 :: 2, p % 2 :: 2]
                        for p in range(4)
                    ]
                )[None]
                raw_record.update(
                    raw_error_RMS_DN16=float(
                        np.sqrt(np.mean((raw.astype(np.float64) - target_raw) ** 2)) * 65535
                    ),
                    noisy_error_RMS_DN16=float(
                        np.sqrt(np.mean((arrays["packed"].astype(np.float64) - target_raw) ** 2))
                        * 65535
                    ),
                )
            if case["id"] in plan["native_cases"]:
                path = Path(plan["external"]) / f"RAW-{index:03d}.npy"
                np.save(path, raw, allow_pickle=False)
                raw_record["prediction"] = ref(path)
                native[case["id"]]["denoised-RAW"] = raw_record["prediction"]
            raw_rows.append(raw_record)
            observations.write(
                json.dumps(
                    {
                        "index": index,
                        "id": case["id"],
                        "arrays": case["arrays"],
                        "parent": case["parent"],
                        "inputs": {
                            k: fingerprint(arrays[k])
                            for k in ["packed", "variance", "colors", "wb"]
                        },
                        "rows": case_rows,
                        "raw": raw_record,
                    }
                )
                + "\n"
            )
            observations.flush()
            if ordinal % 16 == 0:
                save(
                    ROOT / "status-v1.json",
                    {
                        "status": "running",
                        "owner": owner,
                        "counts": counts,
                        "index": index,
                        "id": case["id"],
                        "peak_CUDA_bytes": torch.cuda.max_memory_allocated(),
                    },
                )
                print(
                    ordinal,
                    index,
                    case["id"],
                    "roots",
                    counts["root"],
                    "CUDA_GiB",
                    torch.cuda.max_memory_allocated() / 2**30,
                    flush=True,
                )
            del hybrid, aux, batch
    assert (
        counts == {"root": 822, "network": 822, "sampler": 4110}
        and len(rows) == 1644
        and len(native) == 36
    )
    assert (
        before == model_hash(module)
        and torch.equal(CPU_RNG, torch.get_rng_state())
        and torch.equal(CUDA_RNG, torch.cuda.get_rng_state())
    )
    rows.sort(key=lambda r: (r["index"], r["method"]))
    raw_rows.sort(key=lambda r: r["index"])
    save(
        ROOT / "scores-v1.json",
        {
            "status": "completed-all822-fixed-cases-with-streamed-metrics",
            "plan": ref(ROOT / "plan-v1.json"),
            "rows": rows,
            "summary": summarize(rows),
            "raw_rows": raw_rows,
            "native_predictions": native,
            "owner": owner,
            "counts": counts,
            "module_before": before,
            "module_after": model_hash(module),
            "RNG_unchanged": True,
            "peak_CUDA_allocated_bytes": torch.cuda.max_memory_allocated(),
            "new_parent_DINO_forwards": 0,
            "new_noise_draws": 0,
            "new_training_updates": 0,
            "scope": plan["scope"],
        },
    )
    save(
        ROOT / "status-v1.json",
        {
            "status": "completed-quality-awaiting-array-audit-render-and-viewing",
            "owner": owner,
            "counts": counts,
        },
    )
    print("Completed822 quality roots/4110 nested sampling calls/1644 RGB metric rows", flush=True)


def launch():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    assert not (ROOT / "launch-v1.json").exists() and not (ROOT / "review.claim").exists()
    env = dict(os.environ, PYTHONPATH=str(ROOT / "work/src") + ":" + str(ROOT / "work/scripts"))
    command = [
        str(REPO / ".venv/bin/python"),
        str(ROOT / "work/scripts/review_nonlocal_raw_trial.py"),
        "run",
    ]
    log = (ROOT / "review-v1.log").open("xb")
    child = subprocess.Popen(
        command, cwd=REPO, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
    )
    save(
        ROOT / "launch-v1.json",
        {
            "owner": {"pid": child.pid, "created": psutil.Process(child.pid).create_time()},
            "command": command,
            "plan": ref(ROOT / "plan-v1.json"),
        },
    )
    print("Launched", child.pid)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "run", "launch"])
    args = parser.parse_args()
    {"prepare": prepare, "run": run, "launch": launch}[args.mode]()
