"""Score completed phase-profile outputs on paired synthetic roles and render the GFX crops."""

import argparse
import os
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from probe_phase_profiles import names
from report_scene_wave_guides import native_board

from demosaic.archive_metrics import display, noisy_malvar
from demosaic.experiments.artifacts import checked, read_json, reference, write_json
from demosaic.experiments.evaluation.edge_response import measure

METHODS = ("V143", *names())


def rms(value):
    return float(np.sqrt(np.mean(value**2, dtype=np.float64)) * 65535)


def report_synthetic(plan, collection, output):
    scores, boards = [], []
    by_case = {row["id"]: row for row in collection["synthetic"]}
    for group in plan["groups"]:
        with np.load(checked(group["arrays"])) as data:
            arrays = dict(data)
        parent = np.load(checked(group["parent"]))
        truth = arrays["target"].astype(np.float64)
        weak = truth[2] - truth[1]
        target_energy = np.sum(weak**2)
        quiet = arrays["quiet"][128:384, 128:384]
        region = np.s_[..., 128:384, 128:384]
        assert quiet.any()
        output_by_method = {name: parent.copy() for name in METHODS}
        for sample in by_case[group["id"]]["rows"]:
            with np.load(checked(sample["prediction"])) as data:
                for method in METHODS[1:]:
                    output_by_method[method][sample["role"]][region] = data[method]
        for method, rgb in output_by_method.items():
            metrics = measure(arrays, rgb)
            error = rgb.astype(np.float64) - truth
            metrics["query_full_RMS_DN16"] = rms(error[region])
            metrics["query_quiet_RMS_DN16"] = rms(error[region][..., quiet])
            metrics["query_weak_absent_RMS_DN16"] = rms(error[1][region])
            metrics["weak_absent_projection"] = float(np.sum(error[1] * weak) / target_energy)
            scores.append(
                {
                    **{k: group[k] for k in ("id", "profile", "source", "placement", "CFA")},
                    "method": method,
                    **metrics,
                }
            )
        if group["profile"] == "iso400" and group["source"] in (0, 1) and group["CFA"] == "RGGB":
            context = {key: arrays[key][2:3] for key in ("colors", "wb", "matrix")}
            context["packed"] = arrays["packed"][2:3, :, 64:192, 64:192]
            values = [
                noisy_malvar(context)[0],
                *[
                    output_by_method[k][2][region]
                    for k in ("V143", "sinusoid-t2", "phase-profile-t2")
                ],
                truth[2][region],
            ]
            boards.append(
                native_board(
                    output,
                    group["id"],
                    values,
                    context,
                    {"group": group, "role": 2},
                    labels=("Noisy Malvar", "V143 EMA", "Sinusoid", "Phase bins", "Exact GT"),
                    triplet_indices=(0, 3, 4),
                )
            )
    assert len(scores) == 896 and len(boards) == 4
    return scores, boards


