"""Optional training-only spatial supervision from the frozen first DINO stage."""

import math

import torch

from .color import render
from .precision import ieee_fp32
from .training_context import TrainingContext

POLICY = "frozen-convnext-stage0-spatial-mse-v1"


def feature_options(config):
    value = config.get("dino_feature_weight", 0.0)
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError("DINO feature weight must be finite and nonnegative")
    policy = config.get("dino_feature_policy")
    if (value > 0 and policy != POLICY) or (value == 0 and policy is not None):
        raise ValueError("Unknown or inactive DINO feature policy")
    if value:
        model = config.get("model", {})
        if not model.get("dino") or model.get("dino_feature_fusion") != "convnext-pyramid":
            raise ValueError("DINO feature loss requires a frozen ConvNeXt pyramid")
        if config.get("camera_supervision") != "sensor-valid-v1":
            raise ValueError("DINO feature loss requires sensor-valid camera targets")
        if (
            config.get("noise_pair_draws", 1) != 1
            or config.get("optimizer_batch_groups", 1) != 1
            or config.get("optimizer_forward_groups", 1) != 1
            or TrainingContext.from_config(config) is not None
        ):
            raise ValueError("DINO feature loss requires one noise view/group and native context")
    return float(value), policy


def require_resume_features(previous, current):
    if feature_options(previous) != feature_options(current):
        raise ValueError("Resume DINO feature supervision differs; initialize a new run")


def spatial_feature_loss(model, prediction, batch):
    """Share one frozen encoder; paired RAW/validation bypass this in the trainer."""
    backbone = model.context.backbone
    if backbone.training or any(p.requires_grad for p in backbone.parameters()):
        raise ValueError("Feature-supervision encoder must remain frozen and in evaluation mode")
    target = batch["sensor_target"]
    if prediction.shape != target.shape or prediction.ndim != 4 or prediction.shape[1] != 3:
        raise ValueError("Feature supervision needs matching native camera-RGB targets")
    with torch.autocast(prediction.device.type, enabled=False), ieee_fp32():
        predicted = render(prediction.float(), batch["wb"], batch["matrix"])
        reference = render(target.detach().float(), batch["wb"], batch["matrix"])
        mean, std = model.context.mean.float(), model.context.std.float()
        # The official full encoder returns stage0 before subsequent stages.
        # Execute that stage directly; neither coarse stages nor another model
        # instance are needed for this objective.
        with torch.no_grad():
            reference_features = backbone.stages[0]((reference - mean) / std)
        predicted_features = backbone.stages[0]((predicted - mean) / std)
        return (predicted_features - reference_features).square().mean()
