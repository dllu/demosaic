"""Compare in-place compilation without changing weights or inference defaults.

CPU photos mode tests Dynamo's eager backend only. CUDA photos/serving modes
test real Inductor execution. Full restores include validation, allocations,
transfers and blending; decode, compilation, warmup and export are separate.
"""

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import psutil
import torch

from demosaic.cfa import color_indices, malvar
from demosaic.inference import compile_restoration_blocks, load_checkpoint, restore_tiled
from demosaic.io import RawMetadata, write_rgb16
from demosaic.precision import amp_context
from demosaic.reporting import display_crop, save_triplet
from demosaic.safety import writable_path

MAX_DN16 = 1.0
RMS_DN16 = 0.25


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def ref(path):
    return {"path": str(Path(path).resolve()), "sha256": sha(path)}


def digest(items):
    value = hashlib.sha256()
    for name, tensor in items:
        value.update(name.encode())
        value.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return value.hexdigest()


def difference(actual, reference, *, rows=128):
    """All RGB pixels, without allocating a full-frame float64 difference."""
    if (
        actual.shape != reference.shape
        or actual.ndim != 3
        or actual.shape[0] != 3
        or min(actual.shape[1:]) < 1
    ):
        raise ValueError("Expected matching camera RGB arrays with shape3×H×W")
    if rows < 1:
        raise ValueError("Chunk height must be positive")
    maximum, squared, count = 0.0, 0.0, 0
    for start in range(0, actual.shape[1], rows):
        first = np.asarray(actual[:, start : start + rows], dtype=np.float64)
        second = np.asarray(reference[:, start : start + rows], dtype=np.float64)
        if not np.isfinite(first).all() or not np.isfinite(second).all():
            raise ValueError("Nonfinite RGB value, including outside report crops")
        delta = first - second
        maximum = max(maximum, float(np.abs(delta).max()))
        squared += float(np.square(delta).sum(dtype=np.float64))
        count += delta.size
    rms = (squared / count) ** 0.5
    return {
        "elements": count,
        "max_abs": maximum,
        "RMS": rms,
        "max_abs_DN16": maximum * 65535,
        "RMS_DN16": rms * 65535,
        "passes_predeclared_bound": maximum * 65535 <= MAX_DN16 and rms * 65535 <= RMS_DN16,
    }


def batch(path, device):
    with np.load(path, allow_pickle=False) as arrays:
        values = {key: torch.from_numpy(arrays[key].copy()).to(device) for key in arrays.files}
    if device.type == "cuda":
        for key, value in values.items():
            if value.ndim == 4:
                values[key] = value.contiguous(memory_format=torch.channels_last)
    return values


def predict(model, values, precision):
    with amp_context(values["packed"].device, dtype=precision):
        result = model(*(values[key] for key in ["packed", "variance", "colors", "wb", "matrix"]))
    assert result.dtype == torch.float32, "Physical RGB output must remain FP32"
    return result.detach().cpu().numpy()


def photo_crops(output, entry, values, predictions, metadata):
    common = entry["metadata"]
    roi = common["evaluation_tile_xywh"]
    wb, matrix = values["wb"].cpu(), values["matrix"].cpu()
    noisy = malvar(values["packed"].cpu(), values["colors"].cpu(), wb)
    truth = values["target"].cpu()
    crops = []
    for policy, prediction in predictions.items():
        displayed = [
            (label, display_crop(rgb, wb, matrix, roi, exposure=common["display_exposure"]))
            for label, rgb in [
                ("Noisy (Malvar)", noisy),
                (policy, torch.from_numpy(prediction)),
                ("GT (synthetic)", truth),
            ]
        ]
        crops.append(
            save_triplet(
                output,
                common["source_id"] + ":" + policy,
                displayed,
                caption=common["source_id"] + " / " + policy,
                metadata={
                    **common,
                    **metadata,
                    "policy": policy,
                    "observation": entry["observation"],
                },
            )
        )
    return crops


