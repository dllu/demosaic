"""Replay local phase correction bounds without changing fitted guides or RAW gates."""

import argparse
import importlib.util
import time
from itertools import product
from pathlib import Path

import numpy as np
from probe_fresh_phase_refit import write_array
from probe_surface_aggregation import deliver, field

from demosaic.cfa import PATTERNS
from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.local_validated_waves import LocalWaveConfig
from demosaic.surface_phase_aggregation import bound_phase_average, bound_phase_average_locally

MODES = ("weighted-refit", "tangent-predictive-gate", "global-energy", "local-peak", "local-energy")
STYLES = ("sloped-flat", "wedge", "bent-rail", "two-rails")
FRESH_SEED = 202611172041
TRIALS_PER_STYLE = 4
PEAK_WINDOW = 9
ENERGY_WINDOW = 33


def prepare(root, previous, structure):
    bundle = previous / "output/collection.json"
    original = read_json(bundle)
    old = read_json(checked(original["plan"]))
    disjoint = previous / "disjoint-panel.json"
    nulls = previous / "null-replay.json"
    null_data = read_json(nulls)
    assert checked(null_data["construct_and_corrupt"]) == structure
    root.mkdir()
    work, files = freeze_sources(
        Path.cwd(),
        root,
        [Path(__file__).name, "probe_matched_query_evidence.py", "report_scene_wave_guides.py"],
    )
    write_json(
        root / "plan.json",
        old
        | {
            "root": str(root),
            "work": str(work),
            "frozen_files": files,
            "driver": reference(work / "scripts" / Path(__file__).name),
            "previous": reference(bundle),
            "previous_plan": original["plan"],
            "inputs": [
                reference(bundle),
                original["plan"],
                reference(disjoint),
                reference(nulls),
                reference(structure),
                null_data["source"],
                old["camera_baseline"],
            ],
            "disjoint": reference(disjoint),
            "previous_nulls": reference(nulls),
            "structure": reference(structure),
            "previous_null_design": null_data["source"],
            "peak_window": PEAK_WINDOW,
            "energy_window": ENERGY_WINDOW,
            "modes": MODES,
            "fresh": {"seed": FRESH_SEED, "styles": STYLES, "trials_per_style": TRIALS_PER_STYLE},
            "scope": "Compare existing refit, unbounded tangent, exact previous whole-query cap, "
            "signed 9-pixel local extrema and the same extrema with a 33-pixel local "
            "energy constraint. Keep gates and geometry fixed. Replay frozen positives and "
            "both cameras, repeat the original nulls and stress four new structure families.",
        },
    )


def compare(parent, baseline, tangent):
    return {
        "weighted-refit": baseline,
        "tangent-predictive-gate": tangent,
        "global-energy": bound_phase_average(parent, baseline, tangent),
        "local-peak": bound_phase_average_locally(
            parent, baseline, tangent, peak_window=PEAK_WINDOW
        ),
        "local-energy": bound_phase_average_locally(
            parent, baseline, tangent, peak_window=PEAK_WINDOW, energy_window=ENERGY_WINDOW
        ),
    }


def adopt(plan):
    original = read_json(checked(plan["previous"]))
    disjoint = read_json(checked(plan["disjoint"]))
    out = Path(plan["root"]) / "output"
    out.mkdir()
    result = {}
    for label, rows, key, guides, roles in (
        ("synthetic", original["synthetic"], "prediction", ("scene", "exact-center"), True),
        ("disjoint", disjoint["rows"], "prediction", ("scene",), True),
        ("camera", original["camera"], "predictions", ("scene", "spectral"), False),
    ):
        collected = []
        for row in rows:
            with np.load(checked(row[key])) as f:
                original_arrays = dict(f)
            parent = original_arrays["parent"]
            arrays = {"parent": parent}
            for guide, offset in product(guides, (0,) if label == "disjoint" else (0, 1)):
                baseline = original_arrays[field(guide, "weighted-refit", offset)]
                tangent = original_arrays[field(guide, "tangent-predictive-gate", offset)]
                if roles:
                    estimates = [
                        compare(p, b, t) for p, b, t in zip(parent, baseline, tangent, strict=True)
                    ]
                    arrays.update(
                        {
                            field(guide, mode, offset): np.stack([v[mode] for v in estimates])
                            for mode in MODES
                        }
                    )
                else:
                    arrays.update(
                        {
                            field(guide, mode, offset): v
                            for mode, v in compare(parent, baseline, tangent).items()
                        }
                    )
                if label == "disjoint":
                    np.testing.assert_array_equal(
                        arrays[field("scene", "global-energy", 0)],
                        original_arrays["scene-bounded-tangent"],
                    )
            collected.append(
                row
                | {
                    "prior_prediction": row[key],
                    key: write_array(out / f"{row['id']}.npz", **arrays),
                }
            )
        result[label] = collected
    assert tuple(map(len, result.values())) == (16, 16, 8)
    write_json(
        out / "collection.json",
        {
            "plan": reference(Path(plan["root"]) / "plan.json"),
            "producer": reference(__file__),
            **result,
        },
    )


def structure_module(binding):
    module = importlib.util.spec_from_file_location("frozen_structure_recipes", checked(binding))
    loaded = importlib.util.module_from_spec(module)
    module.loader.exec_module(loaded)
    return loaded


