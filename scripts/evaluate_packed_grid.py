"""Compare legacy/corrected tiling on fixed photo observations, without training."""

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import torch
from benchmark_packed_compilation import batch, difference, digest, read, ref, sha
from torch.nn import functional as F

from demosaic.cfa import malvar, unpack
from demosaic.inference import load_checkpoint, restore_tiled
from demosaic.metrics import quality_metrics
from demosaic.precision import amp_context
from demosaic.reporting import display_crop, save_triplet
from demosaic.safety import writable_path


def export_difference(actual, reference, *, rows=128):
    """All HWC RGB16 values; signed subtraction must not wrap at uint16 limits."""
    if (
        actual.shape != reference.shape
        or actual.ndim != 3
        or actual.shape[-1] != 3
        or min(actual.shape[:2]) < 1
        or actual.dtype != np.uint16
        or reference.dtype != np.uint16
        or rows < 1
    ):
        raise ValueError("Expected matching nonempty HWC uint16 RGB and positive chunk height")
    maximum, squared, changed_values, changed_pixels, count = 0, 0.0, 0, 0, 0
    signed_sum = np.zeros(3, dtype=np.float64)
    for start in range(0, actual.shape[0], rows):
        delta = actual[start : start + rows].astype(np.int32) - reference[
            start : start + rows
        ].astype(np.int32)
        maximum = max(maximum, int(np.abs(delta).max()))
        squared += float(np.square(delta.astype(np.float64)).sum(dtype=np.float64))
        signed_sum += delta.sum(axis=(0, 1), dtype=np.float64)
        changed_values += int(np.count_nonzero(delta))
        changed_pixels += int(np.count_nonzero(np.any(delta != 0, axis=-1)))
        count += delta.size
    pixels = count // 3
    return {
        "RGB_values": count,
        "pixels": pixels,
        "changed_values": changed_values,
        "changed_pixels": changed_pixels,
        "max_abs_DN16": maximum,
        "RMS_DN16": (squared / count) ** 0.5,
        "mean_signed_DN16_RGB": (signed_sum / pixels).tolist(),
        "scope": "Differences of clipped/rounded RGB16 exports, not unquantized RGB or GT errors",
    }


def legacy_operator(receipt):
    assert ref(receipt["path"]) == receipt
    spec = importlib.util.spec_from_file_location("demosaic._legacy_grid_operator", receipt["path"])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.restore_tiled


def scores(prediction, values):
    result = quality_metrics(
        prediction[None, :, 8:-8, 8:-8],
        values["target"].cpu()[:, :, 8:-8, 8:-8],
        values["wb"].cpu(),
        values["matrix"].cpu(),
    )
    result = {
        name: float(value[0]) if torch.isfinite(value[0]) else None
        for name, value in result.items()
    }
    assert all(result[name] is not None for name in ["linear_psnr", "srgb_psnr", "srgb_ssim"])
    return result


