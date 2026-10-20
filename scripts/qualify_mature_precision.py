"""Freeze, preflight and serially run full paired mature FP32/hidden-FP16 quality."""

import argparse
import copy
import os
import shutil
import subprocess
import time
from pathlib import Path

import psutil
from train_directional_bank_trial import guard, read, ref, save

REPO = Path(__file__).resolve().parents[1]
PILOT = REPO / ".cache/benchmarks/mature-mixed-precision-CUDA-v1"
V92 = REPO / ".cache/benchmarks/late-rgb-head-only-v92-original4k-review-v1"


def prepare(root):
    import xml.etree.ElementTree as ET

    import numpy as np
    import torch
    import yaml

    from demosaic.data import CleanDataset
    from demosaic.suite import observation

    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not torch.cuda.is_initialized()
    test_path = Path("/mnt/external/demosaic/mature-full-precision-unit-tests-v2.xml")
    tests = ET.parse(test_path).getroot().find("testsuite")
    assert (
        tests.attrib["tests"] == "20" and tests.attrib["errors"] == tests.attrib["failures"] == "0"
    )
    torch.set_num_threads(2)
    pilot = read(REPO / "docs/results/mature-mixed-precision-CUDA-v1.json")
    assert pilot["selected_policy_for_separate_followup"] == "fp16-hidden"
    assert all(x["finite_screen_passed"] for x in pilot["policy_summaries"])
    assert pilot["actual_native_cells_viewed"] == 48
    for key in ["GPU_receipt", "actual_native_viewing", "scalar_review", "independent_Torch_audit"]:
        assert ref(pilot[key]["path"]) == pilot[key]
    original = read(PILOT / "plan.json")
    previous = read(V92 / "plan.json")
    root = root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    for folder in ["src/demosaic", "scripts"]:
        for p in (REPO / folder).glob("*.py"):
            target = work / folder / p.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, target)
    for name in [
        "pyproject.toml",
        "uv.lock",
        "configs/evaluation.yaml",
        "docs/mature-hidden-FP16-full-quality.md",
        "tests/test_mature_quality_pairs.py",
        "tests/test_mature_precision_tools.py",
    ]:
        target = work / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / name, target)
    protocol = yaml.safe_load((work / "configs/evaluation.yaml").read_text())
    manifest = ref(previous["manifests"]["full427"])
    dataset = CleanDataset(manifest["path"], split="val", patch_size=256, native_crop=True)
    assert len(dataset) == 427
    photo = {
        "manifest": manifest,
        "size": 256,
        "images": 427,
        "synthetic": 16,
        "batch": 2,
        "border": 8,
        "seed": protocol["seed"],
        "wb": protocol["white_balance"],
        "matrix": protocol["camera_to_srgb"],
        "patterns": protocol["patterns"],
        "conditions": protocol["conditions"],
        "source_ids": [r["id"] for r in dataset.rows],
    }
    inputs = [
        ref(test_path),
        ref(REPO / "docs/results/mature-mixed-precision-CUDA-v1.json"),
        *[
            pilot[k]
            for k in [
                "GPU_receipt",
                "actual_native_viewing",
                "scalar_review",
                "independent_Torch_audit",
            ]
        ],
        ref(PILOT / "plan.json"),
        ref(V92 / "final-review.json"),
        manifest,
    ]
    checkpoints = work / "checkpoints"
    checkpoints.mkdir()
    models = {}
    for name, item in original["models"].items():
        assert ref(item["path"])["sha256"] == item["sha256"]
        target = checkpoints / (name + ".pt")
        shutil.copyfile(item["path"], target)
        assert ref(target)["sha256"] == item["sha256"]
        models[name] = {**ref(target), "step": item["step"]}
        inputs.append(ref(target))
    for row in dataset.rows:
        inputs.append({"path": row["cache"], "sha256": row["cache_sha256"]})
    manifests = {k: ref(previous["manifests"][k]) for k in ["known", "unseen"]}
    for item in manifests.values():
        inputs.append(item)
        for case in read(item["path"])["cases"]:
            for crop in case["crops"]:
                inputs.append(
                    {
                        "path": str((Path(item["path"]).parent / crop["path"]).resolve()),
                        "sha256": crop["sha256"],
                    }
                )
    arrays = work / "inputs"
    arrays.mkdir()
    fixtures = []
    axis = torch.arange(256, dtype=torch.float32)[None, None, None]
    conditions = [c for c in protocol["conditions"] if c["name"] in ["adc-only", "iso12800-prior"]]
    specs = [
        ("carrier", l, c, p) for l in [0.01, 0.18] for c in [0.02, 0.1] for p in [4, 8, 16]
    ] + [("flat", l, 0, None) for l in [0.01, 0.18]]
    for kind, level, contrast, period in specs:
        rgb = torch.full((4, 3, 256, 256), level)
        if kind == "carrier":
            rgb *= 1 + contrast * torch.cos(2 * torch.pi * axis / period)
        ids = [
            f"carrier-l{level}-c{contrast}-p{period}-draw{i}"
            if kind == "carrier"
            else f"flat-l{level}-draw{i}"
            for i in range(4)
        ]
        for condition in conditions:
            groups = []
            if condition["name"] == "adc-only":
                obs = [
                    observation(
                        rgb[:1], ids[:1], condition, p, photo["wb"], photo["matrix"], 20261016
                    )
                    for p in photo["patterns"]
                ]
                host = {k: torch.cat([v[k] for v in obs]) for k in obs[0]}
                groups.append(
                    (
                        "all-CFAs",
                        host,
                        [
                            {"pattern": p, "draw": 0, "draw_aliases": [0, 1, 2, 3]}
                            for p in photo["patterns"]
                        ],
                    )
                )
            else:
                for pattern in photo["patterns"]:
                    host = observation(
                        rgb, ids, condition, pattern, photo["wb"], photo["matrix"], 20261016
                    )
                    groups.append(
                        (
                            pattern,
                            host,
                            [
                                {"pattern": pattern, "draw": i, "draw_aliases": [i]}
                                for i in range(4)
                            ],
                        )
                    )
            for suffix, host, cases in groups:
                name = f"{condition['name']}-{kind}-{level}-{contrast}-{period}-{suffix}"
                path = arrays / (name + ".npz")
                np.savez(path, **{k: v.numpy() for k, v in host.items()})
                fixtures.append(
                    {
                        "id": name,
                        "kind": kind,
                        "level": level,
                        "contrast": contrast,
                        "period": period,
                        "condition": condition,
                        "cases": cases,
                        "arrays": ref(path),
                    }
                )
                inputs.append(ref(path))
    assert (
        len(fixtures) == 70
        and sum(len(c["draw_aliases"]) for f in fixtures for c in f["cases"]) == 448
    )
    hue = previous["hue_inputs"]
    inputs.append(hue)
    grid = read(hue["path"])
    previews = list(grid["native_preview_cases"])
    for h, saturation, peak in [
        (30, 0.5, 0.9),
        (315, 0.5, 0.9),
        (30, 0.98, 0.18),
        (315, 0.98, 0.18),
    ]:
        chosen = [
            i
            for i, c in enumerate(grid["cases"])
            if c["source"]["hue_degrees"] == h
            and c["source"]["saturation"] == saturation
            and c["source"]["peak"] == peak
            and c["condition"]["name"] == "iso12800-prior"
            and c["pattern"] == "RGGB"
        ]
        assert len(chosen) == 1
        previews += chosen
    assert len(previews) == len(set(previews)) == 7
    inputs += [{"path": c["arrays"], "sha256": c["sha256"]} for c in grid["cases"]]
    highlight = previous["highlight_inputs"]
    inputs.append(highlight)
    inputs += [
        {"path": c["arrays"], "sha256": c["sha256"]} for c in read(highlight["path"])["cases"]
    ]
    gfx_registry = ref(
        "/mnt/external/demosaic/benchmarks/mature-cudnn-autotune-v2/native/report.json"
    )
    inputs += [original["gfx_fixture"], original["fixtures"][0]["arrays"], gfx_registry]
    # Retain the fixed pilot's complete preflight observations and matching outputs.
    pilot_preflight = [original["fixtures"][i] for i in [0, 1, 2, 27, 28]]
    inputs += [f["arrays"] for f in pilot_preflight]
    inputs += [
        r["RGB"]
        for m in read(pilot["GPU_receipt"]["path"])["models"]
        for r in m["captures"]
        if r["policy"] in ["fp32", "fp16-hidden"]
        and r["fixture"] in {f["id"] for f in pilot_preflight}
    ]
    owners = []
    for folder in [V92, PILOT]:
        state = read(folder / ("status.json" if folder == V92 else "controller-status.json"))
        owners += [state[k] for k in ["controller", "child"] if k in state]
    for key in ["closure_owner", "reference_owner"]:
        owners.append(read(V92 / "queue-launch.json")[key])
    owners.append(read(V92 / "report-assets-status.json")["controller"])
    unique = {}
    for item in inputs:
        assert unique.setdefault(item["path"], item) == item, (
            "One path has conflicting input hashes"
        )
    plan = {
        "root": str(root),
        "work": str(work),
        "output": str(work / "outputs"),
        "models": models,
        "original_models": original["models"],
        "python": str(REPO / ".venv/bin/python3"),
        "HF_HOME": original["HF_HOME"],
        "photo": photo,
        "camera_manifests": manifests,
        "analytic": fixtures,
        "hue": hue,
        "hue_preview_indices": previews,
        "highlights": highlight,
        "gfx_fixture": original["gfx_fixture"],
        "gfx_observation": original["fixtures"][0]["arrays"],
        "gfx_registry": gfx_registry,
        "pilot": ref(REPO / "docs/results/mature-mixed-precision-CUDA-v1.json"),
        "unit_tests": {"JUnit": ref(test_path), "passed": 20},
        "pilot_GPU": pilot["GPU_receipt"],
        "pilot_preflight": pilot_preflight,
        "worker": ref(work / "scripts/qualify_mature_precision.py"),
        "blocking_owners": owners,
        "inputs": list(unique.values()),
        "frozen_files": {
            str(p): ref(p)["sha256"]
            for p in work.rglob("*")
            if p.is_file() and not p.is_relative_to(arrays) and not p.is_relative_to(checkpoints)
        },
        "scope": "Separate full paired quality qualification of original V43/V63 under FP32 and selected hidden-FP16; no training/export/default/full-frame continuation. One original model at a time, each complete observation reused for both policies. All cases retained despite numerical gate failures. Actual132-cell native viewing and independent scalar review precede qualification; actual100MP16-bit study requires a subsequent separate freeze.",
    }
    save(root / "plan.json", plan)
    guard(plan)
    print(
        {
            "plan": ref(root / "plan.json"),
            "analytic_physical_observations": 280,
            "hue_observations": 1176,
            "frozen_files": len(plan["frozen_files"]),
            "inputs": len(plan["inputs"]),
        }
    )


