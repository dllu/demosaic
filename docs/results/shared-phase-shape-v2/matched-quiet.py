"""Descriptively match attained quiet RMS with a single multiplier per condition."""

from collections import defaultdict
from pathlib import Path

import numpy as np
from report_fold_support_pooling import ROI, evaluated, measure
from scipy.optimize import brentq

from demosaic.experiments.artifacts import checked, read_json, reference, write_json

published = Path(__file__).resolve().parent
summary = read_json(published / "summary.json")
report_path = checked(summary["report"])
report = read_json(report_path)
collection = read_json(checked(report["collection"]))
plan = read_json(checked(report["plan"]))
settings = {
    (r["profile"], r["placement"]): r
    for r in plan["settings"]
    if r["method"] == "weighted-refit" and r["budget_DN16"] == 0.02
}
groups = defaultdict(lambda: defaultdict(list))
for binding in collection["synthetic"]:
    group = read_json(checked(binding))
    item = read_json(checked(group["case"]))
    control = read_json(checked(group["control"]))
    stratum = item["profile"], item["placement"]
    setting = settings[stratum]
    key = f"weighted-refit-t{setting['threshold']:g}"
    parent = np.load(checked(item["parent"])).astype(np.float64)
    with np.load(checked(item["target"])) as target:
        truth, quiet = target["target"].astype(np.float64), target["quiet"][ROI]
    with (
        np.load(checked(group["predictions"])) as new,
        np.load(checked(control["output"])) as old,
    ):
        for model, prediction in (
            ("independent", old[f"{plan['reference_arm']}--{key}"]),
            ("shared", new[key]),
        ):
            groups[stratum][model].append(measure(parent, truth, quiet, prediction))


def match(stratum, models, scale):
    metrics = ("quiet_RMS_DN16", "weak_gain", "weak_increment_RMS_DN16")

    def mean(model, multiplier):
        samples = [evaluated(v, scale * multiplier) for v in models[model]]
        return np.array([np.mean([r[name] for r in samples]) for name in metrics])

    levels = {m: mean(m, 1)[0] for m in models}
    smaller = min(levels, key=levels.get)
    larger = max(levels, key=levels.get)
    target = levels[smaller]
    assert mean(larger, 0)[0] < target <= levels[larger]
    multiplier = brentq(lambda v: mean(larger, v)[0] - target, 0, 1, xtol=1e-11)
    paired = {smaller: mean(smaller, 1).tolist(), larger: mean(larger, multiplier).tolist()}
    assert abs(paired[smaller][0] - paired[larger][0]) < 1e-9
    print(*stratum, larger, multiplier, paired)
    return {
        "profile": stratum[0],
        "placement": stratum[1],
        "reduced_model": larger,
        "common_multiplier": multiplier,
        "columns": metrics,
        "matched": paired,
    }


rows = [match(key, models, settings[key]["scale"]) for key, models in groups.items()]
write_json(
    published / "matched-quiet.json",
    {
        "report": reference(report_path),
        "driver": reference(__file__),
        "scope": "Uses held-out targets solely to describe matched achieved quiet RMS.",
        "rows": rows,
    },
)
