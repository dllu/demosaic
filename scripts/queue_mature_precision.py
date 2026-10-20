"""Freeze and queue one bounded precision pilot after all exact V92 review owners."""

import argparse
import os
import shutil
import subprocess
import time
from pathlib import Path

import psutil
from queue_tf32x3_cuda import stop_owned
from review_directional_bank import alive
from train_directional_bank_trial import guard, read, ref, save

REPO = Path(__file__).resolve().parents[1]
REVIEW = REPO / ".cache/benchmarks/late-rgb-head-only-v92-original4k-review-v1"
TRAINING = Path("/mnt/external/demosaic/experiments/late-rgb-head-only-v92-original4k-v1")
CPU_COMPLETE = "completed-genuine-mature-precision-CPU-engineering-no-quality-or-speed-result"


def prepare(root, cpu_receipt):
    import numpy as np
    import torch
    import yaml

    from demosaic.suite import observation

    assert not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    cpu = read(cpu_receipt)
    assert cpu["status"] == CPU_COMPLETE and not cpu["CUDA_initialized"] and not alive(cpu["owner"])
    assert cpu["common_forwards"] == 76
    cpu_plan = read(cpu["plan"]["path"])
    assert ref(cpu["plan"]["path"]) == cpu["plan"]
    guard(cpu_plan)
    for model in cpu["models"]:
        assert (
            model["explicit_FP32_hidden_identity_exact"]
            and model["CPU_repeat_exact"]
            and model["state_parameter_config_RNG_exact"]
        )
    root = root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    trained = Path(cpu_plan["work"])
    for source in trained.glob("src/demosaic/*.py"):
        target = work / "src/demosaic" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for source in (REPO / "scripts").glob("*.py"):
        target = work / "scripts" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for name in [
        "pyproject.toml",
        "uv.lock",
        "configs/evaluation.yaml",
        "docs/mature-mixed-precision-pilot.md",
    ]:
        target = work / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(trained / name, target)
    for name in ["mature_precision_tools.py", "preflight_mature_precision.py"]:
        assert ref(work / "scripts" / name)["sha256"] == ref(trained / "scripts" / name)["sha256"]
    for source in (REPO / "src/demosaic").glob("*.py"):
        assert source.read_bytes() == (work / "src/demosaic" / source.name).read_bytes()
    gfx_path = Path(
        "/mnt/external/demosaic/benchmarks/packed-isotropic-compilation-inputs-v1/inputs.json"
    )
    gfx = read(gfx_path)
    # The standing fixture carries the actual measured noise prior.
    condition = {
        "name": "GFX-input-only",
        "shot": gfx["conditioning"]["shot"],
        "read": gfx["conditioning"]["read"],
    }
    fixtures = [
        {
            "id": "GFX-four-native512-contexts",
            "kind": "gfx",
            "arrays": gfx["serving_probes"][0]["observation"],
            "condition": condition,
        }
    ]
    photo_plan_path = Path("/mnt/external/demosaic/benchmarks/mature-cudnn-GT-photos-v1/plan.json")
    photo = read(photo_plan_path)
    protocol = yaml.safe_load((work / "configs/evaluation.yaml").read_text())
    noisy = next(c for c in protocol["conditions"] if c["name"] == "iso12800-prior")
    photos = [r for r in photo["inputs"] if r["path"].endswith(".npz")]
    assert len(photos) == 2
    fixtures += [
        {"id": f"photo-{i}", "kind": "photo", "arrays": r, "condition": noisy}
        for i, r in enumerate(photos)
    ]
    component_path = Path(
        "/mnt/external/demosaic/experiments/late-rgb-detail-components-v1/plan.json"
    )
    component = read(component_path)
    fixtures += [{**f, "kind": "analytic", "signal_kind": f["kind"]} for f in component["fixtures"]]
    assert (
        len(component["fixtures"]) == 24
        and sum(len(f["cases"]) for f in component["fixtures"]) == 96
    )
    y, x = torch.meshgrid(torch.arange(256), torch.arange(256), indexing="ij")
    rgb = torch.stack(
        (
            0.05 + 0.4 * (x + y / 256) / 256,
            0.08 + 0.3 * y / 256,
            0.18 * (1 + 0.02 * torch.cos(2 * torch.pi * x / 4)),
        )
    )[None]
    adc = next(c for c in protocol["conditions"] if c["name"] == "adc-only")
    patterns = ["RGGB", "BGGR", "GRBG", "GBRG"]
    observations = [
        observation(
            rgb,
            ["fixed-mature-native-ramp"],
            adc,
            p,
            protocol["white_balance"],
            protocol["camera_to_srgb"],
            20261020,
        )
        for p in patterns
    ]
    batch = {
        key: torch.stack([r[key] for r in observations])
        if key == "colors" and observations[0][key].ndim == 1
        else torch.cat([r[key] for r in observations])
        for key in ["packed", "variance", "colors", "wb", "matrix"]
    }
    (work / "inputs").mkdir()
    for variant in ["base", "plus-one-DN"]:
        values = dict(batch)
        if variant != "base":
            values["packed"] = values["packed"] + 1 / 65535
            assert values["packed"].max() < 1
        path = work / "inputs" / ("native-ramp-" + variant + ".npz")
        np.savez(path, **{k: v.numpy() for k, v in values.items()})
        fixtures.append(
            {
                "id": "native-ramp-" + variant,
                "kind": "ramp",
                "patterns": patterns,
                "variant": variant,
                "arrays": ref(path),
                "condition": adc,
            }
        )
    queue = read(REVIEW / "queue-launch.json")
    package = read(REVIEW / "report-assets-launch.json")
    training = read(TRAINING / "status.json")
    review = read(REVIEW / "plan.json")
    assert queue["plan"] == ref(REVIEW / "plan.json")
    assert review["training_plan"] == ref(TRAINING / "plan.json") == training["plan"]
    assert review["training_owner"] == training["controller"]
    assert package["plan"] == ref(REVIEW / "report-assets-plan.json")
    owners = [
        training["controller"],
        training["child"],
        *[queue[k] for k in ["review_owner", "closure_owner", "reference_owner"]],
        {k: package[k] for k in ["pid", "created"]},
    ]
    plan = {
        "root": str(root),
        "work": str(work),
        "output": str(work / "GPU-output"),
        "models": cpu_plan["models"],
        "fixtures": fixtures,
        "CPU_preflight": ref(cpu_receipt),
        "worker": ref(work / "scripts/probe_mature_precision_cuda.py"),
        "controller": ref(work / "scripts/queue_mature_precision.py"),
        "python": cpu_plan["python"],
        "HF_HOME": cpu_plan["HF_HOME"],
        "predecessor_root": str(REVIEW),
        "predecessor_training_status": str(TRAINING / "status.json"),
        "blocking_owners": owners,
        "predecessor_owners": {
            "training": training["controller"],
            "training_child": training["child"],
            "review": queue["review_owner"],
            "closure": queue["closure_owner"],
            "package": {k: package[k] for k in ["pid", "created"]},
        },
        "predecessor_plans": {
            "training": training["plan"],
            "review": queue["plan"],
            "closure": queue["closure_plan"],
            "package": package["plan"],
        },
        "gfx_fixture": ref(gfx_path),
        "photo_registry": ref(
            "/mnt/external/demosaic/benchmarks/mature-cudnn-GT-photos-v1/V43-original/result.json"
        ),
        "protocol": ref(work / "docs/mature-mixed-precision-pilot.md"),
        "inputs": [
            *cpu_plan["inputs"],
            ref(cpu_receipt),
            cpu["plan"],
            ref(REVIEW / "plan.json"),
            ref(REVIEW / "queue-launch.json"),
            ref(REVIEW / "report-assets-plan.json"),
            ref(REVIEW / "report-assets-launch.json"),
            ref(gfx_path),
            ref(photo_plan_path),
            ref(component_path),
            ref(
                "/mnt/external/demosaic/benchmarks/mature-cudnn-GT-photos-v1/V43-original/result.json"
            ),
            *[f["arrays"] for f in fixtures],
        ],
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "scope": "One fixed three-policy/two-mature-model precision screen after exact successful V92 workflow exits. No GPU overlap, training, full-frame continuation, export, default change, automatic retry or promotion.",
    }
    guard(plan)
    save(root / "plan.json", plan)
    print({"plan": ref(root / "plan.json"), "fixtures": len(fixtures), "observations": 110})


