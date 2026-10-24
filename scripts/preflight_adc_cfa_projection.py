"""Verify an actual ADC-policy export before its all-condition evaluation."""

import argparse
import hashlib
import json
from pathlib import Path

import torch

from demosaic.cfa import PATTERNS, adc_cfa_projection, color_indices, mosaic, unpack
from demosaic.inference import load_checkpoint, restore_tiled
from demosaic.precision import amp_context
from demosaic.safety import writable_path


def sha(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


@torch.inference_mode()
def main(export, output, device):
    torch.set_num_threads(2)
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    receipt = json.loads((Path(export).parent / "receipt.json").read_text())
    parent_path = Path(receipt["parent_checkpoint"])
    assert sha(parent_path) == receipt["parent_sha256"]
    assert sha(export) == receipt["export_sha256"]
    device = torch.device(device)
    parent, _ = load_checkpoint(parent_path, device)
    candidate, _ = load_checkpoint(export, device)
    parent.eval()
    candidate.eval()
    projection_mode = candidate.config.adc_cfa_projection_mode
    expected_config = {
        **parent.config.to_dict(),
        "adc_cfa_projection": True,
        "adc_cfa_projection_mode": projection_mode,
    }
    assert candidate.config.to_dict() == expected_config
    a, b = parent.restoration_state_dict(), candidate.restoration_state_dict()
    assert a.keys() == b.keys() and all(torch.equal(a[k], b[k]) for k in a)
    if candidate.context is not None:
        assert candidate.config.dino_revision == parent.config.dino_revision
        assert candidate.config.dino_revision != "main"
        assert all(not p.requires_grad for p in candidate.context.backbone.parameters())
        assert all(
            torch.equal(v, parent.context.backbone.state_dict()[k])
            for k, v in candidate.context.backbone.state_dict().items()
        )
    if device.type == "cuda":
        parent.to(memory_format=torch.channels_last)
        candidate.to(memory_format=torch.channels_last)
        torch.set_float32_matmul_precision("high")
        torch.backends.cudnn.benchmark = True
    # amp_context deliberately leaves CPU inference in FP32; record the
    # precision actually exercised rather than duplicate it under a BF16 label.
    precisions = ["float32", "bfloat16", "float16"] if device.type == "cuda" else ["float32"]
    records = []
    max_error = 0.0
    for h, w in [(32, 40), (48, 64)]:
        raw = (
            torch.rand(4, 4, h // 2, w // 2, generator=torch.Generator().manual_seed(63)) * 0.8
            + 0.1
        )
        raw[:, :, 0, :2] = torch.tensor([0.0, 1.0])
        raw = raw.to(device)
        if device.type == "cuda":
            raw = raw.contiguous(memory_format=torch.channels_last)
        colors = torch.stack([color_indices(p, device=device) for p in PATTERNS])
        wb = raw.new_tensor([[2, 1, 1.5], [1.3, 1, 2.1], [1.7, 1, 1.1], [2.2, 1, 1.4]])
        matrix = torch.eye(3, device=device)[None].expand(4, -1, -1)
        for precision in precisions:
            for shot, read, selected in [
                (0, 0, [0, 1, 2, 3]),
                (0.001, 0, []),
                (0, 0.00001, []),
                ([0, 0.001, 0, 0], [0, 0, 0, 0.00001], [0, 2]),
            ]:
                parent.set_noise(shot, read)
                candidate.set_noise(shot, read)
                variance = torch.zeros_like(raw)
                with amp_context(device, dtype=precision):
                    original = parent(raw, variance, colors, wb, matrix)
                    actual = candidate(raw, variance, colors, wb, matrix)
                assert actual.dtype == torch.float32 and torch.isfinite(actual).all()
                noisy = [i for i in range(4) if i not in selected]
                if noisy:
                    torch.testing.assert_close(actual[noisy], original[noisy], rtol=0, atol=0)
                if selected:
                    expected = adc_cfa_projection(
                        original[selected],
                        raw[selected],
                        colors[selected],
                        wb[selected],
                        mode=projection_mode,
                    )
                    torch.testing.assert_close(actual[selected], expected, rtol=0, atol=0)
                    valid = (raw[selected] > 1 / 65535) & (raw[selected] < 1 - 1 / 65535)
                    error = (mosaic(actual[selected], colors[selected]) - raw[selected]).abs()
                    max_error = max(max_error, float(error[valid].max()))
                    torch.testing.assert_close(
                        mosaic(actual[selected], colors[selected])[~valid],
                        mosaic(original[selected], colors[selected])[~valid],
                        rtol=0,
                        atol=0,
                    )
                records.append(
                    {
                        "native_shape": [h, w],
                        "precision": precision,
                        "shot": shot,
                        "read": read,
                        "adc_images": selected,
                        "positive_prior_images_exact": True,
                    }
                )
    assert max_error < 2e-7
    # A full native16-bit ramp also checks tiled blending and an incomplete
    # final tile batch; no reference image is needed for measured-site fidelity.
    raw = 0.2 + torch.arange(64 * 80).reshape(64, 80) / 65535
    colors = color_indices("RGGB")
    prediction, timing = restore_tiled(
        candidate,
        raw,
        colors,
        shot=0,
        read=0,
        tile=32,
        overlap=8,
        batch_size=4,
        device=device,
        precision="float16" if device.type == "cuda" else "float32",
    )
    error = (unpack(mosaic(prediction[None], colors))[0, 0] - raw).abs().max().item()
    assert error < 2e-7
    assert (mosaic(prediction[None], colors) * 65535).round().unique().numel() > 256
    result = {
        "device": str(device),
        "export": str(export),
        "export_sha256": sha(export),
        "parent_sha256": receipt["parent_sha256"],
        "projection_mode": projection_mode,
        "records": records,
        "max_valid_cfa_error": max_error,
        "tiled_max_cfa_error": error,
        "tiled_observation": timing,
        "identical_restoration_tensors": True,
        "genuine_pinned_foundation": candidate.config.dino_revision if candidate.context else None,
        "cuda_initialized": torch.cuda.is_initialized(),
        "source_files": {p.name: sha(p) for p in Path("src/demosaic").glob("*.py")},
        "driver_sha256": sha(__file__),
        "scope": "Functional parity/data-fidelity preflight, not reconstruction-quality or throughput evidence",
    }
    (output / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: result[k]
                for k in [
                    "device",
                    "max_valid_cfa_error",
                    "tiled_max_cfa_error",
                    "cuda_initialized",
                ]
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    args = parser.parse_args()
    main(args.export, args.output, args.device)
