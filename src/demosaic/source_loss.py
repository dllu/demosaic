"""Detached per-draw diagnostics for finding problematic training photographs."""

import json

import torch

from .losses import DEFAULT_RECONSTRUCTION_EPSILON, reconstruction_loss
from .precision import ieee_fp32
from .safety import writable_path


def validate_source_loss_every(value):
    if type(value) is not int or value < 0:
        raise ValueError("source_loss_every must be a nonnegative integer")
    return value


class SourceLossTrace:
    """Score existing Commons predictions as FP32 singleton losses, without gradients.

    Singleton mask denominators differ from a batch loss. These diagnostics are
    not additive contributions to the actual training objective. High loss can
    reflect difficult noise/detail rather than bad source quality; inspect it.
    """

    def __init__(self, path, config):
        self.path = writable_path(path)
        self.options = {
            "physical_fp32": True,
            "normalized_sensor_weight": config.get("normalized_sensor_weight", 0.0),
            "multiscale_sensor_weight": config.get("multiscale_sensor_weight", 0.0),
            "objective": config.get("reconstruction_objective", "charbonnier-v1"),
            "camera_supervision": config.get("camera_supervision", "reference-white-v1"),
            "reference_interval_weight": config.get("reference_interval_weight", 0.0),
            "reconstruction_charbonnier_epsilon": config.get(
                "reconstruction_charbonnier_epsilon", DEFAULT_RECONSTRUCTION_EPSILON
            ),
            "normalized_band_weight": config.get("normalized_band_weight", 0.0),
        }

    @torch.no_grad()
    def __call__(self, data_step, domain, clean, prediction, auxiliary, batch, *, step):
        if domain != "commons":
            return
        size = len(prediction)
        sources = clean["source"]
        if len(sources) != size:
            raise ValueError("Source trace and predictions have different example counts")
        records = []
        with torch.autocast(prediction.device.type, enabled=False), ieee_fp32():
            for index, source in enumerate(sources):
                # All prepared supervision tensors retain their example axis.
                sample = {
                    key: value[index : index + 1].detach().float()
                    if value.is_floating_point()
                    else value[index : index + 1].detach()
                    for key, value in batch.items()
                }
                value, terms = reconstruction_loss(
                    prediction[index : index + 1].detach().float(),
                    sample,
                    None if auxiliary is None else auxiliary[index : index + 1].detach().float(),
                    **self.options,
                )
                scores = {
                    "singleton_loss_fp32": float(value),
                    "terms": {key: float(term) for key, term in terms.items()},
                }
                if not torch.isfinite(value) or any(not torch.isfinite(t) for t in terms.values()):
                    raise ValueError("Nonfinite source diagnostic")
                records.append(
                    {
                        "event": "source-loss",
                        "step": step,
                        "data_step": data_step,
                        "example_in_source_batch": index,
                        "domain": domain,
                        "source": json.loads(source),
                        **scores,
                        "noise": {
                            key: float(sample[key].reshape(-1)[0]) for key in ("shot", "read")
                        },
                        "colors": sample["colors"][0].tolist(),
                        "wb": sample["wb"][0].tolist(),
                        "matrix": sample["matrix"][0].tolist(),
                        "source_rgb_shape": list(clean["rgb"].shape[1:]),
                        "supervision_shape": list(prediction.shape[1:]),
                        "score_definition": "FP32 detached singleton reconstruction, not an additive batch-loss contribution",
                    }
                )
                if "noise_view" in sample:
                    records[-1]["source_trace_noise_view"] = int(
                        sample["noise_view"].reshape(-1)[0]
                    )
        # Finish all diagnostics before appending; don't leave a partial batch.
        with self.path.open("a") as stream:
            for record in records:
                stream.write(json.dumps(record, allow_nan=False) + "\n")
