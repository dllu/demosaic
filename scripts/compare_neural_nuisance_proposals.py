"""Exact control/cache isolation for closed neural-nuisance proposal ablations."""

import argparse
import sys
from pathlib import Path

import numpy as np

from demosaic.experiments.artifacts import checked, read_json, reference, write_json


def compare(original, fixed, output):
    old_plan, plan = (read_json(r / "plan.json") for r in (original, fixed))
    assert plan["rows"] == old_plan["rows"]
    assert plan["geometry_config"] == old_plan["geometry_config"]
    assert plan["background_configuration"] == old_plan["background_configuration"]
    assert plan["fixed_analytic_frequencies"] and not old_plan.get(
        "fixed_analytic_frequencies", False
    )
    assert plan["maximum_new_neural_forwards"] == 0
    collections = [read_json(r / "collection.json") for r in (original, fixed)]
    assert all(len(c["rows"]) == 48 for c in collections)
    assert collections[0]["plan"] == reference(original / "plan.json")
    assert collections[1]["plan"] == reference(fixed / "plan.json")
    lookups = [{r["id"]: r for r in c["rows"]} for c in collections]
    backgrounds = [read_json(r / "backgrounds-collection.json") for r in (original, fixed)]
    background_rows = [{r["id"]: r for r in c["rows"]} for c in backgrounds]
    assert backgrounds[1]["new_root_forwards"] == backgrounds[1]["new_encoder_forwards"] == 0
    assert all(c["all91_restoration_and_backbone_tensors_unchanged"] for c in backgrounds)
    controls = fields = tiles = 0
    cases = []
    for row in plan["rows"]:
        a, b = (lookup[row["id"]] for lookup in lookups)
        for key in ("parent_values", "packed_values", "colors_values"):
            assert a[key] == b[key]
        for method in a["predictions"]:
            if not method.startswith(("H1-", "conditional-")):
                continue
            left, right = a["predictions"][method], b["predictions"][method]
            assert left["sha256"] == right["sha256"]
            assert checked(left).read_bytes() == checked(right).read_bytes()
            controls += 1
        old_bg, bg = (lookup[row["id"]] for lookup in background_rows)
        for key in ("input_fingerprints", "noise", "identity_zero_noise", "fields"):
            assert old_bg[key] == bg[key]
        for field in bg["fields"]:
            checked(field)
            fields += 1
        if not bg["identity_zero_noise"]:
            assert bg["argument_fingerprints"] == old_bg["argument_fingerprints"]
            assert bg["adopted_from"] == reference(original / "backgrounds-collection.json")
            np.testing.assert_array_equal(
                np.load(checked(bg["mask_A"])), np.load(checked(old_bg["mask_A"]))
            )
            assert b["aux"]["neural_frequency_source"] == "fixed-analytic-proposals"
            assert len(a["aux"]["records"]) == len(b["aux"]["records"])
            for before, after in zip(a["aux"]["records"], b["aux"]["records"], strict=True):
                assert before["xy"] == after["xy"]
                assert before["arms"]["H1-"] == after["arms"]["H1-"]
                assert after["arms"]["neural"]["frequencies"] == after["arms"]["H1-"]["frequencies"]
                assert after["arms"]["neural"]["matched"] == after["arms"]["H1-"]["matched"]
                tiles += 1
        cases.append(
            {
                "id": row["id"],
                "all12_control_files_exact": True,
                "background_fields_adopted_exact": len(bg["fields"]),
                "analytic_diagnostics_unchanged": True,
            }
        )
    assert (controls, fields, tiles) == (576, 88, 412) and "torch" not in sys.modules
    write_json(
        output,
        {
            "original_plan": reference(original / "plan.json"),
            "fixed_plan": reference(fixed / "plan.json"),
            "original_collection": reference(original / "collection.json"),
            "fixed_collection": reference(fixed / "collection.json"),
            "script": reference(__file__),
            "cases": cases,
            "analytic_control_files_byte_exact": controls,
            "neural_background_fields_adopted_exact": fields,
            "tiles_with_unchanged_analytic_diagnostics_and_fixed_proposals": tiles,
            "new_root_forwards": 0,
            "new_encoder_forwards": 0,
            "Torch_imported": False,
            "GT_reference_arrays_loaded": 0,
            "scope": "All48 cases closed; exact physical inputs, parent, analytic controls, analytic discovery/validation records and complete closed neural background cache. Only neural-nuisance proposal source changes to fixed analytic frequencies; coefficients and held-out scores are refitted. Zero neural replay, no target/reference reads.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("fixed", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    compare(args.original.resolve(), args.fixed.resolve(), args.output.resolve())
