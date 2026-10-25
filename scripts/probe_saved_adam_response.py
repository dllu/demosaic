"""Compare fresh Adam's gradient component on retained parameter gradients.

No network or checkpoint is loaded. Two independent zero-parameter optimizer
fixtures check the first-step formula. The model analysis uses saved gradients
and a saved output-direction Jacobian; it is an exploratory linear response,
not an optimizer update to a restoration model or a quality measurement.
"""

import argparse
import hashlib
import json
import math
import os
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import psutil
import torch

from demosaic.safety import writable_path


def binding(path):
    path = Path(path).absolute()
    with path.open("rb") as stream:
        return {"path": str(path), "sha256": hashlib.file_digest(stream, "sha256").hexdigest()}


def write(path, value):
    with Path(path).open("x") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False)+"\n")


def guard(plan):
    for item in plan["inputs"]:
        assert binding(item["path"]) == item, item
    for path, digest in plan["frozen_files"].items():
        assert binding(path)["sha256"] == digest, path


def first_adam_component(gradient, norm, epsilon):
    # Production clips the complete parameter gradient at norm1, with1e-6
    # in the clipping denominator. Adam bias correction cancels beta1/beta2
    # on its first update. Common weight decay is intentionally omitted.
    clipped = gradient*min(1., 1./(norm+1e-6))
    return -clipped/(np.abs(clipped)+epsilon)


def fixture(epsilon):
    """Compare with actual Torch64 AdamW, including clipping and near-eps values."""
    cases = [np.array([0., -1e-12, 1e-10, -1e-8, 1e-6, -.1, 1., 10.]),
             np.array([0., 1e-12, -1e-10, 1e-8, -1e-6, .1, -1., -10.])]
    errors = []
    for values in cases:
        parameter = torch.nn.Parameter(torch.zeros(values.shape, dtype=torch.float64))
        optimizer = torch.optim.AdamW([parameter], lr=1., eps=epsilon, weight_decay=.01)
        assert optimizer.defaults["betas"] == (.9, .999) and len(optimizer.state) == 0
        parameter.grad = torch.from_numpy(values.copy())
        torch.nn.utils.clip_grad_norm_([parameter], 1., error_if_nonfinite=True)
        optimizer.step()
        actual = parameter.detach().numpy()
        expected = first_adam_component(values, float(np.linalg.norm(values)), epsilon)
        error = float(np.max(np.abs(actual-expected)))
        assert error < 2e-14, error
        assert int(optimizer.state[parameter]["step"]) == 1
        errors.append(error)
    return {"fixture_optimizer_steps": 2, "maximum_absolute_Torch64_disagreement": max(errors),
            "scope": "Independent zero-valued dummy parameters, never restoration weights"}


def module_group(name):
    fields = name.split(".")
    if name.startswith("pretrained_rgb.network."):
        return ".".join(fields[:3])
    if name.startswith("pretrained_rgb.measurement_adapter."):
        return "pretrained_rgb.measurement_adapter"
    assert fields[0] == "context" and fields[1] in {"laterals", "smooth", "projections", "gates"}
    return ".".join(fields[:3])


def direction_metrics(norm_squared, dot, correction_norm):
    norm = math.sqrt(max(norm_squared, 0.))
    return {"norm": norm, "dot_saved_correction": dot,
            "correction_cosine": dot/max(norm*correction_norm, 1e-30)}


