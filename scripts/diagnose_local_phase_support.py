"""Measure local support at already selected RAW frequencies, without restoration."""

import argparse
import hashlib
import json
import os
import resource
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import psutil
from local_phase_projection import box_sums, local_phase_projection

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261107/V179-local-phase-support-v1"
V175 = REPO / ".cache/quality-20261107/V175-fresh-noise-matching-v2"
V177 = Path("/mnt/external/demosaic/quality-20261107/V177-phase-frequency-holdout-v1")


def read(path):
    return json.loads(Path(path).read_text())


def ref(path):
    path = Path(path).absolute()
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path), "sha256": digest}


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def fingerprint(array):
    return {
        "shape": list(array.shape),
        "dtype": array.dtype.str,
        "sha256": hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest(),
    }


def prepare():
    assert not ROOT.exists()
    old = read(V177 / "result-v1.json")
    assert ref(old["plan"]["path"]) == old["plan"]
    previous = read(old["plan"]["path"])
    current = read(V175 / "plan-v1.json")
    tests = REPO / ".cache/v179-local-phase-CPU-tests-v1.log"
    assert "20 passed" in tests.read_text()
    assert psutil.virtual_memory().available > 40 * 2**30
    assert shutil.disk_usage(REPO).free > (48 + 0.5 + 0.4 + 0.2 + 2 + 0.15) * 2**30
    assert shutil.disk_usage("/mnt/external").free > (111 + 0.5 + 1.25 + 0.2) * 2**30
    assert previous["batches"] == 307 and previous["observations"] == 1228
    assert previous["source_cache"] == current["cache"]
    ROOT.mkdir()
    work = ROOT / "work"
    for name in [
        "scripts/local_phase_projection.py",
        "scripts/diagnose_local_phase_support.py",
        "tests/test_local_phase_projection.py",
    ]:
        source, target = REPO / name, work / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    axis = [*range(0, 256, 32), 255]
    centers = [[y, x] for y in axis for x in axis]
    sources = [dict(ref(p), text=p.read_text()) for p in work.rglob("*.py")]
    save(
        ROOT / "plan-v1.json",
        {
            "status": "fixed-CPU-local-support-diagnostic-no-model-quality",
            "created_unix_UTC": time.time(),
            "work": str(work),
            "runner": ref(work / "scripts/diagnose_local_phase_support.py"),
            "prior_result": ref(V177 / "result-v1.json"),
            "prior_plan": old["plan"],
            "prior_input_selections": ref(V177 / "input-only-selections-v1.jsonl"),
            "source_cache": previous["source_cache"],
            "selected_steps": previous["selected_steps"],
            "clean_sensor_preflight": current["clean_sensor_preflight"],
            "windows_packed": [33, 65, 129],
            "centers_yx_packed": centers,
            "batches": 307,
            "observations": 1228,
            "local_window_measurements": 298404,
            "selection": "Reuse rank1 from lower-index-green direction of each V177 input-only observation. No peak is reselected; no target/other-phase input changes the bin.",
            "projection": "Each clipped rectangle removes its own unweighted affine plane. Complex box-sum coefficient and full supplied independent-noise variance include nuisance-fit terms. No reflection padding or restored RGB.",
            "target_access": "Hash npz;read only RAW/variance/CFA;measure and fsync all4 input observations;then interpret target/pair arrays for score-only clean projections,conditional pre-ADC variance and exact counterfactual blank support.",
            "groups": "All present/absent and present-primary-global-other-power>=16;window blank means exact absence of constructed mesh in all native RGB samples of its Bayer-cell footprint. Nonblank need not have useful SNR. Windows and paired members are correlated.",
            "descriptive_local_power_edges": [1, 4, 16, 64],
            "new_local_projection_GiB": 0.15,
            "new_external_projection_GiB": 0,
            "CPU_tests": dict(ref(tests), text=tests.read_text()),
            "sources": sources,
            "scope": "Input-only local measurement study on existing noisy training mesh data,not a model/restoration/quality result. Tests localization/evidence tradeoffs at fixed old bins;does not prove V178 hallucinates or that local features improve it. Clean target and conditional pre-ADC variance enter scoring only;ADC/clipping/observed variance proxies prevent calibration claims. No new noise,NN/checkpoint/parent/DINO/RAW-decoder/original/dataz work. Both protected GFX scenes stay unused and excluded. Existing queued recipes and all neural source bytes unchanged.",
        },
    )
    print(
        "Prepared307cachedbatches/1228observations/3localscales/81windows;no model work", flush=True
    )


