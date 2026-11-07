"""Connect the pinned sampler's native first-order backward to Torch autograd.

V170 used the operator for inference. Training also needs this registration;
the pinned CPU/CUDA backward kernels are reused without numerical changes.
"""

import torch
from torch.autograd.function import once_differentiable

_registered = False


def enable_sampler_autograd():
    global _registered
    if _registered:
        return
    namespace = torch.ops.deform_neighbourhood_sampling
    if not hasattr(namespace, "deform_neighbourhood_backward"):
        raise RuntimeError("Load the pinned native sampling library before training")

    def setup_context(ctx, inputs, output):
        ctx.save_for_backward(*inputs[:2])
        ctx.options = inputs[2:]

    @once_differentiable
    def backward(ctx, gradient):
        first, offset = ctx.saved_tensors
        gradients = namespace.deform_neighbourhood_backward.default(
            gradient.contiguous(), first, offset, *ctx.options
        )
        return (*gradients, *(None for _ in ctx.options))

    torch.library.register_autograd(
        "deform_neighbourhood_sampling::deform_neighbourhood",
        backward,
        setup_context=setup_context,
    )
    _registered = True
