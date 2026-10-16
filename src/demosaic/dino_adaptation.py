"""Optional zero-initialized low-rank updates to DINO attention queries/values."""

import math

from torch import nn
from torch.nn.utils import parametrize


class LowRankWeight(nn.Module):
    """W + B A, with unit scale (LoRA alpha = rank) and an initially zero B."""

    def __init__(self, weight, rank):
        super().__init__()
        self.down = nn.Parameter(weight.new_empty(rank, weight.shape[1]))
        self.up = nn.Parameter(weight.new_zeros(weight.shape[0], rank))
        nn.init.kaiming_uniform_(self.down, a=math.sqrt(5))

    def forward(self, weight):
        return weight + self.up @ self.down


def install_qv_adapters(backbone, rank):
    """Adapt the pinned HF DINOv3 ViT layout; reject incomplete target selection.

    Return the same parametrization modules under an external ModuleDict. Its
    state is saved outside context.backbone, whose original pretrained tensors
    are deliberately omitted from portable restoration checkpoints. PyTorch
    deduplicates the shared parameters for optimization/device moves.
    """
    if type(rank) is not int or rank < 1:
        raise ValueError("DINO adapter rank must be a positive integer")
    layers = getattr(backbone, "layer", None)
    if not isinstance(layers, nn.ModuleList) or not len(layers):
        raise ValueError("DINO adapters require the pinned ViT layer/attention layout")
    targets = []
    for index, layer in enumerate(layers):
        attention = getattr(layer, "attention", None)
        for name in ["q_proj", "v_proj"]:
            projection = getattr(attention, name, None)
            if not isinstance(projection, nn.Linear) or parametrize.is_parametrized(projection):
                raise ValueError(f"Unsupported or already adapted DINO projection: {index}/{name}")
            if rank > min(projection.weight.shape):
                raise ValueError("DINO adapter rank exceeds projection dimensions")
            targets.append((f"layer{index:03d}_{name}", projection))
    backbone.requires_grad_(False)
    adapters = nn.ModuleDict()
    for name, projection in targets:
        update = LowRankWeight(projection.weight, rank)
        parametrize.register_parametrization(projection, "weight", update)
        adapters[name] = update
    return adapters
