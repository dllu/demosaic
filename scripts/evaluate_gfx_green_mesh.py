"""One forward per new mesh-context method; reuse saved predictions in later reports."""

import argparse
import gc
import json
import time
from pathlib import Path

import numpy as np
import psutil
import torch
from PIL import Image, ImageDraw, ImageFont
from prepare_gfx_green_mesh_inputs import binding, save

from demosaic.color import linear_to_srgb, srgb_to_linear
from demosaic.inference import load_checkpoint
from demosaic.precision import ieee_fp32
from demosaic.reference import load_rawnind, publisher_input_scale
from demosaic.reporting import display_crop, save_triplet
from demosaic.safety import writable_path


def checked(item):
    assert binding(item["path"]) == item
    return Path(item["path"])


@torch.inference_mode()
def main(plan_path, output):
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized() and psutil.virtual_memory().available > 40 * 2**30
    plan_path = Path(plan_path).resolve()
    plan = json.loads(plan_path.read_text())
    inputs = json.loads(checked(plan["inputs"]).read_text())
    selection = json.loads(checked(inputs["derived_selection"]).read_text())
    arrays = checked(inputs["input_arrays"])
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    save(
        output / "execution-v1.json",
        {
            "driver": binding(__file__),
            "plan": binding(plan_path),
            "input_arrays": binding(arrays),
            "runtime": "CPU IEEE FP32, contiguous, B1, two threads, one native768 context per new method; stored predictions reusable. No autocast/CUDA/noise/RAW/optimizer.",
        },
    )
    with np.load(arrays, allow_pickle=False) as data:
        tensors = {k: torch.from_numpy(data[k].copy()) for k in data.files if k != "raw_context"}
    condition = inputs["conditioning"]
    exposure = inputs["display_exposure"]
    methods = []
    for item in plan["methods"]:
        assert psutil.virtual_memory().available > 32 * 2**30
        if "prediction" in item:
            assert item["source_inputs_sha256"] == inputs["input_arrays"]["sha256"]
            p = checked(item["prediction"])
            values = np.load(p, allow_pickle=False)
            record = {
                **item,
                "actual_root_forwards": 0,
                "actual_encoder_forwards": 0,
                "new_inference": False,
            }
        else:
            path = checked(item["checkpoint"])
            if item["kind"] == "checkpoint":
                model, state = load_checkpoint(path, "cpu")
                assert (
                    state["loaded_sha256"] == item["checkpoint"]["sha256"]
                    and state["step"] == item.get("expected_step", 20000)
                )
                record = {**item, "step": state["step"], "model_config": model.config.to_dict()}
                del state
            else:
                assert item["kind"] == "rawnind-preup"
                for file in item["source_files"]:
                    checked(file)
                meta = selection["raw_metadata"]
                scale = publisher_input_scale(
                    meta["white_levels"], meta["black_levels"], meta["adc_white_level"]
                )
                model = load_rawnind(
                    item["directory"],
                    gain_mode="cfa-channel",
                    device="cpu",
                    input_scale=scale,
                    clip_input=False,
                )
                record = {
                    **item,
                    "input_scale": scale,
                    "gain": "Input-only CFA-channel least squares; signed RAW, no reference/output fit",
                }
            model.eval().to(memory_format=torch.contiguous_format)
            counts = {"root": 0, "encoder": 0}

            def root_hook(*args, counts=counts):
                counts["root"] += 1

            def encoder_hook(*args, counts=counts):
                counts["encoder"] += 1

            hooks = [model.register_forward_pre_hook(root_hook)]
            if item["kind"] == "checkpoint":
                hooks.append(model.context.backbone.register_forward_pre_hook(encoder_hook))
                model.set_noise(condition["shot"], condition["read"])
            started = time.monotonic()
            with ieee_fp32(), torch.autocast("cpu", enabled=False):
                prediction = model(
                    *(tensors[k] for k in ["packed", "variance", "colors", "wb", "matrix"])
                )
            assert counts["root"] == 1
            assert counts["encoder"] == (1 if item["kind"] == "checkpoint" else 0)
            for hook in hooks:
                hook.remove()
            values = prediction.detach().cpu().numpy().copy()
            p = output / (item["label"] + "-RGB-f32.npy")
            assert (
                values.shape == (1, 3, 768, 768)
                and values.dtype == np.float32
                and np.isfinite(values).all()
            )
            np.save(p, values, allow_pickle=False)
            record.update(
                prediction=binding(p),
                source_inputs_sha256=inputs["input_arrays"]["sha256"],
                actual_root_forwards=counts["root"],
                actual_encoder_forwards=counts["encoder"],
                new_inference=True,
                seconds=time.monotonic() - started,
            )
            del prediction, model
            gc.collect()
        assert (
            values.shape == (1, 3, 768, 768)
            and values.dtype == np.float32
            and np.isfinite(values).all()
        )
        methods.append(record)
        save(output / (item["label"] + "-method.json"), record)
        print(
            json.dumps(
                {
                    "event": "method-complete",
                    "label": item["label"],
                    "new_root_forwards": record["actual_root_forwards"],
                }
            ),
            flush=True,
        )
    labels = [
        "ISO6400 camera JPEG",
        "Noisy Malvar",
        *[r["label"] for r in methods],
        "ISO100 AHD, not GT",
        "ISO100 camera JPEG",
    ]
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
    board = Image.new("RGB", (len(labels) * 176 + 8, 440), "#eeeeee")
    draw = ImageDraw.Draw(board)
    for j, label in enumerate(labels):
        draw.text((8 + j * 176, 5), label, fill="black", font=font)
    crops = []
    for row, case in enumerate(inputs["cases"]):
        roi = case["ROI_xywh"]
        displayed = {}
        for label, key in [("Noisy Malvar", "noisy_rgb"), ("ISO100 AHD, not GT", "reference_rgb")]:
            displayed[label] = display_crop(
                tensors[key], tensors["wb"], tensors["matrix"], roi, exposure=exposure
            )
        for role, label in [
            ("noisy_camera_jpeg", "ISO6400 camera JPEG"),
            ("reference_camera_jpeg", "ISO100 camera JPEG"),
        ]:
            raw_jpeg = np.load(checked(case["camera_JPEGs"][role]["pixels"]), allow_pickle=False)
            assert raw_jpeg.shape == (160, 160, 3) and raw_jpeg.dtype == np.uint8
            displayed[label] = linear_to_srgb(
                (srgb_to_linear(raw_jpeg.astype(np.float32) / 255) * exposure).clip(0, 1)
            )
        for item in methods:
            values = torch.from_numpy(
                np.load(checked(item["prediction"]), mmap_mode="r", allow_pickle=False).copy()
            )
            displayed[item["label"]] = display_crop(
                values, tensors["wb"], tensors["matrix"], roi, exposure=exposure
            )
        draw.text((8, 35 + row * 200), case["name"], fill="black", font=font)
        for j, label in enumerate(labels):
            pixels = np.rint(displayed[label].clip(0, 1) * 255).astype(np.uint8)
            board.paste(Image.fromarray(pixels), (8 + j * 176, 55 + row * 200))
        for item in methods:
            receipt = save_triplet(
                output / "triplets",
                case["name"] + item["label"],
                [
                    ("Noisy Malvar", displayed["Noisy Malvar"]),
                    (item["label"], displayed[item["label"]]),
                    ("ISO100 ref, not GT", displayed["ISO100 AHD, not GT"]),
                ],
                caption="New green mesh case; independent aperture/time/motion differences, not exactGT.",
                metadata={
                    "case": case,
                    "method": item,
                    "conditioning": condition,
                    "display_exposure": exposure,
                    "source_bindings": inputs["source_bindings"],
                    "input_arrays": inputs["input_arrays"],
                    "RAW_context_xywh": selection["raw_context_xywh"],
                    "reference": "DSCF3835 ISO100/f5.6/2.5s, independent AHD camera RGB; not exactGT",
                    "scope": "Native160 context-crop comparison, not full-frame inference or a paired quality score.",
                },
            )
            crops.append(
                {
                    "label": item["label"],
                    "region": case["name"],
                    "image": binding(output / "triplets" / receipt["image"]),
                    "metadata": binding(
                        (output / "triplets" / receipt["image"]).with_suffix(".json")
                    ),
                }
            )
    image = output / "comparison-native.png"
    board.save(image)
    result = {
        "status": "completed-new-green-mesh-CPU-context-inference-awaiting-actual-native-viewing",
        "driver": binding(__file__),
        "plan": binding(plan_path),
        "inputs": plan["inputs"],
        "input_arrays": binding(arrays),
        "methods": methods,
        "native_comparison": binding(image),
        "triplets": crops,
        "display_exposure": exposure,
        "JPEG_display": "Decode camera sRGB, apply sharedlinear x4 display gain, encode sRGB; intrinsic camera tone/sharpness/denoising/geometric processing differs from RAW pipeline.",
        "new_root_forwards": sum(r["actual_root_forwards"] for r in methods),
        "new_encoder_forwards": sum(r["actual_encoder_forwards"] for r in methods),
        "new_RAW_decodes": 0,
        "new_noise_observations": 0,
        "optimizer_updates": 0,
        "CUDA_initialized": False,
        "scope": "Two new native160 regions from one768context, same observedRAW and conditioning across RAW methods. CameraJPEGs separately integer-matched; residual lens/framing/processing differences remain. No warp, native resize, target fit, exactGT, PSNR, training or full-frame/speed claim. Future reports may reuse bound FP32 controls without new forwards.",
    }
    save(output / "result-v1.json", result)
    print(
        json.dumps({"status": result["status"], "new_root_forwards": result["new_root_forwards"]}),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    main(args.plan, args.output)
