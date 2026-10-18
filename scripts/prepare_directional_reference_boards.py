"""Append matched retained V43/RawNIND crops after the directional CPU closure."""

import argparse
import copy
import json
import os
import shutil
import time
from pathlib import Path

import numpy as np
from build_native_crop_board import build, case_key, identity, read_crop
from close_camera_supervision_review import alive, read, ref, save, sha, synthetic_geometry


def append_references(fresh_path, retained, output, kind, *, gfx_fixture=None):
    """Keep original PNGs, checking all common settings and input pixels."""
    fresh_path, output = Path(fresh_path), Path(output)
    fresh = read(fresh_path)
    geometry_summary = fresh
    if kind == "synthetic" and "native_crop" not in geometry_summary:
        original = fresh["native_crops"][0]["model"]["native_source_report"]
        assert ref(original["path"]) == original
        geometry_summary = read(original["path"])
    cases = {case_key(c, kind) for c in fresh["native_crops"]}
    output.mkdir(parents=True, exist_ok=False)
    entries, witnesses = [], []
    selections = [(fresh_path, fresh["native_crops"], False)]
    for selection in retained:
        report_path = Path(selection["report"]["path"])
        assert ref(report_path) == selection["report"]
        report = read(report_path)
        crops = [
            c
            for c in report["native_crops"]
            if identity(c)[1] == selection["checkpoint_sha256"]
            and (not selection.get("label") or identity(c)[0] == selection["label"])
            and case_key(c, kind) in cases
        ]
        assert len(crops) == len(cases) and {case_key(c, kind) for c in crops} == cases
        if selection.get("verify_GFX_inputs"):
            fixture = read(gfx_fixture["path"])
            assert ref(gfx_fixture["path"]) == gfx_fixture
            assert report["sources"] == fixture["gfx_sources"]
            observation = fixture["serving_probes"][0]["observation"]
            assert ref(observation["path"]) == observation
            with np.load(observation["path"], allow_pickle=False) as arrays:
                for index, region in enumerate(fixture["gfx_regions"]):
                    source = next(
                        r
                        for r in report["float_contexts"]
                        if r["role"] == "noisy-packed" and r["region"] == region["region"]
                    )
                    path = report_path.parent / source["image"]
                    assert sha(path) == source["sha256"] == region["noisy_packed"]["sha256"]
                    assert np.array_equal(
                        np.load(path, allow_pickle=False), arrays["packed"][index : index + 1]
                    )
                    reference = next(
                        r
                        for r in report["float_contexts"]
                        if r["role"] == "reference-rgb" and r["region"] == region["region"]
                    )
                    reference_path = report_path.parent / reference["image"]
                    assert (
                        sha(reference_path)
                        == reference["sha256"]
                        == region["reference_RGB"]["sha256"]
                    )
                    witnesses.append(
                        {
                            "region": region["region"],
                            "packed_exact": ref(path),
                            "reference_exact": ref(reference_path),
                            "fixture": gfx_fixture,
                        }
                    )
        selections.append((report_path, crops, True))
    for report_path, crops, retained_flag in selections:
        for crop in crops:
            _, _, png = read_crop(report_path, crop, kind)
            result = copy.deepcopy(crop)
            if kind == "synthetic":
                # The source selection/loader is unchanged, and its direct
                # native cache slice is checked before adding missing metadata.
                geometry = synthetic_geometry(crop, geometry_summary)
                for key, value in geometry["crop_metadata"].items():
                    assert key not in result or result[key] == value
                    result[key] = value
            elif kind == "gfx" and "source" not in result:
                # Only the old RawNIND report lacks this shared field. Above,
                # actual packed arrays, reference bytes and RAF identities were
                # matched to the same frozen observation; no RAF is decoded.
                assert witnesses and retained_flag
                template = next(
                    c for c in fresh["native_crops"] if case_key(c, kind) == case_key(crop, kind)
                )
                assert template["source"]["GFX_sources"] == read(report_path)["sources"]
                result["source"] = copy.deepcopy(template["source"])
            label, digest = identity(crop)
            result["model"] = {
                **result.get("model", {}),
                "label": label,
                "sha256": digest,
                "native_source_report": ref(report_path),
                "native_source_PNG": png,
                "retained_baseline": retained_flag,
            }
            target = output / ("native-" + crop["png_sha256"] + ".png")
            assert not target.exists()
            shutil.copyfile(png["path"], target)
            result["image"] = target.name
            entries.append(result)
    report_path = output / "report.json"
    save(
        report_path,
        {
            **{
                k: fresh[k]
                for k in ["manifest", "patch_size", "native_crop", "split", "protocol"]
                if k in fresh
            },
            "native_crops": entries,
            "GFX_input_witnesses": witnesses,
            "scope": "Matched retained V43/RawNIND baseline supplement. Exact original PNGs and labels; no inference, warping, resizing or new quality finding. Actual manual review required.",
        },
    )
    return build([report_path], output / "board.png", kind)


def run(plan):
    import torch

    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    results = []
    for panel, specification in plan["panels"].items():
        result = append_references(
            specification["fresh_report"],
            specification["retained"],
            Path(plan["output"]) / panel,
            specification["kind"],
            gfx_fixture=plan.get("gfx_fixture"),
        )
        results.append(
            {
                "panel": panel,
                "board": result["board"],
                "receipt": ref(Path(plan["output"]) / panel / "board.json"),
                "native_cells": result["native_cells_exact"],
                "triplets": len(result["source_triplets"]),
            }
        )
    save(
        Path(plan["output"]) / "receipt.json",
        {
            "status": "prepared-directional-working-reference-boards-awaiting-manual-review",
            "boards": results,
            "scope": "No new inference or quality decision. Source/ROI/noise/exposure/reference metadata and unchanged native cells verified. Every final board needs actual viewing.",
        },
    )
    assert not torch.cuda.is_initialized()
    return results


def main(plan_path):
    os.nice(10)
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    plan = read(plan_path)
    assert ref(__file__) == plan["worker"]
    status_path = Path(plan["closure_root"]) / "closure-status.json"
    while True:
        status = read(status_path)
        assert status["controller"] == plan["closure_owner"]
        if status["status"].startswith("failed-"):
            raise RuntimeError("CPU closure failed; no automatic supplement or retry")
        if not alive(plan["closure_owner"]):
            assert (
                status["status"]
                == "completed-CPU-numerical-and-native-board-preparation-awaiting-manual-review"
            )
            break
        time.sleep(5)
    Path(plan["output"]).mkdir(parents=True, exist_ok=False)
    print(json.dumps({"boards": run(plan)}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    main(parser.parse_args().plan)
