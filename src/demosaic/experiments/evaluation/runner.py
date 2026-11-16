"""Stream the established held-out cases through an explicitly loaded component."""

import numpy as np
import torch

from ..artifacts import checked, read_json, reference, write_json
from ..paths import writable_output
from .detail import DetailMetrics, summarize
from .native import load_native, write_native


def evaluate_cases(model, manifest, output, *, checkpoint, method, device="cpu"):
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
            value = model(torch.from_numpy(parent).to(device), *batch).float().cpu().numpy()
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
    write_json(output / "scores.json", result)
    return reference(output / "scores.json")