def photos(model, fixture, output, device, backend, checkpoint):
    precision = "float16" if device.type == "cuda" else "float32"
    cases = []
    for entry in fixture["photos"]:
        values = batch(entry["observation"]["path"], device)
        reference = predict(model, values, precision)
        fp32 = predict(model, values, "float32")
        cases.append((entry, values, reference, fp32))
    started = time.perf_counter()
    compile_restoration_blocks(model, backend=backend)
    prepare_seconds = time.perf_counter() - started
    comparisons, crops, forward_seconds = [], [], []
    for index, (entry, values, expected, fp32) in enumerate(cases):
        call_started = time.perf_counter()
        prediction = predict(model, values, precision)
        forward_seconds.append(time.perf_counter() - call_started)
        error = difference(prediction[0], expected[0])
        if device.type == "cpu":
            assert error["max_abs"] == 0, "CPU eager backend must remain bitwise equal"
        for policy, value in [("eager", expected), ("compiled", prediction)]:
            np.save(output / f"photo{index}-{policy}-RGB-f32.npy", value, allow_pickle=False)
        comparisons.append(
            {
                "source_id": entry["metadata"]["source_id"],
                "observation": entry["observation"],
                "compiled_vs_eager": error,
                "eager_vs_IEEE_FP32": difference(expected[0], fp32[0]),
            }
        )
        crops.extend(
            photo_crops(
                output,
                entry,
                values,
                {"Eager": expected, "Compiled": prediction},
                {"checkpoint": checkpoint, "precision": precision, "backend": backend},
            )
        )
    return {
        "status": "completed-photo-compilation-comparison",
        "passes_predeclared_bound": all(
            entry["compiled_vs_eager"]["passes_predeclared_bound"] for entry in comparisons
        ),
        "comparisons": comparisons,
        "native_crops": crops,
        "compile_prepare_seconds": prepare_seconds,
        "compiled_forward_wall_seconds": forward_seconds,
        "compile_and_first_calls_seconds": time.perf_counter() - started,
        "timing_scope": "Includes lazy graph capture/code generation, calls, saves and previews; not a latency benchmark",
    }


def serving_probes(model, fixture, output, backend):
    cases = []
    for entry in fixture["serving_probes"]:
        values = batch(entry["observation"]["path"], torch.device("cuda"))
        assert tuple(values["packed"].shape) == (4, 4, 256, 256)
        cases.append((entry, values, predict(model, values, "float16")))
    torch.cuda.synchronize()
    started = time.perf_counter()
    compile_restoration_blocks(model, backend=backend)
    prepare_seconds = time.perf_counter() - started
    comparisons, forward_seconds = [], []
    for index, (entry, values, expected) in enumerate(cases):
        call_started = time.perf_counter()
        actual = predict(model, values, "float16")
        forward_seconds.append(time.perf_counter() - call_started)
        comparisons.append(
            {
                "name": entry["name"],
                "observation": entry["observation"],
                "batch_pixel_errors": [
                    difference(a, b) for a, b in zip(actual, expected, strict=True)
                ],
            }
        )
        np.save(output / f"serving{index}-eager-RGB-f32.npy", expected, allow_pickle=False)
        np.save(output / f"serving{index}-compiled-RGB-f32.npy", actual, allow_pickle=False)
    torch.cuda.synchronize()
    return {
        "passes_predeclared_bound": all(
            error["passes_predeclared_bound"]
            for entry in comparisons
            for error in entry["batch_pixel_errors"]
        ),
        "comparisons": comparisons,
        "compile_prepare_seconds": prepare_seconds,
        "compiled_forward_wall_seconds": forward_seconds,
        "compile_and_probe_wall_seconds": time.perf_counter() - started,
    }


def full(model, fixture, output, compiled, backend, repeats):
    probes = serving_probes(model, fixture, output, backend) if compiled else None
    if probes is not None and not probes["passes_predeclared_bound"]:
        return {
            "status": "completed-serving-compilation-accuracy-rejected",
            "serving_probes": probes,
            "full_frame_samples": [],
        }
    raw = np.load(fixture["full_raw"]["path"], mmap_mode="r", allow_pickle=False)
    assert raw.shape == (8746, 11662) and raw.dtype == np.float32
    meta = RawMetadata(**fixture["gfx_metadata"])
    conditioning = fixture["conditioning"]
    options = {
        "shot": conditioning["shot"],
        "read": conditioning["read"],
        "tile": 512,
        "overlap": 64,
        "batch_size": 4,
        "device": "cuda",
        "precision": "float16",
        "wb": meta.white_balance,
        "matrix": meta.camera_to_srgb,
    }
    warm, warm_timing = restore_tiled(model, raw, color_indices(meta.pattern), **options)
    assert torch.isfinite(warm).all()
    del warm
    timings, repeat_errors = [], []
    saved = output / "full-camera-RGB-f32.npy"
    for index in range(repeats):
        host = {
            "available_GiB": psutil.virtual_memory().available / 2**30,
            "load_average": list(psutil.getloadavg()),
        }
        prediction, timing = restore_tiled(model, raw, color_indices(meta.pattern), **options)
        assert timing["tiles"] == 520 and timing["megapixels"] == 101.995852
        values = prediction.numpy()
        if index == 0:
            np.save(saved, values, allow_pickle=False)
            write_rgb16(
                output / "full-linear16.tiff",
                values.transpose(1, 2, 0),
                metadata=meta,
                flip=meta.flip,
            )
        else:
            repeat_errors.append(
                difference(values, np.load(saved, mmap_mode="r", allow_pickle=False))
            )
        timings.append({"repeat": index, "timing": timing, "host_before": host})
        del prediction, values
        print(json.dumps({"repeat": index, "timing": timing}), flush=True)
    return {
        "status": "completed-full-frame-compilation-timing-case",
        "policy": "compiled" if compiled else "eager",
        "serving_probes": probes,
        "excluded_warmup": warm_timing,
        "full_frame_samples": timings,
        "repeat_pixel_errors": repeat_errors,
        "full_F32": ref(saved),
        "RGB16": ref(output / "full-linear16.tiff"),
        "timing_scope": "restore_tiled wall: raw validation, allocation, transfer, neural compute and blending; excludes source decoding, compilation, excluded warmup, saving, repeat comparisons and TIFF encoding",
    }


