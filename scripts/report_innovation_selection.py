"""Close four input-only selectors before two exact-template geometry reads."""

import argparse
import gzip
import json
import os
import shutil
import sys
import time
from collections import Counter

import numpy as np
import psutil
from directional_trial_protocol import REPO, freeze, guard, read, ref, save
from green_phase_spectrum import tapered_spectrum
from innovation_frequency_selection import (
    VIEWS,
    fundamental_distances,
    measurement_fields,
    pooled_score,
    select_pooled,
)
from lossless_native import fingerprint, load_native
from mesh_orientation_response import sectors
from native_alias_geometry import carrier_footprints
from phase_admission_protocol import owner_live

ROOT = REPO / ".cache/quality-20261108/V196-innovation-selection-v1"
PREVIOUS = REPO / ".cache/quality-20261108/V195-directional-response-trial-v1"
METHOD = "V195-whole-response-EMA"


def lines(path):
    with gzip.open(path, "rt") as stream:
        return [json.loads(line) for line in stream]


def prepare():
    assert not (ROOT / "plan-v2.json").exists()
    failure = read(ROOT / "selection-failure-v1.json")
    assert failure["original_plan"] == ref(ROOT / "plan-v1.json")
    assert failure["preserved_prefix"] == ref(ROOT / "input-selections-v1.jsonl.gz")
    prefix = lines(failure["preserved_prefix"]["path"])
    assert len(prefix) == 23
    final = REPO / "docs/results/v195-response-final-v1.json"
    verification = REPO / "docs/results/v195-response-publication-verification-v1.json"
    closure = REPO / "docs/results/v195-completed-execution-v1.json"
    assert read(verification)["publication"] == ref(final)
    assert read(final)["status"].startswith("completed-")
    execution = read(closure)
    assert all(
        not owner_live(owner) for owner in execution["all_registered_owners_terminal"].values()
    )
    tests = REPO / ".cache/v196-innovation-CPU-tests-v2.log"
    assert "16 passed" in tests.read_text()
    manifest = REPO / "docs/images/v195-directional-response-v1/manifest-v1.json"
    figures = read(manifest)
    cases = {board["case"]["id"]: board["case"] for board in figures["images"]}
    scores_path = PREVIOUS / "scores-v1.json"
    predictions = read(scores_path)["native_predictions"]
    assert len(cases) == len(predictions) == 36 and set(cases) == set(predictions)
    # Previous targets/metrics were used adaptively in development; this is not
    # a blind experiment. No new target ARRAY access occurs during selection.
    old, input_hashes = {}, {}
    journal = PREVIOUS / "quality-observations-v1.jsonl.gz"
    with gzip.open(journal, "rt") as stream:
        for line in stream:
            row = json.loads(line)
            if row["id"] in cases and row["method"] == METHOD:
                input_hashes[row["id"]] = row["inputs"]
                selection = row["pooled"]
                old[row["id"]] = (
                    None
                    if selection is None
                    else [
                        selection["selection"]["bin_yx"][0][d][k]
                        for k in range(4)
                        for d in range(2)
                    ]
                )
    assert set(old) == set(cases)
    orientation = REPO / ".cache/quality-20261108/V194-orientation-response-v1/plan-v2.json"
    geometry = {item["case"]["id"]: item["geometry"] for item in read(orientation)["cases"]}
    stage = ROOT / "source-v2"
    stage.mkdir()
    work, sources = freeze(
        stage,
        [
            "report_innovation_selection.py",
            "audit_innovation_selection.py",
            "render_innovation_selection.py",
        ],
    )
    test_copy = work / "tests/test_innovation_frequency_selection.py"
    test_copy.parent.mkdir(exist_ok=True)
    shutil.copyfile(REPO / "tests/test_innovation_frequency_selection.py", test_copy)
    sources[str(test_copy)] = ref(test_copy)["sha256"]
    bindings = [
        ref(ROOT / "plan-v1.json"),
        ref(ROOT / "selection-failure-v1.json"),
        failure["preserved_prefix"],
    ] + [
        ref(p)
        for p in [final, verification, closure, manifest, scores_path, journal, orientation, tests]
    ]
    records = []
    for name in sorted(cases):
        case = cases[name]
        records.append(
            {
                "case": case,
                "prediction": predictions[name][METHOD],
                "previous_RAW_FP32_bins": old[name],
                "input_fingerprints": input_hashes[name],
            }
        )
        bindings += [case["arrays"], predictions[name][METHOD]]
    neural = execution["previous103_neural_hashes_unchanged"]
    assert len(neural) == 103
    for name, digest in neural.items():
        assert ref(REPO / "src/demosaic" / name)["sha256"] == digest
    assert shutil.disk_usage(REPO).free > 40.02 * 2**30
    save(
        ROOT / "plan-v2.json",
        {
            "status": "prepared-four-input-only-selection-views-no-new-restorations-or-quality",
            "created_unix_UTC": time.time(),
            "runner": ref(work / "scripts/report_innovation_selection.py"),
            "auditor": ref(work / "scripts/audit_innovation_selection.py"),
            "renderer": ref(work / "scripts/render_innovation_selection.py"),
            "frozen_files": sources,
            "inputs": bindings,
            "cases": records,
            "preserved_prefix": failure["preserved_prefix"],
            "preserved_prefix_rows": 23,
            "metadata_correction": ref(ROOT / "selection-failure-v1.json"),
            "geometry": geometry,
            "method": METHOD,
            "checkpoint": figures["method_checkpoints"][METHOD],
            "views": {
                k: {
                    "field": field,
                    "lower_native_frequency": low,
                    "upper_native_frequency": 1 / 3,
                    "bins": 8,
                }
                for k, (field, low) in VIEWS.items()
            },
            "neural103": neural,
            "CPU_tests": ref(tests),
            "prior_fixture_log": ref(REPO / ".cache/v196-innovation-CPU-tests-v1.log"),
            "new_local_forecast_GiB": 0.02,
            "new_external_bytes": 0,
            "scope": "All36 previously retained development native contexts; RAW or RAW-minus-sampled-V195WholeEMA, each1/16..1/3 or1/64..1/3 band. Four equal8-bin selectors use bothgreens,weighted-affine Hann,mean normalizedpower,3x3pooling andconjugate3x3NMS,FP64CPU arithmetic. NominalRAW Fouriervariance remains sharedunits,not residualnoise orcalibratedconfidence; outputandRAWarecorrelated. Closeall144selections andfullscorefingerprints beforeaccessing two previouslydeclared exactprocedural templates. Weighted/tapered nativeRGB powerproximity atfixedradius1andceil(packedaxis/65),nearest-recipe-normal regions andrecipefundamental distances aregeometryonly,not achievableamplitude/recoverybounds,isolatedwire-family gain,neuralquality,flat safety orpopulationevidence. RealISO100/JPEGreferences neverread/scored; ADC-only selectors diagnosticbutmodelbypassesreadout. ZeroTorch/model/checkpointloads,neuralforwards,newsource/noisedraws,RAWdecode,original/datazaccess. All103neuralfiles,priorarrays,receiptsandcheckpointsunchanged. Input NPZ file hashes includecontainerbytes,while targetarrayaccess staysoutside selection. Old results informedthisdevelopmentdesign;notblind.",
        },
    )
    print("Prepared36cachedcontexts x4views;zero new restoration;0.02GiB local budget")


