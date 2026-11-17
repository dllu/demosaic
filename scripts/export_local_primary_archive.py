"""Bind closed local-primary outputs to the existing native prediction archive schema."""

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

from demosaic.experiments.artifacts import checked, read_json, reference, write_json
from demosaic.prediction_archive import fingerprint, iter_predictions


def export(result_path, output):
    if "torch" in sys.modules or os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise RuntimeError("Archive export requires NumPy only and hidden CUDA")
    result = read_json(result_path)
    assert result["all_complete"]
    assert (result["kind"], result["cases"]) in {("preflight", 3), ("full", 3162)}
    plan = read_json(checked(result["plan"]))
    canonical = read_json(checked(plan["canonical_inputs"]))
    records = {(r["stage"], r["batch"]): r for r in canonical["records"]}
    output = Path(output).resolve()
    output.mkdir()
    predictions, supervision = output / "predictions", output / "supervision"
    predictions.mkdir()
    supervision.mkdir()
    manifest = output / "records.jsonl"
    sources, contexts, count, batches = [], {label: set() for label in result["models"]}, 0, 0
    with manifest.open("x") as stream:
        for binding in result["case_records"]:
            case = read_json(checked(binding))
            if case["stage"] != "photo":
                continue
            canonical_case = records["photo", case["batch"]]
            assert case["canonical_arrays"] == canonical_case["arrays"]
            assert case["input_fingerprints"] == {
                k: canonical_case["fingerprints"][k]
                for k in ["packed", "variance", "colors", "wb", "matrix"]
            }
            source = checked(case["canonical_arrays"])
            target = supervision / (case["canonical_arrays"]["sha256"] + ".npz")
            if not target.exists():
                os.link(source, target)
            with np.load(target, allow_pickle=False) as data:
                descriptions = {key: fingerprint(data[key]) for key in data.files}
            context = {
                **canonical_case["context"],
                "input_fingerprints": case["input_fingerprints"],
            }
            context_key = json.dumps(context, sort_keys=True, allow_nan=False)
            assert {v["arm"] for v in case["variants"]} == set(result["models"])
            for variant in case["variants"]:
                label = variant["arm"]
                specification = result["models"][label]
                assert (
                    variant["checkpoint"] == specification["checkpoint"]
                    and variant["weights"] == "EMA"
                )
                assert context_key not in contexts[label]
                contexts[label].add(context_key)
                prediction_source = checked(variant["prediction"])
                value = np.load(prediction_source, allow_pickle=False)
                assert value.dtype == np.float32 and value.shape[0] == len(context["ids"])
                prediction_path = predictions / f"batch-{count:06d}.npy"
                os.link(prediction_source, prediction_path)
                row = {
                    "schema": "demosaic-predictions-v1",
                    "index": count,
                    "model": {
                        "label": label,
                        "sha256": specification["checkpoint"]["sha256"],
                        "step": specification["step"],
                        "weights": "EMA",
                        "self_ensemble": "none",
                    },
                    "context": context,
                    "prediction": reference(prediction_path),
                    "prediction_values": fingerprint(value),
                    "supervision": reference(target),
                    "supervision_values": descriptions,
                }
                stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
                count += 1
            batches += 1
            sources.append(binding)
    assert batches == (3108 if result["kind"] == "full" else 1)
    assert count == batches * len(result["models"])
    values = list(contexts.values())
    assert all(value == values[0] for value in values)
    # Exercise the established reader's path/hash/value checks. Hardlinks own
    # archive-local names without copying or changing any tensor bytes.
    verified = sum(1 for _ in iter_predictions(manifest))
    assert verified == count
    write_json(
        output / "result.json",
        {
            "producer": reference(__file__),
            "source_result": reference(result_path),
            "kind": result["kind"],
            "manifest": reference(manifest),
            "records": count,
            "photo_batches": batches,
            "models": result["models"],
            "source_cases": sources,
            "all_records_verified_with_existing_reader": True,
            "scope": "New archive adapter records explicitly derived from closed canonical CPU outputs, not original legacy receipts. All native FP32 predictions and canonical physical/target arrays retain exact bytes by same-filesystem hardlinks. Same context/conditioning and all logical fingerprints checked. Photo/synthetic sources remain distinct; preflight is not a full427 result.0 neural/RAW/noise/GPU/optimizer calls. Suitable for the unchanged full427 local-detail analysis at declared compatible steps.",
        },
    )
    print("Verified native archive", count, "model/batch records")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    export(args.result, args.output)
