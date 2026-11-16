"""Compare fixed local-wave waveform arms using closed scores and native cells."""

import argparse
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from demosaic.experiments.artifacts import checked, read_json, reference, write_json


def report(root):
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[-2:])
    plan = read_json(root / "plan.json")
    closed = read_json(root / "both-arms-closed-before-GT.json")
    if closed["plan"] != reference(root / "plan.json"):
        raise ValueError("Study closure differs")
    if "comparison_sources" in plan:
        sources = {
            name: Path(checked(binding)).parent
            for name, binding in plan["comparison_sources"].items()
        }
        labels = {"individual": "H3 individual", "background": "H3 piecewise"}
    else:
        sources = {"H1-legacy": Path(checked(plan["controls"]["plan"])).parent}
        sources.update(
            {name: Path(checked(binding)).parent for name, binding in plan["arms"].items()}
        )
        labels = {"H1-legacy": "H1 legacy", "matching": "H1 matched", "harmonics": "H3 matched"}
    baseline = next(iter(sources))
    score_paths = {
        name: path
        / (
            "finite-scores-v2.json"
            if (path / "finite-scores-v2.json").exists()
            else "finite-scores.json"
        )
        for name, path in sources.items()
    }
    scores = {name: read_json(path)["rows"] for name, path in score_paths.items()}
    means = []
    for name, rows in scores.items():
        for placement in ["near", "far"]:
            for method in dict.fromkeys(r["method"] for r in rows):
                values = [r for r in rows if r["placement"] == placement and r["method"] == method]
                if len(values) != 2:
                    raise ValueError("Expected exactly two geometries per descriptive mean")
                means.append(
                    {
                        "arm": name,
                        "placement": placement,
                        "method": method,
                        **{
                            k: float(np.mean([v[k] for v in values]))
                            for k in values[0]
                            if k not in {"source", "placement", "method", "profile"}
                        },
                    }
                )
    reports = {
        name: read_json(
            path / ("report-v2" if (path / "report-v2").exists() else "report") / "report.json"
        )
        for name, path in sources.items()
    }
    output = root / "comparison"
    output.mkdir()
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)

    def cells(figure):
        value = np.asarray(Image.open(checked(figure["image"])))
        result = []
        for panel in figure["panels"]:
            x, y, w, h = panel["xywh"]
            if (w, h) != (160, 160):
                raise ValueError("Expected native160 source cells")
            result.append((panel["label"], value[y : y + h, x : x + w]))
        return result

    comparisons = {}
    for arm, item in reports.items():
        comparisons[arm] = {
            Path(f["image"]["path"]).name: f
            for f in item["figures"]
            if f["image"]["path"].endswith("-comparison.png")
        }
    if not all(set(comparisons[a]) == set(comparisons[baseline]) for a in comparisons):
        raise ValueError("Native case coverage differs across arms")
    figures, channels = [], 0
    for name in comparisons[baseline]:
        source_cells = {a: cells(items[name]) for a, items in comparisons.items()}
        old = source_cells[baseline]
        for arm in sources:
            new = source_cells[arm]
            for i in [0, 1, *range(4, len(old))]:
                np.testing.assert_array_equal(old[i][1], new[i][1])
        # Two rows retain both support aggregations; no cell pixels are resized.
        rows = []
        for support, index in [("local", 3), ("global", 2)]:
            rows.append(
                [
                    old[0],
                    old[1],
                    *[
                        (f"{labels.get(a, a)} {support}", source_cells[a][index][1])
                        for a in sources
                    ],
                    *old[4:],
                ]
            )
        canvas = Image.new("RGB", (8 + 168 * len(rows[0]), 384), "#eeeeee")
        draw, panels = ImageDraw.Draw(canvas), []
        for row_index, row in enumerate(rows):
            for column, (label, cell) in enumerate(row):
                x, y = 8 + 168 * column, 24 + 192 * row_index
                draw.text((x, y - 19), label, font=font, fill="black")
                canvas.paste(Image.fromarray(cell), (x, y))
                panels.append({"label": label, "xywh": [x, y, 160, 160]})
        path = output / name
        canvas.save(path)
        saved = np.asarray(Image.open(path))
        for panel, (_, value) in zip(panels, [c for row in rows for c in row], strict=True):
            x, y, w, h = panel["xywh"]
            np.testing.assert_array_equal(saved[y : y + h, x : x + w], value)
            channels += value.size
        figures.append(
            {
                "image": reference(path),
                "panels": panels,
                "source_figures": {a: comparisons[a][name] for a in comparisons},
                "no_resize": True,
            }
        )
    changes = []
    old_collection = read_json(sources[baseline] / "collection.json")
    old_rows = {r["id"]: r for r in old_collection["rows"]}
    for arm in sources:
        collection = read_json(sources[arm] / "collection.json")
        for row in collection["rows"]:
            for key in ["parent_values", "packed_values", "colors_values"]:
                if row[key] != old_rows[row["id"]][key]:
                    raise ValueError("Compared waveform arms have different native inputs")
            deltas = {}
            for method, binding in row["predictions"].items():
                a, b = [
                    np.load(checked(v), allow_pickle=False)
                    for v in [old_rows[row["id"]]["predictions"][method], binding]
                ]
                delta = b.astype(np.float64) - a.astype(np.float64)
                deltas[method] = {
                    "pixel_bytes_exact": a.dtype == b.dtype and a.tobytes() == b.tobytes(),
                    "maximum_camera_DN16": float(np.max(np.abs(delta)) * 65535),
                    "RMS_camera_DN16": float(np.sqrt(np.mean(delta**2)) * 65535),
                }
            changes.append({"arm": arm, "case": row["id"], "methods": deltas})
    write_json(
        output / "summary.json",
        {
            "status": "completed-controlled-scalar-and-native-comparison-awaiting-viewing",
            "plan": reference(root / "plan.json"),
            "reporter": reference(__file__),
            "both_arms_closed": reference(root / "both-arms-closed-before-GT.json"),
            "score_sources": {a: reference(p) for a, p in score_paths.items()},
            "means": means,
            "figures": figures,
            "channels_reread_exact": channels,
            "changes_from_legacy"
            if "comparison_sources" not in plan
            else "changes_from_baseline": changes,
            "baseline_arm": baseline,
            "scope": "Same development sources/RAW/parent/noise/ROIs/display; descriptive two-geometry means. Joint harmonic support does not establish each individual harmonic. Both real references and JPEGs are qualitative, never scored. No broad promotion. All native cells preserve source report pixels exactly.",
        },
    )
    print(len(figures), "native paired-support boards", channels, "exact RGB channels")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    report(args.root.resolve())
