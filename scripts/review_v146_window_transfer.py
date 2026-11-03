"""Isolate inference Fourier-window transfer with unchanged V146 weights."""

import argparse
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import psutil
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import live

REPO = Path(__file__).resolve().parents[1]
BASE = REPO / ".cache/quality-20261103/V146-coherent-frequency-v1"
NAMES = ("packed", "variance", "colors", "wb", "matrix")


def relocated_controller_source(source, repo):
    """Relocate only the assignment, leaving quoted source-generation code intact."""
    assignment = '\nREPO = Path(__file__).resolve().parents[1]\n'
    if source.count(assignment) != 1:
        raise ValueError("Expected exactly one repository-root assignment")
    result = source.replace(assignment, f'\nREPO = Path({str(repo)!r})\n', 1)
    compile(result, "<frozen-controller>", "exec")
    return result


def prepare(root):
    import numpy as np
    import torch

    from demosaic.prediction_archive import fingerprint
    from demosaic.suite import observation

    torch.set_num_threads(1)
    assert not torch.cuda.is_initialized()
    root = root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    root.mkdir(parents=True, exist_ok=False)
    previous = BASE / "review-v1"
    old = read(previous / "queue-plan-v1.json")
    training = read(BASE / "plan.json")
    assert old["training_plan"] == ref(BASE / "plan.json")
    guard(training)
    for phase in ("CPU", "CUDA", "train"):
        assert not live(read(BASE / f"{phase}-V146-result.json")["owner"])
    endpoints = read(previous / "endpoint-verification-v1.json")["endpoints"]
    collections = {k: read(previous / k / "collection-v1.json") for k in endpoints}
    predictions = {
        k: {v["id"]: v["prediction"] for v in c["observations"]}
        for k, c in collections.items()
    }
    originals = old["observations"]
    selected = [o for o in originals if min(o["output_shape"][-2:]) >= 512]
    assert len(originals) == 694 and len(selected) == 582
    palettes = [
        o for o in originals if o["kind"] == "flat" and o["id"].endswith("adc-only-RGGB")
    ]
    assert len(palettes) == 6
    conditions = [
        {"name": "adc-only", "shot": 0.0, "read": 0.0, "exposure": 1.0},
        {"name": "iso6400-prior", "shot": 0.00128, "read": 6.5536e-6, "exposure": 1.0},
        {"name": "iso12800-prior", "shot": 0.00256, "read": 2.62144e-5, "exposure": 1.0},
    ]
    lock = {
        "operator": ref(__file__),
        "base_git_commit": "93e0f69",
        "original_queue": ref(previous / "queue-plan-v1.json"),
        "original_endpoints": endpoints,
        "training_plan": ref(BASE / "plan.json"),
        "window_trained_packed": 128,
        "window_transfer_packed": 256,
        "new_training_updates": 0,
        "selected_reused_contexts": 582,
        "short_context_bypasses_per_transfer": 112,
        "fresh_flat_native_size": 512,
        "fresh_flat_palettes": [o["case"]["source"] for o in palettes],
        "fresh_flat_conditions": conditions,
        "fresh_flat_noise_seed": 2026110302,
        "planned_new_observation_draws": 72,
        "planned_new_root_forwards": 1524,
        "scope": "Inference-only packed128→256 Fourier geometry transfer, both raw and EMA "
        "V146 weights unchanged. Reuse694 prior inputs/controls; execute582 fitting contexts "
        "per transfer and bypass112 shorter contexts to their exact original predictions. "
        "Add72 fresh512 analytic flats:6 palettes×4CFAs×3 priors, tested with all5 endpoints. "
        "Fresh noise, not new independent photographs. No resize/upsampling, training, "
        "periodic correction, RAW decode or dataz access. Real ISO100/JPEG references are not GT.",
    }
    save(root / "design-lock-v1.json", lock)
    frozen_controller = root / "controller-v1.py"
    frozen_controller.write_text(relocated_controller_source(Path(__file__).read_text(), REPO))
    shared = root / "shared"
    for directory in ("src", "scripts"):
        shutil.copytree(
            previous / "work" / directory,
            shared / directory,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
    collector = shared / "scripts/collect_retained_checkpoint_pilot.py"
    code = collector.read_text()
    needle = '        actual = model.restoration_state_dict()\n'
    assert code.count(needle) == 1
    code = code.replace(
        needle,
        '        if model.config.raw_frequency_features:\n'
        '            if model.config.raw_frequency_window != plan["raw_frequency_window"]:\n'
        '                raise ValueError("Loaded Fourier-window metadata differs")\n'
        '            if model.pretrained_rgb.raw_frequency.max_window != plan["raw_frequency_window"]:\n'
        '                raise ValueError("Actual Fourier module window differs")\n' + needle,
    )
    collector.write_text(code)
    source_proof = {}
    for p in (shared / "src/demosaic").glob("*.py"):
        assert p.read_bytes() == (REPO / "src/demosaic" / p.name).read_bytes()
        source_proof[p.name] = ref(p)["sha256"]
    assert len(source_proof) == 82
    inputs = root / "inputs"
    inputs.mkdir()
    before = torch.get_rng_state().clone()
    fresh = []
    for palette in palettes:
        assert ref(palette["arrays"]["path"]) == palette["arrays"]
        original = dict(np.load(palette["arrays"]["path"]))
        source = palette["case"]["source"]
        rgb = torch.tensor(source["linear_srgb"], dtype=torch.float32)[None, :, None, None]
        rgb = rgb.expand(1, 3, 512, 512).contiguous()
        for condition in conditions:
            for pattern in ("RGGB", "BGGR", "GRBG", "GBRG"):
                identity = f"flat512-{source['id']}-{condition['name']}-{pattern}"
                batch = observation(
                    rgb, [identity], condition, pattern, original["wb"][0].tolist(),
                    original["matrix"][0].tolist(), lock["fresh_flat_noise_seed"],
                )
                arrays = {k: v.numpy() for k, v in batch.items()}
                path = inputs / f"{identity}.npz"
                np.savez(path, **arrays)
                fresh.append({
                    "id": identity, "kind": "flat", "cohort": "fresh-flat512", "fresh": True,
                    "source": source, "noise": condition, "pattern": pattern,
                    "arrays": ref(path), "ROI_xywh": [176, 176, 160, 160],
                    "output_shape": [1, 3, 512, 512], "display_exposure": 1,
                    "reference_role": "Exact analytic flat GT, independent native512 noise draw",
                    "input_fingerprints": {k: fingerprint(arrays[k]) for k in NAMES},
                })
    assert len(fresh) == 72 and torch.equal(before, torch.get_rng_state())
    assert not torch.cuda.is_initialized()
    export_proofs = {}
    transfer = {}
    for label, binding in endpoints.items():
        assert ref(binding["path"]) == binding
        state = torch.load(binding["path"], map_location="cpu", weights_only=True, mmap=True)
        assert state["step"] == 500 and state["model_config"]["raw_frequency_window"] == 128
        assert len(state["ema"]) == 96
        derived = dict(state)
        derived["model_config"] = {**state["model_config"], "raw_frequency_window": 256}
        derived["inference_only"] = True
        derived["inference_geometry_override"] = {
            "trained_packed_window": 128, "inference_packed_window": 256,
            "source_export": binding, "design": ref(root / "design-lock-v1.json"),
        }
        dest = root / f"V146-{label}-window256-inference.pt"
        with dest.open("xb") as stream:
            torch.save(derived, stream)
        dest.chmod(0o444)
        actual = torch.load(dest, map_location="cpu", weights_only=True, mmap=True)
        assert actual["config"] == state["config"]
        assert all(torch.equal(actual[k][n], v) for k in ("model", "ema") for n, v in state[k].items())
        changed = {k for k in state["model_config"] if state["model_config"][k] != actual["model_config"][k]}
        assert changed == {"raw_frequency_window"}
        transfer[label] = ref(dest)
        export_proofs[label] = {"source": binding, "derived": ref(dest), "all96_model_EMA_tensors_exact": True}
        del state, derived, actual
    save(root / "export-verification-v1.json", {
        "status": "pass", "design": ref(root / "design-lock-v1.json"),
        "endpoints": export_proofs, "source_modules_exact": source_proof,
        "fresh_observation_draws": 72, "nonzero_noise_observations": 48,
        "global_CPU_RNG_unchanged": True, "CUDA_initialized": False, "new_model_forwards": 0,
    })
    stages = {}
    stage_specs = [
        ("V143", training["parent"], fresh, False, 91),
        ("EMA128", endpoints["EMA"], fresh, True, 96),
        ("raw128", endpoints["raw-model"], fresh, True, 96),
        ("EMA256", transfer["EMA"], selected + fresh, True, 96),
        ("raw256", transfer["raw-model"], selected + fresh, True, 96),
    ]
    for label, checkpoint, cases, frequency, tensors in stage_specs:
        point, work = root / label, root / label / "work"
        for directory in ("src", "scripts"):
            shutil.copytree(shared / directory, work / directory)
        state = torch.load(checkpoint["path"], map_location="cpu", weights_only=True, mmap=True)
        plan = {
            "root": str(point), "work": str(work), "checkpoint": checkpoint,
            "collector": ref(work / "scripts/collect_retained_checkpoint_pilot.py"),
            "step": state["step"], "expected_lineage": state["config"]["initialized_from"],
            "EMA_tensors": tensors, "raw_frequency_features": frequency,
            "raw_frequency_window": 256 if label.endswith("256") else 128 if frequency else 64,
            "expected_backbone": training["parent_backbone"], "observations": cases,
            "planned_new_root_forwards": len(cases), "model_label": label,
            "inputs": [checkpoint, ref(root / "design-lock-v1.json"), ref(root / "export-verification-v1.json")]
            + [o["arrays"] for o in cases],
            "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
            "launch_RAM_GiB": 52, "runtime_RAM_GiB": 32,
            "launch_internal_reserve_GiB": 96, "runtime_internal_reserve_GiB": 96,
            "launch_external_reserve_GiB": 208, "runtime_external_reserve_GiB": 208,
            "CUDA_quota_GiB": 12, "scope": lock["scope"] + " Stage: " + label,
        }
        if frequency:
            original_label = "EMA" if label.startswith("EMA") else "raw-model"
            plan["expected_full_model_sha256"] = collections[original_label]["full_model_before"]
        path = point / "plan-v1.json"
        save(path, plan)
        stages[label] = ref(path)
        del state
    assert sum(len(read(p["path"])["observations"]) for p in stages.values()) == 1524
    save(root / "queue-plan-v1.json", {
        "design": ref(root / "design-lock-v1.json"), "operator": ref(__file__),
        "controller": ref(frozen_controller),
        "stages": stages, "original_observations": originals, "fresh_flats": fresh,
        "original_predictions": predictions, "original_collections": {
            k: ref(previous / k / "collection-v1.json") for k in endpoints
        }, "scope": lock["scope"],
    })
    return root / "queue-plan-v1.json"


def controller(path):
    queue = read(path)
    root = path.parent
    (root / "controller.claim").open("x").close()
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    state = {"queue": ref(path), "owner": owner, "completed": {}}
    child = child_owner = None
    try:
        for label, binding in queue["stages"].items():
            assert ref(binding["path"]) == binding
            plan = read(binding["path"])
            guard(plan)
            began = time.monotonic()
            while psutil.virtual_memory().available < 52 * 2**30:
                assert time.monotonic() - began < 7200
                save(root / "status-v1.json", {**state, "status": "waiting-for-52GiB-headroom", "stage": label})
                time.sleep(2)
            assert shutil.disk_usage(root).free > 96 * 2**30
            assert shutil.disk_usage("/mnt/external").free > 208 * 2**30
            work = Path(plan["work"])
            env = dict(os.environ, PYTHONPATH=f"{work / 'src'}:{work / 'scripts'}",
                       CUDA_VISIBLE_DEVICES="0", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                       OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
                       CUBLAS_WORKSPACE_CONFIG=":4096:8")
            with (root / f"collect-{label}-v1.log").open("x") as log:
                child = subprocess.Popen(
                    [str(REPO / ".venv/bin/python"), "-P", plan["collector"]["path"], binding["path"]],
                    cwd=work, env=env, stdin=subprocess.DEVNULL, stdout=log,
                    stderr=subprocess.STDOUT, start_new_session=True,
                )
                child_owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                save(root / "status-v1.json", {**state, "status": "running-declared-stage",
                                               "stage": label, "child": child_owner})
                assert child.wait(timeout=3600) == 0, label
            result = work.parent / "collection-v1.json"
            assert read(result)["counts"] == {"root": len(plan["observations"]), "encoder": len(plan["observations"])}
            assert not live(child_owner)
            state["completed"][label] = ref(result)
        save(root / "status-v1.json", {**state, "status": "completed-1524-new-forwards-awaiting-audits",
                                       "new_root_forwards": 1524, "new_DINO_forwards": 1524})
    except BaseException as error:
        if child is not None and child.poll() is None and live(child_owner):
            os.killpg(child.pid, signal.SIGTERM)
            child.wait(timeout=30)
        save(root / "status-v1.json", {**state, "status": "failed-preserved-no-automatic-retry", "error": repr(error)})
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller"))
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path))
    else:
        controller(args.path.resolve())
