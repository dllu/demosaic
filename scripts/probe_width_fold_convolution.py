"""CPU algebra/compute audit of width folding; no model-quality or GPU claim."""

import argparse
import copy
import os
import shutil
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from train_directional_bank_trial import ref, save

from demosaic.pretrained_rgb import RgbRestorationTrunk
from demosaic.safety import writable_path

PARENT = Path("/mnt/external/demosaic/models/dino-convnext-wide-long-control-b16-v63-step20000.pt")
PARENT_SHA = "ed70952dd33c5d7da39199bf1306b58b579862920fb0cccd6b222f19871bc9b5"


def fold_width(value):
    n, c, h, w = value.shape
    if w % 2:
        raise ValueError("Width folding requires an even padded width")
    return value.reshape(n, c, h, w // 2, 2).permute(0, 1, 4, 2, 3).reshape(n, 2 * c, h, w // 2)


def unfold_width(value):
    n, twice_c, h, w = value.shape
    if twice_c % 2:
        raise ValueError("Width unfolding requires phase-paired channels")
    return (
        value.reshape(n, twice_c // 2, 2, h, w)
        .permute(0, 1, 3, 4, 2)
        .reshape(n, twice_c // 2, h, 2 * w)
    )


def folded_kernel(weight):
    """Independent phase-index derivation for stride1/padding1 dense3x3."""
    out_channels, in_channels, kh, kw = weight.shape
    if (kh, kw) != (3, 3):
        raise ValueError("This diagnostic supports only dense3x3 kernels")
    result = weight.new_zeros(2 * out_channels, 2 * in_channels, 3, 3)
    for output_phase in (0, 1):
        for dx in (-1, 0, 1):
            block_offset, input_phase = divmod(output_phase + dx, 2)
            result[output_phase::2, input_phase::2, :, block_offset + 1] = weight[:, :, :, dx + 1]
    return result


class FoldedWidthConv(nn.Module):
    def __init__(self, original):
        super().__init__()
        if (
            original.kernel_size != (3, 3)
            or original.stride != (1, 1)
            or original.padding != (1, 1)
            or original.dilation != (1, 1)
            or original.groups != 1
            or original.padding_mode != "zeros"
        ):
            raise ValueError("Unsupported convolution geometry")
        self.register_buffer("weight", folded_kernel(original.weight.detach()))
        self.register_buffer(
            "bias",
            None if original.bias is None else original.bias.detach().repeat_interleave(2),
        )

    def forward(self, value):
        width = value.shape[-1]
        fmt = (
            torch.channels_last
            if value.is_contiguous(memory_format=torch.channels_last)
            else torch.contiguous_format
        )
        padded = F.pad(value, (0, width % 2)) if width % 2 else value
        packed = fold_width(padded).contiguous(memory_format=fmt)
        result = F.conv2d(packed, self.weight, self.bias, padding=1)
        return unfold_width(result)[..., :width].contiguous(memory_format=fmt)


def convert_trunk(model):
    """Local wrappers preserve existing stride2/down/up modules and all offsets."""
    result = copy.deepcopy(model)

    def visit(module):
        for name, child in list(module.named_children()):
            if isinstance(child, nn.Conv2d) and child.kernel_size == (3, 3):
                setattr(module, name, FoldedWidthConv(child))
            else:
                visit(child)

    visit(result)
    return result


def difference(actual, expected):
    delta = actual.double() - expected.double()
    return {
        "max_abs": float(delta.abs().max()),
        "RMS": float(delta.square().mean().sqrt()),
        "expected_max_abs": float(expected.double().abs().max()),
        "finite": bool(torch.isfinite(actual).all() and torch.isfinite(expected).all()),
        "exact": bool(torch.equal(actual, expected)),
    }


def numpy_convolution(value, weight, bias):
    """Tiny independent scalar cross-correlation, including every padded boundary."""
    n, _, height, width = value.shape
    padded = np.pad(value, ((0, 0), (0, 0), (1, 1), (1, 1)))
    output = np.empty((n, len(weight), height, width), dtype=np.float64)
    for batch in range(n):
        for channel in range(len(weight)):
            for y in range(height):
                for x in range(width):
                    patch = padded[batch, :, y : y + 3, x : x + 3]
                    output[batch, channel, y, x] = np.sum(patch * weight[channel]) + bias[channel]
    return output


def census(model):
    rows, hooks = [], []

    def capture(name, module, inputs, output):
        x = inputs[0]
        if isinstance(module, nn.ConvTranspose2d):
            mac = x.numel() * module.out_channels // module.groups
        else:
            mac = output.numel() * module.in_channels // module.groups
        mac *= module.kernel_size[0] * module.kernel_size[1]
        eligible = isinstance(module, nn.Conv2d) and module.kernel_size == (3, 3)
        rows.append(
            {
                "name": name,
                "kind": type(module).__name__,
                "weight_shape": list(module.weight.shape),
                "input_shape": list(x.shape),
                "output_shape": list(output.shape),
                "MAC_native32_B1": mac,
                "MAC_native512_B4": mac * 1024,
                "eligible_width_fold": eligible,
                "weight_elements": module.weight.numel(),
            }
        )

    for name, module in model.named_modules():
        if isinstance(module, (nn.Conv2d, nn.ConvTranspose2d)):
            hooks.append(
                module.register_forward_hook(
                    lambda module, inputs, output, name=name: capture(name, module, inputs, output)
                )
            )
    try:
        model(torch.zeros(1, 3, 32, 32), torch.ones(1, 1, 32, 32) * 0.1)
    finally:
        for hook in hooks:
            hook.remove()
    assert len(rows) == 64 and sum(r["eligible_width_fold"] for r in rows) == 58
    original = sum(r["MAC_native32_B1"] for r in rows)
    eligible = sum(r["MAC_native32_B1"] for r in rows if r["eligible_width_fold"])
    return {
        "layers": rows,
        "MAC_per_native_pixel": original // (32 * 32),
        "MAC_native512_B4": original * 1024,
        "MAC_100MP_without_overlap_or_padding": original // (32 * 32) * 100_000_000,
        "dense_folded_MAC_native512_B4": (original + eligible) * 1024,
        "eligible_original_weight_elements": sum(
            r["weight_elements"] for r in rows if r["eligible_width_fold"]
        ),
        "folded_kernel_dense_storage_factor": 4,
        "folded_kernel_structural_nonzero_fraction": 0.5,
        "folded_even_width_activation_element_factor": 1,
        "convention": "Dense convolution MACs include padded-zero taps; one MAC is one multiply plus add. Bias, activation, residual, packing, conditioning, DINO, physics, tile overlap and output work excluded. Target census is analytical scaling of the executed native32/B1 geometry, not a target-size forward or timing.",
    }


@torch.inference_mode()
def main(output):
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    root = writable_path(output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    executed = root / "executed-source.py"
    shutil.copyfile(__file__, executed)
    source = ref(__file__)
    trunk_source = ref("src/demosaic/pretrained_rgb.py")
    shutil.copyfile(trunk_source["path"], root / "executed-pretrained-rgb.py")
    assert ref(PARENT)["sha256"] == PARENT_SHA
    initial_rng = torch.get_rng_state().clone()
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(20261020)
        state = torch.load(PARENT, map_location="cpu", weights_only=False)
        assert state["step"] == 20000
        prefix = "pretrained_rgb.network."
        weights = {
            k.removeprefix(prefix): v for k, v in state["ema"].items() if k.startswith(prefix)
        }
        assert len(weights) == 64 and all(torch.isfinite(v).all() for v in weights.values())
        model = RgbRestorationTrunk().eval().requires_grad_(False)
        model.load_state_dict(weights, strict=True)
        del state
        measured_census = census(model)
        generator = torch.Generator().manual_seed(20261020)
        selected = [
            "m_head",
            "m_down1.0.res.0",
            "m_down2.0.res.0",
            "m_down3.0.res.0",
            "m_body.0.res.0",
            "m_tail",
        ]
        cases = []
        for dtype in [torch.float64, torch.float32]:
            for fmt_name, fmt in [
                ("contiguous", torch.contiguous_format),
                ("channels_last", torch.channels_last),
            ]:
                for width in [6, 7]:
                    for name in selected:
                        layer = copy.deepcopy(model.get_submodule(name)).to(dtype=dtype)
                        candidate = FoldedWidthConv(layer)
                        layer.to(memory_format=fmt)
                        candidate.to(memory_format=fmt)
                        value = torch.randn(
                            (1, layer.in_channels, 5, width), generator=generator
                        ).to(dtype)
                        value = value.contiguous(memory_format=fmt)
                        expected, actual = layer(value), candidate(value)
                        error = difference(actual, expected)
                        assert error["finite"]
                        if dtype == torch.float64:
                            assert error["max_abs"] <= 1e-11 * max(1, error["expected_max_abs"])
                        cases.append(
                            {
                                "layer": name,
                                "dtype": str(dtype),
                                "format": fmt_name,
                                "input_shape": list(value.shape),
                                **error,
                            }
                        )
        # Nonzero bias and all image edges are independently checked outside
        # the learned bias-free trunk. There is no clean target or image score.
        layer = nn.Conv2d(3, 5, 3, padding=1, bias=True).double()
        value = torch.randn((1, 3, 5, 7), generator=generator, dtype=torch.float64)
        independent = numpy_convolution(
            value.numpy(), layer.weight.detach().numpy(), layer.bias.detach().numpy()
        )
        numpy_error = difference(FoldedWidthConv(layer)(value), torch.from_numpy(independent))
        assert numpy_error["max_abs"] < 1e-12
        full_cases = []
        examples = {
            "numpy-input": value.numpy(),
            "numpy-kernel": layer.weight.detach().numpy(),
            "numpy-bias": layer.bias.detach().numpy(),
            "numpy-expected": independent,
        }
        # The actual trunk deliberately casts its head/tail inputs to FP32;
        # module.double() cannot make that a supported FP64 execution path.
        # FP64 algebra is checked above at the individual-convolution level.
        for dtype in [torch.float32]:
            original = copy.deepcopy(model).to(dtype=dtype)
            candidate = convert_trunk(original)
            assert sum(isinstance(m, FoldedWidthConv) for m in candidate.modules()) == 58
            rgb = torch.randn((1, 3, 32, 32), generator=generator).to(dtype) * 0.2
            noise = torch.ones((1, 1, 32, 32), dtype=dtype) * 0.1
            for fmt_name, fmt in [
                ("contiguous", torch.contiguous_format),
                ("channels_last", torch.channels_last),
            ]:
                original.to(memory_format=fmt)
                candidate.to(memory_format=fmt)
                a = original(rgb.contiguous(memory_format=fmt), noise.contiguous(memory_format=fmt))
                b = candidate(
                    rgb.contiguous(memory_format=fmt), noise.contiguous(memory_format=fmt)
                )
                error = difference(b, a)
                assert error["finite"]
                full_cases.append(
                    {
                        "dtype": str(dtype),
                        "format": fmt_name,
                        "input_shape": list(rgb.shape),
                        **error,
                    }
                )
                if fmt_name == "contiguous":
                    examples[str(dtype) + "-input"] = rgb.numpy()
                    examples[str(dtype) + "-noise"] = noise.numpy()
                    examples[str(dtype) + "-original"] = a.numpy()
                    examples[str(dtype) + "-folded"] = b.numpy()
    assert torch.equal(initial_rng, torch.get_rng_state()) and not torch.cuda.is_initialized()
    assert ref(__file__) == source and ref(PARENT)["sha256"] == PARENT_SHA
    assert ref(trunk_source["path"]) == trunk_source
    arrays = root / "generated-trunk-arrays.npz"
    np.savez(arrays, **examples)
    result = {
        "status": "completed-CPU-width-fold-algebra-and-compute-audit",
        "driver": source,
        "executed_source": ref(executed),
        "parent_checkpoint": ref(PARENT),
        "trunk_source": trunk_source,
        "executed_trunk_source": ref(root / "executed-pretrained-rgb.py"),
        "parent_EMA_trunk_tensors_strictly_loaded": 64,
        "torch": str(torch.__version__),
        "numpy": str(np.__version__),
        "seed": 20261020,
        "CPU_threads": torch.get_num_threads(),
        "selected_kernel_cases": cases,
        "independent_numpy_nonzero_bias_and_boundary_case": numpy_error,
        "whole_trunk_cases": full_cases,
        "compute_census": measured_census,
        "arrays": ref(arrays),
        "CPU_RNG_unchanged": True,
        "CUDA_initialized": False,
        "model_quality_statistics_read": False,
        "production_or_training_modified": False,
        "scope": "Generated CPU inputs and genuine V63 EMA trunk only, without DINO/measurement offsets, physical inverse or photo inference. FP64 checks the algebra; FP32 is approximate, not bitwise/full-model/RGB16 parity. This dense width-fold implementation doubles eligible convolution MACs and quadruples their dense kernel storage. No CUDA timing, memory-peak, quality or speedup claim; no training/inference/default change or queued GPU execution.",
    }
    save(root / "receipt.json", result)
    print(
        {
            "receipt": ref(root / "receipt.json"),
            "kernel_cases": len(cases),
            "trunk_cases": full_cases,
            "MAC_per_native_pixel": measured_census["MAC_per_native_pixel"],
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args().output)