def predecessor_ready(plan):
    root = Path(plan["predecessor_root"])
    statuses = [
        read(root / name)
        for name in ["status.json", "closure-status.json", "report-assets-status.json"]
    ]
    training = read(plan["predecessor_training_status"])
    expected = plan["predecessor_owners"]
    assert (
        training["controller"] == expected["training"]
        and training["child"] == expected["training_child"]
    )
    assert [s["controller"] for s in statuses] == [
        expected[k] for k in ["review", "closure", "package"]
    ]
    assert training["plan"] == plan["predecessor_plans"]["training"]
    assert [s["plan"] for s in statuses] == [
        plan["predecessor_plans"][k] for k in ["review", "closure", "package"]
    ]
    if any(s["status"].startswith("failed-") for s in [training, *statuses]):
        raise RuntimeError("A preceding V92 job failed; no new precision GPU work or retry")
    owners = plan["blocking_owners"] + [s["child"] for s in statuses if s.get("child")]
    if any(alive(o) for o in owners):
        return False
    assert (
        training["status"]
        == "completed-original4000-head-only-awaiting-full-quality-and-native-review"
    )
    assert (
        statuses[0]["status"]
        == "completed-directional-bank-inference-awaiting-statistical-and-manual-native-closure"
    )
    assert (
        set(statuses[0]["completed"])
        == {
            "boundary",
            "known",
            "unseen",
            "full427",
            "statistics",
            "sensitivity",
            "gfx",
            "analytic",
            "hue",
            "highlights",
        }
        and len(statuses[0]["completed"]) == 10
    )
    assert (
        statuses[1]["status"]
        == "completed-CPU-numerical-and-native-board-preparation-awaiting-manual-review"
    )
    assert statuses[2]["status"] == "prepared-native-report-assets-awaiting-manual-inspection"
    assert ref(statuses[2]["result"]["path"]) == statuses[2]["result"]
    package = read(statuses[2]["result"]["path"])
    assert package["native_cells_verified"] == 125 and package["source_triplets_verified"] == 81
    assert len(package["selected_triplets"]) == 12 and len(package["all_boards"]) == 8
    return True


