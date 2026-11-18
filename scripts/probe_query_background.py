"""Compare exactly matched single- and two-boundary query background fits."""

import argparse
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
from probe_donor_phase_geometry import sensor_box
from probe_fresh_phase_refit import write_array
from probe_matched_query_evidence import deliver

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.local_validated_waves import LocalWaveConfig


def prepare(root, previous):
    source = reference(previous / "output/collection.json")
    source_plan = read_json(checked(read_json(checked(source))["plan"]))
    root.mkdir()
    work, hashes = freeze_sources(
        Path.cwd(), root, [Path(__file__).name, "report_scene_wave_guides.py"]
    )
    write_json(
        root / "plan.json",
        source_plan
        | {
            "root": str(root),
            "work": str(work),
            "driver": reference(work / "scripts" / Path(__file__).name),
            "frozen_files": hashes,
            "previous": source,
            "inputs": [source, source_plan["camera_baseline"], source_plan["camera_conditions"]],
            "scope": "Compare one and up to two parallel boundaries on the same A-only discovery "
            "samples. Both arms refine all edge offsets and use identical guide, amplitude, "
            "same-side eligibility and query score. Copy the historical A-only bounded-grid "
            "prediction arrays exactly. The original checkpoint and all sensor observations are fixed.",
        },
    )


def predict(parent, samples, colors, fits, noise, query, configs, threshold, *, edges=False):
    outputs, summaries = {}, {}
    for label, config in configs.items():
        values, diagnostics = deliver(
            parent, samples, colors, fits, noise, query, config, threshold, edges=edges
        )
        outputs.update({f"{label}-{key}": val for key, val in values.items() if key != "parent"})
        summaries[label] = diagnostics
    return outputs, summaries


def synth(plan, rows, configs, out):
    result = []
    for row in rows:
        case = read_json(checked(row["case"]))
        profile = case["profile"]
        threshold = plan["settings"][profile]["threshold"]
        noise = plan["profiles"][profile]
        packed, cfa = sensor_box(case["sensor"], plan["query_xywh"])
        with np.load(checked(row["prediction"])) as loaded:
            old = dict(loaded)
        local, witnesses = [], []
        for rgb, raw, colors, role in zip(old["parent"], packed, cfa, row["roles"], strict=True):
            fit = {key: role["fits"][key] for key in ("scene", "exact-center")}
            v, detail = predict(rgb, raw, colors, fit, noise, row["query"], configs, threshold)
            local.append(v)
            witnesses.append(detail)
        arrays = old | {k: np.stack([r[k] for r in local]) for k in local[0]}
        result.append(
            row
            | {
                "old_prediction": row["prediction"],
                "prediction": write_array(out / f"{row['id']}.npz", **arrays),
                "background_diagnostics": witnesses,
            }
        )
        print(row["id"], flush=True)
    return result


def camera(plan, rows, configs, out):
    baseline = read_json(checked(plan["camera_baseline"]))["camera"]
    noise = {
        r["board"]["id"]: r["noise"]
        for r in read_json(checked(plan["camera_conditions"]))["camera"]
    }
    result = []
    for row, witness in zip(rows, baseline, strict=True):
        key, source = witness["id"], witness["source"]
        assert key == row["id"]
        x, y, w, h = source["query_box"]
        with np.load(checked(source["query_arrays"])) as data:
            samples = data["packed"][0, :, y // 2 : (y + h) // 2, x // 2 : (x + w) // 2]
            colors = data["colors"][0]
        with np.load(checked(row["predictions"])) as data:
            old = dict(data)
        values, details = predict(
            old["parent"],
            samples,
            colors,
            row["fits"],
            noise[key],
            row["query"],
            configs,
            2,
            edges=True,
        )
        result.append(
            row
            | {
                "old_prediction": row["predictions"],
                "predictions": write_array(out / f"{key}.npz", **(old | values)),
                "background_diagnostics": details,
            }
        )
        print(row["id"], flush=True)
    return result


def collect(path):
    import torch

    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    source = read_json(checked(plan["previous"]))
    cfg = LocalWaveConfig(**plan["config"])
    configs = {
        "refined": replace(cfg, edge_search="full-frame"),
        "parallel": replace(cfg, edge_search="full-frame", background="parallel_step"),
    }
    out = Path(plan["root"]) / "output"
    out.mkdir()
    start = time.monotonic()
    rows = synth(plan, source["synthetic"], configs, out)
    cams = camera(plan, source["camera"], configs, out)
    assert len(rows) == 16 and len(cams) == 8
    write_json(
        out / "collection.json",
        {
            "plan": reference(path),
            "CPU_wall_seconds": time.monotonic() - start,
            "restoration_calls": 0,
            "synthetic": rows,
            "camera": cams,
            "compared_configs": {k: v.to_dict() for k, v in configs.items()},
        },
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    actions = cli.add_subparsers(dest="action", required=True)
    setup = actions.add_parser("prepare")
    setup.add_argument("root", type=Path)
    setup.add_argument("previous", type=Path)
    run = actions.add_parser("collect")
    run.add_argument("plan", type=Path)
    args = cli.parse_args()
    if args.action == "prepare":
        prepare(args.root.resolve(), args.previous.resolve())
    else:
        collect(args.plan.resolve())
