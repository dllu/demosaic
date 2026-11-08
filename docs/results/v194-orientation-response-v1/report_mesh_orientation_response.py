"""Read-only directional projections of two predeclared saved native examples."""

import argparse
import ast
import json
import os
import random
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import psutil
from lossless_native import load_native
from mesh_orientation_response import native_angles, project
from phase_admission_protocol import owner_live, read, ref

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261108/V194-orientation-response-v1"
PREPARATION = ROOT.with_name("V194-orientation-response-preparation-v1")


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def geometry(case):
    """Replay existing metadata draws only, checking the original terminal state."""
    original = read(case["origin_plan"]["path"])["observations"][case["origin_index"]]
    assert original["id"] == case["id"] and original["arrays"] == case["arrays"]
    rng = random.Random(case["seed"])
    assert rng.getrandbits(63) == case["source"]["recipe"]["seed"]
    rotation, flip, homography = rng.randrange(4), rng.random() < 0.5, rng.random() < 0.2
    assert not homography, "This fixed two-case diagnostic accepts exact D4 geometry only"
    rng.random()  # optical-blur choice is drawn even at the fixed zero probability
    assert repr(rng.getstate()) == original["source"]["geometry_final_rng_state"]
    angles = native_angles(case["source"]["recipe"]["angles_radians"], rotation, flip)
    return {
        "rotation90_CCW": rotation,
        "horizontal_flip_after_rotation": flip,
        "homography": False,
        "saved_geometry_RNG_state_exact": True,
        "recipe_normals_radians": case["source"]["recipe"]["angles_radians"],
        "native_normals_radians": angles,
    }


def prepare():
    assert not (ROOT / "plan-v2.json").exists()
    completed = REPO / "docs/results/v193-completed-execution-v1.json"
    closure = read(completed)
    for owner in closure["all_terminal_owners"].values():
        assert not owner_live(owner)
    final = read(closure["publication"]["path"])
    assert ref(closure["publication"]["path"]) == closure["publication"]
    assert read(closure["verification"]["path"])["publication"] == closure["publication"]
    for name, digest in closure["previous103_neural_hashes_unchanged"].items():
        assert ref(REPO / "src/demosaic" / name)["sha256"] == digest
    prep = read(PREPARATION / "plan-v1.json")
    for source in prep["sources"]:
        assert ref(source["path"]) == {k: source[k] for k in ["path", "sha256"]}
    tests = ROOT / "CPU-contracts-v2.log"
    assert "16 passed" in tests.read_text()
    assert shutil.disk_usage(REPO).free > 40.005 * 2**30
    assert psutil.virtual_memory().available > 32 * 2**30
    old_src = Path(prep["cases"][0]["origin_plan"]["path"]).parent / "work/src/demosaic"
    # The original data preparation algorithm must match the geometry we replay.
    for name, function in [
        ("data.py", "augment_before_downsample"),
        ("textures.py", "crossed_line_texture"),
    ]:
        functions = []
        for folder in [old_src, REPO / "src/demosaic"]:
            tree = ast.parse((folder / name).read_text())
            functions.append(
                ast.dump(
                    next(
                        n
                        for n in tree.body
                        if isinstance(n, ast.FunctionDef) and n.name == function
                    )
                )
            )
        assert functions[0] == functions[1]
    manifest = read(final["figures"]["path"])
    trial = read(final["plan"]["path"])
    parent_scores = read(
        REPO / ".cache/quality-20261107/V175-fresh-noise-matching-v2/plan-v1.json"
    )["parent_scores"]
    score_sources = {
        "V143 parent": parent_scores,
        "V183-coherent-pair-EMA": trial["baseline_scores"],
    }
    for version in ["V187", "V191", "V193"]:
        for endpoint in ["raw", "EMA"]:
            method = next(
                m for m in prep["methods"] if m.startswith(version) and m.endswith(endpoint)
            )
            score_sources[method] = (
                trial[version + "_scores"]
                if version != "V193"
                else ref(Path(final["plan"]["path"]).parent / "scores-v1.json")
            )
    cases = []
    for case in prep["cases"]:
        board = next(
            b for b in manifest["images"] if not b["triplet"] and b["case"]["id"] == case["id"]
        )
        entries = []
        for method in prep["methods"]:
            score_label = "parent" if method == "V143 parent" else method
            scores = read(score_sources[method]["path"])
            row = next(
                r for r in scores["rows"] if r["id"] == case["id"] and r["method"] == score_label
            )
            entries.append(
                {
                    "method": method,
                    "prediction": case["parent"]
                    if method == "V143 parent"
                    else board["predictions"][method],
                    "prior_whole_template_gain": row["template_gain"],
                    "score_source": score_sources[method],
                    "checkpoint_metadata": read(case["origin_plan"]["path"])["checkpoint"]
                    if method == "V143 parent"
                    else manifest["method_checkpoints"][method],
                }
            )
        cases.append({"case": case, "geometry": geometry(case), "methods": entries})
    work = ROOT / "work"
    for path in [
        Path(__file__),
        REPO / "scripts/mesh_orientation_response.py",
        REPO / "scripts/lossless_native.py",
        REPO / "scripts/phase_admission_protocol.py",
        REPO / "tests/test_mesh_orientation_response.py",
    ]:
        shutil.copyfile(path, work / path.name)
    bindings = [
        ref(completed),
        closure["publication"],
        closure["verification"],
        final["plan"],
        final["figures"],
        ref(PREPARATION / "plan-v1.json"),
        ref(tests),
    ]
    for item in cases:
        case = item["case"]
        bindings += [case["arrays"], case["origin_plan"]]
        for entry in item["methods"]:
            bindings += [entry["prediction"], entry["score_source"]]
    inputs = list({b["path"]: b for b in bindings}.values())
    plan = {
        "status": "prepared-D4-corrected-orientation-supplement-before-any-saved-prediction-projection",
        "created_unix_UTC": time.time(),
        "runner": ref(work / Path(__file__).name),
        "original_preparation": ref(PREPARATION / "plan-v1.json"),
        "correction": "Original recipe normals precede augmentation. Metadata inspection found seed2302 rot2+horizontalflip and seed2309 rot3. Correct native normals before reading actual saved predictions. Original plan/math/tests remain unchanged. Same two cases/eight methods; no result-based case/angle selection.",
        "cases": cases,
        "inputs": inputs,
        "sources": [dict(ref(p), text=p.read_text()) for p in work.glob("*.py")],
        "neural103": closure["previous103_neural_hashes_unchanged"],
        "tests": dict(ref(tests), text=tests.read_text()),
        "minimum_GiB": {"local": 40, "RAM": 32},
        "new_local_forecast_GiB": 0.005,
        "scope": "Sixteen saved native512 camera-RGB projections on two fixed present-mesh examples. Eight comparators, known D4-corrected recipe normals, full-context unweighted affine detrending. No checkpoint load, model/Torch/CUDA call, image regeneration, source/noise draw, original/dataz/real-reference access or optimization. Three disjoint conjugate-closed native spectral regions recompose the existing whole-template score. Regions have envelope/intersection leakage and are not isolated wire-family amplitudes, confidence or generalization evidence. Existing V193 full quality and native comparisons remain authoritative.",
    }
    for b in inputs:
        assert ref(b["path"]) == b
    save(ROOT / "plan-v2.json", plan)
    print(
        "Prepared16nativeprojections/2fixedexamples/8comparators/D4-correctedangles; no saved prediction pixels read"
    )