def fresh_structure(style, angle, width, shift, level, height):
    yy, xx = np.ogrid[:256, :256]
    a, b = np.cos(angle), np.sin(angle)
    x0, y0 = xx - 127.5, yy - 127.5
    response = np.zeros((256, 256))
    for x, y in product(np.linspace(-0.4, 0.4, 5), repeat=2):
        normal = a * (x0 + x) + b * (y0 + y) - shift
        tangent = b * (x0 + x) - a * (y0 + y)
        if style == "sloped-flat":
            covered = 0.10 * (0.4 + 0.45 * x0 / 128 + 0.12 * y0 / 128)
        elif style == "wedge":
            covered = (normal > 0) & (normal < width + 4 * tangent / 128)
        elif style == "bent-rail":
            curve = 8 * (tangent / 128) ** 2 - 3
            covered = (normal > curve) & (normal < curve + width)
        else:
            covered = ((normal > 0) & (normal < width)).astype(float)
            covered += 0.65 * ((normal > width + 11) & (normal < 1.65 * width + 11))
        response += covered / 25
    modulation = level + height * response
    return (modulation * np.array([0.84, 1, 0.79])[:, None, None]).astype(np.float32)


def fresh_cases(plan):
    for i, (profile, style, trial) in enumerate(
        product(plan["profiles"], STYLES, range(TRIALS_PER_STYLE))
    ):
        rng = np.random.default_rng(np.random.SeedSequence([FRESH_SEED, 0, i]))
        angle, width, shift, level, height = [
            float(rng.uniform(a, b))
            for a, b in ((0.07, 3.05), (6, 14), (-29, 29), (0.035, 0.085), (0.05, 0.15))
        ]
        period = np.clip(2 * width, 8, 26)
        a, b = np.cos(angle) / period, np.sin(angle) / period
        yield {
            "profile": profile,
            "style": style,
            "trial": trial,
            "CFA": tuple(PATTERNS)[trial],
            "angle_radians": angle,
            "width_shift_level_height": [width, shift, level, height],
            "guide_frequencies_xy": [[a, b], [-b, a]],
            "noise_seed": [FRESH_SEED, 1, i],
        }


def null_panel(plan, label):
    original = structure_module(plan["structure"])
    scope = Path(plan["root"])
    cfg = LocalWaveConfig(**plan["config"])
    before = read_json(checked(plan["previous_nulls"]))
    if label == "retained":
        previous = read_json(checked(plan["previous_null_design"]))
        assert len(previous["rows"]) == len(before["rows"]) == 36
        profiles = list(plan["profiles"])
        styles = ["flat", "step", "rail"]
        cases = (
            r
            | {
                "noise_seed": [
                    original.SEED,
                    1,
                    profiles.index(r["profile"]),
                    styles.index(r["style"]),
                    r["trial"],
                ]
            }
            for r in previous["rows"]
        )
        constructor = original.construct
    else:
        cases = fresh_cases(plan)
        constructor = fresh_structure
    rows = []
    for idx, row in enumerate(cases):
        profile, style, trial = row["profile"], row["style"], row["trial"]
        colors = np.array(PATTERNS[row["CFA"]])
        parent = constructor(style, row["angle_radians"], *row["width_shift_level_height"])
        noise = plan["profiles"][profile]
        rng = np.random.default_rng(np.random.SeedSequence(row["noise_seed"]))
        packed = original.corrupt(parent, colors, rng, noise)
        fit = {"null": {"active": [True, True], "frequencies_xy": row["guide_frequencies_xy"]}}
        raw, _ = deliver(
            parent,
            packed,
            colors,
            fit,
            noise,
            original.QUERY,
            cfg,
            plan["settings"][profile]["threshold"],
        )
        metrics = {}
        for offset in (0, 1):
            outputs = compare(
                parent,
                raw[field("null", "weighted-refit", offset)],
                raw[field("null", "tangent-predictive-gate", offset)],
            )
            for name, output in outputs.items():
                d = (output[original.MEASURE].astype(float) - parent[original.MEASURE]) * 65535
                ident = field("null", name, offset)
                metrics[ident] = {
                    "RMS_DN16": float(np.sqrt(np.mean(d**2))),
                    "max_abs_DN16": float(np.max(np.abs(d))),
                    "changed_pixels": int(np.any(d != 0, axis=0).sum()),
                }
                if label == "retained" and name in (
                    "weighted-refit",
                    "tangent-predictive-gate",
                    "global-energy",
                ):
                    old_name = (
                        field("null", "bounded-tangent", offset)
                        if name == "global-energy"
                        else ident
                    )
                    assert metrics[ident] == before["rows"][idx]["metrics"][old_name]
        if label == "retained":
            assert (profile, style, trial) == tuple(
                before["rows"][idx][k] for k in ("profile", "style", "trial")
            )
        rows.append(
            {k: v for k, v in row.items() if k not in ("metrics", "parallel_edges")}
            | {"metrics": metrics}
        )
        print(label, profile, style, trial, flush=True)
    assert len(rows) == (36 if label == "retained" else 32)
    write_json(
        scope / f"null-{label}.json",
        {"plan": reference(scope / "plan.json"), "producer": reference(__file__), "rows": rows},
    )


def run(path, work):
    import torch

    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    start = time.monotonic()
    if work == "adopt":
        adopt(plan)
    else:
        null_panel(plan, work)
    print(work, "seconds", time.monotonic() - start, flush=True)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    actions = cli.add_subparsers(dest="action", required=True)
    setup = actions.add_parser("prepare")
    setup.add_argument("root", type=Path)
    setup.add_argument("previous", type=Path)
    setup.add_argument("structure", type=Path)
    execute = actions.add_parser("run")
    execute.add_argument("plan", type=Path)
    execute.add_argument("work", choices=("adopt", "retained", "fresh"))
    cmd = cli.parse_args()
    if cmd.action == "prepare":
        prepare(cmd.root.resolve(), cmd.previous.resolve(), cmd.structure.resolve())
    else:
        run(cmd.plan.resolve(), cmd.work)