def checked_plan(entry=None):
    plan = read(ROOT / "plan-v2.json")
    guard(plan, entry)
    for name, digest in plan["neural103"].items():
        assert ref(REPO / "src/demosaic" / name)["sha256"] == digest
    assert shutil.disk_usage(REPO).free > 40 * 2**30
    assert psutil.virtual_memory().available > 16 * 2**30
    return plan


def select():
    plan = checked_plan(__file__)
    (ROOT / "selection-v2.claim").open("x").close()
    os.nice(10)
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    bridges = []
    prefix = lines(plan["preserved_prefix"]["path"])
    assert len(prefix) == plan["preserved_prefix_rows"] == 23
    assert [r["id"] for r in prefix] == [i["case"]["id"] for i in plan["cases"][:23]]
    with gzip.open(ROOT / "input-selections-v2.jsonl.gz", "xt", compresslevel=6) as stream:
        for item, row in zip(plan["cases"][:23], prefix, strict=True):
            assert (
                row["arrays"] == item["case"]["arrays"] and row["prediction"] == item["prediction"]
            )
            assert all(
                row["inputs"][k] == item["input_fingerprints"][k]
                for k in ["packed", "variance", "colors"]
            )
            stream.write(json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n")
            if row["previous_FP32_RAW_bridge"] is not None:
                bridges.append(row["previous_FP32_RAW_bridge"])
        for item in plan["cases"][23:]:
            case = item["case"]
            with np.load(case["arrays"]["path"], allow_pickle=False) as arrays:
                packed, variance, colors = [arrays[k] for k in ["packed", "variance", "colors"]]
            restored = load_native(item["prediction"])
            fields = measurement_fields(packed, restored, colors)
            scores = {key: pooled_score(value, variance, colors) for key, value in fields.items()}
            views = {}
            for name, (field, lower) in VIEWS.items():
                selected = select_pooled(scores[field], lower)
                bins = np.asarray(selected["bins_yx_rank_order"])
                f = (
                    np.minimum(bins, np.asarray(packed.shape[-2:]) - bins)
                    / np.asarray(packed.shape[-2:])
                    / 2
                )
                views[name] = dict(
                    selected,
                    score=fingerprint(scores[field]),
                    bins_below_old_lower=int((np.hypot(f[:, 0], f[:, 1]) < 1 / 16).sum()),
                )
            old = item["previous_RAW_FP32_bins"]
            actual = views["RAW_current"]["bins_yx_rank_order"]
            bridge = (
                None
                if old is None
                else {
                    "rank_order_equal": old == actual,
                    "set_overlap": len(set(map(tuple, old)) & set(map(tuple, actual))),
                }
            )
            if bridge is not None:
                bridges.append(bridge)
            row = {
                "id": case["id"],
                "kind": case["kind"],
                "arrays": case["arrays"],
                "prediction": item["prediction"],
                "packed_shape": list(packed.shape[-2:]),
                "inputs": {
                    k: fingerprint(v)
                    for k, v in zip(
                        ["packed", "variance", "colors"], [packed, variance, colors], strict=True
                    )
                },
                "restored": fingerprint(restored),
                "fields": {k: fingerprint(v) for k, v in fields.items()},
                "views": views,
                "previous_FP32_RAW_bridge": bridge,
            }
            for key, value in row["inputs"].items():
                assert value == item["input_fingerprints"][key]
            stream.write(json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n")
            print(
                "selected",
                case["id"],
                [views[n]["bins_below_old_lower"] for n in VIEWS],
                flush=True,
            )
    assert "torch" not in sys.modules
    save(
        ROOT / "input-completion-v1.json",
        {
            "status": "closed144input-only-selections-before-template-array-access",
            "created_unix_UTC": time.time(),
            "owner": owner,
            "plan": ref(ROOT / "plan-v2.json"),
            "journal": ref(ROOT / "input-selections-v2.jsonl.gz"),
            "preserved_prefix": plan["preserved_prefix"],
            "reused_contexts_without_remeasurement": 23,
            "new_suffix_contexts": 13,
            "cases": 36,
            "selections": 144,
            "new_target_array_accesses": 0,
            "new_real_reference_accesses": 0,
            "previous_FP32_RAW_bridges": bridges,
            "Torch_imported": False,
        },
    )
    print(
        "PASS input closure;FP32 raw rank bridges",
        sum(b["rank_order_equal"] for b in bridges),
        "/",
        len(bridges),
    )


def project():
    plan = checked_plan(__file__)
    completion = read(ROOT / "input-completion-v1.json")
    assert not owner_live(completion["owner"])
    assert completion["journal"] == ref(ROOT / "input-selections-v2.jsonl.gz")
    (ROOT / "projection.claim").open("x").close()
    inputs = {r["id"]: r for r in lines(completion["journal"]["path"])}
    cases = {r["case"]["id"]: r["case"] for r in plan["cases"]}
    rows = []
    for case_id, geometry in plan["geometry"].items():
        case, selection = cases[case_id], inputs[case_id]
        with np.load(case["arrays"]["path"], allow_pickle=False) as arrays:
            template = arrays["target_present"].astype(np.float64) - arrays["target_empty"].astype(
                np.float64
            )
        power = sum(abs(tapered_spectrum(v)["spectrum"]) ** 2 for v in template[0])
        masks = sectors(power.shape, geometry["native_normals_radians"])
        for name, view in selection["views"].items():
            bins = np.asarray(view["bins_yx_rank_order"])
            fundamentals = fundamental_distances(
                tuple(selection["packed_shape"]),
                bins,
                geometry["native_normals_radians"],
                case["source"]["recipe"]["periods_final_pixels"],
            )
            for radius in [1, int(np.ceil(max(selection["packed_shape"]) / 65))]:
                principal, _ = carrier_footprints(tuple(selection["packed_shape"]), bins, radius)
                regions = []
                for k, mask in enumerate(masks):
                    energy = float(power[mask].sum())
                    regions.append(
                        {
                            "region": k,
                            "GT_power_fraction": energy / float(power.sum()),
                            "principal_proximity": float(power[mask & principal].sum()) / energy,
                        }
                    )
                rows.append(
                    {
                        "id": case_id,
                        "view": name,
                        "radius_native_bins": radius,
                        "template": fingerprint(template),
                        "native_power": fingerprint(power),
                        "principal_proximity": float(power[principal].sum() / power.sum()),
                        "regions": regions,
                        "fundamentals": fundamentals,
                    }
                )
        print("projected", case_id, flush=True)
    assert len(rows) == 16 and "torch" not in sys.modules
    counts = Counter(r["kind"] for r in inputs.values())
    save(
        ROOT / "result-v1.json",
        {
            "status": "completed-four-view-geometry-awaiting-independent-audit",
            "created_unix_UTC": time.time(),
            "plan": ref(ROOT / "plan-v2.json"),
            "input_completion": ref(ROOT / "input-completion-v1.json"),
            "input_journal": ref(ROOT / "input-selections-v2.jsonl.gz"),
            "context_counts": dict(counts),
            "rows": rows,
            "new_neural_forwards": 0,
            "new_source_noise_draws": 0,
            "real_reference_reads": 0,
            "Torch_imported": False,
            "scope": plan["scope"],
        },
    )
    print("PASS16two-example/view/radius geometry rows;no new quality inference")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "select", "project"])
    phase = parser.parse_args().phase
    {"prepare": prepare, "select": select, "project": project}[phase]()
