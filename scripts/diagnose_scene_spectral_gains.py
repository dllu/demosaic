"""Replay the spatial spectral head and separate its delivered correction by band."""

import argparse
import os
import time
from pathlib import Path

import numpy as np
import psutil
import torch
from evaluate_scene_spectral_detail import load_arguments, write_array
from profile_raw_kernel_inference import model_hash

from demosaic.cfa import malvar, pack
from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.io import read_raw
from demosaic.models import load_model
from demosaic.precision import ieee_fp32
from demosaic.prediction_archive import fingerprint
from demosaic.scene_restoration import encode_scene
from demosaic.scene_spectral_detail import SceneSpectralDetail


def prepare(root, pilot):
    original = reference(pilot / "plan.json")
    result = reference(pilot / "collection/result.json")
    native = reference(pilot / "review/result.json")
    receipt = read_json(checked(result))
    assert receipt["plan"] == original and len(receipt["records"]) == 134
    assert read_json(checked(native))["collection"] == result
    root.mkdir()
    work, sources = freeze_sources(
        Path.cwd(), root, [Path(__file__).name, "report_scene_spectral_gains.py"]
    )
    write_json(
        root / "plan.json",
        {
            "root": str(root),
            "work": str(work),
            "inputs": [original, result, native],
            "frozen_files": sources,
            "original": original,
            "completed_pilot": result,
            "native_pilot": native,
            "driver": reference(work / "scripts" / Path(__file__).name),
            "reporter": reference(work / "scripts/report_scene_spectral_gains.py"),
            "gain_bounds": [0, 2],
            "scope": "All fixed pilot development and GFX observations. Freeze the existing learned support "
            "and separate the already scene-weighted coefficients at the original native frequency crossfade. "
            "No target/reference loaded in this stage.",
        },
    )


def split_correction(head, base, args, scene, boxes):
    packed, variance, colors, wb = [args[k].cuda() for k in ("packed", "variance", "colors", "wb")]
    output, auxiliary = head(
        base,
        packed,
        variance,
        colors,
        wb,
        scene=scene,
        boxes_xywh=boxes,
        mode="spatial",
        return_aux=True,
    )
    delta = auxiliary["spectral_delta"]
    freq = torch.fft.fftfreq(delta.shape[-1], device=base.device)
    radius = torch.hypot(freq[:, None], freq[None, :])
    high = ((radius - 0.125) / 0.125).clamp(0, 1)
    fields = torch.stack(
        [
            malvar(
                head.synthesis(delta * weight, auxiliary["geometry"]) * auxiliary["support"],
                colors,
                wb,
            )
            for weight in (1 - high, high)
        ]
    )
    torch.testing.assert_close(fields.sum(0), auxiliary["correction"], rtol=0, atol=1e-7)
    return output, fields, float((fields.sum(0) - auxiliary["correction"]).abs().max())