def report_real(plan, collection, output):
    real = read_json(checked(plan["camera_guide_source"]))
    original = read_json(Path(real["plan"]["path"]).with_name("result.json"))
    old = {v["id"]: v for v in original["boards"]}
    by_case = {row["id"]: row for row in collection["camera"]}
    boards = []
    for row in plan["camera_cases"]:
        key = row["id"]
        baseline = old[key]
        source = np.asarray(Image.open(checked(baseline["image"])))
        aligned = by_case[key]
        with np.load(checked(row["query_arrays"])) as data:
            calibration = {k: data[k] for k in ("wb", "matrix")}
        with np.load(checked(aligned["prediction"])) as data:
            phase, sinusoid = [data[k] for k in ("phase-profile-t2", "sinusoid-t2")]
        with np.load(checked(row["prediction"])) as data:
            parent = data["parent"]
        base_x, base_y = row["query_box"][:2]
        rx, ry, w, h = baseline["ROI_xywh"]
        x, y = rx - base_x, ry - base_y
        assert w == h == 160
        roi = np.s_[:, y : y + h, x : x + w]
        exposure = baseline["display_exposure"]
        srgb = display(phase[None], calibration, exposure=exposure)[0][roi]
        phase_pixels = np.rint(srgb.transpose(1, 2, 0) * 255).astype(np.uint8)
        pixels = []
        for i, panel in enumerate(baseline["panels"]):
            px, py, pw, ph = panel["png_xywh"]
            if i == 3:
                pixels.append(("Sinusoid guide", source[py : py + ph, px : px + pw]))
                pixels.append(("Phase bins guide", phase_pixels))
            else:
                pixels.append((panel["label"], source[py : py + ph, px : px + pw]))
        image = Image.new("RGB", (8 + 168 * len(pixels), 192), "#eeeeee")
        draw = ImageDraw.Draw(image)
        panels = []
        for i, (label, values) in enumerate(pixels):
            assert values.shape == (160, 160, 3)
            px = 8 + 168 * i
            image.paste(Image.fromarray(values), (px, 24))
            draw.text((px, 5), label, fill="black")
            panels.append({"label": label, "png_xywh": [px, 24, 160, 160]})
        path = output / (key + ".png")
        image.save(path)
        new = np.asarray(Image.open(path))
        for p, (_, values) in zip(panels, pixels, strict=True):
            px, py, pw, ph = p["png_xywh"]
            np.testing.assert_array_equal(new[py : py + ph, px : px + pw], values)
        boards.append(
            {
                "id": key,
                "image": reference(path),
                "panels": panels,
                "original_board": baseline,
                "source": row,
                "prediction": aligned["prediction"],
                "phase_correction_RMS_DN16": rms(phase[roi].astype(np.float64) - parent[roi]),
                "sinusoid_correction_RMS_DN16": rms(sinusoid[roi].astype(np.float64) - parent[roi]),
            }
        )
    assert len(boards) == 8
    return boards


def report(path):
    plan = read_json(path)
    assert reference(__file__)["sha256"] == plan["frozen_files"][str(Path(__file__))]
    root = Path(plan["root"])
    receipt = root / "output/collection.json"
    collection = read_json(receipt)
    assert collection["plan"] == reference(path) and collection["query_roles"] == 384
    output = root / "review"
    output.mkdir()
    scores, simulated = report_synthetic(plan, collection, output)
    cameras = report_real(plan, collection, output)
    by_arm = defaultdict(list)
    for row in scores:
        by_arm[row["profile"], row["placement"], row["method"]].append(row)
    label_fields = {"id", "profile", "placement", "method", "source", "CFA"}
    means = []
    for (profile, placement, method), rows in by_arm.items():
        assert len(rows) == 32
        assert {v["CFA"] for v in rows} == {"RGGB", "BGGR", "GBRG", "GRBG"}
        means.append(
            {
                "profile": profile,
                "placement": placement,
                "method": method,
                **{
                    key: float(np.mean([v[key] for v in rows]))
                    for key in sorted(set(rows[0]) - label_fields)
                },
            }
        )
    write_json(
        output / "result.json",
        {
            "driver": reference(__file__),
            "collection": reference(receipt),
            "plan": reference(path),
            "metrics": scores,
            "mean_over_8_sources_and_4_CFAs": means,
            "synthetic_boards": simulated,
            "camera_boards": cameras,
            "viewing": "pending",
            "scope": "All fits close before targets enter. Eight fresh-noise query geometries,"
            " with source-balanced equal-CFA averages. Existing full-field finite-wire"
            " metrics plus quiet/absent error in the 256px query. Eight native GFX"
            " comparisons use the exact old noisy/AHD and JPEG pixels. Qualitative"
            " real comparison only. No model calls or sensor draws.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    os.sched_setaffinity(0, [6, 7])
    os.nice(10)
    report(parser.parse_args().plan.resolve())
