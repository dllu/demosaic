"""Check conditional risk decompositions against independently audited score rows."""

import argparse
from collections import defaultdict
from decimal import Decimal, localcontext
from pathlib import Path

from train_directional_bank_trial import read, ref, save


def main(root):
    effects = read(root / "conditional-effects-v1.json")
    scores = read(root / "scores-v1.json")
    audit = read(root / "independent-metrics-audit-v1.json")
    assert audit["status"] == "pass"
    lookup = {(r["id"], r["method"]): r for r in scores["rows"]}
    methods = {
        "native_native": "native-native",
        "relative_relative": "relative-relative",
        "relative_native": "relative-native",
        "native_relative": "native-relative",
    }
    max_risk_error = max_algebra_error = max_reduction_error = 0.0
    risk_checks = algebra_checks = reductions = 0
    groups = defaultdict(list)
    with localcontext() as ctx:
        ctx.prec = 50
        for row in effects["rows"]:
            for label, method in methods.items():
                score = lookup[row["id"], method]
                if row["region"] == "crop" and "crop_error_RMS_DN16" not in score:
                    expected = sum(
                        Decimal(str(score[f"crop_{part}_RMS_DN16"])) ** 2
                        for part in ["spatial", "DC"]
                    )
                else:
                    field = {
                        "full": "full_error_RMS_DN16",
                        "crop": "crop_error_RMS_DN16",
                        "quiet": "quiet_error_RMS_DN16",
                        "blank": "blank_error_RMS_DN16",
                    }[row["region"]]
                    expected = Decimal(str(score[field])) ** 2
                actual = Decimal(str(row[label + "_MSE_DN16_squared"]))
                error = abs(actual - expected)
                assert error < Decimal("0.00000002"), (row["id"], method, error)
                max_risk_error = max(max_risk_error, float(error))
                risk_checks += 1
            nn, rr, rn, nr = (
                Decimal(str(row[label + "_MSE_DN16_squared"])) for label in methods
            )
            expected = {
                "proposal_change_at_N_map": rn - nn,
                "proposal_change_at_R_map": rr - nr,
                "map_change_at_N_proposal": nr - nn,
                "map_change_at_R_proposal": rr - rn,
                "average_proposal_change": (rn - nn + rr - nr) / 2,
                "average_map_change": (nr - nn + rr - rn) / 2,
                "combined_change": rr - nn,
            }
            for field, value in expected.items():
                error = abs(Decimal(str(row[field])) - value)
                assert error < Decimal("0.0000000001")
                max_algebra_error = max(max_algebra_error, float(error))
                algebra_checks += 1
            groups[
                row["kind"], str(row["condition"]), row["cohort"], row["region"]
            ].append(row)
        summary = {
            (r["kind"], r["condition"], r["cohort"], r["region"]): r
            for r in effects["summary"]
        }
        assert set(summary) == set(groups)
        for key, members in groups.items():
            assert summary[key]["cases"] == len(members)
            fields = members[0].keys() - {"id", "kind", "condition", "cohort", "region"}
            for field in fields:
                expected = sum(Decimal(str(r[field])) for r in members) / len(members)
                error = abs(Decimal(str(summary[key][field])) - expected)
                assert error < Decimal("0.0000000001")
                max_reduction_error = max(max_reduction_error, float(error))
                reductions += 1
    assert len(effects["rows"]) == 2176 and risk_checks == 8704
    save(
        root / "conditional-effects-audit-v1.json",
        {
            "status": "pass",
            "effects": ref(root / "conditional-effects-v1.json"),
            "independent_score_audit": ref(root / "independent-metrics-audit-v1.json"),
            "scores": ref(root / "scores-v1.json"),
            "auditor": dict(ref(Path(__file__)), text=Path(__file__).read_text()),
            "region_rows": len(effects["rows"]),
            "risk_checks": risk_checks,
            "conditional_algebra_checks": algebra_checks,
            "Decimal_group_reductions": reductions,
            "maximum_risk_difference_DN16_squared": max_risk_error,
            "maximum_algebra_difference_DN16_squared": max_algebra_error,
            "maximum_reduction_difference_DN16_squared": max_reduction_error,
            "new_neural_forwards": 0,
            "new_noise_draws": 0,
            "scope": "Risk checked against squared independently audited RMS, or spatial/DC sum of squares for crops. Decimal algebra checks both swap orders and equal-weight group reductions. This verifies fixed-field risk arithmetic, not training or gate-weight causality. No real reference is scored.",
        },
    )
    print("PASS:", risk_checks, "risk checks;", algebra_checks, "algebra;", reductions, "reductions")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    main(parser.parse_args().root.absolute())
