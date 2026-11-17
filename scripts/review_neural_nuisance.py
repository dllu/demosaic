"""Closed-cohort tradeoffs and absolute errors for the neural-nuisance pilot."""

import argparse
import sys
from pathlib import Path

import numpy as np

from demosaic.experiments.artifacts import checked, read_json, reference, write_json


def review(root, output):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plan = read_json(root / "plan.json")
    collection = read_json(root / "collection.json")
    assert len(collection["rows"]) == len(plan["rows"]) == 48
    assert collection["plan"] == reference(root / "plan.json")
    audit = read_json(root / "independent-audit.json")
    assert audit["collection"] == reference(root / "collection.json")
    matched = read_json(root / "native/report.json")
    assert matched["collection"] == reference(root / "collection.json")
    output.mkdir(exist_ok=False)
    records = {r["id"]: r for r in collection["rows"]}
    scores = read_json(root / "finite-scores.json")["rows"]
    roles = []
    identity_error = 0.0
    for group in plan["finite_groups"]:
        with np.load(checked(group["arrays"]), allow_pickle=False) as z:
            target = z["target"].astype(np.float64)
            masks = {
                "full": np.ones(target.shape[-2:], bool),
                "quiet": z["quiet"],
                "edge": z["edge_band"],
            }
        parent = next(r["parent"] for r in plan["rows"] if r["id"] == group["cases"][0])
        methods = ["V143", *records[group["cases"][0]]["predictions"]]
        for method in methods:
            value = (
                np.load(checked(parent)).astype(np.float64)
                if method == "V143"
                else np.stack(
                    [
                        np.load(checked(records[case]["predictions"][method]))
                        for case in group["cases"]
                    ]
                ).astype(np.float64)
            )
            for role in range(3):
                row = {
                    "profile": group["profile"],
                    "source": group["metadata"]["recipe"]["source"],
                    "placement": group["metadata"]["placement"],
                    "method": method,
                    "role": role,
                }
                for name, mask in masks.items():
                    error = (value[role] - target[role])[:, mask]
                    dc = error.mean(-1, keepdims=True)
                    mse = float(np.vdot(error, error) / error.size)
                    bias = float(np.mean(dc**2))
                    spatial = float(np.mean((error - dc) ** 2))
                    identity_error = max(identity_error, abs(mse - bias - spatial))
                    for key, v in (("", mse), ("_DC", bias), ("_spatial", spatial)):
                        row[name + key + "_RMS_DN16"] = float(np.sqrt(v) * 65535)
                roles.append(row)
    assert len(roles) == 684 and identity_error < 1e-14
    write_json(
        output / "absolute-role-errors.json",
        {
            "script": reference(__file__),
            "plan": reference(root / "plan.json"),
            "collection": reference(root / "collection.json"),
            "rows": roles,
            "maximum_mse_bias_spatial_identity_error": identity_error,
            "scope": "Absolute target errors separately for edge-only/one/two-direction roles, all19 fixed methods. No role-difference cancellation. Reused two-source development cohort.",
        },
    )

    comparisons = []
    role_means = []
    for profile in ("iso400", "iso1600", "iso6400"):
        for placement in ("near", "far"):
            for method in methods:
                selected = [
                    r
                    for r in scores
                    if (r["profile"], r["placement"], r["method"]) == (profile, placement, method)
                ]
                assert len(selected) == 2
                keys = [k for k, v in selected[0].items() if isinstance(v, float)]
                comparisons.append(
                    {
                        "profile": profile,
                        "placement": placement,
                        "method": method,
                        "sources": 2,
                        **{k: float(np.mean([r[k] for r in selected])) for k in keys},
                    }
                )
                for role in range(3):
                    selected_roles = [
                        r
                        for r in roles
                        if (r["profile"], r["placement"], r["method"], r["role"])
                        == (profile, placement, method, role)
                    ]
                    assert len(selected_roles) == 2
                    keys = [k for k, v in selected_roles[0].items() if isinstance(v, float)]
                    role_means.append(
                        {
                            "profile": profile,
                            "placement": placement,
                            "method": method,
                            "role": role,
                            **{k: float(np.mean([r[k] for r in selected_roles])) for k in keys},
                        }
                    )

    diagnostics = []
    for row in plan["rows"]:
        record = records[row["id"]]
        if record["aux"]["identity_zero_noise"]:
            continue
        entry = {
            "id": row["id"],
            "kind": row["kind"],
            "tiles": record["aux"]["patches"],
            "arms": {},
        }
        for arm in ("H1-", "neural"):
            tiles = [r["arms"][arm] for r in record["aux"]["records"]]
            mses = np.asarray([r["heldout_full_standardized_MSE_by_color"] for r in tiles])
            entry["arms"][arm] = {
                "unweighted_tile_fold_color_MSE_mean": float(mses.mean()),
                "MSE_median": float(np.median(mses)),
                "MSE_maximum": float(mses.max()),
                "matched_direction_pairs": sum(len(r["matched"]) for r in tiles),
            }
            if plan.get("aggregation_config"):
                entry["arms"][arm]["MSE_scope"] = (
                    "Mean of two direction-specific phase full models; H1 Gram spectrum does not describe the phase kernel."
                )
            else:
                eigenvalues = np.asarray(
                    [r["wave_residual_Gram_eigenvalues_by_direction_color"] for r in tiles]
                )
                entry["arms"][arm]["residual_Gram_eigenvalue_quantiles"] = np.quantile(
                    eigenvalues, [0, 0.1, 0.5, 0.9, 1]
                ).tolist()
            if arm == "neural":
                coefficients = np.asarray(
                    [r["neural_nuisance_coefficients_by_color"] for r in tiles]
                )
                entry["arms"][arm]["neural_coefficient_quantiles"] = np.quantile(
                    coefficients, [0, 0.1, 0.5, 0.9, 1]
                ).tolist()
                entry["arms"][arm]["neural_coefficient_scope"] = (
                    "Actual fixed global background; carrier amplitudes fitted locally"
                    if plan["geometry_config"].get("amplitude_window", 0)
                    and plan["geometry_config"].get("amplitude_nuisance") == "global"
                    else "Global discovery initialization; local-query coefficients used for actual spatial-amplitude prediction/delivery"
                    if plan["geometry_config"].get("amplitude_window", 0)
                    else "Global prediction/delivery coefficients"
                )
        diagnostics.append(entry)

    figures = []
    colors = ("#6a777f", "#bd6e18", "#137b86")
    for error_key, title in (
        ("quiet_error_RMS_DN16", "Quiet-region absolute error"),
        ("weak_increment_error_RMS_DN16", "Weak-increment error"),
    ):
        fig, axes = plt.subplots(3, 2, figsize=(10, 10), squeeze=False, layout="constrained")
        for i, profile in enumerate(("iso400", "iso1600", "iso6400")):
            for j, placement in enumerate(("near", "far")):
                ax = axes[i, j]
                parent = next(
                    r
                    for r in comparisons
                    if (r["profile"], r["placement"], r["method"]) == (profile, placement, "V143")
                )
                for prefix, label, color in zip(
                    ("H1-", "conditional-", ""),
                    (
                        ("Analytic raw wave", "Analytic phase", "Neural phase")
                        if plan.get("aggregation_config")
                        else ("Analytic raw wave", "Analytic conditional", "Neural conditional")
                    ),
                    colors,
                    strict=True,
                ):
                    for mode, style in (("local", "-"), ("global", "--")):
                        points = [
                            next(
                                r
                                for r in comparisons
                                if (r["profile"], r["placement"], r["method"])
                                == (profile, placement, f"{prefix}{mode}-t{t}")
                            )
                            for t in (0, 2, 4)
                        ]
                        x = [100 * (r[error_key] / parent[error_key] - 1) for r in points]
                        y = [100 * r["weak_gain"] for r in points]
                        ax.plot(
                            x,
                            y,
                            style,
                            color=color,
                            marker="o",
                            markersize=3,
                            label=label + " " + mode,
                        )
                        if mode == "local":
                            for px, py, t in zip(x, y, (0, 2, 4), strict=True):
                                ax.annotate(
                                    str(t),
                                    (px, py),
                                    fontsize=7,
                                    xytext=(3, 3),
                                    textcoords="offset points",
                                )
                ax.axhline(parent["weak_gain"] * 100, color="black", linewidth=0.6, label="V143")
                ax.axvline(0, color="black", linewidth=0.5)
                ax.set_title(profile + " / " + placement)
                ax.set_xlabel(title + " change vs V143 (%)")
                ax.set_ylabel("Weak response (% of GT increment)")
                ax.ticklabel_format(axis="both", style="plain", useOffset=False)
                ax.grid(alpha=0.2)
        axes[0, 0].legend(fontsize=6)
        fig.suptitle("Two reused sources; fixed thresholds 0/2/4; global/shared CFA split")
        path = output / (
            "quiet-tradeoff.png" if error_key.startswith("quiet") else "increment-tradeoff.png"
        )
        fig.savefig(path, dpi=140)
        plt.close(fig)
        figures.append(reference(path))
    assert "torch" not in sys.modules
    write_json(
        output / "summary.json",
        {
            "plan": reference(root / "plan.json"),
            "collection": reference(root / "collection.json"),
            "independent_audit": reference(root / "independent-audit.json"),
            "script": reference(__file__),
            "means": comparisons,
            "absolute_role_means": role_means,
            "A_only_diagnostics": diagnostics,
            "plots": figures,
            "new_neural_forwards": 0,
            "Torch_imported": False,
            "scope": "All48 corrections closed before target analysis; compare conditional neural vs conditional analytic as primary. Legacy raw-sinusoid control isolates delivery change. Fixed0/2/4 sweeps, all roles/errors retained. Tile/fold/color MSE means unweighted diagnostic, not independent image observations or calibrated probabilities. Global split changes historical local-H1 masks; no historical quality equivalence asserted. No population-confidence/generalization claim.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    review(args.root.resolve(), args.output.resolve())