@torch.inference_mode()
def photos(checkpoint, inputs, output, device):
    output = writable_path(output)
    assert not output.exists()
    device = torch.device(device)
    if device.type == "cpu":
        assert not torch.cuda.is_available() and not torch.cuda.is_initialized(), "Hide CUDA"
    torch.set_num_threads(2 if device.type == "cpu" else 4)
    fixture = read(inputs)
    for path, expected in fixture["files"].items():
        assert sha(path) == expected, path
    old_restore = legacy_operator(fixture["legacy_inference"])
    model, state = load_checkpoint(checkpoint, device)
    model.eval()
    assert model.config.restoration_backbone == "packed-isotropic"
    if device.type == "cuda":
        model.to(memory_format=torch.channels_last)
    precision = "float16" if device.type == "cuda" else "float32"
    grid = 32 if model.config.dino else 4
    checkpoint = {
        "path": str(Path(checkpoint).resolve()),
        "sha256": state["loaded_sha256"],
        "step": state["step"],
        "weights": "EMA",
        "model_config": model.config.to_dict(),
    }
    del state
    before = digest(model.state_dict().items())
    identities = {name: id(value) for name, value in model.named_parameters()}
    keys = tuple(model.state_dict())
    import demosaic

    sources = {str(p): sha(p) for p in Path(demosaic.__file__).parent.glob("*.py")}
    output.mkdir(parents=True)
    cases, crops = [], []
    assert len(fixture["photos"]) == 2
    for index, entry in enumerate(fixture["photos"]):
        values = batch(entry["observation"]["path"], device)
        assert tuple(values["packed"].shape) == (1, 4, 255, 255)
        assert tuple(values["target"].shape) == (1, 3, 510, 510)
        condition = entry["metadata"]["conditioning"]
        model.set_noise(condition["shot"], condition["read"])
        # Independent whole-frame comparator: extend complete packed cells,
        # rather than calling the corrected tiler's native-coordinate padding.
        cells = grid // 2
        packed = F.pad(values["packed"], (0, -255 % cells, 0, -255 % cells), mode="replicate")
        variance = packed.clamp_min(0) * condition["shot"] + condition["read"]
        with amp_context(device, dtype=precision):
            whole = model(packed, variance, values["colors"], values["wb"], values["matrix"])
        assert whole.dtype == torch.float32
        predictions = {"Whole": whole[0, :, :510, :510].cpu()}
        raw = unpack(values["packed"].cpu())[0, 0]
        options = {
            "shot": condition["shot"],
            "read": condition["read"],
            "tile": 256,
            "overlap": 64,
            "batch_size": 1,
            "device": str(device),
            "wb": values["wb"][0].cpu(),
            "matrix": values["matrix"][0].cpu(),
            "precision": precision,
        }
        timings = {}
        for policy, restore in [("Legacy", old_restore), ("Corrected", restore_tiled)]:
            predictions[policy], timings[policy] = restore(
                model, raw, values["colors"][0], **options
            )
        assert timings["Corrected"]["tile_grid_alignment"] == grid
        assert timings["Corrected"]["tile_stride"] % grid == 0
        assert "tile_grid_alignment" not in timings["Legacy"]
        wb, matrix = values["wb"].cpu(), values["matrix"].cpu()
        roi = entry["metadata"]["evaluation_tile_xywh"]
        noisy = display_crop(
            malvar(values["packed"].cpu(), values["colors"].cpu(), wb), wb, matrix, roi, exposure=1
        )
        truth = display_crop(values["target"].cpu(), wb, matrix, roi, exposure=1)
        metrics, errors, arrays = {}, {}, {}
        for policy, prediction in predictions.items():
            assert prediction.dtype == torch.float32 and prediction.shape == (3, 510, 510)
            path = output / f"photo{index}-{policy}-RGB-f32.npy"
            np.save(path, prediction.numpy(), allow_pickle=False)
            arrays[policy] = ref(path)
            metrics[policy] = scores(prediction, values)
            if policy != "Whole":
                errors[policy] = difference(
                    prediction[:, 128:-128, 128:-128].numpy(),
                    predictions["Whole"][:, 128:-128, 128:-128].numpy(),
                )
            crops.append(
                save_triplet(
                    output,
                    str(index) + ":" + policy,
                    [
                        ("Noisy (Malvar)", noisy),
                        (policy, display_crop(prediction[None], wb, matrix, roi, exposure=1)),
                        ("GT (synthetic)", truth),
                    ],
                    caption=entry["metadata"]["source"]["id"] + " / " + policy,
                    metadata={
                        **entry["metadata"],
                        "checkpoint": checkpoint,
                        "precision": precision,
                        "device": str(device),
                        "policy": policy,
                        "observation": entry["observation"],
                    },
                )
            )
        cases.append(
            {
                "source_id": entry["metadata"]["source"]["id"],
                "observation": entry["observation"],
                "arrays": arrays,
                "exact_synthetic_GT_metrics_border8": metrics,
                "interior_exclude128_errors_against_whole": errors,
                "timings_engineering_only": timings,
            }
        )
    assert before == digest(model.state_dict().items())
    assert identities == {name: id(value) for name, value in model.named_parameters()}
    assert keys == tuple(model.state_dict())
    assert sha(checkpoint["path"]) == checkpoint["sha256"]
    for path, expected in {**fixture["files"], **sources}.items():
        assert sha(path) == expected, path
    result = {
        "status": "completed-fixed-photo-grid-comparison-awaiting-native-visual-review",
        "checkpoint": checkpoint,
        "fixture": ref(inputs),
        "legacy_inference": fixture["legacy_inference"],
        "source_files": sources,
        "driver": ref(__file__),
        "cases": cases,
        "native_crops": crops,
        "grid": grid,
        "precision": precision,
        "device": str(device),
        "GPU_name": torch.cuda.get_device_name(device) if device.type == "cuda" else None,
        "torch": str(torch.__version__),
        "CUDA_initialized": torch.cuda.is_initialized(),
        "all_tensor_bytes_parameter_identities_and_keys_unchanged": True,
        "full_model_state_sha256": before,
        "scope": "Two selected fixed CPU native510 observations, distinct from the official427 "
        "GPU panel. No training, correction of output values, compilation, model selection "
        "or promotion. Whole-network output is a numerical comparator, not GT. GT metrics "
        "are separate. Timings are engineering telemetry, not latency evidence. Native "
        "inspection and full-frame validation remain necessary.",
    }
    (output / "receipt.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    args = parser.parse_args()
    photos(args.checkpoint, args.inputs, args.output, args.device)