def run():
    plan = read(ROOT / "plan-v2.json")
    assert ref(__file__) == plan["runner"]
    for b in plan["inputs"]:
        assert ref(b["path"]) == b
    for b in plan["sources"]:
        assert ref(b["path"]) == {k: b[k] for k in ["path", "sha256"]}
    (ROOT / "run.claim").open("x").close()
    os.nice(10)
    os.sched_setaffinity(0, [8, 9])
    rows = []
    for item in plan["cases"]:
        assert (
            shutil.disk_usage(REPO).free > 40 * 2**30
            and psutil.virtual_memory().available > 32 * 2**30
        )
        case = item["case"]
        with np.load(case["arrays"]["path"], allow_pickle=False) as arrays:
            present, empty = [arrays[n][0] for n in ["target_present", "target_empty"]]
        for entry in item["methods"]:
            value = load_native(entry["prediction"])
            assert value.shape == (1, 3, 512, 512) and value.dtype == np.float32
            measured = project(value[0], present, empty, item["geometry"]["native_normals_radians"])
            assert abs(measured["whole_template_gain"] - entry["prior_whole_template_gain"]) < 2e-12
            rows.append(
                {
                    "id": case["id"],
                    "method": entry["method"],
                    "prediction": entry["prediction"],
                    **measured,
                }
            )
            print(
                case["seed"],
                entry["method"],
                "whole",
                measured["whole_template_gain"],
                "sectors",
                [s["gain"] for s in measured["sectors"]],
                flush=True,
            )
    assert len(rows) == 16 and "torch" not in sys.modules
    save(
        ROOT / "result-v1.json",
        {
            "status": "completed-saved-native-directional-projections-awaiting-independent-audit",
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "plan": ref(ROOT / "plan-v2.json"),
            "rows": rows,
            "whole_template_bridges": 16,
            "native_RGB_values_read": 16 * 3 * 512 * 512,
            "Torch_imported": False,
            "neural_forwards": 0,
            "source_noise_draws": 0,
            "scope": plan["scope"],
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "run"])
    globals()[parser.parse_args().phase]()
