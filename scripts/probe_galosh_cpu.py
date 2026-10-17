"""Small pinned GALOSH CPU-port + Malvar comparison on existing observations."""

import argparse
import json
import math
import os
import subprocess
import time
from pathlib import Path

import numpy as np
import torch
from prepare_galosh_cpu import sha
from probe_rawforge_cpu import GFX, cases
from torch.nn import functional as F

from demosaic.cfa import color_indices, malvar
from demosaic.color import render
from demosaic.reporting import display_crop, save_triplet
from demosaic.safety import writable_path


def read(path):
    return json.loads(Path(path).read_text())


def unpack(packed):
    assert packed.dtype == np.float32 and packed.shape[:2] == (1, 4)
    h, w = packed.shape[-2:]
    result = np.empty((2 * h, 2 * w), dtype=np.float32)
    for phase in range(4):
        result[phase // 2 :: 2, phase % 2 :: 2] = packed[0, phase]
    assert np.array_equal(result, F.pixel_shuffle(torch.from_numpy(packed), 2)[0, 0].numpy())
    return result


def scores(prediction, target, wb, matrix, roi):
    x, y, w, h = roi
    a = prediction[..., y : y + h, x : x + w]
    b = target[..., y : y + h, x : x + w]
    mse = (a.clamp(0, 1).double() - b.clamp(0, 1).double()).square().mean()
    displayed = [render(v, wb, matrix).double() for v in [a, b]]
    display_mse = (displayed[0] - displayed[1]).square().mean()
    return {
        "camera_clipped_PSNR": -10 * math.log10(max(float(mse), 1e-12)),
        "sRGB_PSNR": -10 * math.log10(max(float(display_mse), 1e-12)),
    }


@torch.inference_mode()
def main(build, output, *, threads=1):
    assert not torch.cuda.is_available() and not torch.cuda.is_initialized()
    if type(threads) is not int or threads not in (1, 2):
        raise ValueError("Use one or two CPU threads for this shared-machine probe")
    torch.set_num_threads(2)
    output = writable_path(output)
    if output.exists():
        raise ValueError("Probe exists; inspect it or select a fresh output")
    built = read(build)
    assert built["status"] == "built-local-AArch64-canonical-CPU-reference-no-quality-result"
    for path, digest in {**built["official_sources"], **built["local_sources"]}.items():
        assert sha(path) == digest
    binary = built["binary"]
    assert sha(binary["path"]) == binary["sha256"]
    selected = cases()
    for case in selected:
        assert sha(case["observation"]) == case["observation_sha256"]
        assert case["pattern"] == "RGGB"
        if "reference_array" in case:
            assert sha(case["reference_array"]) == case["reference_array_sha256"]
    output.mkdir(parents=True)
    source = output / "source"
    source.mkdir()
    for path in [
        Path(__file__),
        Path(__file__).with_name("prepare_galosh_cpu.py"),
        Path(__file__).with_name("probe_rawforge_cpu.py"),
        *Path("src/demosaic").glob("*.py"),
    ]:
        (source / path.name).write_bytes(path.read_bytes())
    nominal_gfx = read(GFX / "report.json")["conditioning"]
    plan = {
        "build": str(build),
        "build_sha256": sha(build),
        "binary": binary,
        "cases": selected,
        "modes": ["blind", "supplied-nominal"],
        "luma_strength": 1.0,
        "chroma_strength": 1.0,
        "OMP_NUM_THREADS": threads,
        "input_contract": "Original packed signed observations unpacked exactly; clamp to [0,1] for the publisher's documented input range, with every clipped count recorded. No WB/gain transform before the raw denoiser. Output Bayer is independently WB-aware Malvar demosaiced. No fitting to reference.",
        "source_files": {str(p): sha(p) for p in source.glob("*.py")},
        "scope": "Two fixed CPU-noise photographic observations and four cached GFX512 contexts only. Explicit AArch64 CPU port; not original x86/GPU parity, a full benchmark, full-frame inference, trained model improvement or SOTA.",
    }
    (output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    results, arrays, crops = [], [], []
    environment = {**os.environ, "OMP_NUM_THREADS": str(threads), "OMP_DYNAMIC": "FALSE"}
    for case in selected:
        if case["kind"] == "synthetic-photo":
            with np.load(case["observation"], allow_pickle=False) as data:
                batch = {k: torch.from_numpy(data[k].copy()) for k in data.files}
            target, wb, matrix = batch["target"], batch["wb"], batch["matrix"]
            nominal = case["source"]["source_crop"]["condition"]
        else:
            batch = {
                "packed": torch.from_numpy(np.load(case["observation"], allow_pickle=False)),
                "colors": color_indices(case["pattern"])[None],
            }
            target = torch.from_numpy(np.load(case["reference_array"], allow_pickle=False))
            wb = torch.tensor(case["wb"], dtype=torch.float32).reshape(1, 3)
            matrix = torch.tensor(case["matrix"], dtype=torch.float32).reshape(1, 3, 3)
            nominal = nominal_gfx
        raw = unpack(batch["packed"].numpy())
        clamp_record = {
            "below_zero_samples": int((raw < 0).sum()),
            "above_one_samples": int((raw > 1).sum()),
            "total_samples": raw.size,
        }
        input_file = output / (case["id"] + "-input-clipped-f32.bin")
        np.clip(raw, 0, 1).astype("<f4").tofile(input_file)
        h, w = raw.shape
        noisy = malvar(batch["packed"], batch["colors"], wb)
        roi = case["roi_xywh"]
        exact = case["kind"] == "synthetic-photo"
        for mode in plan["modes"]:
            name = case["id"] + "-" + mode
            output_file = output / (name + "-output-raw-f32.bin")
            shot, read_noise = (0.0, 0.0) if mode == "blind" else (nominal["shot"], nominal["read"])
            command = [
                binary["path"],
                str(input_file),
                str(output_file),
                str(w),
                str(h),
                "galosh",
                "1",
                "1",
                "1",
                str(shot),
                str(read_noise),
            ]
            started = time.perf_counter()
            with (output / (name + ".log")).open("xb") as log:
                subprocess.run(
                    command, env=environment, stdout=log, stderr=subprocess.STDOUT, check=True
                )
            elapsed = time.perf_counter() - started
            values = np.fromfile(output_file, dtype="<f4")
            assert values.size == h * w and np.isfinite(values).all()
            values = values.reshape(h, w)
            packed = np.stack([values[p // 2 :: 2, p % 2 :: 2] for p in range(4)])[None].copy()
            assert np.array_equal(
                packed, F.pixel_unshuffle(torch.from_numpy(values[None, None]), 2).numpy()
            )
            prediction = malvar(torch.from_numpy(packed), batch["colors"], wb)
            assert prediction.shape == (1, 3, h, w) and torch.isfinite(prediction).all()
            path = output / (name + "-RGB-f32.npy")
            np.save(path, prediction.numpy(), allow_pickle=False)
            arrays.append(
                {
                    "case": case["id"],
                    "mode": mode,
                    "input": {"path": str(input_file), "sha256": sha(input_file)},
                    "raw_output": {"path": str(output_file), "sha256": sha(output_file)},
                    "RGB": {"path": str(path), "sha256": sha(path)},
                    "input_clipping": clamp_record,
                    "command": command,
                    "process_wall_seconds_shared_machine": elapsed,
                }
            )
            metrics = scores(prediction, target, wb, matrix, roi) if exact else None
            results.append({"case": case["id"], "mode": mode, "metrics": metrics})
            target_roi = roi if exact else [0, 0, 160, 160]
            crops.append(
                save_triplet(
                    output,
                    name,
                    [
                        (
                            label,
                            display_crop(rgb, wb, matrix, area, exposure=case["display_exposure"]),
                        )
                        for label, rgb, area in [
                            ("Noisy (Malvar)", noisy, roi),
                            ("GALOSH + Malvar", prediction, roi),
                            (
                                "GT (synthetic)" if exact else "ISO100 ref (not GT)",
                                target,
                                target_roi,
                            ),
                        ]
                    ],
                    caption="GALOSH / " + case["id"] + " / " + mode,
                    metadata={
                        "case": case,
                        "method": {
                            "name": "GALOSH CPU AArch64 port + independent Malvar",
                            "binary": binary,
                            "upstream_commit": built["official_commit"],
                            "checkpoint": "None: training-free method; binary/source hashes identify execution",
                        },
                        "ROI_xywh": roi,
                        "white_balance": wb.tolist(),
                        "camera_to_srgb": matrix.tolist(),
                        "display_exposure": case["display_exposure"],
                        "reference": case["reference"],
                        "conditioning": {
                            "mode": mode,
                            "supplied_shot": shot,
                            "supplied_read_variance": read_noise,
                            "nominal_observation": nominal,
                            "internal_stabilized_sigma_reestimation_retained": True,
                            "luma_strength": 1.0,
                            "chroma_strength": 1.0,
                        },
                        "input_preprocessing": plan["input_contract"],
                        "input_clipping": clamp_record,
                        "compute_precision": f"C CPU FP32, FP contraction off/OpenMP{threads}; subsequent independent CPU FP32 Malvar/render",
                    },
                )
            )
            print(json.dumps({"case": case["id"], "mode": mode, "seconds": elapsed}), flush=True)
    assert len(results) == len(arrays) == len(crops) == 12 and not torch.cuda.is_initialized()
    assert sha(binary["path"]) == binary["sha256"]
    report = {
        "status": "completed-small-GALOSH-CPU-port-pilot-awaiting-independent-and-native-review",
        "plan": str(output / "plan.json"),
        "plan_sha256": sha(output / "plan.json"),
        "results": results,
        "arrays": arrays,
        "native_crops": crops,
        "CUDA_initialized": False,
        "limitations": "Two selected synthetic photos/four real512px contexts. Input clipped to publisher[0,1] range explicitly, so this cascade includes a different negative-tail preprocessing policy than the signed neural models. Supplied noise is nominal; the publisher's stabilized-sigma reestimate remains active. Real reference is not GT and has no scores. Shared-machine small-context CPU wall times do not establish full100MP or GPU speed. AArch64 port has no original x86/GPU numerical parity. No trained model change, tuning to GT, broad quality/SOTA, convergence or promotion claim.",
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--threads", type=int, default=1)
    args = parser.parse_args()
    main(args.build, args.output, threads=args.threads)
