"""Cross fixed actual V151/V152 proposal/support maps; no training or GT in output."""

import argparse
import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import psutil
from review_v146_window_transfer import relocated_controller_source
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import live

REPO = Path(__file__).resolve().parents[1]
METHODS = {
    "native-native": ("native", "native"),
    "relative-relative": ("relative", "relative"),
    "relative-native": ("relative", "native"),
    "native-relative": ("native", "relative"),
    "native-full": ("native", "full"),
    "relative-full": ("relative", "full"),
}
ORIGINALS = {"native-native", "relative-relative"}


def compose(base, proposal, support, colors, wb):
    """Fixed signed Malvar composition, with no target argument or learned work."""
    from demosaic.cfa import malvar

    if proposal.ndim != 4 or proposal.shape[1] != 4:
        raise ValueError("Expected four-phase packed proposal")
    n, _, h, w = proposal.shape
    if base.shape != (n, 3, 2 * h, 2 * w):
        raise ValueError("Parent/proposal shapes differ")
    if support is not None and support.shape != (n, 1, h, w):
        raise ValueError("Expected one spatial support channel")
    return base + malvar(proposal if support is None else proposal * support, colors, wb)


def prepare(root):
    import numpy as np
    import yaml

    assert not root.exists() and root.is_relative_to(REPO / ".cache")
    recipe = REPO / "configs/support-crossover-v152.yaml"
    config = yaml.safe_load(recipe.read_text())
    previous = Path(config["previous_trial"])
    old = read(previous / "plan-v1.json")
    guard(old)
    assert read(previous / "execution-completion-v1.json")["scientific_owner_count"] == 9
    assert read(previous / "native-viewing-v1.json")["primary_figures_covered"] == 72
    cases = read(previous / "quality-design-v1.json")["observations"]
    assert len(cases) == 822 and len({case["id"] for case in cases}) == 822
    expected = 0
    for case in cases:
        parent = np.load(case["parent"]["path"], mmap_mode="r")
        n, _, h, w = parent.shape
        expected += 4 * parent.nbytes + 2 * n * 5 * (h // 2) * (w // 2) * 4
    assert psutil.virtual_memory().available > 52 * 2**30
    assert shutil.disk_usage(REPO).free > 98 * 2**30 + expected
    assert shutil.disk_usage("/mnt/external").free > 208 * 2**30
    root.mkdir(parents=True)
    work = root / "work/scripts"
    work.mkdir(parents=True)
    script_names = [
        "score_support_crossover.py",
        "audit_support_crossover.py",
        "audit_support_crossover_reconstruction.py",
        "render_support_crossover.py",
        "report_checkpoint_pilot.py",
        "report_late_spectral_mixed_quiet.py",
    ]
    for name in script_names:
        shutil.copyfile(REPO / "scripts" / name, work / name)
    runner = work / Path(__file__).name
    runner.write_text(relocated_controller_source(Path(__file__).read_text(), REPO))
    review = read(previous / "review-result-v1.json")["collections"]
    adopted = {}
    for key in ["native", "relative"]:
        collection = review[config[f"{key}_endpoint"]]
        adopted[key] = {"collection": collection, "export": read(collection["path"])["export"]}
    save(
        root / "quality-design-v1.json",
        {
            "observations": cases,
            "endpoints": list(METHODS),
            "learned_forward_replays": 1644,
            "new_derived_output_arrays": 3288,
            "new_parent_DINO_forwards": 0,
            "new_noise_draws": 0,
            "scope": config["scope"],
        },
    )
    stages = [
        {
            "name": "review",
            "argv": [str(runner), "worker", str(root)],
            "result": str(root / "review-result-v1.json"),
        }
    ]
    stages += [
        {"name": name, "argv": [str(work / script), str(root)], "result": str(root / output)}
        for name, script, output in [
            ("scores", "score_support_crossover.py", "scores-v1.json"),
            ("metric-audit", "audit_support_crossover.py", "independent-metrics-audit-v1.json"),
            (
                "reconstruction-audit",
                "audit_support_crossover_reconstruction.py",
                "independent-reconstruction-v1.json",
            ),
            ("render", "render_support_crossover.py", "figures-v1.json"),
        ]
    ]
    plan = {
        "root": str(root),
        "previous": str(previous),
        "runner": ref(runner),
        "neural_work": old["work"],
        "work": str(work),
        "parent": old["parent"],
        "training_plan": ref(previous / "plan-v1.json"),
        "design": ref(root / "quality-design-v1.json"),
        "adopted": adopted,
        "methods": METHODS,
        "stages": stages,
        "expected_new_bytes": expected,
        "learned_forward_replays": 1644,
        "new_derived_arrays": 3288,
        "new_parent_DINO_forwards": 0,
        "new_noise_draws": 0,
        "inputs": [
            ref(recipe),
            ref(previous / "plan-v1.json"),
            ref(previous / "quality-design-v1.json"),
            ref(previous / "scores-v1.json"),
            ref(root / "quality-design-v1.json"),
        ]
        + [binding for item in adopted.values() for binding in item.values()]
        + [
            ref(root.parent / name)
            for name in [
                "collaborative-detail-v1/transfer-v1.py",
                "V144-V145-photo-supplement-v1/operator-v2.py",
                "collaborative-detail-v1/audit-transfer-v1.py",
            ]
        ],
        "frozen_files": {
            **old["frozen_files"],
            **{str(p): ref(p)["sha256"] for p in work.glob("*.py")},
        },
        "scope": config["scope"],
    }
    save(root / "plan-v1.json", plan)
    guard(plan)
    print(root / "plan-v1.json", "expected new GiB", expected / 2**30)


def worker(root):
    import numpy as np
    import torch
    from profile_raw_kernel_inference import model_hash

    from demosaic.late_spectral_matrix import LateSpectralMatrixDetail
    from demosaic.late_spectral_relative import LateSpectralRelativeDetail
    from demosaic.prediction_archive import fingerprint

    path = root / "plan-v1.json"
    plan = read(path)
    guard(plan)
    assert ref(__file__) == plan["runner"]
    assert (
        Path(LateSpectralMatrixDetail.forward.__code__.co_filename)
        .resolve()
        .is_relative_to(Path(plan["neural_work"]) / "src")
    )
    (root / "review.claim").open("x").close()
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
    cpu_rng, cuda_rng = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
    constructors = {"native": LateSpectralMatrixDetail, "relative": LateSpectralRelativeDetail}
    modules, archived, before = {}, {}, {}
    counts = dict.fromkeys(constructors, 0)
    for name, constructor in constructors.items():
        item = plan["adopted"][name]
        state = torch.load(item["export"]["path"], map_location="cpu", weights_only=True)
        assert (
            state["step"] == 1000
            and state["endpoint"] == "raw"
            and state["parent"] == plan["parent"]
        )
        module = constructor(**state["module_config"]).cuda().eval()
        module.load_state_dict(state["state_dict"], strict=True)
        module.register_forward_hook(
            lambda *args, name=name: counts.__setitem__(name, counts[name] + 1)
        )
        modules[name] = module
        before[name] = model_hash(module)
        collection = read(item["collection"]["path"])
        assert collection["module_before"] == collection["module_after"] == before[name]
        archived[name] = {o["id"]: o for o in collection["observations"]}
    output = root / "outputs-v1"
    output.mkdir(exist_ok=False)
    for method in METHODS:
        if method not in ORIGINALS:
            (output / method).mkdir()
    auxiliary = root / "auxiliary-v1"
    auxiliary.mkdir(exist_ok=False)
    observations = {method: [] for method in METHODS}
    journal = (root / "review-trace-v1.jsonl").open("x")
    for index, case in enumerate(read(plan["design"]["path"])["observations"]):
        assert (
            psutil.virtual_memory().available > 32 * 2**30
            and shutil.disk_usage(root).free > 96 * 2**30
        )
        assert shutil.disk_usage("/mnt/external").free > 208 * 2**30
        assert (
            ref(case["arrays"]["path"]) == case["arrays"]
            and ref(case["parent"]["path"]) == case["parent"]
        )
        arrays = dict(np.load(case["arrays"]["path"]))
        base = torch.from_numpy(np.load(case["parent"]["path"])).cuda()
        batch = {
            k: torch.from_numpy(arrays[k]).cuda() for k in ["packed", "variance", "colors", "wb"]
        }
        inputs = {k: fingerprint(arrays[k]) for k in batch}
        controls, proposals, maps, coefficient = {}, {}, {}, {}
        with torch.inference_mode():
            for name, module in modules.items():
                prediction, aux = module(base, **batch, return_aux=True)
                original = archived[name][case["id"]]
                assert original["parent"] == case["parent"] and original["inputs"] == inputs
                assert ref(original["prediction"]["path"]) == original["prediction"]
                np.testing.assert_array_equal(
                    prediction.cpu().numpy(), np.load(original["prediction"]["path"])
                )
                controls[name] = prediction
                proposals[name] = module.synthesis(aux["spectral_delta"], aux["geometry"])
                maps[name] = aux["support"]
                coefficient[name] = float(aux["spectral_delta"].abs().square().mean().sqrt())
                del aux
            dest = auxiliary / f"case-{index:03d}.npz"
            np.savez(
                dest,
                **{f"{key}_proposal": value.cpu().numpy() for key, value in proposals.items()},
                **{f"{key}_support": value.cpu().numpy() for key, value in maps.items()},
            )
            aux_ref = ref(dest)
            for method, (frequency, gate) in METHODS.items():
                support = None if gate == "full" else maps[gate]
                value = compose(base, proposals[frequency], support, batch["colors"], batch["wb"])
                assert torch.isfinite(value).all()
                if method in ORIGINALS:
                    assert torch.equal(value, controls[frequency])
                    binding = archived[frequency][case["id"]]["prediction"]
                else:
                    dest = output / method / f"prediction-{index:03d}.npy"
                    np.save(dest, value.cpu().numpy())
                    binding = ref(dest)
                observations[method].append(
                    {
                        "id": case["id"],
                        "prediction": binding,
                        "values": fingerprint(value.cpu().numpy()),
                        "parent": case["parent"],
                        "inputs": inputs,
                        "auxiliary": aux_ref,
                        "proposal": frequency,
                        "support_map": gate,
                        "support_mean": 1.0 if support is None else float(support.mean()),
                        "coefficient_correction_RMS": coefficient[frequency],
                        "module_forwards": int(method in ORIGINALS),
                        "derived_diagnostic": method not in ORIGINALS,
                    }
                )
                del value
        journal.write(
            json.dumps({"index": index, "id": case["id"], "counts": counts, "auxiliary": aux_ref})
            + "\n"
        )
        journal.flush()
        if index % 64 == 0:
            print(json.dumps({"done": index + 1, "counts": counts}), flush=True)
        del arrays, base, batch, controls, proposals, maps
    journal.close()
    assert counts == {"native": 822, "relative": 822}
    after = {key: model_hash(value) for key, value in modules.items()}
    assert (
        after == before
        and torch.equal(cpu_rng, torch.get_rng_state())
        and torch.equal(cuda_rng, torch.cuda.get_rng_state())
    )
    collections = {}
    for method, (frequency, support) in METHODS.items():
        dest = root / f"{method}-collection-v1.json"
        composition = {
            "proposal_export": plan["adopted"][frequency]["export"],
            "support_export": None if support == "full" else plan["adopted"][support]["export"],
            "policy": "original maps held fixed after their own original forwards",
            "full_support": support == "full",
        }
        save(
            dest,
            {
                "status": "completed-fixed-component-diagnostic",
                "plan": ref(path),
                "composition": composition,
                "module_before": before,
                "module_after": after,
                "RNG_unchanged": True,
                "observations": observations[method],
                "component_forwards": 822 if method in ORIGINALS else 0,
                "new_parent_DINO_forwards": 0,
                "new_noise_draws": 0,
            },
        )
        collections[method] = ref(dest)
    guard(plan)
    save(
        root / "review-result-v1.json",
        {
            "status": "completed-fixed-support-crossover-awaiting-audits-and-viewing",
            "plan": ref(path),
            "collections": collections,
            "component_forwards": 1644,
            "archived_predictions_exact": 1644,
            "new_derived_output_arrays": 3288,
            "additional_fixed_synthesis_calls": 1644,
            "additional_fixed_Malvar_calls": 4932,
            "new_parent_DINO_forwards": 0,
            "new_noise_draws": 0,
            "module_before": before,
            "module_after": after,
            "RNG_unchanged": True,
            "CUDA_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "scope": plan["scope"],
        },
    )


def controller(root):
    plan = read(root / "plan-v1.json")
    guard(plan)
    assert ref(__file__) == plan["runner"]
    (root / "controller.claim").open("x").close()
    state = {
        "plan": ref(root / "plan-v1.json"),
        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "completed": {},
    }
    child = owner = None
    try:
        for stage in plan["stages"]:
            guard(plan)
            while psutil.virtual_memory().available < 52 * 2**30:
                save(
                    root / "status-v1.json",
                    {**state, "status": "waiting-for-headroom", "stage": stage["name"]},
                )
                time.sleep(2)
            env = dict(
                os.environ,
                PYTHONPATH=f"{plan['neural_work']}/src:{plan['work']}:{plan['neural_work']}/scripts",
                OMP_NUM_THREADS="2",
                OPENBLAS_NUM_THREADS="1",
                MKL_NUM_THREADS="1",
                HF_HUB_OFFLINE="1",
                TRANSFORMERS_OFFLINE="1",
                CUDA_VISIBLE_DEVICES="0",
                CUBLAS_WORKSPACE_CONFIG=":4096:8",
            )
            with (root / f"{stage['name']}-v1.log").open("x") as log:
                child = subprocess.Popen(
                    [str(REPO / ".venv/bin/python"), "-P", *stage["argv"]],
                    cwd=root,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
                owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                save(
                    root / "status-v1.json",
                    {
                        **state,
                        "status": "running-fixed-stage",
                        "stage": stage["name"],
                        "child": owner,
                    },
                )
                elapsed, last = 0.0, time.monotonic()
                while child.poll() is None:
                    time.sleep(2)
                    now = time.monotonic()
                    if live(owner) and psutil.Process(child.pid).status() != psutil.STATUS_STOPPED:
                        elapsed += min(now - last, 5.0)
                    last = now
                    assert elapsed < 1800
                assert child.returncode == 0, stage["name"]
            assert not live(owner)
            state["completed"][stage["name"]] = {
                "owner": owner,
                "owner_exited": True,
                "result": ref(stage["result"]),
            }
        save(
            root / "status-v1.json",
            {**state, "status": "completed-audited-diagnostic-awaiting-native-viewing"},
        )
    except BaseException as error:
        if child is not None and child.poll() is None and live(owner):
            os.killpg(child.pid, signal.SIGTERM)
            child.wait(timeout=30)
        save(
            root / "status-v1.json",
            {**state, "status": "failed-preserved-no-automatic-retry", "error": repr(error)},
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "worker", "controller"])
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    {"prepare": prepare, "worker": worker, "controller": controller}[args.mode](
        args.root.absolute()
    )
