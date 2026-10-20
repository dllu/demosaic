"""Full fixed analytic/color/real-scene fields for paired mature precision review."""

import copy
from pathlib import Path

import numpy as np
from audit_colored_flats import metrics as color_metrics
from build_native_crop_board import MODEL_FIELDS, read_crop
from mature_precision_review_tools import carrier_metrics, flat_metrics, linear_rgb
from mature_quality_pairs import POLICIES, load_arrays, native_pair, physical_rows, save_new
from train_directional_bank_trial import read, ref

from demosaic.reporting import display_crop, save_triplet


def analytic_panel(runner, fixtures, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    rows, crops, observations = [], [], []
    for fixture in fixtures:
        host = load_arrays(fixture["arrays"])
        pred, digest = runner(host, fixture["condition"])
        truth = linear_rgb(host["target"].numpy(), host["wb"].numpy(), host["matrix"].numpy())
        measured, paths = {}, {}
        for policy in POLICIES:
            path = output / (fixture["id"] + "-" + policy + ".npy")
            np.save(path, pred[policy].numpy(), allow_pickle=False)
            paths[policy] = ref(path)
            p = linear_rgb(pred[policy].numpy(), host["wb"].numpy(), host["matrix"].numpy())
            measured[policy] = (
                carrier_metrics(p, truth, fixture["period"])
                if fixture["kind"] == "carrier"
                else flat_metrics(p, truth)
            )
        differences = physical_rows(pred["fp32"], pred["fp16-hidden"])
        for j, case in enumerate(fixture["cases"]):
            # ADC aliases retain the old case labels without another identical forward.
            for draw in case["draw_aliases"]:
                rows.append(
                    {
                        "kind": fixture["kind"],
                        "level": fixture["level"],
                        "contrast": fixture["contrast"],
                        "period": fixture["period"],
                        "condition": fixture["condition"]["name"],
                        "pattern": case["pattern"],
                        "draw": draw,
                        "physical_observation": fixture["id"] + ":" + str(j),
                        "actual_draw": case["draw"],
                        "input_sha256": digest,
                        "RGB": paths,
                        "index_in_RGB": j,
                        "physical": differences[j],
                        "metrics": {
                            p: {k: float(v[j]) for k, v in measured[p].items()} for p in POLICIES
                        },
                    }
                )
            selected = [
                fixture["kind"],
                fixture["level"],
                fixture["contrast"],
                fixture["period"],
            ] in [["carrier", 0.01, 0.1, 8], ["carrier", 0.18, 0.02, 16], ["flat", 0.18, 0, None]]
            if (
                selected
                and fixture["condition"]["name"] == "iso12800-prior"
                and case["pattern"] == "RGGB"
                and case["draw"] == 0
            ):
                key = fixture["id"] + ":" + str(j)
                metadata = {
                    "source_id": key,
                    "source": {
                        "kind": "analytic",
                        "fixture": fixture["arrays"],
                        "case": case,
                        "formula": "level*(1+contrast*cos(2*pi*x/period))"
                        if fixture["kind"] == "carrier"
                        else "constant level",
                    },
                    "evaluation_tile_xywh": [48, 48, 160, 160],
                    "condition": fixture["condition"],
                    "pattern": case["pattern"],
                    "white_balance": host["wb"][j].tolist(),
                    "camera_to_srgb": host["matrix"][j].tolist(),
                    "reference": "Exact analytic clean target",
                }
                sliced = {k: v[j : j + 1] for k, v in host.items()}
                crops += native_pair(
                    runner,
                    output,
                    key,
                    {p: v[j : j + 1] for p, v in pred.items()},
                    sliced,
                    metadata,
                    roi=[48, 48, 160, 160],
                    reference="GT (analytic)",
                    exposure=16 if fixture["level"] == 0.01 else 1,
                )
        observations.append({"fixture": fixture, "RGB": paths})
    if len(rows) != 448 or len(observations) != 70:
        raise ValueError("Full analytic coverage differs")
    save_new(
        output / "report.json",
        {
            "status": "completed-full-analytic-policy-arrays-awaiting-native-and-scalar-review",
            "rows": rows,
            "observations": observations,
            "native_crops": crops,
            "physical_observations_per_policy": 280,
            "labeled_cases_per_policy": 448,
        },
    )


def hue_panel(runner, hue_ref, preview_indices, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    plan = read(hue_ref["path"])
    rows, crops = [], []
    for i, case in enumerate(plan["cases"]):
        source = {"path": case["arrays"], "sha256": case["sha256"]}
        host = load_arrays(source)
        pred, digest = runner(host, case["condition"])
        paths, scores = {}, {}
        original = {k: v.numpy() for k, v in host.items()}
        for policy in POLICIES:
            path = output / f"case-{i:04d}-{policy}.npy"
            np.save(path, pred[policy].numpy(), allow_pickle=False)
            paths[policy] = ref(path)
            scores[policy] = color_metrics(pred[policy].numpy(), original)
        rows.append(
            {
                "kind": "hue",
                "case_index": i,
                "case": case,
                "metrics": scores,
                "RGB": paths,
                "physical": physical_rows(pred["fp32"], pred["fp16-hidden"])[0],
                "input_sha256": digest,
            }
        )
        if i in preview_indices:
            metadata = {
                "case": case,
                "ROI_xywh": plan["roi_xywh"],
                "conditioning": case["condition"],
                "white_balance": plan["white_balance"],
                "camera_to_srgb": plan["camera_to_srgb"],
                "reference": "Exact uniform analytic target",
            }
            crops += native_pair(
                runner,
                output,
                case["id"],
                pred,
                host,
                metadata,
                roi=plan["roi_xywh"],
                reference="GT (analytic)",
            )
        if (i + 1) % 96 == 0:
            print({"stage": "hue", "model": runner.label, "cases_done": i + 1}, flush=True)
    if len(rows) != 1176 or len(crops) != 14:
        raise ValueError("Full hue/native coverage differs")
    save_new(
        output / "report.json",
        {
            "status": "completed-full-hue-policy-arrays-awaiting-native-and-scalar-review",
            "input_plan": hue_ref,
            "rows": rows,
            "native_crops": crops,
        },
    )


def gfx_panel(runner, fixture_ref, observation, registry_ref, output):

    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    fixture = read(fixture_ref["path"])
    host = load_arrays(observation)
    pred, digest = runner(host, fixture["conditioning"])
    report_path = Path(registry_ref["path"])
    templates = [
        c for c in read(report_path)["native_crops"] if c["model_label"] == "V43:original-FP32"
    ]
    if len(templates) != 4:
        raise ValueError("Missing standing GFX regions")
    crops, arrays = [], {}
    for policy in POLICIES:
        path = output / (policy + "-RGB.npy")
        np.save(path, pred[policy].numpy(), allow_pickle=False)
        arrays[policy] = ref(path)
    for i, template in enumerate(templates):
        parts, _, _ = read_crop(report_path, template, "gfx")
        expected = fixture["gfx_regions"][i]
        if (
            template["region"] != expected["region"]
            or template["context_xywh"] != expected["context_xywh"]
        ):
            raise ValueError("GFX ROI/source changed")
        metadata = {k: copy.deepcopy(v) for k, v in template.items() if k not in MODEL_FIELDS}
        x, y = template["region"]["noisy_xy"]
        cx, cy, _, _ = template["context_xywh"]
        roi = [x - cx, y - cy, 160, 160]
        for policy in POLICIES:
            model = {**runner.metadata(policy), "RGB": arrays[policy]}
            crops.append(
                save_triplet(
                    output,
                    model["label"] + ":" + template["region"]["name"],
                    [
                        ("Noisy (Malvar)", parts[0].astype(np.float64) / 255),
                        (
                            "Denoised",
                            display_crop(
                                pred[policy][i : i + 1],
                                host["wb"][i : i + 1],
                                host["matrix"][i : i + 1],
                                roi,
                                exposure=4,
                            ),
                        ),
                        ("ISO100 ref (not GT)", parts[2].astype(np.float64) / 255),
                    ],
                    caption=template["region"]["name"] + " / " + model["label"],
                    metadata={
                        **metadata,
                        "model": model,
                        "model_label": model["label"],
                        "checkpoint_sha256": runner.checkpoint["sha256"],
                    },
                )
            )
    save_new(
        output / "report.json",
        {
            "status": "completed-fresh-standing-GFX-policy-contexts-awaiting-native-review",
            "native_crops": crops,
            "RGB": arrays,
            "physical": physical_rows(pred["fp32"], pred["fp16-hidden"]),
            "input_sha256": digest,
            "reference": "Separate ISO100 exposure, not GT; no reference score",
        },
    )


def highlight_panel(runner, inputs_ref, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    plan = read(inputs_ref["path"])
    rows, crops = [], []
    for i, case in enumerate(plan["cases"]):
        host = load_arrays({"path": case["arrays"], "sha256": case["sha256"]})
        pred, digest = runner(host, plan["conditioning"])
        paths = {}
        for policy in POLICIES:
            path = output / f"case-{i}-{policy}.npy"
            np.save(path, pred[policy].numpy(), allow_pickle=False)
            paths[policy] = ref(path)
        metadata = {
            "source": plan["sources"],
            "region": case["region"],
            "context_xywh": case["context_xywh"],
            "ROI_xywh": case["ROI_xywh"],
            "conditioning": plan["conditioning"],
            "white_balance": plan["metadata"]["white_balance"],
            "camera_to_srgb": plan["metadata"]["camera_to_srgb"],
            "reference": "Independent DSCF3880 ISO100 f/5.6 AHD reference, not GT; optics/time/moving content differ",
        }
        crops += native_pair(
            runner,
            output,
            case["region"]["name"],
            pred,
            host,
            metadata,
            roi=case["ROI_xywh"],
            reference="ISO100 AHD / not GT",
            reference_rgb=host["reference_rgb"],
            exposure=plan["display_exposure"],
        )
        rows.append(
            {
                "case": case,
                "RGB": paths,
                "physical": physical_rows(pred["fp32"], pred["fp16-hidden"])[0],
                "input_sha256": digest,
            }
        )
    save_new(
        output / "report.json",
        {
            "status": "completed-supplementary-highlight-policy-contexts-awaiting-native-review",
            "rows": rows,
            "native_crops": crops,
            "reference_scores": None,
        },
    )
