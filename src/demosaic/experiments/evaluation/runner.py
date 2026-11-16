"""Stream the established held-out cases through an explicitly loaded component."""

import numpy as np
import torch

from ..artifacts import checked, read_json, reference, write_json
from ..paths import writable_output
from .detail import DetailMetrics, summarize
from .native import load_native, write_native


def evaluate_cases(
    model, manifest, output, *, checkpoint, method, device="cpu", anchor_reference=None
):
    """Read cached parent predictions; real independent references are never scored.

    Accept the existing quality-design `observations` schema. Inputs, references
    and predictions remain distinct; only physical observation fields enter
    the model. Native image publication is a separate explicit rendering step.
    """
    binding = reference(manifest)
    document = read_json(checked(binding))
    cases = document["observations"]
    ids = [case["id"] for case in cases]
    if not cases or len(set(ids)) != len(ids):
        raise ValueError("Evaluation needs unique nonempty case IDs")
    anchor_rows = anchor_document = None
    anchor_values = anchor_channels = 0
    if anchor_reference is not None:
        anchor_document = read_json(checked(anchor_reference["scores"]))
        selected = [r for r in anchor_document["rows"] if r["method"] == anchor_reference["method"]]
        anchor_rows = {r["id"]: r for r in selected}
        if len(anchor_rows) != len(selected) or set(anchor_rows) != set(ids):
            raise ValueError("Anchor control must cover the exact case identities")
    output = writable_output(output)
    output.mkdir(parents=True, exist_ok=False)
    metric = DetailMetrics()
    rows, predictions = [], {}
    model.eval()
    with torch.inference_mode():
        for index, case in enumerate(cases):
            with np.load(checked(case["arrays"]), allow_pickle=False) as archive:
                arrays = dict(archive)
            parent = load_native(case["parent"])
            batch = [
                torch.from_numpy(arrays[k]).to(device)
                for k in ("packed", "variance", "colors", "wb")
            ]
            model_args = (torch.from_numpy(parent).to(device), *batch)
            delivered = (
                model(*model_args, return_aux=True) if anchor_rows is not None else model(*model_args)
            )
            if anchor_rows is not None:
                delivered, aux = delivered
                anchor = aux["anchor_output"].float().cpu().numpy()
                actual = metric.measure(case, arrays, parent, anchor)
                for name, expected in anchor_rows[case["id"]].items():
                    if name == "method":
                        continue
                    if name not in actual or actual[name] != expected:
                        raise ValueError(f"Frozen anchor scalar mismatch: {case['id']} / {name}")
                    anchor_values += isinstance(expected, (int, float))
                retained = anchor_document["native_predictions"].get(case["id"], {})
                if anchor_reference["method"] in retained:
                    expected = load_native(retained[anchor_reference["method"]])
                    np.testing.assert_array_equal(anchor.view(np.uint32), expected.view(np.uint32))
                    anchor_channels += anchor.size
            value = delivered.float().cpu().numpy()
            row = metric.measure(case, arrays, parent, value)
            row["method"] = method
            rows.append(row)
            predictions[case["id"]] = write_native(
                output / f"prediction-{index:04d}.json", value, baseline=case["parent"]
            )
    checked(binding)
    result = {
        "status": "completed-cached-component-evaluation",
        "cases": binding,
        "checkpoint": checkpoint,
        "method": method,
        "rows": rows,
        "summary": summarize(rows),
        "native_predictions": predictions,
        "new_parent_DINO_forwards": 0,
        "new_noise_draws": 0,
        "scope": "Numerical evaluation only; native review and model selection remain separate.",
    }
    if anchor_reference is not None:
        checked(anchor_reference["scores"])
        result["anchor_verification"] = {
            "reference": anchor_reference,
            "cases": len(anchor_rows),
            "exact_scalar_checks": anchor_values,
            "exact_retained_native_RGB_channels": anchor_channels,
            "new_anchor_forwards": 0,
            "scope": "Existing complete anchor path from the same forward. Every retained control scalar and available original native array matches exactly.",
        }
    write_json(output / "scores.json", result)
    return reference(output / "scores.json")