def worker(plan_path, mode, label=None):
    import numpy as np
    import torch
    from mature_quality_fields import analytic_panel, gfx_panel, highlight_panel, hue_panel
    from mature_quality_pairs import (
        KEYS,
        PairRunner,
        camera_panel,
        load_arrays,
        photo_dataset,
        photo_panel,
        physical_rows,
        save_new,
    )
    from profile_raw_kernel_inference import model_hash

    from demosaic.inference import load_checkpoint
    from demosaic.precision import amp_context
    from demosaic.suite import observation

    plan = read(plan_path)
    guard(plan)
    assert ref(__file__) == plan["worker"]
    cpu = mode == "CPU"
    device = torch.device("cpu") if cpu else torch.device("cuda", torch.cuda.current_device())
    torch.set_num_threads(2 if cpu else 4)
    if cpu:
        assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not torch.cuda.is_initialized()
    previous = None
    if not cpu:
        previous = (
            torch.backends.cudnn.benchmark,
            torch.backends.cudnn.benchmark_limit,
            torch.cuda.get_per_process_memory_fraction(device),
        )
        torch.cuda.set_per_process_memory_fraction(
            min(previous[2], 16 * 2**30 / torch.cuda.get_device_properties(device).total_memory),
            device,
        )
        torch.backends.cudnn.benchmark, torch.backends.cudnn.benchmark_limit = True, 10
    results = []
    output = Path(plan["output"])
    output.mkdir(parents=True, exist_ok=True)
    try:
        for name, checkpoint in plan["models"].items():
            if label is not None and name != label:
                continue
            model, state = load_checkpoint(checkpoint["path"], device)
            assert (
                state["loaded_sha256"] == checkpoint["sha256"]
                and state["step"] == checkpoint["step"]
            )
            del state
            model.eval()
            if not cpu:
                model.to(memory_format=torch.channels_last)
            expected_model = next(
                m for m in read(plan["pilot_GPU"]["path"])["models"] if m["model"] == name
            )
            assert model_hash(model) == expected_model["model_sha256"]
            assert model_hash(model.context.backbone) == expected_model["DINO_sha256"]
            folder = output / (mode + "-" + name)
            folder.mkdir(exist_ok=False)
            direct = None
            if cpu:
                opt = plan["photo"]
                data = photo_dataset(dict(opt, size=64))
                host = observation(
                    data[0]["rgb"][None],
                    [data.rows[0]["id"]],
                    opt["conditions"][0],
                    "RGGB",
                    opt["wb"],
                    opt["matrix"],
                    opt["seed"],
                )
                model.set_noise(0, 0)
                with torch.inference_mode(), amp_context("cpu", dtype="float32"):
                    direct = model(*(host[k] for k in KEYS)).numpy().copy()
            runner = PairRunner(model, name, checkpoint, device, engineering=cpu)
            parity = []
            if cpu:
                predicted, _ = runner(host, plan["photo"]["conditions"][0])
                assert predicted["fp32"].numpy().tobytes() == direct.tobytes()
                small = copy.deepcopy(plan)
                small["photo"].update(
                    size=64,
                    images=2,
                    synthetic=1,
                    batch=1,
                    conditions=[
                        c
                        for c in small["photo"]["conditions"]
                        if c["name"] in ["adc-only", "iso12800-prior"]
                    ],
                )
                photo_panel(runner, small, folder / "photo")
            elif mode == "GPU-preflight":
                original = next(
                    m for m in read(plan["pilot_GPU"]["path"])["models"] if m["model"] == name
                )
                records = {(r["policy"], r["fixture"]): r for r in original["captures"]}
                for i, fixture in enumerate(plan["pilot_preflight"]):
                    host = load_arrays(fixture["arrays"])
                    predicted, _ = runner(host, fixture["condition"])
                    for policy, value in predicted.items():
                        path = folder / f"fixture{i}-{policy}.npy"
                        np.save(path, value.numpy(), allow_pickle=False)
                        prior = np.load(
                            records[policy, fixture["id"]]["RGB"]["path"], allow_pickle=False
                        )
                        differences = physical_rows(torch.from_numpy(prior), value)
                        passed = all(
                            r["max_abs_DN16"] <= 1 and r["RMS_DN16"] <= 0.25 for r in differences
                        )
                        parity.append(
                            {
                                "fixture": fixture["id"],
                                "policy": policy,
                                "RGB": ref(path),
                                "matching_policy_pilot_RGB": records[policy, fixture["id"]]["RGB"],
                                "differences_DN16": differences,
                                "matching_policy_parity_pass": passed,
                            }
                        )
                        save(folder / "preflight-progress.json", parity)
                        if not passed:
                            raise ValueError(
                                f"Matching-policy pilot parity failed: {name}/{fixture['id']}/"
                                f"{policy}; prediction and differences preserved"
                            )
            else:
                assert mode == "quality"
                stages = ["known", "unseen", "photo", "analytic", "hue", "gfx", "highlights"]
                for stage in stages:
                    save(
                        output / (name + "-progress.json"),
                        {
                            "model": name,
                            "stage": stage,
                            "owner": {
                                "pid": os.getpid(),
                                "created": psutil.Process().create_time(),
                            },
                        },
                    )
                    if stage in ["known", "unseen"]:
                        camera_panel(runner, plan["camera_manifests"][stage], folder / stage)
                    elif stage == "photo":
                        photo_panel(runner, plan, folder / stage)
                    elif stage == "analytic":
                        analytic_panel(runner, plan["analytic"], folder / stage)
                    elif stage == "hue":
                        hue_panel(runner, plan["hue"], plan["hue_preview_indices"], folder / stage)
                    elif stage == "gfx":
                        gfx_panel(
                            runner,
                            plan["gfx_fixture"],
                            plan["gfx_observation"],
                            plan["gfx_registry"],
                            folder / stage,
                        )
                    else:
                        highlight_panel(runner, plan["highlights"], folder / stage)
            result = {
                **runner.finish(),
                "mode": mode,
                "engineering_only": mode != "quality",
                "direct_FP32_control_forward": cpu,
                "direct_control_forwards": int(cpu),
                "matching_policy_pilot_replay": parity,
            }
            if cpu:
                assert result["actual_forwards"] == 50 and result["policy_observations"] == 50
            elif mode == "GPU-preflight":
                assert result["actual_forwards"] == 10 and result["policy_observations"] == 28
            else:
                assert result["policy_observations"] == 28056
                expected_pairs = ((443 + 1) // 2) * 28 + 70 + 1176 + 1 + 2
                expected_pairs += sum(
                    (len(c["crops"]) + 3) // 4
                    for m in plan["camera_manifests"].values()
                    for c in read(m["path"])["cases"]
                )
                assert result["actual_forwards"] == 2 * expected_pairs
            save_new(folder / "receipt.json", result)
            results.append(result)
            del runner, model
            if not cpu:
                torch.cuda.empty_cache()
    finally:
        if previous:
            torch.backends.cudnn.benchmark, torch.backends.cudnn.benchmark_limit = previous[:2]
            torch.cuda.set_per_process_memory_fraction(previous[2], device)
    guard(plan)
    save_new(
        output / (mode + ("-" + label if label else "") + "-receipt.json"),
        {
            "status": "completed-full-precision-" + mode + "-awaiting-review",
            "plan": ref(plan_path),
            "models": results,
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "CUDA_initialized": torch.cuda.is_initialized(),
            "backend_settings_restored": True,
            "scope": "Discarded execution proof only"
            if mode != "quality"
            else "Complete paired-policy quality arrays/scores only; actual native/independent scalar review and qualification decision remain required",
        },
    )


def alive(owner):
    try:
        p = psutil.Process(owner["pid"])
        return p.create_time() == owner["created"] and p.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def controller(plan_path):
    from queue_tf32x3_cuda import stop_owned

    plan = read(plan_path)
    root = Path(plan["root"])
    guard(plan)
    with (root / "controller.claim").open("x") as stream:
        stream.write(str(os.getpid()))
    state = {
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "plan": ref(plan_path),
        "completed": [],
    }
    child = None

    def record(status, **extra):
        state.update(status=status, updated_unix=time.time(), **extra)
        save(root / "controller-status.json", state)

    def resources(ram):
        return (
            psutil.virtual_memory().available >= ram * 2**30
            and shutil.disk_usage(root).free >= 64 * 2**30
            and shutil.disk_usage("/mnt/external").free >= 500 * 2**30
        )

    def headroom():
        began = time.monotonic()
        stable = None
        record("waiting-for-stable-full-quality-headroom")
        while True:
            assert time.monotonic() - began < 3600
            if resources(48):
                stable = time.monotonic() if stable is None else stable
            else:
                stable = None
            if stable is not None and time.monotonic() - stable >= 60:
                return
            time.sleep(5)

    try:
        assert not any(alive(o) for o in plan["blocking_owners"])
        for mode, label in [
            ("CPU", None),
            ("GPU-preflight", None),
            ("quality", "V43"),
            ("quality", "V63"),
        ]:
            if mode != "CPU":
                headroom()
            guard(plan)
            assert resources(48)
            work = Path(plan["work"])
            env = dict(
                os.environ,
                CUDA_VISIBLE_DEVICES="" if mode == "CPU" else "0",
                HF_HOME=plan["HF_HOME"],
                HF_HUB_OFFLINE="1",
                TRANSFORMERS_OFFLINE="1",
                OMP_NUM_THREADS="2" if mode == "CPU" else "4",
                OPENBLAS_NUM_THREADS="2" if mode == "CPU" else "4",
                PYTHONPATH=str(work / "src") + ":" + str(work / "scripts"),
            )
            name = mode + ("-" + label if label else "")
            with (root / (name + ".log")).open("xb") as log:
                args = [plan["python"], "-P", plan["worker"]["path"], mode, str(plan_path)] + (
                    ["--label", label] if label else []
                )
                child = subprocess.Popen(
                    args,
                    cwd=work,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                record("running-full-precision-" + name, child=owner)
                deadline = time.monotonic() + (7200 if mode == "quality" else 1800)
                while child.poll() is None:
                    if time.monotonic() > deadline or not resources(24):
                        raise RuntimeError(
                            "Owned full-quality worker reached resource/runtime bound; no retry"
                        )
                    time.sleep(2)
                assert child.wait() == 0
            receipt = Path(plan["output"]) / (name + "-receipt.json")
            outcome = read(receipt)
            assert outcome["owner"] == owner and outcome["backend_settings_restored"]
            if mode == "CPU":
                assert not outcome["CUDA_initialized"]
            state["completed"].append(name)
            record("completed-full-precision-" + name, receipt=ref(receipt))
        guard(plan)
        record(
            "completed-full-precision-quality-arrays-awaiting-native-and-independent-scalar-review"
        )
    except BaseException as error:
        if child is not None and child.poll() is None:
            stop_owned(child, state["child"])
        record("failed-full-precision-quality-preserved-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "CPU", "GPU-preflight", "quality", "run"])
    parser.add_argument("path", type=Path)
    parser.add_argument("--label", choices=["V43", "V63"])
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.path)
    elif args.mode == "run":
        controller(args.path.resolve())
    else:
        worker(args.path.resolve(), args.mode, args.label)
