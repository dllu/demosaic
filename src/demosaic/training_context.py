"""Matched central supervision with an explicitly chosen surrounding input field."""

from dataclasses import dataclass

import torch

FULL_FIELDS = frozenset({"target", "sensor_target", "sensor_reference", "sensor_mask"})
PACKED_FIELDS = frozenset({"packed", "variance"})
CONFIG_FIELDS = ("forward_patch_size", "loss_patch_size", "validation_patch_size")


def _size(value, label):
    if type(value) is not int or value < 4 or value % 2:
        raise ValueError(f"{label} must be an even native size of at least four")
    return value


def _bounds(shape, size):
    height, width = shape
    if size > min(height, width) or (height - size) % 4 or (width - size) % 4:
        raise ValueError("Central crop must fit and preserve both Bayer phase offsets")
    return (height - size) // 2, (width - size) // 2


def crop_training_batch(batch, size):
    """Crop physical samples, clean targets and masks in their own coordinate units.

    Metadata is shared unchanged; no values are interpolated or random draws made.
    Unrecognized spatial fields refuse cropping rather than retaining a larger mask.
    """
    _size(size, "Crop size")
    shape = tuple(n * 2 for n in batch["packed"].shape[-2:])
    top, left = _bounds(shape, size)
    if shape == (size, size):
        return batch
    result = {}
    half = tuple(n // 2 for n in shape)
    for key, value in batch.items():
        if key in FULL_FIELDS:
            if value.ndim != 4 or tuple(value.shape[-2:]) != shape:
                raise ValueError(f"Unexpected full-resolution field shape: {key}")
            result[key] = value[..., top : top + size, left : left + size]
        elif key in PACKED_FIELDS:
            if value.ndim != 4 or tuple(value.shape[-2:]) != half:
                raise ValueError(f"Unexpected packed-resolution field shape: {key}")
            result[key] = value[
                ..., top // 2 : (top + size) // 2, left // 2 : (left + size) // 2
            ]
        elif torch.is_tensor(value) and value.ndim >= 3 and tuple(value.shape[-2:]) in (
            shape,
            half,
        ):
            raise ValueError(f"Unrecognized spatial training field: {key}")
        else:
            result[key] = value
    return result


@dataclass(frozen=True)
class TrainingContext:
    source_size: int
    forward_size: int
    loss_size: int
    validation_size: int

    @classmethod
    def from_config(cls, config):
        if not any(key in config for key in CONFIG_FIELDS):
            return None
        source = _size(config.get("patch_size", 256), "Source patch size")
        forward = _size(config.get("forward_patch_size", source), "Forward patch size")
        loss = _size(config.get("loss_patch_size", forward), "Loss patch size")
        validation = _size(config.get("validation_patch_size", source), "Validation patch size")
        if any(size < 32 or size % 16 for size in (source, validation)):
            raise ValueError("Source/validation datasets require sizes >=32 divisible by 16")
        _bounds((source, source), forward)
        _bounds((forward, forward), loss)
        if config.get("optimizer_batch_groups", 1) != 1:
            raise ValueError("Explicit training context currently requires a single source batch")
        return cls(source, forward, loss, validation)

    def forward_batch(self, batch):
        expected = (self.source_size // 2,) * 2
        if tuple(batch["packed"].shape[-2:]) != expected:
            raise ValueError("Prepared source batch differs from declared training context")
        return crop_training_batch(batch, self.forward_size)

    def supervision(self, prediction, auxiliary, source_batch):
        if tuple(prediction.shape[-2:]) != (self.forward_size,) * 2:
            raise ValueError("Prediction differs from declared forward context")
        top, left = _bounds(prediction.shape[-2:], self.loss_size)
        prediction = prediction[..., top : top + self.loss_size, left : left + self.loss_size]
        if auxiliary is not None:
            if tuple(auxiliary.shape[-2:]) != (self.forward_size // 2,) * 2:
                raise ValueError("Auxiliary mosaic differs from declared forward context")
            auxiliary = auxiliary[
                ..., top // 2 : (top + self.loss_size) // 2,
                left // 2 : (left + self.loss_size) // 2,
            ]
        return prediction, auxiliary, crop_training_batch(source_batch, self.loss_size)


def require_resume_context(previous, current):
    before, after = TrainingContext.from_config(previous), TrainingContext.from_config(current)
    if before is None and after is None:
        return
    if before is None:
        size = previous.get("patch_size", 256)
        before = TrainingContext(size, size, size, size)
    if after is None:
        size = current.get("patch_size", 256)
        after = TrainingContext(size, size, size, size)
    if before != after:
        raise ValueError("Resume input context or central supervision geometry differs")