@torch.inference_mode()
def collect(plan_path, limit):
    plan = read_json(plan_path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    original = read_json(checked(plan["original"]))
    pilot = read_json(checked(plan["completed_pilot"]))
    binding = pilot["heads"]["spatial"]
    state = torch.load(checked(binding), map_location="cpu", weights_only=True)
    assert state["step"] == 800 and state["mode"] == "spatial"
    device = torch.cuda.get_device_properties(0)
    torch.cuda.set_per_process_memory_fraction(min(1.0, 6 * 2**30 / device.total_memory))
    torch.set_num_threads(2)
    base, _ = load_model("v120", checkpoint=checked(state["parent"]), device="cpu")
    encoder = base.context.cuda().eval()
    head = SceneSpectralDetail(
        encoder.backbone.config.hidden_sizes,
        max_window=state["max_window"],
        adapter_width=state["adapter_width"],
    )
    head.load_state_dict(state["ema"], strict=True)
    head.cuda().eval()
    assert model_hash(encoder.backbone) == state["DINO_sha256"]
    del base
    training = read_json(checked(original["training"]))
    native = read_json(checked(original["native"]))
    real_sources = read_json(checked(original["whole_camera_sources"]))["full_real_noisy_sources"]
    development = read_json(checked(original["development"]))["cases"]
    declared = [
        (read_json(checked(record)), True)
        for record in (development[:limit] if limit else development)
    ]
    declared += [
        (r, False)
        for r in native["observations"]
        if r["kind"] != "development" and (not limit or r["id"] == "mesh-profile3879")
    ]
    saved = {x["id"]: x for x in (read_json(checked(r)) for r in pilot["records"])}
    directory = Path(plan["root"]) / ("qualification" if limit else "basis")
    directory.mkdir()
    seen, rows, started = {}, [], time.monotonic()
    maximum = 0.0
    with ieee_fp32():
        for item, development_case in declared:
            if psutil.virtual_memory().available < 32 * 2**30:
                raise RuntimeError("Shared memory reserve unavailable")
            key = item["id"]
            earlier = saved[key]
            input_bound = item["inputs"] if development_case else item["arrays"]
            args, packed = load_arguments(input_bound, development=development_case)
            assert {k: fingerprint(v) for k, v in args.items()} == earlier["physical"]
            if development_case:
                scene = encode_scene(
                    encoder,
                    packed,
                    args["colors"][0],
                    args["wb"][0],
                    args["matrix"][0],
                    long_side=training["preview_long_side"],
                    exposure=training["preview_exposure"],
                )
            else:
                family = "main" if item["kind"] == "gfx" else "mesh"
                if family not in seen:
                    raw = checked(real_sources[family])
                    assert raw.parent.name == "gfx-qualitative-20231231"
                    raw, metadata = read_raw(raw)
                    assert metadata.pattern == "RGGB"
                    scene = encode_scene(
                        encoder,
                        pack(torch.from_numpy(raw)[None, None])[0],
                        args["colors"][0],
                        args["wb"][0],
                        args["matrix"][0],
                        long_side=training["preview_long_side"],
                        exposure=training["preview_exposure"],
                    )
                    seen[family] = scene
                scene = seen[family]
            assert [fingerprint(v) for v in scene.features] == earlier["scene_features"]
            parent = torch.from_numpy(
                np.load(checked(earlier["parent"]), allow_pickle=False)
            ).cuda()
            output, fields, error = split_correction(
                head, parent, args, scene, earlier["boxes_xywh"]
            )
            expected = torch.from_numpy(
                np.load(checked(earlier["variants"]["spatial"]), allow_pickle=False)
            ).cuda()
            torch.testing.assert_close(output, expected, rtol=0, atol=0)
            maximum = max(maximum, error)
            basis = write_array(directory / f"{key}-basis.npy", fields.cpu().numpy())
            row = {
                "id": key,
                "kind": "development" if development_case else "camera",
                "inputs": input_bound,
                "source_id": item.get("source_id"),
                "parent": earlier["parent"],
                "learned": earlier["variants"]["spatial"],
                "basis": basis,
                "boxes_xywh": earlier["boxes_xywh"],
                "weights": binding,
                "decomposition_max_abs": error,
            }
            receipt = directory / f"{key}.json"
            write_json(receipt, row)
            rows.append(reference(receipt))
            print(len(rows), key, round(time.monotonic() - started, 3), flush=True)
    assert len(rows) == (limit + 1 if limit else 134)
    write_json(
        directory / "result.json",
        {
            "driver": reference(__file__),
            "plan": reference(plan_path),
            "rows": rows,
            "checkpoint": binding,
            "seconds": time.monotonic() - started,
            "cuda_peak_GiB": torch.cuda.max_memory_allocated() / 2**30,
            "replayed_outputs_exact": len(rows),
            "max_decomposition_abs": maximum,
            "qualification": bool(limit),
            "target_reads": 0,
        },
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("path", type=Path)
    p.add_argument("--prepare-from", type=Path)
    p.add_argument("--limit", type=int, default=0)
    a = p.parse_args()
    if a.prepare_from:
        prepare(a.path.resolve(), a.prepare_from.resolve())
    else:
        os.sched_setaffinity(0, (6, 7))
        os.nice(11)
        collect(a.path.resolve(), a.limit)
