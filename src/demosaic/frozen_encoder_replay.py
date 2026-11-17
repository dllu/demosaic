"""Evaluation-only reuse of identical frozen CPU DINO calls across checkpoints."""

from contextlib import contextmanager

import torch

from .prediction_archive import fingerprint


class FrozenDinoReplay:
    """Compare checkpoints without recomputing their identical frozen features.

    All backbones must be identical, frozen CPU DINOv3 ConvNeXt instances in
    evaluation mode. Their weights must stay unchanged for this object's life.
    Each group permits one identical input/hidden-state request; different inputs
    are rejected before replay. Consumers must leave returned features unchanged,
    independently checked before group exit. No training/autograd use is allowed.
    """

    def __init__(self, backbones):
        self.backbones = list(backbones)
        if not self.backbones or len({id(b) for b in self.backbones}) != len(self.backbones):
            raise ValueError("Require distinct frozen backbone instances")
        self.originals = [b.forward for b in self.backbones]
        self.configuration = self._configuration(self.backbones[0])
        reference = self.backbones[0].state_dict()
        for backbone in self.backbones:
            if (
                backbone.training
                or backbone.config.model_type != "dinov3_convnext"
                or any(p.requires_grad or p.device.type != "cpu" for p in backbone.parameters())
            ):
                raise ValueError("Require frozen CPU DINOv3 ConvNeXt in evaluation mode")
            if (
                type(backbone) is not type(self.backbones[0])
                or self._configuration(backbone) != self.configuration
            ):
                raise ValueError("Backbone classes or configurations differ")
            values = backbone.state_dict()
            if values.keys() != reference.keys() or any(
                t.dtype != reference[k].dtype or not torch.equal(t, reference[k])
                for k, t in values.items()
            ):
                raise ValueError("Backbone state tensors differ")
        self.active = False

    @staticmethod
    def _configuration(backbone):
        config = backbone.config
        return config.to_dict() if hasattr(config, "to_dict") else vars(config).copy()

    @contextmanager
    def group(self):
        if self.active or not torch.is_inference_mode_enabled():
            raise ValueError("Use a nonnested inference-only replay group")
        if any(
            b.training or any(p.requires_grad or p.device.type != "cpu" for p in b.parameters())
            for b in self.backbones
        ):
            raise ValueError("Backbone became trainable")
        if any(self._configuration(b) != self.configuration for b in self.backbones):
            raise ValueError("Backbone configuration changed")
        if any(
            b.forward != original
            for b, original in zip(self.backbones, self.originals, strict=True)
        ):
            raise ValueError("Backbone forward changed outside the replay group")
        self.active = True
        statistics = {"requests": 0, "executions": 0, "replays": 0}
        cached = {}

        def request(original, *args, **kwargs):
            if (
                args
                or set(kwargs) != {"pixel_values", "output_hidden_states"}
                or kwargs["output_hidden_states"] is not True
                or kwargs["pixel_values"].device.type != "cpu"
            ):
                raise ValueError("Replay requires an explicit CPU hidden-state request")
            signature = fingerprint(kwargs["pixel_values"])
            statistics["requests"] += 1
            if cached:
                if signature != cached["signature"]:
                    raise ValueError("Frozen encoder inputs differ before replay")
                statistics["replays"] += 1
                return cached["output"]
            output = original(**kwargs)
            cached.update(
                signature=signature,
                output=output,
                hidden=[fingerprint(t) for t in output.hidden_states],
            )
            statistics["executions"] += 1
            return output

        try:
            for backbone, original in zip(self.backbones, self.originals, strict=True):
                backbone.forward = lambda *a, original=original, **kw: request(original, *a, **kw)
            yield statistics
            if cached and cached["hidden"] != [
                fingerprint(t) for t in cached["output"].hidden_states
            ]:
                raise ValueError("A consumer modified replayed hidden states")
        finally:
            for backbone, original in zip(self.backbones, self.originals, strict=True):
                backbone.forward = original
            self.active = False
