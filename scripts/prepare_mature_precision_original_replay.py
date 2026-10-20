"""Freeze one bounded replay using the unchanged original precision pilot worker."""

import argparse
import copy
from pathlib import Path

from qualify_mature_precision import alive
from train_directional_bank_trial import guard, read, ref, save

REPO = Path(__file__).resolve().parents[1]


def prepare(root):
    pilot = REPO / ".cache/benchmarks/mature-mixed-precision-CUDA-v1"
    original_path = pilot / "plan.json"
    original = read(original_path)
    guard(original)
    plan = copy.deepcopy(original)
    statuses = []
    for folder, expected in [
        (
            pilot,
            "completed-mature-precision-pilot-arrays-awaiting-native-and-independent-scalar-review",
        ),
        (
            REPO / ".cache/benchmarks/mature-hidden-FP16-full-quality-v1",
            "failed-full-precision-quality-preserved-no-automatic-retry",
        ),
        (
            REPO / ".cache/benchmarks/mature-precision-execution-drift-v1",
            "completed-execution-diagnostics-awaiting-review",
        ),
    ]:
        path = folder / "controller-status.json"
        status = read(path)
        assert status["status"] == expected
        assert not any(alive(status[k]) for k in ("controller", "child"))
        plan["blocking_owners"] += [status[k] for k in ("controller", "child")]
        statuses.append(ref(path))
    root = root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    root.mkdir(parents=True, exist_ok=False)
    plan.update(
        root=str(root),
        output=str(root / "outputs"),
        models={"V43": original["models"]["V43"]},
        fixtures=original["fixtures"][:2],
        original_plan=ref(original_path),
        predecessor_diagnostic_statuses=statuses,
        preparer=ref(__file__),
        scope="One diagnostic replay using the byte-identical original frozen worker/controller/source environment, original V43 checkpoint and first two original fixtures only. Preserve original dtype hooks, warmups, policy order, synchronized repeats and FP32 identity control. Exactly25 real forwards (13 instrumented/12 timing repeats); timing values are retained but not interpreted. No policy/quality gate changes, full qualification retry, training, full-frame continuation or production adoption.",
    )
    assert plan["fixtures"][0]["kind"] == "gfx" and plan["fixtures"][1]["kind"] == "photo"
    receipt = read(pilot / "work/GPU-output/receipt.json")
    captures = next(m for m in receipt["models"] if m["model"] == "V43")["captures"]
    plan["matching_pilot_outputs"] = [
        c for c in captures if c["fixture"] in {f["id"] for f in plan["fixtures"]}
    ]
    assert len(plan["matching_pilot_outputs"]) == 6
    plan["inputs"] += [ref(original_path), ref(__file__)] + statuses
    plan["inputs"] += [c["RGB"] for c in plan["matching_pilot_outputs"]]
    save(root / "plan.json", plan)
    guard(plan)
    print(ref(root / "plan.json"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    prepare(args.root)
