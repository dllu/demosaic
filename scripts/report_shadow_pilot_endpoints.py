"""Compare completed shadow-pilot endpoints using retained predictions only."""

import argparse
import importlib.util
import os
import shutil
from pathlib import Path

from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import live


def analyze(queue_path):
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise RuntimeError("Retained-output analysis must run with CUDA disabled")
    queue = read(queue_path)
    guard(queue)
    root = Path(queue["root"])
    status = read(root / "status.json")
    if (
        status["plan"] != ref(queue_path)
        or live(status["owner"])
        or status["status"] != "completed-pilot-predictions-awaiting-independent-and-native-review"
    ):
        raise RuntimeError("Wait for the exact original endpoint collection to finish")
    baseline = read(queue["baseline_collection"]["path"])
    if baseline["counts"] != {"root": 64, "encoder": 64}:
        raise ValueError("Unexpected completed V120 shadow baseline")
    baseline_rows = {r["id"]: r for r in baseline["observations"]}
    methods = {}
    arms = queue.get("arms", ("V126", "V127"))
    for arm in arms:
        binding = status["completed"][arm]
        if ref(binding["path"]) != binding:
            raise ValueError("Endpoint collection changed")
        collection = read(binding["path"])
        execution_path = root / arm / "plan-v1.json"
        execution = read(execution_path)
        guard(execution)
        if collection["plan"] != ref(execution_path) or collection["counts"] != {
            "root": 86,
            "encoder": 86,
        }:
            raise ValueError("Unexpected pilot endpoint identity/count")
        methods[arm] = execution, collection, execution_path, binding
    if binding := queue.get("matched_control_collection"):
        if ref(binding["path"]) != binding:
            raise ValueError("Saved matched control changed")
        matched = read(binding["path"])
        control_execution = read(matched["plan"]["path"])
        if ref(matched["plan"]["path"]) != matched["plan"]:
            raise ValueError("Saved matched-control execution changed")
        guard(control_execution)
        if matched["counts"] != {"root": 86, "encoder": 86}:
            raise ValueError("Saved matched-control call count differs")
        control_observations, control_rows, control_binding = (
            control_execution["observations"],
            matched["observations"],
            binding,
        )
        control_label = queue.get("matched_control_label", "V126 1k EMA")
        if control_execution.get("model_label", control_label) != control_label:
            raise ValueError("Saved matched-control label differs")
    else:
        control_observations, control_rows, _, control_binding = methods["V126"]
        control_observations, control_rows = (
            control_observations["observations"],
            control_rows["observations"],
        )
        control_label = "V126 1k EMA"
    expected_inputs = [(o["id"], o["input_fingerprints"]) for o in control_observations]
    for execution, _, _, _ in methods.values():
        if [
            (o["id"], o["input_fingerprints"]) for o in execution["observations"]
        ] != expected_inputs:
            raise ValueError("Pilot endpoints did not share identical observations")
    controls = {r["id"]: r for r in control_rows}
    outputs = {}
    for arm in arms:
        execution, collection, execution_path, binding = methods[arm]
        destination = root / f"analysis-{arm}-v1"
        destination.mkdir(exist_ok=False)
        observations = []
        extra = [
            queue["baseline_collection"],
            control_binding,
            binding,
            ref(execution_path),
            ref(queue_path),
        ]
        for original in execution["observations"]:
            observed = dict(original)
            if observed["kind"] == "shadow-material":
                row = baseline_rows[observed["id"]]
                selected = [{"model": {"label": "V120"}, "prediction": row["prediction"]}]
            else:
                selected = [
                    c
                    for c in observed["controls"]
                    if c.get("label", c.get("model", {}).get("label"))
                    in {"V120", "V120-profile3879"}
                ]
                if len(selected) != 1:
                    raise ValueError("Exactly one matched retained V120 control is required")
            if arm != "V126":
                selected.append(
                    {
                        "model": {"label": control_label},
                        "prediction": controls[observed["id"]]["prediction"],
                    }
                )
            observed["controls"] = selected
            extra.extend(c["prediction"] for c in selected)
            observations.append(observed)
        analysis = {
            **execution,
            "root": str(destination),
            "observations": observations,
            "model_label": f"{arm} 1k EMA",
            "actual_execution_plan": ref(execution_path),
            "inputs": [*execution["inputs"], *extra],
            "scope": (
                execution["scope"] + " Report-only metadata derives from the original86-call "
                f"collection; controls are retained V120 and matched {control_label} when distinct. "
                "Material scores apply the fixed display exposure before reduction, so "
                "camera/sRGB PSNR and band errors use exposure-normalized units. "
                "Same-source conditions/CFAs are not independent photographs. No new inference."
            ),
        }
        save(destination / "plan-v1.json", analysis)
        derived = {
            **collection,
            "plan": ref(destination / "plan-v1.json"),
            "actual_neural_collection": binding,
            "new_forwards_in_this_derivation": 0,
        }
        save(destination / "collection-v1.json", derived)
        source = destination / "reporter-source-v1.py"
        shutil.copyfile(Path(__file__).with_name("report_checkpoint_pilot.py"), source)
        spec = importlib.util.spec_from_file_location(f"shadow_report_{arm}", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        from demosaic import archive_metrics

        expected = Path(execution["work"]) / "src/demosaic/archive_metrics.py"
        if ref(archive_metrics.__file__)["sha256"] != ref(expected)["sha256"]:
            raise ValueError("Analysis reductions differ from the frozen implementation")
        module.report(destination / "plan-v1.json", destination / "collection-v1.json")
        outputs[arm] = ref(destination / "report-v1/report.json")
    save(
        root / "retained-analysis-v1.json",
        {
            "status": "scored-rendered-awaiting-independent-and-actual-native-review",
            "queue": ref(queue_path),
            "reports": outputs,
            "new_neural_forwards": 0,
            "new_noise_observations": 0,
            "RAW_decodes": 0,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("queue_plan", type=Path)
    analyze(parser.parse_args().queue_plan.resolve())
