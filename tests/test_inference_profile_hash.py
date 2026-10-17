import hashlib
import importlib.util
import struct
from pathlib import Path

import pytest
import torch


@pytest.fixture(scope="module")
def model_hash():
    path = Path(__file__).parents[1] / "scripts/profile_raw_kernel_inference.py"
    spec = importlib.util.spec_from_file_location("profile_hash_regression", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.model_hash


def expected(name, value, data):
    header = name + str(value.dtype) + str(tuple(value.shape))
    return hashlib.sha256(header.encode() + data).hexdigest()


def test_channels_last_pointwise_weights_hash_like_identical_nchw_values(model_hash):
    model = torch.nn.Module()
    value = torch.arange(64 * 21, dtype=torch.float32).reshape(64, 21, 1, 1)
    model.register_parameter("weight", torch.nn.Parameter(value.clone()))
    oracle = expected("weight", value, value.numpy().tobytes())
    assert model_hash(model) == oracle
    model.to(memory_format=torch.channels_last)
    assert model.weight.is_contiguous() and model.weight.stride(-1) == 21
    assert model_hash(model) == oracle
    assert torch.equal(model.weight, value)


@pytest.mark.parametrize(
    "dtype,values,encoded",
    [
        (torch.float32, [-0.0, 1.5, -2.25], struct.pack("=3I", 0x80000000, 0x3FC00000, 0xC0100000)),
        (torch.bfloat16, [-0.0, 1.5, -2.25], struct.pack("=3H", 0x8000, 0x3FC0, 0xC010)),
        (torch.int64, [-7, 0, 5], struct.pack("=3q", -7, 0, 5)),
    ],
)
def test_hash_preserves_exact_dtype_bits_including_negative_zero(
    model_hash, dtype, values, encoded
):
    model = torch.nn.Module()
    value = torch.tensor(values, dtype=dtype)
    model.register_buffer("value", value)
    assert model_hash(model) == expected("value", value, encoded)


@pytest.mark.parametrize("scalar", [False, True])
@pytest.mark.parametrize(
    "dtype,encoded",
    [
        (torch.float32, struct.pack("=I", 0x3F800000)),
        (torch.bfloat16, struct.pack("=H", 0x3F80)),
        (torch.int64, struct.pack("=q", 1)),
    ],
)
def test_scalar_and_nonunit_stride_singleton_hash_canonical_bytes(
    model_hash, scalar, dtype, encoded
):
    value = (
        torch.tensor(1, dtype=dtype)
        if scalar
        else torch.empty_strided((1,), (21,), dtype=dtype).fill_(1)
    )
    model = torch.nn.Module()
    model.register_buffer("value", value)
    assert model_hash(model) == expected("value", value, encoded)


def test_noncontiguous_buffer_hash_uses_logical_order_without_mutation(model_hash):
    value = torch.arange(12, dtype=torch.float32).reshape(3, 4).T
    model = torch.nn.Module()
    model.register_buffer("value", value)
    strides, pointer = value.stride(), value.data_ptr()
    assert model_hash(model) == expected("value", value, value.numpy().tobytes(order="C"))
    assert model.value.stride() == strides and model.value.data_ptr() == pointer