def run():
    plan = read(ROOT / "plan-v1.json")
    for binding in plan["sources"]:
        assert ref(binding["path"]) == {k: binding[k] for k in ["path", "sha256"]}
    for name in [
        "prior_result",
        "prior_plan",
        "prior_input_selections",
        "source_cache",
        "clean_sensor_preflight",
    ]:
        assert ref(plan[name]["path"]) == plan[name]
    assert Path(__file__).is_relative_to(Path(plan["work"]))
    (ROOT / "run.claim").open("x").close()
    os.nice(10)
    os.sched_setaffinity(0, [6, 7])
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    save(ROOT / "owner-v1.json", owner)
    selection_rows = [
        json.loads(line)
        for line in Path(plan["prior_input_selections"]["path"]).read_text().splitlines()
    ]
    assert [row["step"] for row in selection_rows] == plan["selected_steps"]
    cache = {row["step"]: row for row in read(plan["source_cache"]["path"])["batches"]}
    preflight = {row["step"]: row for row in read(plan["clean_sensor_preflight"]["path"])["rows"]}
    centers = np.asarray(plan["centers_yx_packed"])
    calls = scored_calls = points = 0
    try:
        with (
            (ROOT / "input-local-measurements-v1.jsonl").open("x") as measured,
            (ROOT / "scored-local-measurements-v1.jsonl").open("x") as scored,
        ):
            for batch_ordinal, selected in enumerate(selection_rows):
                while psutil.virtual_memory().available < 32 * 2**30:
                    time.sleep(2)
                item = cache[selected["step"]]
                assert item["arrays"] == selected["original_inputs"]
                assert ref(item["arrays"]["path"]) == item["arrays"]
                assert preflight[item["step"]]["fresh_noise_eligible"]
                with np.load(item["arrays"]["path"], allow_pickle=False) as archive:
                    raw = {key: archive[key] for key in ["packed", "variance", "colors"]}
                    assert raw["packed"].shape == (4, 4, 256, 256)
                    assert {key: fingerprint(value) for key, value in raw.items()} == {
                        key: item["inputs"][key] for key in raw
                    }
                    inputs = []
                    for frame, directions in enumerate(selected["observations"]):
                        primary = directions[0]
                        greens = np.flatnonzero(raw["colors"][frame] == 1)
                        assert [
                            primary["selection_phase"],
                            primary["other_phase"],
                        ] == greens.tolist()
                        phase = primary["other_phase"]
                        peak = primary["peaks"][0]
                        windows = []
                        for side in plan["windows_packed"]:
                            result = local_phase_projection(
                                raw["packed"][frame, phase],
                                raw["variance"][frame, phase],
                                peak["bin_yx"],
                                window=side,
                                centers_yx=centers,
                            )
                            assert (result["noise_variance"] > 0).all()
                            power = abs(result["coefficient"]) ** 2 / result["noise_variance"]
                            windows.append(
                                {
                                    "window": side,
                                    "coefficient_RI": np.stack(
                                        (result["coefficient"].real, result["coefficient"].imag), 1
                                    ).tolist(),
                                    "noise_variance": result["noise_variance"].tolist(),
                                    "nominal_power": power.tolist(),
                                    "boxes_xywh": result["boxes_xywh"].tolist(),
                                }
                            )
                            calls += 1
                            points += len(power)
                        inputs.append(
                            {
                                "frame": frame,
                                "selection_phase": int(greens[0]),
                                "other_phase": phase,
                                "bin_yx": peak["bin_yx"],
                                "global_other_power": peak["other_phase_power"],
                                "windows": windows,
                            }
                        )
                    measurement = {
                        "step": item["step"],
                        "original_inputs": item["arrays"],
                        "used_inputs": {key: fingerprint(value) for key, value in raw.items()},
                        "observations": inputs,
                    }
                    measured.write(json.dumps(measurement, allow_nan=False) + "\n")
                    measured.flush()
                    os.fsync(measured.fileno())
                    # Targets and pair indices are interpreted only after the
                    # input-only batch is durably committed.
                    target, pairs = archive["target"], archive["pair_indices"]
                    assert (
                        fingerprint(target) == item["inputs"]["target"]
                        and fingerprint(pairs) == item["inputs"]["pair_indices"]
                    )
                    assert pairs.shape == (2, 2) and len(np.unique(pairs)) == 4
                    labels, support = {}, {}
                    for first, second in pairs:
                        signal = np.any(target[first] != target[second], axis=0)
                        packed_support = signal.reshape(256, 2, 256, 2).any((1, 3))
                        labels[int(first)], labels[int(second)] = True, False
                        support[int(first)], support[int(second)] = (
                            packed_support,
                            np.zeros((256, 256), bool),
                        )
                    for observation in inputs:
                        frame, phase = observation["frame"], observation["other_phase"]
                        clean = (
                            target[
                                frame, raw["colors"][frame, phase], phase // 2 :: 2, phase % 2 :: 2
                            ]
                            .astype(np.float64)
                            .clip(min=0)
                        )
                        physical_variance = (
                            clean * item["metadata"]["noise"]["shot"]
                            + item["metadata"]["noise"]["read"]
                        )
                        for window in observation["windows"]:
                            truth = local_phase_projection(
                                clean,
                                physical_variance,
                                observation["bin_yx"],
                                window=window["window"],
                                centers_yx=centers,
                            )
                            scored_calls += 1
                            np.testing.assert_array_equal(truth["boxes_xywh"], window["boxes_xywh"])
                            assert (truth["noise_variance"] > 0).all()
                            blank = box_sums(support[frame], truth["boxes_xywh"]) == 0
                            record = {
                                "step": item["step"],
                                "frame": frame,
                                "present": labels[frame],
                                "window": window["window"],
                                "bin_yx": observation["bin_yx"],
                                "global_other_power": observation["global_other_power"],
                                "nominal_power": window["nominal_power"],
                                "exact_counterfactual_blank": blank.tolist(),
                                "clean_coefficient_RI": np.stack(
                                    (truth["coefficient"].real, truth["coefficient"].imag), 1
                                ).tolist(),
                                "clean_conditional_preADC_variance": truth[
                                    "noise_variance"
                                ].tolist(),
                                "clean_conditional_power": (
                                    abs(truth["coefficient"]) ** 2 / truth["noise_variance"]
                                ).tolist(),
                                "proxy_over_clean_conditional_variance": (
                                    np.asarray(window["noise_variance"]) / truth["noise_variance"]
                                ).tolist(),
                            }
                            scored.write(json.dumps(record, allow_nan=False) + "\n")
                    scored.flush()
                    os.fsync(scored.fileno())
                if batch_ordinal % 10 == 0:
                    status = {
                        "status": "measuring-and-target-scoring-CPU-only",
                        "owner": owner,
                        "completed_batches": batch_ordinal + 1,
                        "local_input_projection_calls": calls,
                        "score_only_clean_projection_calls": scored_calls,
                        "local_window_measurements": points,
                    }
                    temporary = ROOT / "status-v1.tmp"
                    temporary.write_text(json.dumps(status, indent=2) + "\n")
                    temporary.replace(ROOT / "status-v1.json")
            assert (
                calls == scored_calls == 3684
                and points == plan["local_window_measurements"] == 298404
            )
        assert "torch" not in sys.modules and "rawpy" not in sys.modules
        save(
            ROOT / "result-v1.json",
            {
                "status": "completed-local-input-measurements-and-target-only-scoring-no-quality-result",
                "owner": owner,
                "plan": ref(ROOT / "plan-v1.json"),
                "input_journal": ref(ROOT / "input-local-measurements-v1.jsonl"),
                "scored_journal": ref(ROOT / "scored-local-measurements-v1.jsonl"),
                "batches": 307,
                "observations": 1228,
                "local_input_projection_calls": calls,
                "score_only_clean_projection_calls": scored_calls,
                "local_window_measurements": points,
                "new_neural_forwards": 0,
                "new_parent_DINO_forwards": 0,
                "new_noise_draws": 0,
                "new_checkpoint_loads": 0,
                "Torch_imported": False,
                "rawpy_imported": False,
                "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                "scope": plan["scope"],
            },
        )
        print(
            "Completed307batches/1228observations/298404localwindows;no model or restored RGB",
            flush=True,
        )
    except BaseException as error:
        save(
            ROOT / "failure-v1.json",
            {
                "status": "failed-preserve-prefix-no-automatic-retry",
                "owner": owner,
                "error": repr(error),
                "source": ref(__file__),
            },
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "run"])
    {"prepare": prepare, "run": run}[parser.parse_args().phase]()
