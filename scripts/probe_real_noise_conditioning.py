"""CPU-only sensitivity to supplied noise priors on fixed cached real contexts."""

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np
import psutil
import torch

from demosaic.cfa import color_indices, malvar
from demosaic.inference import load_checkpoint
from demosaic.precision import ieee_fp32
from demosaic.reporting import display_crop, save_triplet


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def ref(path):
    return {"path": str(path), "sha256": sha(path)}


def read(path):
    return json.loads(Path(path).read_text())


def state_digest(model):
    digest = hashlib.sha256()
    for name, value in model.state_dict().items():
        digest.update(name.encode())
        digest.update(str((value.dtype, tuple(value.shape))).encode())
        digest.update(value.detach().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


@torch.inference_mode()
def predict_context(model, packed, colors, wb, matrix, *, shot, read_noise, variance_factor):
    """Multiply shot/read variances together; leave every measured pixel fixed."""
    if not np.isfinite([shot, read_noise, variance_factor]).all():
        raise ValueError("Noise conditioning must be finite")
    if min(shot, read_noise) < 0 or variance_factor <= 0:
        raise ValueError("Noise coefficients must be nonnegative and factor positive")
    shot, read_noise = shot * variance_factor, read_noise * variance_factor
    model.set_noise(shot, read_noise)
    with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
        variance = packed.float().clamp_min(0) * shot + read_noise
        result = model(packed.float(), variance, colors, wb, matrix)
    if result.dtype != torch.float32 or not torch.isfinite(result).all():
        raise ValueError("Expected finite FP32 camera RGB")
    return result


def difference(first, second):
    delta = first.double() - second.double()
    assert torch.isfinite(delta).all()
    return {
        "elements": delta.numel(),
        "max_abs_DN16": delta.abs().max().item() * 65535,
        "RMS_DN16": delta.square().mean().sqrt().item() * 65535,
    }


def alive(owner):
    try:
        process = psutil.Process(owner["pid"])
        return (
            process.create_time() == owner["created"] and process.status() != psutil.STATUS_ZOMBIE
        )
    except psutil.NoSuchProcess:
        return False


def run(plan_path):
    assert not torch.cuda.is_available() and not torch.cuda.is_initialized(), "Hide CUDA"
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    plan = read(plan_path)
    root, status = Path(plan["root"]), Path(plan["status"])
    assert not status.exists()
    with (root / "launch.claim").open("x") as stream:
        stream.write(str(os.getpid()) + "\n")
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    info = {
        "controller": owner,
        "plan": ref(plan_path),
        "CUDA_initialized": False,
        "completed_cases": 0,
    }

    def guard():
        for path, expected in {**plan["inputs"], **plan["guards"]}.items():
            assert sha(path) == expected, path

    def record(state, **fields):
        info.update(status=state, updated_unix=time.time(), **fields)
        temporary = status.with_suffix(".tmp")
        temporary.write_text(json.dumps(info, indent=2, allow_nan=False) + "\n")
        temporary.replace(status)
        print(json.dumps({"status": state, **fields}), flush=True)

    def yield_for_reviews():
        if alive(plan["training_owner"]):
            return
        waiting = False
        while True:
            active = []
            for entry in plan["review_and_timing_owners"]:
                if alive(entry["owner"]):
                    active.append(entry["owner"])
                else:
                    state = read(entry["workflow"])
                    if (
                        state["controller"] == entry["owner"]
                        and state.get("child")
                        and alive(state["child"])
                    ):
                        active.append(state["child"])
            if not active:
                break
            if not waiting:
                record("waiting-for-owned-review-and-timing-owners-no-CPU-compute", active=active)
                waiting = True
            time.sleep(15)
        if waiting:
            record("resuming-CPU-noise-conditioning-diagnostic")

    try:
        guard()
        fixture = read(plan["fixture"]["path"])
        metadata = fixture["gfx_metadata"]
        colors = color_indices(metadata["pattern"])[None]
        wb = torch.tensor(metadata["white_balance"], dtype=torch.float32)[None]
        matrix = torch.tensor(metadata["camera_to_srgb"], dtype=torch.float32)[None]
        cases, models = [], []
        for checkpoint in plan["checkpoints"]:
            yield_for_reviews()
            assert psutil.virtual_memory().available > 16 * 2**30
            model, loaded = load_checkpoint(checkpoint["path"], "cpu")
            assert loaded["loaded_sha256"] == checkpoint["sha256"]
            model.eval()
            del loaded
            digest = state_digest(model)
            identities = [id(p) for p in model.parameters()]
            keys = list(model.state_dict())
            for factor in plan["variance_factors_execution_order"]:
                for region in fixture["gfx_regions"][:4]:
                    yield_for_reviews()
                    packed = torch.from_numpy(np.load(region["noisy_packed"]["path"]).copy())
                    reference = torch.from_numpy(np.load(region["reference_RGB"]["path"]).copy())
                    packed_before = packed.clone()
                    prediction = predict_context(
                        model,
                        packed,
                        colors,
                        wb,
                        matrix,
                        shot=fixture["conditioning"]["shot"],
                        read_noise=fixture["conditioning"]["read"],
                        variance_factor=factor,
                    )
                    assert torch.equal(packed, packed_before)
                    assert prediction.shape == (1, 3, 512, 512)
                    name = region["region"]["name"]
                    key = f"{checkpoint['label']}-{name}-variance{factor:g}"
                    array_path = root / (key + "-RGB-f32.npy")
                    np.save(array_path, prediction.numpy())
                    nominal_path = root / (f"{checkpoint['label']}-{name}-variance1-RGB-f32.npy")
                    nominal = torch.from_numpy(np.load(nominal_path))
                    roi = [176, 176, 160, 160]
                    panels = [
                        ("Noisy (Malvar)", malvar(packed, colors, wb), roi),
                        (f"{checkpoint['label']} var x{factor:g}", prediction, roi),
                        ("ISO100 ref, not GT", reference, [0, 0, 160, 160]),
                    ]
                    crop = save_triplet(
                        root / "crops",
                        key,
                        [
                            (
                                label,
                                display_crop(
                                    value,
                                    wb,
                                    matrix,
                                    panel_roi,
                                    exposure=fixture["display_exposure"],
                                ),
                            )
                            for label, value, panel_roi in panels
                        ],
                        caption=key,
                        metadata={
                            "checkpoint": checkpoint,
                            "region": region,
                            "ROI_in_context_xywh": roi,
                            "ROI_in_reference_array_xywh": [0, 0, 160, 160],
                            "noise_conditioning": {
                                "shot": fixture["conditioning"]["shot"] * factor,
                                "read": fixture["conditioning"]["read"] * factor,
                                "variance_factor": factor,
                                "std_factor": factor**0.5,
                            },
                            "display_exposure": fixture["display_exposure"],
                            "WB": metadata["white_balance"],
                            "camera_to_srgb": metadata["camera_to_srgb"],
                            "device": "CPU",
                            "precision": "float32",
                            "extent": "512px context, not full-frame inference",
                            "reference": region["reference"],
                            "source_RAFs": fixture["gfx_sources"],
                        },
                    )
                    cases.append(
                        {
                            "key": key,
                            "checkpoint": checkpoint,
                            "region": name,
                            "variance_factor": factor,
                            "RGB_f32": ref(array_path),
                            "difference_from_nominal": difference(prediction, nominal),
                            "ROI_difference_from_nominal": difference(
                                prediction[..., 176:336, 176:336], nominal[..., 176:336, 176:336]
                            ),
                            "crop": crop,
                        }
                    )
                    record(
                        "running-cached-CPU-noise-conditioning-sensitivity",
                        completed_cases=len(cases),
                        last_case=key,
                    )
            yield_for_reviews()
            first = fixture["gfx_regions"][0]
            packed = torch.from_numpy(np.load(first["noisy_packed"]["path"]).copy())
            repeated = predict_context(
                model,
                packed,
                colors,
                wb,
                matrix,
                shot=fixture["conditioning"]["shot"],
                read_noise=fixture["conditioning"]["read"],
                variance_factor=1,
            )
            expected = torch.from_numpy(
                np.load(
                    root
                    / (f"{checkpoint['label']}-{first['region']['name']}-variance1-RGB-f32.npy")
                )
            )
            assert torch.equal(repeated, expected), "Nominal repeat changed after profile switches"
            assert state_digest(model) == digest and list(model.state_dict()) == keys
            assert [id(p) for p in model.parameters()] == identities
            models.append(
                {
                    **checkpoint,
                    "all_state_bytes_keys_and_parameter_IDs_unchanged": True,
                    "nominal_repeat_bitwise_equal": True,
                    "state_digest": digest,
                }
            )
            del model
        guard()
        assert len(cases) == 24 and not torch.cuda.is_initialized()
        result = {
            "status": "completed-CPU-noise-conditioning-sensitivity-awaiting-native-visual-review",
            "plan": ref(plan_path),
            "fixture": plan["fixture"],
            "cases": cases,
            "models": models,
            "CUDA_initialized": False,
            "scope": plan["scope"],
        }
        (root / "receipt.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
        record(result["status"], result=ref(root / "receipt.json"))
    except BaseException as error:
        record("failed-no-automatic-restart", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    run(parser.parse_args().plan)
