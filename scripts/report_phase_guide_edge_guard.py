"""Score the edge exclusion against the same fixed and unguarded guides."""

import argparse
import os
from pathlib import Path

import numpy as np
from probe_phase_guide_edge_guard import WIDTHS
from report_fold_support_pooling import ROI, evaluated, insert_camera_panels, measure
from report_fresh_phase_refit import donor_errors
from report_scene_wave_guides import native_board

from demosaic.archive_metrics import display, noisy_malvar
from demosaic.experiments.artifacts import checked, read_json, reference, write_json


def camera_boards(output, plan, collected):
    images = []
    for item, new in zip(plan["camera"], collected, strict=True):
        original = item["board"]
        scene = original["source"]
        assert new["id"] == original["id"]
        x, y, w, h = original["ROI_xywh"]
        bx, by, *_ = scene["query_box"]
        crop = np.s_[:, y - by : y - by + h, x - bx : x - bx + w]
        with np.load(checked(scene["query_arrays"])) as f:
            context = {k: f[k] for k in ("wb", "matrix")}
        additions, changes, excluded = [], {}, {}
        with (
            np.load(checked(new["output"])) as f,
            np.load(checked(original["new_prediction"])) as b,
        ):
            before = b["weighted-refit-t2"][crop].astype(np.float64)
            for width in WIDTHS:
                name = f"guard{width}"
                value = f[name]
                after = value[crop].astype(np.float64)
                changes[name] = float(np.sqrt(np.mean((after - before) ** 2)) * 65535)
                record = new["fits"][name]["records"][0]
                excluded[name] = record["guide_search_excluded"]
                if not any(excluded[name]):
                    np.testing.assert_array_equal(after, before)
                rgb = display(value[None], context, exposure=original["display_exposure"])[0][crop]
                additions.append(
                    (
                        f"Edge guard {width}px",
                        np.rint(rgb.transpose(1, 2, 0) * 255).astype(np.uint8),
                    )
                )
        image, panels = insert_camera_panels(
            output, original["id"], original, "Recentered weighted", additions
        )
        images.append(
            {
                **original,
                "image": image,
                "panels": panels,
                "previous_image": original["image"],
                "guarded_prediction": new["output"],
                "change_from_unguarded_RMS_DN16": changes,
                "excluded_green_sites": excluded,
            }
        )
    assert len(images) == 8
    return images


def report(path):
    plan = read_json(path)
    frozen_reporter = Path(plan["work"]) / "scripts" / Path(__file__).name
    assert plan["frozen_files"][str(frozen_reporter)] == reference(frozen_reporter)["sha256"]
    root = Path(plan["root"])
    closed = root / "output/collection.json"
    collection = read_json(closed)
    before = read_json(checked(plan["previous_report"]))
    assert collection["plan"] == reference(path) and collection["new_synthetic_calls"] == 576
    output = root / "review"
    output.mkdir()
    rows, boards, guides = [], [], []
    exact = 0
    for link in collection["synthetic"]:
        observed = read_json(checked(link))
        prior = read_json(checked(observed["previous"]))
        case = read_json(checked(observed["case"]))
        key = case["id"]
        assert key == observed["id"] == prior["id"] and observed["case"] == prior["case"]
        meta = {k: case[k] for k in ("id", "source", "profile", "placement", "CFA")}
        all_settings = [
            r
            for r in plan["settings"]
            if (r["profile"], r["placement"]) == (case["profile"], case["placement"])
        ]
        assert len(all_settings) == 4
        parent = np.load(checked(case["parent"])).astype(np.float64)
        with np.load(checked(case["target"])) as f:
            truth, quiet = f["target"].astype(np.float64), f["quiet"][ROI]
        with (
            np.load(checked(observed["output"])) as new,
            np.load(checked(prior["output"])) as saved,
            np.load(checked(case["predictions"])) as baseline,
        ):
            for arm, roles in observed["fits"].items():
                kind, guard = arm.split("-")
                for role, fit in enumerate(roles):
                    tile = fit["records"][0]
                    removed = tile["guide_search_excluded"]
                    assert fit["phase_guide_edge_guard_px"] == int(guard.removeprefix("guard"))
                    assert (
                        fit["guide_frequencies_xy"]
                        == prior["fits"][f"{kind}-recentered"][role]["guide_frequencies_xy"]
                    )
                    if not any(removed):
                        for name in new.files:
                            if name.startswith(arm + "--"):
                                prior_name = name.replace(arm, f"{kind}-recentered", 1)
                                np.testing.assert_array_equal(
                                    new[name][role], saved[prior_name][role]
                                )
                        exact += 1
                    for fold, frequency in enumerate(tile["frequencies"]):
                        guides.append(
                            {
                                **meta,
                                "arm": arm,
                                "role": role,
                                "fold": fold,
                                "excluded_sites": removed[fold],
                                "frequency_errors_native_bins": donor_errors(
                                    {
                                        "metadata": case["metadata"],
                                        "frequencies": frequency,
                                    }
                                ),
                            }
                        )
                for setting in all_settings:
                    name = f"{arm}--{setting['method']}-t{setting['threshold']:g}"
                    moments = measure(parent, truth, quiet, new[name])
                    values = evaluated(moments, setting["scale"])
                    parent_metrics = evaluated(moments, 0)
                    rows.append(
                        {
                            **meta,
                            **setting,
                            "arm": arm,
                            **values,
                            "delta_from_parent": {
                                k: v - parent_metrics[k] for k, v in values.items()
                            },
                        }
                    )
            if case["source"] in (40, 41) and case["placement"] == "near":
                setting = next(
                    s
                    for s in all_settings
                    if s["method"] == "weighted-refit" and s["budget_DN16"] == 0.02
                )
                k = f"weighted-refit-t{setting['threshold']:g}"
                p = parent[2][ROI]
                frames = [
                    p + setting["scale"] * (img[2] - p)
                    for img in [
                        baseline[k],
                        saved[f"nominal-recentered--{k}"],
                        *(new[f"nominal-guard{width}--{k}"] for width in WIDTHS),
                    ]
                ]
                with np.load(checked(case["sensor"])) as sensor:
                    context = {n: sensor[n][2:3] for n in ("colors", "wb", "matrix")}
                    context["packed"] = sensor["packed"][2:3, :, 64:192, 64:192]
                boards.append(
                    native_board(
                        output,
                        key,
                        [noisy_malvar(context)[0], *frames, truth[2][ROI]],
                        context,
                        {"case": case, "prediction": link, "operating_point": setting},
                        labels=(
                            "Noisy Malvar",
                            "Fixed guide",
                            "Unguarded search",
                            "Edge guard 8px",
                            "Edge guard 24px",
                            "Exact GT",
                        ),
                    )
                )
    assert len(rows) == len(before["metrics"]) == 768
    assert len(guides) == 1152 and len(boards) == 4
    write_json(
        output / "result.json",
        {
            "driver": reference(__file__),
            "plan": reference(path),
            "collection": reference(closed),
            "metrics": [*before["metrics"], *rows],
            "guarded_guide_choices": guides,
            "unguarded_guide_choices": before["guides"],
            "zero_exclusion_refits_bitexact": exact,
            "boards": boards,
            "camera": camera_boards(output, plan, collection["camera"]),
        },
    )
    print(len(rows), len(guides), exact, "edge exclusion report complete", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    os.sched_setaffinity(0, [6, 7])
    os.nice(10)
    report(args.path.resolve())
