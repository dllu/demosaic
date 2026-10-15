"""Keep numerical image operations in IEEE FP32 without disabling cuDNN."""

from contextlib import contextmanager, nullcontext

import torch


def amp_context(device, enabled=True):
    return (
        torch.autocast("cuda", dtype=torch.bfloat16)
        if (enabled and torch.device(device).type == "cuda")
        else nullcontext()
    )


@contextmanager
def ieee_fp32():
    convolution = torch.backends.cudnn.conv.fp32_precision
    matmul = torch.backends.cuda.matmul.fp32_precision
    try:
        torch.backends.cudnn.conv.fp32_precision = "ieee"
        torch.backends.cuda.matmul.fp32_precision = "ieee"
        yield
    finally:
        torch.backends.cudnn.conv.fp32_precision = convolution
        torch.backends.cuda.matmul.fp32_precision = matmul
