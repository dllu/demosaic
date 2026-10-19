"""Isolated inference-only implicit-GEMM convolution candidate.

This is not imported by production inference/training. Interpreter execution
checks indexing only; it does not reproduce TF32 or Tensor Core arithmetic.
Actual CUDA error gates and timing must pass before any integration.
"""

import os

import torch
import triton
import triton.language as tl


@triton.jit
def _implicit_conv(
    X, W, Y,
    N: tl.constexpr, IC: tl.constexpr, IH: tl.constexpr, IW: tl.constexpr,
    OC: tl.constexpr, OH: tl.constexpr, OW: tl.constexpr,
    KH: tl.constexpr, KW: tl.constexpr, STRIDE: tl.constexpr, PAD: tl.constexpr,
    XN: tl.constexpr, XC: tl.constexpr, XH: tl.constexpr, XW: tl.constexpr,
    WN: tl.constexpr, WC: tl.constexpr, WH: tl.constexpr, WW: tl.constexpr,
    BM: tl.constexpr, BN: tl.constexpr, BK: tl.constexpr,
):
    rows = tl.program_id(0) * BM + tl.arange(0, BM)
    cols = tl.program_id(1) * BN + tl.arange(0, BN)
    batch = rows // (OH * OW)
    oy = rows // OW % OH
    ox = rows % OW
    reduction = tl.arange(0, BK)
    acc = tl.full((BM, BN), 0, tl.float32)
    for start in range(tl.cdiv(KH * KW * IC, BK)):
        k = start * BK + reduction
        channel = k % IC
        ky = k // IC // KW
        kx = k // IC % KW
        iy = oy[:, None] * STRIDE - PAD + ky[None, :]
        ix = ox[:, None] * STRIDE - PAD + kx[None, :]
        xp = X + batch[:, None] * XN + channel[None, :] * XC + iy * XH + ix * XW
        valid = (rows[:, None] < N * OH * OW) & (k[None, :] < KH * KW * IC)
        valid = valid & (iy >= 0) & (iy < IH) & (ix >= 0) & (ix < IW)
        lhs = tl.load(xp, mask=valid, other=0)
        wp = W + cols[None, :] * WN + channel[:, None] * WC
        wp = wp + ky[:, None] * WH + kx[:, None] * WW
        rhs = tl.load(wp, mask=(cols[None, :] < OC) & (k[:, None] < KH * KW * IC), other=0)
        acc = tl.dot(lhs, rhs, acc, input_precision="tf32x3", out_dtype=tl.float32)
    yp = Y + rows[:, None] * OC + cols[None, :]
    tl.store(yp, acc, mask=(rows[:, None] < N * OH * OW) & (cols[None, :] < OC))


def _pair(value):
    if type(value) is int:
        return (value, value)
    if isinstance(value, (list, tuple)) and len(value) == 2 and all(type(v) is int for v in value):
        return tuple(value)
    raise ValueError("Use integer scalar or pair geometry")


def convolution(value, weight, *, stride=1, padding=1, interpreter=False):
    """FP32/channels-last dense3x3s1p1 or dense2x2s2p0, no bias/groups."""
    if torch.is_grad_enabled():
        raise ValueError("Experimental convolution is inference-only; disable gradients")
    cpu_interpreter = (
        interpreter and os.environ.get("TRITON_INTERPRET") == "1"
        and value.device.type == weight.device.type == "cpu"
    )
    if not cpu_interpreter and (value.device.type != "cuda" or weight.device != value.device):
        raise ValueError("Use CUDA operands, or the explicit CPU interpreter for indexing tests")
    if value.dtype != torch.float32 or weight.dtype != torch.float32:
        raise ValueError("FP32 input and weights required")
    if value.ndim != 4 or weight.ndim != 4 or weight.shape[1] != value.shape[1]:
        raise ValueError("Expected compatible dense NCHW tensor shapes")
    if not value.is_contiguous(memory_format=torch.channels_last) or not weight.is_contiguous(memory_format=torch.channels_last):
        raise ValueError("Both operands must be channels-last contiguous")
    stride, padding = _pair(stride), _pair(padding)
    kh, kw = weight.shape[-2:]
    if ((kh, kw), stride, padding) not in [((3, 3), (1, 1), (1, 1)), ((2, 2), (2, 2), (0, 0))]:
        raise ValueError("Only the mature hidden3x3s1p1 and2x2s2p0 operators are covered")
    n, ic, ih, iw = value.shape
    oc = weight.shape[0]
    oh, ow = ((size + 2 * pad - kernel) // step + 1 for size, pad, kernel, step in zip((ih, iw), padding, (kh, kw), stride, strict=True))
    if min(n, ic, ih, iw, oc, oh, ow) < 1:
        raise ValueError("Positive convolution dimensions required")
    result = torch.empty((n, oc, oh, ow), device=value.device, dtype=torch.float32, memory_format=torch.channels_last)
    grid = (triton.cdiv(n * oh * ow, 64), triton.cdiv(oc, 64))
    _implicit_conv[grid](value, weight, result, n, ic, ih, iw, oc, oh, ow, kh, kw, stride[0], padding[0], *value.stride(), *weight.stride(), 64, 64, 32, num_warps=4, num_stages=3, enable_fp_fusion=False)
    return result
