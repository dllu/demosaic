"""Describe an already audited four-pass training prefix, never model quality.

Losses belong to the changing raw model before each update. Means mix images
within each batch; fresh noise, optimizer state and learning rate all change.
"""

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from decimal import Decimal, localcontext
from pathlib import Path

import numpy as np
import psutil

TERMS = {
    "pixel": 1.0,
    "gradient": 0.25,
    "local_regret": 1.0,
    "DC_regret": 1.0,
    "flat_anchor": 0.25,
    "pair_difference": 1.0,
    "pair_common": 1.0,
}
FIELDS = ["loss", *TERMS, "correction_RMS_DN16", "gradient_norm"]
DOMAINS = ["mesh", "weak", "photo", "flat", "mixed"]


def read(path):
    return json.loads(Path(path).read_text())


def ref(path):
    path = Path(path).absolute()
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def mean(values):
    value = math.fsum(values) / len(values)
    with localcontext() as context:
        context.prec = 60
        independent = float(sum(Decimal.from_float(v) for v in values) / Decimal(len(values)))
    assert abs(value - independent) < 1e-12
    return value


def value(row, field):
    return float(row["terms"][field] if field in TERMS else row[field])


def stats(values):
    assert len(values) and np.isfinite(values).all()
    return {
        "mean": mean(values),
        "median": float(np.median(values)),
        "minimum": min(values),
        "maximum": max(values),
        "p10": float(np.quantile(values, 0.1)),
        "p90": float(np.quantile(values, 0.9)),
    }


def summarize(audit_path, output):
    assert not output.exists()
    audit = read(audit_path)
    assert (
        audit["status"]
        == "pass-real-row5000-checkpoint-four-complete-passes-and-distinct-fifth-visit"
    )
    assert audit["complete_continuation_rows_checked"] == 4000
    assert audit["FP32_loss_totals_checked"] == 3600 and audit["maximum_loss_total_difference"] == 0
    binding = audit["journal_prefix"]
    with Path(binding["path"]).open("rb") as stream:
        data = stream.read(binding["bytes"])
    assert len(data) == binding["bytes"] and hashlib.sha256(data).hexdigest() == binding["sha256"]
    rows = [json.loads(line) for line in data.splitlines()]
    assert len(rows) == 4000
    assert ref(audit["plan"]["path"]) == audit["plan"]
    plan = read(audit["plan"]["path"])
    owner = audit["training_owner"]
    process = psutil.Process(owner["pid"])
    assert process.create_time() == owner["created"] and process.status() not in ["dead", "zombie"]
    updates = checks = 0
    for row in rows:
        if not row["noisy"]:
            continue
        t = {key: np.float32(v) for key, v in row["terms"].items()}
        assert set(t) == set(TERMS)
        total = np.float32(t["pixel"] + np.float32(0.25) * t["gradient"])
        for term in [
            t["local_regret"],
            t["DC_regret"],
            np.float32(0.25) * t["flat_anchor"],
            t["pair_difference"],
            t["pair_common"],
        ]:
            total = np.float32(total + term)
        expected = float(np.float32(np.float32(plan["domain_weights"][row["domain"]]) * total))
        assert row["loss"] == expected
        updates += 1
    assert updates == 3600
    groups = []
    selected = {}
    for domain in DOMAINS:
        for scene_pass in range(1, 5):
            complete = [
                r
                for r in rows[(scene_pass - 1) * 1000 : scene_pass * 1000]
                if r["domain"] == domain
            ]
            current = [r for r in complete if r["noisy"]]
            selected[domain, scene_pass] = current
            measured = {field: stats([value(row, field) for row in current]) for field in FIELDS}
            checks += len(measured)
            weighted = {
                field: measured[field]["mean"] * weight * plan["domain_weights"][domain]
                for field, weight in TERMS.items()
            }
            component_total = math.fsum(weighted.values())
            groups.append(
                {
                    "domain": domain,
                    "scene_pass": scene_pass,
                    "rows": len(complete),
                    "updates": len(current),
                    "ADC_skips": len(complete) - len(current),
                    "new_sensor_batches": sum(r["fresh_noise_eligible"] for r in current),
                    "retained_noisy_batches": sum(not r["fresh_noise_eligible"] for r in current),
                    "stats": measured,
                    "weighted_term_means": weighted,
                    "term_shares_of_recomposed_scalar_mean": {
                        k: v / component_total for k, v in weighted.items()
                    },
                    "reported_preclip_norm_above_threshold": sum(
                        r["gradient_norm"] > plan["gradient_clip"] for r in current
                    ),
                    "preclip_threshold": plan["gradient_clip"],
                }
            )
    paired = []
    for domain in DOMAINS:
        first, last = selected[domain, 1], selected[domain, 4]
        assert len(first) == len(last)
        assert all(
            a["cache_step"] == b["cache_step"]
            and a["original_batch"] == b["original_batch"]
            and a["original_parent"] == b["original_parent"]
            for a, b in zip(first, last, strict=True)
        )
        for field in FIELDS:
            a, b = [[value(row, field) for row in current] for current in [first, last]]
            before, after = mean(a), mean(b)
            differences = [y - x for x, y in zip(a, b, strict=True)]
            paired.append(
                {
                    "domain": domain,
                    "field": field,
                    "scene_rows": len(a),
                    "first_pass_mean": before,
                    "fourth_pass_mean": after,
                    "percent_change_of_means": 100 * (after / before - 1) if before else None,
                    "paired_difference": stats(differences),
                    "decreased": sum(v < 0 for v in differences),
                    "increased": sum(v > 0 for v in differences),
                    "equal": sum(v == 0 for v in differences),
                }
            )
            checks += 3
    counts = Counter(row["domain"] for row in rows)
    result = {
        "status": "completed-descriptive-four-pass-training-loss-reduction-not-quality",
        "audit": ref(audit_path),
        "plan": audit["plan"],
        "journal_prefix": binding,
        "training_owner_observed_live": owner,
        "continuation_rows": 4000,
        "noisy_updates": updates,
        "domain_rows": dict(counts),
        "groups": groups,
        "first_to_fourth_paired_reductions": paired,
        "independent_Decimal_mean_checks": checks,
        "exact_FP32_loss_totals_rechecked": updates,
        "source": {**ref(__file__), "text": Path(__file__).read_text()},
        "neural_forwards": 0,
        "checkpoint_loads": 0,
        "optimizer_updates": 0,
        "sensor_draws": 0,
        "Torch_imported": "torch" in sys.modules,
        "rawpy_imported": "rawpy" in sys.modules,
        "scope": "Posthoc descriptive reduction after initial scalar inspection, restricted to the previously audited 4000-row prefix. Losses are measured on the changing raw model before each update, not fixed-checkpoint evaluations. Same clean scene rows, fresh noise except three retained photo rows per pass; LR and parameters also change. Batch means mix multiple contrasts/images. Correlated scene/pair visits are not independent replications; no p-values or generalization/quality claims. Scalar term shares do not measure gradient or optimizer-update contributions. No original/source arrays, model inference, new noise, checkpoint loading or training intervention. Final raw/EMA quality and native comparisons remain pending.",
    }
    assert not result["Torch_imported"] and not result["rawpy_imported"]
    with output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    for domain in DOMAINS:
        print(
            domain,
            {
                r["field"]: r["percent_change_of_means"]
                for r in paired
                if r["domain"] == domain
                and r["field"] in ["loss", "pair_difference", "flat_anchor"]
            },
        )
    print("PASS3600 exact FP32 totals;350 Decimal means; no Torch/inference/noise", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summarize(args.audit, args.output)
