"""Measure both conditional swap orders on actual fixed output arrays."""

import argparse
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
from train_directional_bank_trial import read, ref, save


def main(root):
    review = read(root / "review-result-v1.json")
    methods = ["native-native", "relative-relative", "relative-native", "native-relative"]
    maps = {
        method: {o["id"]: o for o in read(review["collections"][method]["path"])["observations"]}
        for method in methods
    }
    rows = []
    groups = defaultdict(list)
    for case in read(root / "quality-design-v1.json")["observations"]:
        if case["kind"] == "real":
            continue
        arrays = dict(np.load(case["arrays"]["path"]))
        values = {
            method: np.load(maps[method][case["id"]]["prediction"]["path"]).astype(np.float64)
            for method in methods
        }
        target = arrays["target"].astype(np.float64)
        x, y, w, h = case["ROI_xywh"]
        errors = {method: (value - target) * 65535 for method, value in values.items()}
        regions = {
            "full": {key: value for key, value in errors.items()},
            "crop": {key: value[..., y : y + h, x : x + w] for key, value in errors.items()},
        }
        if case["kind"] == "mixed-quiet":
            regions["quiet"] = regions["crop"]
        if case["kind"] == "mesh":
            mask = (
                np.all(arrays["target_present"] == arrays["target_empty"], axis=1)[0]
                if case["present"]
                else np.ones(target.shape[-2:], bool)
            )
            assert mask.any()
            regions["blank"] = {key: value[0][:, mask] for key, value in errors.items()}
        condition = (
            case["present"]
            if case["kind"] == "mesh"
            else (case["variant"]["name"] if case["kind"] == "photo" else case["noise"]["name"])
        )
        for region, selected in regions.items():
            risk = {key: float(np.mean(value**2)) for key, value in selected.items()}
            nn, rr, rn, nr = (risk[key] for key in methods)
            proposal_at_N = rn - nn
            proposal_at_R = rr - nr
            map_at_N = nr - nn
            map_at_R = rr - rn
            proposal_average = (proposal_at_N + proposal_at_R) / 2
            map_average = (map_at_N + map_at_R) / 2
            assert abs(proposal_average + map_average - (rr - nn)) < 1e-10
            row = {
                "id": case["id"],
                "kind": case["kind"],
                "cohort": case.get("cohort"),
                "condition": condition,
                "region": region,
                "native_native_MSE_DN16_squared": nn,
                "relative_relative_MSE_DN16_squared": rr,
                "relative_native_MSE_DN16_squared": rn,
                "native_relative_MSE_DN16_squared": nr,
                "proposal_change_at_N_map": proposal_at_N,
                "proposal_change_at_R_map": proposal_at_R,
                "map_change_at_N_proposal": map_at_N,
                "map_change_at_R_proposal": map_at_R,
                "average_proposal_change": proposal_average,
                "average_map_change": map_average,
                "combined_change": rr - nn,
            }
            rows.append(row)
            groups[case["kind"], str(condition), case.get("cohort"), region].append(row)
    summary = []
    for (kind, condition, cohort, region), members in groups.items():
        item = {
            "kind": kind,
            "condition": condition,
            "cohort": cohort,
            "region": region,
            "cases": len(members),
        }
        fields = members[0].keys() - {"id", "kind", "condition", "cohort", "region"}
        for field in fields:
            item[field] = math.fsum(row[field] for row in members) / len(members)
        assert (
            abs(
                item["average_proposal_change"]
                + item["average_map_change"]
                - item["combined_change"]
            )
            < 1e-10
        )
        summary.append(item)
    assert len(rows) == 2176
    save(
        root / "conditional-effects-v1.json",
        {
            "status": "completed-fixed-array-two-order-risk-reduction",
            "review": ref(root / "review-result-v1.json"),
            "source": dict(ref(Path(__file__)), text=Path(__file__).read_text()),
            "rows": rows,
            "summary": summary,
            "new_neural_forwards": 0,
            "new_noise_draws": 0,
            "scope": "Exact target used only for scoring existing constructed-target arrays, never output. MSE in cameraRGB x65535 squared, equal observation weights; mean RMS is not used for additive attribution. Both conditional swap orders and their equal average are reported. They sum to RR-minus-NN risk, but are not a unique causal attribution of training or gate weights. Maps remain the original data-dependent fields; no real-reference error is scored.",
        },
    )
    for item in summary:
        if item["region"] == "quiet":
            print(item)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    main(parser.parse_args().root.absolute())
