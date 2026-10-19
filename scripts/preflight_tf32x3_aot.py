"""Compile all seven mature hidden-convolution shapes for SM121 without CUDA.

This verifies compiler acceptance and instruction selection. It never loads a
kernel onto a device and does not establish correctness or speed on hardware.
"""

import argparse
import json
import os
from pathlib import Path

import torch
import triton
from experimental_tf32x3_conv import _implicit_conv
from probe_tf32x3_cpu import ref
from triton.backends.compiler import GPUTarget
from triton.compiler import ASTSource

from demosaic.safety import writable_path


def main(output):
    os.nice(10)
    assert not torch.cuda.is_initialized()
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "", "Hide CUDA"
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    operator = Path(__file__).with_name("experimental_tf32x3_conv.py")
    records = []
    target = GPUTarget("cuda", 121, 32)
    # B4/native512: four3x3 feature scales and three stride2 transitions.
    for ic, oc, size, kernel, stride, padding in [
        (64, 64, 512, 3, 1, 1), (128, 128, 256, 3, 1, 1),
        (256, 256, 128, 3, 1, 1), (512, 512, 64, 3, 1, 1),
        (64, 128, 512, 2, 2, 0), (128, 256, 256, 2, 2, 0),
        (256, 512, 128, 2, 2, 0),
    ]:
        out_size = (size + 2 * padding - kernel) // stride + 1
        constants = {
            "N": 4, "IC": ic, "IH": size, "IW": size,
            "OC": oc, "OH": out_size, "OW": out_size,
            "KH": kernel, "KW": kernel, "STRIDE": stride, "PAD": padding,
            "XN": ic * size * size, "XC": 1, "XH": ic * size, "XW": ic,
            "WN": ic * kernel * kernel, "WC": 1, "WH": ic * kernel, "WW": ic,
            "BM": 64, "BN": 64, "BK": 32,
        }
        compiled = triton.compile(
            ASTSource(_implicit_conv, {"X": "*fp32", "W": "*fp32", "Y": "*fp32"}, constexprs=constants),
            target=target,
            options={"num_warps": 4, "num_stages": 3, "enable_fp_fusion": False},
        )
        name = f"IC{ic}-OC{oc}-H{size}-K{kernel}"
        ptx = compiled.asm["ptx"]
        assert "mma.sync" in ptx and ".tf32.tf32.f32" in ptx
        assert "cvt.rna.tf32.f32" in ptx
        (output / f"{name}.ptx").write_text(ptx)
        (output / f"{name}.cubin").write_bytes(compiled.asm["cubin"])
        record = {
            "shape": name, "constants": constants,
            "PTX": ref(output / f"{name}.ptx"), "cubin": ref(output / f"{name}.cubin"),
            "TF32_MMA_instructions_in_static_PTX": ptx.count(".tf32.tf32.f32"),
            "RNA_TF32_conversions_in_static_PTX": ptx.count("cvt.rna.tf32.f32"),
            "shared_memory_bytes": compiled.metadata.shared,
            "kernel_loaded": compiled.module is not None,
        }
        assert not record["kernel_loaded"] and not torch.cuda.is_initialized()
        records.append(record)
        with (output / "cases.jsonl").open("a") as stream:
            stream.write(json.dumps(record) + "\n")
        print(json.dumps({key: record[key] for key in ("shape", "shared_memory_bytes")}), flush=True)
    assert not torch.cuda.is_initialized()
    receipt = {
        "status": "passed-all7-SM121-hidden-convolution-AOT-compiles-no-CUDA-execution",
        "driver": ref(__file__), "operator": ref(operator), "cases": records,
        "torch_version": str(torch.__version__), "triton_version": triton.__version__,
        "target": {"backend": "cuda", "arch": 121, "warp_size": 32},
        "CUDA_initialized": False,
        "scope": "Ahead-of-time compiler acceptance and TF32 tensor instruction selection only. Shapes cover the seven unique dense hidden convolution geometries of the mature B4/native512 trunk. No GPU load, kernel execution, Tensor Core arithmetic parity, measured speedup, model accuracy or production integration. No backward implementation or training support.",
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"receipt": ref(output / "receipt.json")}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args().output)