@torch.inference_mode()
def main(args):
    output = writable_path(args.output)
    assert not output.exists()
    device = torch.device(args.device)
    if device.type == "cpu":
        assert args.stage == "photos" and args.backend == "eager"
        assert not torch.cuda.is_available() and not torch.cuda.is_initialized(), "Hide CUDA"
    else:
        assert args.backend == "inductor" and psutil.virtual_memory().available > 24 * 2**30
    torch.set_num_threads(2 if device.type == "cpu" else 4)
    fixture = read(args.inputs)
    for path, expected in fixture["files"].items():
        assert sha(path) == expected, path
    import demosaic

    source_files = {str(p): sha(p) for p in Path(demosaic.__file__).parent.glob("*.py")}
    model, state = load_checkpoint(args.checkpoint, device)
    model.eval()
    if device.type == "cuda":
        model.to(memory_format=torch.channels_last)
    assert model.config.restoration_backbone == "packed-isotropic"
    checkpoint = {
        "path": str(Path(args.checkpoint).resolve()),
        "sha256": state["loaded_sha256"],
        "step": state["step"],
        "weights": "EMA",
        "model_config": model.config.to_dict(),
    }
    del state
    before = digest(model.state_dict().items())
    identities = {name: id(value) for name, value in model.named_parameters()}
    keys = tuple(model.state_dict())
    output.mkdir(parents=True)
    result = (
        photos(model, fixture, output, device, args.backend, checkpoint)
        if args.stage == "photos"
        else full(model, fixture, output, args.compiled, args.backend, args.repeats)
    )
    assert before == digest(model.state_dict().items())
    assert identities == {name: id(value) for name, value in model.named_parameters()}
    assert keys == tuple(model.state_dict()) and not any("_orig_mod" in key for key in keys)
    restoration = model.packed_isotropic
    blocks = [restoration.local_blocks, *restoration.groups, restoration.decoder]
    compiled_components = sum(callable(block._compiled_call_impl) for block in blocks)
    assert compiled_components == (len(blocks) if args.stage == "photos" or args.compiled else 0)
    assert all(
        block._compiled_call_impl is None
        for block in [restoration.stem, restoration.local_stem, restoration.up, restoration.head]
    )
    assert sha(args.checkpoint) == checkpoint["sha256"]
    for path, expected in {**fixture["files"], **source_files}.items():
        assert sha(path) == expected, path
    result.update(
        checkpoint=checkpoint,
        fixture=ref(args.inputs),
        source_files=source_files,
        driver=ref(__file__),
        parameters_keys_and_tensor_bytes_unchanged=True,
        full_model_state_sha256=before,
        backend=args.backend if args.stage == "photos" or args.compiled else None,
        compiled_components=compiled_components,
        device=str(device),
        GPU_name=torch.cuda.get_device_name(device) if device.type == "cuda" else None,
        CUDA_version=torch.version.cuda,
        torch=str(torch.__version__),
        CUDA_initialized=torch.cuda.is_initialized(),
        accuracy_bounds_DN16={"max_abs": MAX_DN16, "RMS": RMS_DN16},
        scope="Inference engineering only. Same weights and physical conditioning; "
        "no training, output correction, model promotion or production-default change. "
        "CPU eager-backend proof is not Inductor/CUDA evidence. Native visual review "
        "and full saved RGB comparison remain necessary before adopting a compute policy. "
        "Shared-machine timing ranges are not confidence intervals or a unique hardware optimum.",
    )
    (output / "receipt.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--stage", choices=["photos", "full"], required=True)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    parser.add_argument("--backend", choices=["eager", "inductor"], default="inductor")
    parser.add_argument("--compiled", action="store_true")
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("At least one full-frame timing repeat is required")
    main(args)