def run(path):
    path = path.resolve()
    plan = read(path)
    assert ref(__file__) == plan["controller"]
    root = Path(plan["root"])
    with (root / "controller.claim").open("x") as stream:
        stream.write(str(os.getpid()))
    status = {
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "plan": ref(path),
    }
    child = None

    def record(value, **fields):
        status.update(status=value, updated_unix=time.time(), **fields)
        save(root / "controller-status.json", status)

    def resources(ram):
        return (
            psutil.virtual_memory().available >= ram * 2**30
            and shutil.disk_usage(REPO).free >= 64 * 2**30
            and shutil.disk_usage("/mnt/external").free >= 500 * 2**30
        )

    try:
        guard(plan)
        record("waiting-for-exact-V92-training-review-closure-reference-package-exits")
        deadline = time.monotonic() + 43200
        while not predecessor_ready(plan):
            assert time.monotonic() < deadline, "Predecessor wait bound exhausted; no retry"
            time.sleep(5)
        record("waiting-for-stable-precision-pilot-headroom")
        started, stable = time.monotonic(), None
        while True:
            assert time.monotonic() - started < 3600, "Resource wait bound exhausted; no retry"
            now = time.monotonic()
            stable = now if stable is None and resources(48) else stable if resources(48) else None
            if stable is not None and now - stable >= 60:
                break
            time.sleep(5)
        guard(plan)
        assert predecessor_ready(plan) and not Path(plan["output"]).exists()
        work = Path(plan["work"])
        env = dict(
            os.environ,
            CUDA_VISIBLE_DEVICES="0",
            HF_HOME=plan["HF_HOME"],
            HF_HUB_OFFLINE="1",
            TRANSFORMERS_OFFLINE="1",
            OMP_NUM_THREADS="4",
            OPENBLAS_NUM_THREADS="4",
            PYTHONPATH=str(work / "src") + ":" + str(work / "scripts"),
        )
        with (root / "GPU-worker.log").open("xb") as log:
            child = subprocess.Popen(
                [plan["python"], "-P", plan["worker"]["path"], str(path)],
                cwd=work,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
            record("running-fixed-mature-precision-pilot", child=owner)
            deadline = time.monotonic() + 900
            while child.poll() is None:
                if time.monotonic() > deadline or not resources(24):
                    raise RuntimeError(
                        "Owned precision pilot reached runtime/resource bound; no retry"
                    )
                time.sleep(2)
            assert child.wait() == 0
        guard(plan)
        receipt = Path(plan["output"]) / "receipt.json"
        result = read(receipt)
        assert result["owner"] == owner and result["backend_settings_restored"]
        record(
            "completed-mature-precision-pilot-arrays-awaiting-native-and-independent-scalar-review",
            receipt=ref(receipt),
        )
    except BaseException as error:
        if child is not None and child.poll() is None:
            stop_owned(child, status["child"])
        record("failed-mature-precision-pilot-preserved-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    p = modes.add_parser("prepare")
    p.add_argument("root", type=Path)
    p.add_argument("cpu_receipt", type=Path)
    p = modes.add_parser("run")
    p.add_argument("plan", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.root, args.cpu_receipt)
    else:
        run(args.plan)
