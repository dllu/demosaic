"""Optional identity-initialized adaptation around a frozen DINO encoder."""

import math

from torch import nn
from torch.nn.utils import parametrize


class DinoInputAdapter(nn.Module):
    """Learn a local preview residual before the frozen patch encoder.

    This internal feature input is not a restored-image output or a teacher
    target. A zero final convolution initially preserves the supplied preview.
    The original CFA restoration path and its physical units stay independent.
    """

    def __init__(self):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Conv2d(3, 24, 3, padding=1, padding_mode="replicate"),
            nn.SiLU(),
            nn.Conv2d(24, 24, 3, padding=1, padding_mode="replicate"),
            nn.SiLU(),
            nn.Conv2d(24, 3, 3, padding=1, padding_mode="replicate"),
        )
        nn.init.zeros_(self.layers[-1].weight)
        nn.init.zeros_(self.layers[-1].bias)

    def forward(self, preview):
        return preview + self.layers(preview).to(preview.dtype)


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