def run(path):
    plan = json.loads(Path(path).read_text())
    guard(plan)
    assert binding(__file__) == plan["worker"]
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "" and not torch.cuda.is_initialized()
    assert psutil.virtual_memory().available >= plan["minimum_available_RAM_GiB"]*2**30
    os.nice(10)
    torch.set_num_threads(2)
    rng = torch.get_rng_state().clone()

    def forbid(*_args, **_kwargs):
        raise RuntimeError("Module/model forwards forbidden in saved-gradient analysis")

    torch.nn.Module._call_impl = forbid
    output = writable_path(plan["output"])
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    fixtures = fixture(plan["epsilon"])
    original = json.loads(Path(plan["parameter_result"]["path"]).read_text())
    rows, checked_arrays = [], 0
    for index in plan["case_indices"]:
        case = original["rows"][index]
        assert case["full_gradients"] and case["parameter_tensors"] == 89
        assert binding(case["full_gradients"]["path"]) == case["full_gradients"]
        total = defaultdict(float)
        groups = defaultdict(lambda: defaultdict(float))
        layers = []
        baseline_norm, candidate_norm = case["baseline_gradient_norm"], case["candidate_gradient_norm"]
        with np.load(case["full_gradients"]["path"], allow_pickle=False) as archive:
            assert set(archive.files) == {f"g{k}_{j}" for k in range(3) for j in range(89)}
            for j, layer in enumerate(case["layers"]):
                values = []
                for k, label in enumerate(("baseline", "band", "correction")):
                    a = archive[f"g{k}_{j}"]
                    assert a.dtype == np.float32 and list(a.shape) == layer["shape"] and np.isfinite(a).all()
                    assert hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest() == layer["gradients_sha256"][label]
                    values.append(a.ravel().astype(np.float64))
                    checked_arrays += 1
                baseline, addition, correction = values
                candidate = baseline+addition
                adam_old = first_adam_component(baseline, baseline_norm, plan["epsilon"])
                adam_new = first_adam_component(candidate, candidate_norm, plan["epsilon"])
                measures = {"elements": baseline.size, "correction_norm_squared": float(correction@correction),
                            "raw_baseline_dot": -float(baseline@correction),
                            "raw_candidate_dot": -float(candidate@correction),
                            "Adam_baseline_dot": float(adam_old@correction),
                            "Adam_candidate_dot": float(adam_new@correction),
                            "Adam_baseline_norm_squared": float(adam_old@adam_old),
                            "Adam_candidate_norm_squared": float(adam_new@adam_new),
                            "Adam_difference_dot": float((adam_new-adam_old)@correction),
                            "Adam_difference_norm_squared": float((adam_new-adam_old)@(adam_new-adam_old)),
                            "gradient_sign_flips": int(np.count_nonzero(baseline*candidate < 0)),
                            "baseline_zero_candidate_nonzero": int(np.count_nonzero((baseline == 0) & (candidate != 0)))}
                raw_gram = np.array([[a@b for b in values] for a in values])
                assert np.allclose(raw_gram, layer["Gram_F64"], atol=1e-9, rtol=1e-10)
                for key, value in measures.items():
                    total[key] += value
                    groups[module_group(layer["parameter"])][key] += value
                layers.append({"parameter": layer["parameter"], **measures})
        assert abs(total["raw_baseline_dot"]+case["baseline_corrective_derivative"]) < 1e-9
        assert abs(total["raw_candidate_dot"]+case["candidate_corrective_derivative"]) < 1e-9
        assert abs(total["Adam_difference_dot"]-(total["Adam_candidate_dot"]-total["Adam_baseline_dot"])) < 1e-8
        correction_norm = math.sqrt(total["correction_norm_squared"])
        rows.append({"case_index": index, "source_id": case["source_id"], "contrast": case["contrast"],
                     "condition": case["condition"], "full_gradients": case["full_gradients"],
                     "baseline": direction_metrics(total["Adam_baseline_norm_squared"], total["Adam_baseline_dot"], correction_norm),
                     "candidate": direction_metrics(total["Adam_candidate_norm_squared"], total["Adam_candidate_dot"], correction_norm),
                     "baseline_raw_correction_cosine": case["baseline_correction_cosine"],
                     "candidate_raw_correction_cosine": case["candidate_correction_cosine"],
                     "totals": dict(total), "groups": {k: dict(v) for k, v in groups.items()}, "layers": layers})
        print({"case": index, "Adam_baseline_dot": total["Adam_baseline_dot"],
               "Adam_candidate_dot": total["Adam_candidate_dot"], "addition_change": total["Adam_difference_dot"]}, flush=True)
    assert checked_arrays == 534 and torch.equal(rng, torch.get_rng_state()) and not torch.cuda.is_initialized()
    guard(plan)
    result = {"plan": binding(path), "worker": binding(__file__),
              "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
              "rows": rows, "checked_stored_FP32_gradient_arrays": checked_arrays,
              "first_step_formula_fixture": fixtures, "model_and_encoder_forwards": 0,
              "restoration_optimizer_updates": 0, "noise_generation": 0, "RAW_decodes": 0,
              "Torch_RNG_unchanged": True, "CUDA_initialized": False,
              "wall_seconds": time.monotonic()-started, "scope": plan["scope"]}
    write(output/"result-v1.json", result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    run(parser.parse_args().plan)
