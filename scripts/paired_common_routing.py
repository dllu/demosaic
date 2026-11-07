"""Training-only common-error adjoint with the support activation held fixed."""

import torch

from demosaic.cfa import malvar
from demosaic.precision import ieee_fp32


class _UseCorrectionAdjoint(torch.autograd.Function):
    """Preserve every value bit, including signed zero; attach another adjoint.

    This intentionally specifies a surrogate derivative. It is not the finite
    difference derivative of the numerical forward function. Only first-order
    training uses it; ordinary model inference never calls this function.
    """

    @staticmethod
    def forward(ctx, value, correction):
        return value.clone()

    @staticmethod
    def backward(ctx, gradient):
        return None, gradient


def common_output_with_fixed_support(module, output, aux, colors, wb=None):
    """Keep actual RGB values while removing common-loss derivatives through support.

    Re-synthesize the same spectral correction with support.detach(), add the
    direct RGB correction, and use that correction's derivative. This removes
    both support-parameter gradients and the indirect proposal -> support path.
    Direct spectral and spatial RGB derivatives remain. Other losses continue
    to differentiate the original output normally. Support values are still
    applied: neither inference nor the numerical common loss is ungated.

    Replaying FFT synthesis and fixed Malvar adds training computation, without
    another neural root forward or trainable parameter. Targets are not inputs.
    This routing does not guarantee an open gate, accuracy or flat-field safety.
    """
    if (
        output.ndim != 4
        or output.shape[1] != 3
        or min(output.shape) < 1
        or output.dtype != torch.float32
        or output.shape[-2] % 2
        or output.shape[-1] % 2
    ):
        raise ValueError("Expected nonempty FP32 native RGB with even spatial dimensions")
    required = {"spectral_delta", "geometry", "support", "spatial_correction"}
    if not required.issubset(aux):
        raise ValueError("Missing spectral/support/spatial training auxiliaries")
    support, spatial = aux["support"], aux["spatial_correction"]
    if (
        spatial.shape != output.shape
        or support.shape != (len(output), 1, output.shape[-2] // 2, output.shape[-1] // 2)
        or any(v.dtype != output.dtype or v.device != output.device for v in (support, spatial))
    ):
        raise ValueError("Support and direct RGB correction must align with FP32 output")
    with torch.autocast(output.device.type, enabled=False), ieee_fp32():
        proposal = module.synthesis(aux["spectral_delta"], aux["geometry"])
        if proposal.shape != (len(output), 4, *support.shape[-2:]):
            raise ValueError("Spectral synthesis must return aligned packed four-phase data")
        correction = malvar(proposal * support.detach(), colors, wb) + spatial
        return _UseCorrectionAdjoint.apply(output.detach(), correction)
