import os
import subprocess
import sys
from pathlib import Path

import pytest
import torch

from scripts.experimental_tf32x3_conv import convolution


def test_cpu_is_rejected_without_explicit_interpreter_and_gradients_are_rejected():
    x, w = torch.ones(1, 3, 5, 5), torch.ones(4, 3, 3, 3)
    with pytest.raises(ValueError, match="inference-only"):
        convolution(x, w)
    with torch.inference_mode(), pytest.raises(ValueError, match="CUDA operands"):
        convolution(x, w)
    assert not torch.cuda.is_initialized()


def test_actual_triton_CPU_interpreter_indexes_batches_padding_edges_tails_and_stride():
    # Import/decorate inside a fresh interpreter process; no device or global
    # execution-policy changes leak into the test runner or training process.
    source = """
import torch
from scripts.experimental_tf32x3_conv import convolution
torch.set_num_threads(2)
generator=torch.Generator().manual_seed(73)
with torch.inference_mode():
    for shape, channels, kernel, stride, padding in [
        ((1,3,7,11),5,3,1,1), ((2,4,9,5),7,2,2,0),
        ((1,8,4,6),3,3,1,1), ((2,3,2,2),2,2,2,0),
        ((1,64,3,5),65,3,1,1),
    ]:
        x=torch.randn(shape,generator=generator).contiguous(memory_format=torch.channels_last)
        w=torch.randn((channels,shape[1],kernel,kernel),generator=generator).contiguous(memory_format=torch.channels_last)
        actual=convolution(x,w,stride=stride,padding=padding,interpreter=True)
        expected=torch.nn.functional.conv2d(x.double(),w.double(),stride=stride,padding=padding).float()
        assert actual.is_contiguous(memory_format=torch.channels_last)
        torch.testing.assert_close(actual,expected,atol=2e-5,rtol=2e-5)
    assert not torch.cuda.is_initialized()
print('five actual interpreter indexing cases passed; not TF32/GPU arithmetic parity')
"""
    env = dict(os.environ, TRITON_INTERPRET="1", CUDA_VISIBLE_DEVICES="", OMP_NUM_THREADS="2", OPENBLAS_NUM_THREADS="2")
    result = subprocess.run([sys.executable, "-c", source], check=False, cwd=Path(__file__).parents[1], env=env, text=True, capture_output=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'five actual interpreter indexing cases passed' in result.stdout
