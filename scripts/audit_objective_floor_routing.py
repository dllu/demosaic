"""Bind ADC/noisy gradient-norm groups to the completed V150 training trace."""

import argparse
import time
from pathlib import Path

import numpy as np
from train_directional_bank_trial import guard, read, ref, save


def main(root, destination):
    plan = read(root / "plan-v1.json")
    guard(plan)
    training = read(root / "train-result-v1.json")
    cache = read(plan["cache"]["path"])
    assert len(training["trace"]) == len(cache["batches"]) == 1000
    for row, batch in zip(training["trace"], cache["batches"], strict=True):
        assert row["step"] == batch["step"] and row["batch"] == batch["arrays"]
        assert row["domain"] == batch["metadata"]["domain"]
    groups = []
    for arm in training["trace"][0]["arms"]:
        for domain in [None, "mesh", "weak", "flat", "mixed", "photo"]:
            for adc in [True, False]:
                selected = []
                steps = []
                for row, batch in zip(training["trace"], cache["batches"], strict=True):
                    noise = batch["metadata"]["noise"]
                    is_adc = noise["shot"] == noise["read"] == 0
                    if is_adc == adc and (domain is None or row["domain"] == domain):
                        selected.append(row["arms"][arm]["gradient_norm"])
                        steps.append(row["step"])
                values = np.asarray(selected, dtype=np.float64)
                assert len(values) and np.isfinite(values).all() and values.min() >= 0
                groups.append(
                    {
                        "arm": arm,
                        "domain": domain or "all1000",
                        "ADC_only": adc,
                        "steps": steps,
                        "batches": len(values),
                        "median_logged_preclip_norm": float(np.median(values)),
                        "mean_logged_preclip_norm": float(values.mean()),
                        "p90_logged_preclip_norm": float(np.quantile(values, 0.9)),
                        "maximum_logged_preclip_norm": float(values.max()),
                        "norm_exceeds_one": int((values > 1).sum()),
                        "sum_logged_preclip_norm_squared": float(values @ values),
                        "sum_norm_capped_at_one_squared_proxy": float(
                            np.minimum(values, 1) @ np.minimum(values, 1)
                        ),
                    }
                )
    save(
        destination,
        {
            "status": "pass-complete1000-step-trace-noise-bindings",
            "recorded_unix_UTC": time.time(),
            "training": ref(root / "train-result-v1.json"),
            "cache": plan["cache"],
            "training_audit": ref(root / "independent-training-audit-v1.json"),
            "auditor": dict(ref(__file__), text=Path(__file__).read_text()),
            "groups": groups,
            "new_forwards": 0,
            "new_noise_draws": 0,
            "scope": "All1000 native2DN/floor16 logged preclip norms matched to cached noise metadata. Capping norms at1 is a proxy for clipped gradient energy, omitting the clip implementation epsilon. These are norms, not gradient directions, parameter displacements or Adam influence. No causal claim or quality improvement follows from allocation alone.",
        },
    )
    print(
        "PASS",
        len(training["trace"]) * len(training["trace"][0]["arms"]),
        "trace/noise bindings and",
        len(groups),
        "groups",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    main(args.root.absolute(), args.destination.absolute())
