"""Score closed scene-guide outputs and render native finite-wire comparisons."""

import argparse
from collections import defaultdict
from itertools import permutations
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from probe_scene_wave_guides import MODES

from demosaic.archive_metrics import display, noisy_malvar
from demosaic.experiments.artifacts import checked, read_json, reference, write_json
from demosaic.experiments.evaluation.edge_response import measure

METHODS = ("V143", *MODES)


def native_board(output, key, values, arrays, metadata):
    labels = (
        "Noisy Malvar",
        "V143 EMA",
        "Query only",
        "Matching guide",
        "Unrelated guide",
        "Exact GT",
    )
    cells = [
        np.rint(
            display(value[None], arrays, exposure=2)[0, :, 48:208, 48:208].transpose(1, 2, 0) * 255
        ).astype(np.uint8)
        for value in values
    ]

    def render(indices, filename):
        image = Image.new("RGB", (8 + 168 * len(indices), 192), "#eeeeee")
        draw = ImageDraw.Draw(image)
        panels = []
        for i, index in enumerate(indices):
            cell, label = cells[index], labels[index]
            assert cell.shape == (160, 160, 3)
            x = 8 + 168 * i
            image.paste(Image.fromarray(cell), (x, 24))
            draw.text((x, 5), label, fill="black")
            panels.append({"label": label, "png_xywh": [x, 24, 160, 160]})
        path = output / filename
        image.save(path)
        pixels = np.asarray(Image.open(path))
        for panel, index in zip(panels, indices, strict=True):
            x = panel["png_xywh"][0]
            np.testing.assert_array_equal(pixels[24:184, x : x + 160], cells[index])
        return {"image": reference(path), "panels": panels}

    return {
        **metadata,
        "id": key,
        "ROI_xywh": [176, 176, 160, 160],
        "display_exposure": 2,
        "ADC_bits": 16,
        "black_level": 0.03,
        "board": render(range(6), key + "-comparison.png"),
        "triplet": render((0, 3, 5), key + "-triplet.png"),
    }


def report(root):
    plan_path, collection_path = root / "plan.json", root / "output/collection.json"
    plan, collection = read_json(plan_path), read_json(collection_path)
    assert collection["plan"] == reference(plan_path)
    assert collection["query_target_arrays_read"] == 0 and len(collection["rows"]) == 96
    results = {row["id"]: row for row in collection["rows"]}
    guides = read_json(checked(collection["guides"]))
    groups = defaultdict(list)
    for row in plan["cases"]:
        groups[row["profile"], row["source"], row["placement"]].append(row)
    assert len(groups) == 32
    output = root / "review"
    output.mkdir()
    measurements, boards, coverage = [], [], []
    for guide, frequencies in guides.items():
        recipe = plan["donors"][guide]["simulation"]["recipe"]
        truth = np.asarray(
            [
                (np.cos(angle) / period, np.sin(angle) / period)
                for angle, period in zip(recipe["wire_angles"], recipe["periods"], strict=True)
            ]
        )
        estimate = np.asarray(frequencies)
        distance = (
            np.minimum(
                np.linalg.norm(truth[:, None] - estimate[None], axis=-1),
                np.linalg.norm(truth[:, None] + estimate[None], axis=-1),
            )
            * 256
        )
        assignment = min(
            permutations(range(2)), key=lambda p: distance[0, p[0]] + distance[1, p[1]]
        )
        coverage.append(
            {
                "guide": guide,
                "donor_estimates": frequencies,
                "native_256_bin_distances": [
                    float(distance[i, j]) for i, j in enumerate(assignment)
                ],
            }
        )
    for (profile, geometry, placement), rows in groups.items():
        assert [v["sample"] for v in rows] == [0, 1, 2]
        assert all(
            v["arrays"] == rows[0]["arrays"] and v["parent"] == rows[0]["parent"] for v in rows
        )
        with np.load(checked(rows[0]["arrays"])) as data:
            arrays = dict(data)
        parent = np.load(checked(rows[0]["parent"]))
        values = {method: parent.copy() for method in MODES}
        for row in rows:
            sample = row["sample"]
            result = results[row["id"]]
            with np.load(checked(result["outputs"])) as outputs:
                for method in MODES:
                    values[method][sample, :, 128:384, 128:384] = outputs[method]
            for method, key in (("matching-guide", "matching"), ("unrelated-guide", "unrelated")):
                fit = result["query_fits"][method]
                assert fit["guide_frequencies_xy"] == guides[row[key]]
                assert fit["records"][0]["frequencies"] == [guides[row[key]]] * 2
        for method, value in {"V143": parent, **values}.items():
            fields = measure(arrays, value)
            fields["query_error_RMS_DN16"] = float(
                np.sqrt(
                    np.mean(
                        (
                            value[..., 128:384, 128:384].astype(np.float64)
                            - arrays["target"][..., 128:384, 128:384]
                        )
                        ** 2
                    )
                )
                * 65535
            )
            measurements.append(
                {
                    "profile": profile,
                    "source": geometry,
                    "placement": placement,
                    "method": method,
                    **fields,
                }
            )
        if profile == "iso400" and geometry in (0, 1):
            context = {k: arrays[k][2:3] for k in ("colors", "wb", "matrix")}
            context["packed"] = arrays["packed"][2:3, :, 64:192, 64:192]
            crops = [noisy_malvar(context)[0]]
            crops.extend(
                v[2, :, 128:384, 128:384] for v in (parent, *values.values(), arrays["target"])
            )
            boards.append(
                native_board(
                    output,
                    f"source{geometry}-{placement}",
                    crops,
                    context,
                    {
                        "query": rows[2],
                        "parents": plan["parents"],
                        "scoring_reference": "Exact constructed GT",
                        "matching_guide": guides[rows[2]["matching"]],
                        "unrelated_guide": guides[rows[2]["unrelated"]],
                        "selection": "Both placements for procedural sources0/1 at ISO400, role2.",
                    },
                )
            )
    assert len(measurements) == 128 and len(boards) == 4
    grouped = defaultdict(list)
    names = set(measurements[0]) - {"profile", "source", "placement", "method"}
    for row in measurements:
        grouped[row["profile"], row["placement"], row["method"]].append(row)
    summaries = []
    for (profile, placement, method), rows in grouped.items():
        assert {row["source"] for row in rows} == set(range(8))
        summaries.append(
            {
                "profile": profile,
                "placement": placement,
                "method": method,
                **{k: float(np.mean([v[k] for v in rows])) for k in sorted(names)},
            }
        )
    write_json(
        output / "result.json",
        {
            "producer": reference(__file__),
            "plan": reference(plan_path),
            "collection": reference(collection_path),
            "measurements": measurements,
            "summary": summaries,
            "guide_coverage": coverage,
            "boards": boards,
            "scope": "Exact signed strong and weak increments with independent query noise on each role."
            " The 256px query correction occupies the center of each retained 512px parent."
            " Report full-field original GT masks and centered query RMS. Eight synthetic"
            " geometries, RGGB only. Separate guide frequencies estimated from independent"
            " synthetic donor RAW. Four selected comparison boards and same-coordinate triplets.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    report(parser.parse_args().root.resolve())
