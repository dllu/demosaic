"""Close a complete camera panel while the remaining primary collection runs."""

import argparse
import ast
import csv
import inspect
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

from demosaic.experiments.artifacts import checked, read_json, reference, write_json
from demosaic.real_suite import measured_sensor_psnr
from demosaic.suite import summarize


@torch.inference_mode()
def analyze(root, stage, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    plan_path = root / "full-plan.json"
    plan = read_json(plan_path)
    # Use exactly the trained collector's metric/aggregation functions. This
    # observer cannot quietly change a formula while a frozen producer runs.
    for filename, function in [("real_suite.py", measured_sensor_psnr), ("suite.py", summarize)]:
        tree = ast.parse((Path(plan["work"]) / "src/demosaic" / filename).read_text())
        original = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function.__name__)
        assert ast.dump(original) == ast.dump(ast.parse(inspect.getsource(function)).body[0])
    torch.set_num_threads(4)
    canonical = read_json(checked(plan["canonical_inputs"]))
    records = [r for r in canonical["records"] if r["stage"] == stage]
    assert len(records) == plan["stages"][stage]["calls_per_model"]
    preflight = read_json(checked(plan["preflight"]))
    inherited = {}
    for binding in preflight["case_records"]:
        case = read_json(checked(binding))
        inherited[case["stage"], case["batch"]] = binding
    bindings = []
    for record in records:
        key = stage, record["batch"]
        path = root / "full" / f"{stage}-{record['batch']:05d}" / "result.json"
        if key in inherited:
            binding = inherited[key]
        elif path.exists():
            binding = reference(path)
        else:
            raise RuntimeError(f"Panel incomplete; batch {key} has no closed result. Do not publish a partial mean.")
        bindings.append(binding)
    rows, native, metric_checks = [], [], []
    seen_scenes = set()
    for record, binding in zip(records, bindings, strict=True):
        case = read_json(checked(binding))
        assert case["stage"] == stage and case["batch"] == record["batch"]
        assert case["canonical_arrays"] == record["arrays"]
        assert [v["arm"] for v in case["variants"]] == ["V120", "none", "pooled", "spatial"]
        with np.load(checked(record["arrays"]), allow_pickle=False) as data:
            target = torch.from_numpy(data["sensor_reference"].copy())[..., 32:-32, 32:-32]
            mask = torch.from_numpy(data["sensor_mask"].copy())[..., 32:-32, 32:-32]
        for variant in case["variants"]:
            arm = variant["arm"]
            assert variant["checkpoint"] == plan["models"][arm]["checkpoint"]
            prediction = torch.from_numpy(np.load(checked(variant["prediction"]), allow_pickle=False))
            assert torch.isfinite(prediction).all()
            scores, counts = measured_sensor_psnr(prediction[..., 32:-32, 32:-32], target, mask)
            saved_scores = [r["metrics"]["sensor_psnr"] for r in variant["rows"]]
            saved_counts = [r["metrics"]["reference_samples"] for r in variant["rows"]]
            assert scores.tolist() == saved_scores and counts.tolist() == saved_counts
            assert [r["id"] for r in variant["rows"]] == record["context"]["ids"]
            rows.extend(variant["rows"])
            metric_checks.append({"batch": record["batch"], "arm": arm, "native_predictions": len(scores), "scores_bit_exact": True})
        if record["context"]["scene"] not in seen_scenes:
            seen_scenes.add(record["context"]["scene"])
            native.append({"case": binding, "canonical": record, "sample": 0,
                           "selection": "First capture/first native crop of every fixed scene; center160, declared independently of scores."})
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["model"], row["scene"], row["pair"], row["pattern"]].append(row)
    pairs = []
    for (arm, scene, pair, pattern), values in grouped.items():
        assert len(values) == 9
        metrics = {}
        for key in values[0]["metrics"]:
            observed = [r["metrics"][key] for r in values if r["metrics"][key] is not None]
            metrics[key] = float(np.mean(observed)) if observed else None
        pairs.append({"model": arm, "id": scene, "kind": "real", "condition": pair,
                      "pattern": pattern, "metrics": metrics})
    scenes = defaultdict(list)
    for pair in pairs:
        scenes[pair["model"], pair["id"]].append(pair)
    scene_rows = []
    for (arm, scene), values in sorted(scenes.items()):
        assert len(values) == 2
        scene_rows.append({"arm": arm, "scene": scene,
                           "sensor_psnr": float(np.mean([r["metrics"]["sensor_psnr"] for r in values])),
                           "ahd_srgb_psnr": float(np.mean([r["metrics"]["ahd_srgb_psnr"] for r in values]))})
    expected_scenes = 4 if stage == "known" else 5
    assert len(scene_rows) == expected_scenes * 4
    assert len(rows) == plan["stages"][stage]["observations_per_model"] * 4
    summary = summarize(pairs, comparison_metrics=("sensor_psnr", "ahd_srgb_psnr", "ahd_srgb_ssim"))
    aggregation_checks = []
    for overall in summary["overall"]:
        observed = [r["sensor_psnr"] for r in scene_rows if r["arm"] == overall["model"]]
        delta = float(np.mean(observed)) - overall["metrics"]["sensor_psnr"]["mean"]
        # These independent sums use sorted versus manifest scene order. Their
        # FP64 rounding may differ; retain the exact difference and require it
        # below1e-12 dB. Per-crop original FP32 scores above remain bit-exact.
        assert abs(delta) < 1e-12
        aggregation_checks.append({"arm": overall["model"], "sorted_minus_manifest_order_dB": delta})
    output.mkdir(parents=True)
    table = output / "per-crop.csv"
    names = list(rows[0]["metrics"])
    with table.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["model", "scene", "pair", "id", *names])
        writer.writeheader()
        writer.writerows({**{k: row[k] for k in ["model", "scene", "pair", "id"]}, **row["metrics"]} for row in rows)
    write_json(output / "result.json", {
        "script": reference(__file__), "plan": reference(plan_path), "stage": stage,
        "cases": bindings, "metric_checks": metric_checks, "per_scene": scene_rows,
        "aggregation_checks": aggregation_checks,
        "per_pair": pairs, "summary": summary, "per_crop": reference(table), "native_selection": native,
        "models": plan["models"], "weights": "EMA", "inference_policy": "Original collector: CPU IEEE FP32 native B4/B1, shared checked frozen local features; full noisy scene for pooled/spatial.",
        "scope": "Complete fixed camera panel, all captures/native crops. Recomputed measured-CFA metrics from saved predictions exactly; averages crops within capture, captures within scene, then scenes. Independent AHD RGB metrics are auxiliary, not exact RGB GT. This observer makes0 neural/GPU/noise/RAW/optimizer calls. Full427 photo collection and actual native viewing are separate; no partial photo mean or primary chart point is inferred.",
    })
    print(stage, "complete", len(bindings), "batches", expected_scenes, "scenes", len(rows), "crop/model rows")
    for value in summary["overall"]:
        print(value["model"], value["metrics"]["sensor_psnr"]["mean"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("stage", choices=["known", "unseen"])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    analyze(args.root, args.stage, args.output)
