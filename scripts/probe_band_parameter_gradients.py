"""Measure a frozen model's parameter response to band supervision on train data."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np
import psutil
import torch
from probe_band_supervision import band, binding, guard, save

from demosaic.inference import load_checkpoint
from demosaic.losses import reconstruction_loss


def tensor_hash(value):
    return hashlib.sha256(value.detach().contiguous().numpy().tobytes()).hexdigest()


def state_hash(module):
    digest = hashlib.sha256()
    for name, value in module.state_dict().items():
        digest.update(name.encode())
        digest.update(value.detach().contiguous().numpy().tobytes())
    return digest.hexdigest()


def run(path):
    plan = json.loads(Path(path).read_text())
    guard(plan)
    assert binding(__file__) == plan["worker"] and os.environ["CUDA_VISIBLE_DEVICES"] == ""
    assert not torch.cuda.is_initialized() and psutil.virtual_memory().available >= 40*2**30
    torch.set_num_threads(2)
    output = Path(plan["output"])
    output.mkdir(parents=True, exist_ok=False)
    model, state = load_checkpoint(plan["checkpoint"]["path"], "cpu")
    model.eval()
    assert state["loaded_sha256"] == plan["checkpoint"]["sha256"] and state["step"] == 20000
    original = model.restoration_state_dict()
    assert len(original) == 91 and all(torch.equal(v, state["ema"][k]) for k, v in original.items())
    parameters = {k: v for k, v in model.named_parameters() if v.requires_grad}
    assert len(parameters) == 89 and all(p.device.type == "cpu" for p in model.parameters())
    before, encoder_before, configuration = state_hash(model), state_hash(model.context.backbone), model.config.to_dict()
    # The numeric backbone hash convention used by the project's official receipts.
    from profile_raw_kernel_inference import model_hash
    assert model_hash(model.context.backbone) == plan["official_backbone_sha256"]
    del state, original
    rng = torch.get_rng_state().clone()
    calls = {"model": 0, "encoder": 0}
    def count(name):
        def hook(*_a):
            calls[name] += 1
        return hook
    handles = [model.register_forward_pre_hook(count("model")), model.context.backbone.register_forward_pre_hook(count("encoder"))]
    rows, maximum_error = [], 0.
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    for index, case in enumerate(plan["cases"]):
        assert psutil.virtual_memory().available >= 32*2**30
        with np.load(case["arrays"]["path"], allow_pickle=False) as archive:
            batch = {k: torch.from_numpy(archive[k].copy()) for k in case["input_tensor_SHA256"]}
        assert {k: tensor_hash(v) for k, v in batch.items()} == case["input_tensor_SHA256"]
        model.set_noise(case["noise_conditioning"]["shot"], case["noise_conditioning"]["read"])
        prediction, auxiliary = model(*(batch[k] for k in ("packed", "variance", "colors", "wb", "matrix")), auxiliary=True)
        batch["sensor_target"] = batch["target"]
        baseline, baseline_parts = reconstruction_loss(prediction, batch, auxiliary, camera_supervision="sensor-valid-v1", reconstruction_charbonnier_epsilon=.0003)
        candidate, parts = reconstruction_loss(prediction, batch, auxiliary, camera_supervision="sensor-valid-v1", reconstruction_charbonnier_epsilon=.0003, normalized_band_weight=.0003)
        assert all(torch.equal(baseline_parts[k], parts[k]) for k in baseline_parts)
        addition = .0003*parts["normalized_band"]
        assert torch.equal(candidate, baseline+addition)
        target_band = band(batch["target"])
        target_band[..., :8, :] = target_band[..., -8:, :] = target_band[..., :, :8] = target_band[..., :, -8:] = 0
        coefficient = ((batch["target"]-prediction.detach())*target_band).sum()/target_band.square().sum().clamp_min(1e-20)
        direction = (coefficient*target_band).detach()
        vectors = []
        for value, retain in ((baseline, True), (addition, True), ((prediction*direction).sum(), False)):
            gradients = torch.autograd.grad(value, tuple(parameters.values()), retain_graph=retain, allow_unused=True)
            vectors.append([g.detach() if g is not None else torch.zeros_like(p) for p, g in zip(parameters.values(), gradients, strict=True)])
        labels = ("baseline", "band", "correction")
        layer_rows, gram = [], np.zeros((3, 3))
        for j, (name, parameter) in enumerate(parameters.items()):
            values = [v[j] for v in vectors]
            assert all(torch.isfinite(v).all() for v in values)
            a = [v.contiguous().numpy().ravel().astype(np.float64) for v in values]
            local = np.zeros((3, 3))
            for m in range(3):
                for n in range(m, 3):
                    numpy_value = float(a[m]@a[n])
                    torch_value = float(torch.dot(values[m].reshape(-1).double(), values[n].reshape(-1).double()))
                    error = abs(numpy_value-torch_value)
                    assert error <= 1e-9+1e-10*abs(numpy_value), (name, m, n, error)
                    maximum_error = max(maximum_error, error)
                    local[m, n] = local[n, m] = numpy_value
            gram += local
            layer_rows.append({"parameter": name, "shape": list(parameter.shape), "gradients_sha256": dict(zip(labels, map(tensor_hash, values), strict=True)), "Gram_F64": local.tolist()})
        norms = math.sqrt(gram[0, 0]), math.sqrt(max(gram[0, 0]+2*gram[0, 1]+gram[1, 1], 0))
        slopes = gram[0, 2], gram[0, 2]+gram[1, 2]
        cosine = [-v/max(n*math.sqrt(gram[2, 2]), 1e-30) for v, n in zip(slopes, norms, strict=True)]
        retained = None
        if index in plan["retain_full_gradient_case_indices"]:
            target = output/f"full-parameter-gradients-{index:02d}.npz"
            np.savez(target, **{f"g{m}_{j}": v.numpy() for m, group in enumerate(vectors) for j, v in enumerate(group)})
            retained = binding(target)
        prediction_file = output/f"prediction-{index:02d}.npy"
        np.save(prediction_file, prediction.detach().numpy(), allow_pickle=False)
        rows.append({"source_id": case["source_id"], "contrast": case["additional_contrast_factor"], "condition": case["condition"],
                     "input": case["arrays"], "prediction": binding(prediction_file), "missing_coefficient": float(coefficient),
                     "baseline_loss": float(baseline.detach()), "band_addition": float(addition.detach()), "parameter_tensors": len(parameters),
                     "Gram_F64": gram.tolist(), "layers": layer_rows, "full_gradients": retained,
                     "baseline_gradient_norm": norms[0], "candidate_gradient_norm": norms[1], "gradient_norm_ratio": norms[1]/norms[0],
                     "baseline_corrective_derivative": slopes[0], "candidate_corrective_derivative": slopes[1],
                     "baseline_correction_cosine": cosine[0], "candidate_correction_cosine": cosine[1],
                     "correction_per_gradient_ratio": (slopes[1]/slopes[0])/(norms[1]/norms[0]) if slopes[0] < -1e-12 else None})
        del vectors, prediction, auxiliary, baseline, candidate, parts, addition, gradients, values
        assert torch.equal(rng, torch.get_rng_state()) and all(p.grad is None for p in model.parameters())
        print({"cases_completed": index+1, "planned": len(plan["cases"]), "cosine_change": cosine[1]-cosine[0]}, flush=True)
    for h in handles:
        h.remove()
    assert calls == {"model": 8, "encoder": 8}
    assert state_hash(model) == before and state_hash(model.context.backbone) == encoder_before and model.config.to_dict() == configuration
    assert not torch.cuda.is_initialized()
    guard(plan)
    save(output/"result-v1.json", {"plan": binding(path), "worker": binding(__file__), "owner": owner, "rows": rows,
                                  "calls": calls, "maximum_independent_Gram_error": maximum_error, "parameter_backward_evaluations": 24,
                                  "model_backbone_config_and_Torch_RNG_unchanged": True, "optimizer_updates": 0, "new_noise_observations": 0,
                                  "RAW_decodes": 0, "CUDA_initialized": False, "scope": plan["scope"]})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    run(parser.parse_args().plan)
