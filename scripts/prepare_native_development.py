"""Freeze held-out binned camera targets and shared physical-noise observations."""

import argparse
import datetime
import hashlib
import json
import os
import random
import re
import shutil
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import psutil
import torch

from demosaic.cfa import PATTERNS, color_indices, mosaic
from demosaic.noise import add_noise, variance_map
from demosaic.prediction_archive import fingerprint

REPO = Path(__file__).absolute().parents[1]


def binding(path):
    path = Path(path).absolute()
    with path.open("rb") as stream:
        return {"path": str(path), "sha256": hashlib.file_digest(stream, "sha256").hexdigest()}


def write(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def checked(item):
    if binding(item["path"]) != item:
        raise ValueError(f"Changed prepared input: {item['path']}")
    return Path(item["path"])


def prepare(selection, output):
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or torch.cuda.is_initialized():
        raise ValueError("Prepare native development observations with CUDA hidden")
    os.nice(10)
    process = psutil.Process()
    process.cpu_affinity(process.cpu_affinity()[:2])
    torch.set_num_threads(2)
    if psutil.virtual_memory().available < 48 * 2**30:
        raise RuntimeError("Native development preparation needs48GiB available RAM")
    selection = Path(selection).absolute()
    selection_ref = binding(selection)
    spec = json.loads(selection.read_text())
    if spec["split"] != "development" or spec["usage"].endswith("training") is False:
        raise ValueError("Require the explicitly held-out development selection")
    output = Path(output).resolve()
    if not (output.is_relative_to(REPO / ".cache") or
            output.is_relative_to(Path("/mnt/external/demosaic"))):
        raise ValueError("Use repository cache or external project scratch")
    if shutil.disk_usage(output.parent).free < 128 * 2**30:
        raise RuntimeError("Native development output needs128GiB free disk")
    output.mkdir(parents=True, exist_ok=False)
    owner = {"pid": os.getpid(), "created": process.create_time()}
    source = output / "source"
    source.mkdir()
    source_files = [Path(__file__), *list((REPO / "src/demosaic").glob("*.py"))]
    for path in source_files:
        shutil.copyfile(path, source / path.name)
    write(output / "prepare-claim.json", {"owner": owner, "selection": selection_ref})
    calls = 0

    def forbidden(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("Native data preparation forbids neural Module calls")

    torch.nn.Module._call_impl = forbidden
    python_rng, numpy_rng, torch_rng = random.getstate(), np.random.get_state(), torch.get_rng_state()
    try:
        for item in [spec["source_quarantine"], spec["source_review"], *spec["evidence"]]:
            checked(item)
        (output / "targets").mkdir()
        (output / "observations").mkdir()
        rows, observations = [], []
        protocol = spec["noise_protocol"]
        if (protocol["bit_depth"] != 16 or protocol["black_level"] != .03
                or len(protocol["patterns"]) != 4 or len(protocol["conditions"]) != 3):
            raise ValueError("Unexpected declared noise protocol")
        assert len(spec["rows"]) == spec["ROI_count"] == 20
        assert len({r["scene_group"] for r in spec["rows"]}) == spec["source_groups"] == 11
        for row in spec["rows"]:
            identity = row["case_id"]
            if (not re.fullmatch(r"[A-Za-z0-9_-]+", identity)
                    or row["split"] != "development" or row["source"]["license"] != "CC0-1.0"):
                raise ValueError("Invalid development source identity or rights")
            arrays = {}
            for factor in (4, 8):
                item = row[f"bin{factor}"]
                if binding(item["path"])["sha256"] != item["sha256"]:
                    raise ValueError("Source camera cache changed")
                arrays[factor] = np.load(item["path"], allow_pickle=False)
                assert arrays[factor].dtype == np.uint16 and list(arrays[factor].shape) == item["shape"]
            x, y, width, height = row["xywh"]
            assert width == height == 256
            pixels = arrays[8][y:y+height, x:x+width].copy()
            assert pixels.shape == (256, 256, 3)
            guard = spec["bin4_guard"]
            offset = spec["bin8_to_bin4_offset"]
            x0, y0 = 2*x+offset-guard, 2*y+offset-guard
            x1, y1 = 2*(x+width)+offset+guard, 2*(y+height)+offset+guard
            assert x0 >= 0 and y0 >= 0 and x1 <= arrays[4].shape[1] and y1 <= arrays[4].shape[0]
            assert int(arrays[4][y0:y1, x0:x1].max()) < spec["bin4_clip_threshold"]
            integer_path = output / "targets" / (identity + "-uint16.npy")
            with integer_path.open("xb") as stream:
                np.save(stream, pixels, allow_pickle=False)
            clean = torch.from_numpy(pixels.astype(np.float32)).permute(2, 0, 1)[None] / 65535
            camera_path = output / "targets" / (identity + "-camera-FP32.npy")
            with camera_path.open("xb") as stream:
                np.save(stream, clean.contiguous().numpy(), allow_pickle=False)
            wb = torch.tensor(row["raw_metadata"]["white_balance"], dtype=torch.float32)[None]
            matrix = torch.tensor(row["raw_metadata"]["camera_to_srgb"], dtype=torch.float32)[None]
            assert torch.isfinite(matrix).all() and torch.isfinite(wb).all() and (wb > 0).all()
            assert torch.linalg.det(matrix).abs().min() > 1e-6
            target_record = {**row, "cache": str(integer_path), "cache_sha256": binding(integer_path)["sha256"],
                             "reference_uint16": binding(integer_path), "reference_camera_FP32": binding(camera_path),
                             "reference_fingerprint": fingerprint(clean), "color_space": "linear-camera-RGB",
                             "target_role": spec["target_role"], "shape": [256, 256, 3], "dtype": "uint16",
                             "bin_factor": 8, "no_resize_or_geometry": True,
                             "guarded_bin4_maximum_code": int(arrays[4][y0:y1, x0:x1].max())}
            rows.append(target_record)
            for condition in protocol["conditions"]:
                shot, read = float(condition["shot"]), float(condition["read"])
                assert condition["exposure"] == 1.0
                for pattern in protocol["patterns"]:
                    colors = color_indices(pattern)[None]
                    sampled = mosaic(clean, colors)
                    manual = np.stack([pixels[i//2::2, i%2::2, color].astype(np.float32)/65535
                                       for i, color in enumerate(PATTERNS[pattern])])[None]
                    assert np.array_equal(sampled.numpy(), manual)
                    key = f"{protocol['seed']}:{identity}:{condition['name']}:{pattern}"
                    seed = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "little") % 2**63
                    generator = torch.Generator(device="cpu").manual_seed(seed)
                    noisy = add_noise(sampled, shot, read, bit_depth=16, black_level=.03, generator=generator)
                    variance = variance_map(noisy, shot, read)
                    values = {"packed": noisy, "variance": variance, "colors": colors, "wb": wb, "matrix": matrix}
                    assert all(torch.isfinite(v).all() for v in values.values())
                    assert noisy.shape == variance.shape == (1, 4, 128, 128) and (variance >= 0).all()
                    if shot == read == 0:
                        assert float((noisy-sampled).abs().max()) <= 1/(2*65535*.97)+1e-7
                    name = f"{identity}-{condition['name']}-{pattern}"
                    path = output / "observations" / (name + ".npz")
                    with path.open("xb") as stream:
                        np.savez(stream, **{k:v.contiguous().numpy() for k,v in values.items()})
                    observations.append({"id": name, "case_id": identity, "source_id": row["source_id"],
                         "scene_group": row["scene_group"], "source_file_id": row["file_id"],
                         "condition": condition, "pattern": pattern, "seed": seed, "black_level": .03,
                         "arrays": binding(path), "input_fingerprints": {k:fingerprint(v) for k,v in values.items()},
                         "reference_camera_FP32": binding(camera_path), "score_ROI_xywh": spec["score_ROI_xywh"],
                         "target_role": spec["target_role"]})
            print({"case": identity, "observations": len(observations), "new_neural_forwards": calls}, flush=True)
            assert psutil.virtual_memory().available >= 32 * 2**30
        assert len(observations) == spec["planned_shared_observations"] == 240
        assert len({r["id"] for r in observations}) == 240
        manifest = {"format_version": 1, "split": "development", "usage": spec["usage"],
                    "selection": selection_ref, "target_role": spec["target_role"], "noise_protocol": protocol,
                    "rows": rows, "observations": observations,
                    "score_ROI_xywh": spec["score_ROI_xywh"], "scope": spec["scope"]}
        write(output / "manifest.json", manifest)
        from demosaic.raw_clean import RawCleanDataset
        try:
            RawCleanDataset(output / "manifest.json")
        except ValueError as error:
            assert str(error) == "Native RAW targets require a train manifest"
        else:
            raise AssertionError("Held-out development manifest entered the training loader")
        assert random.getstate() == python_rng and torch.equal(torch.get_rng_state(), torch_rng)
        after = np.random.get_state()
        assert after[0] == numpy_rng[0] and np.array_equal(after[1], numpy_rng[1]) and after[2:] == numpy_rng[2:]
        assert not torch.cuda.is_initialized() and calls == 0 and binding(selection) == selection_ref
        result = {"status": "completed-native-development-inputs-no-model-evaluation",
                  "recorded_local": datetime.datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(),
                  "owner": owner, "selection": selection_ref, "manifest": binding(output / "manifest.json"),
                  "driver": binding(source / Path(__file__).name),
                  "source_files": [binding(p) for p in sorted(source.glob("*.py"))],
                  "source_groups": 11, "native256_targets": 20, "physical_noise_observations": 240,
                  "noise_draws_once_then_shared_by_all_future_methods": True,
                  "mosaic_phase_sampling_independently_exact_to_source_uint16_codes": True,
                  "native_uint16_target_pixels_copied_without_resize": True,
                  "training_loader_rejects_development_manifest": True,
                  "global_Python_NumPy_Torch_RNG_unchanged": True, "CUDA_initialized": False,
                  "new_neural_forwards": calls, "optimizer_updates": 0, "RAW_decodes": 0,
                  "quality_claim": None, "scope": spec["scope"]}
        write(output / "result-v1.json", result)
        print({"status": result["status"], "targets": 20, "observations": 240,
               "new_neural_forwards": calls}, flush=True)
        return output / "result-v1.json"
    except BaseException as error:
        write(output / "failure-v1.json", {"owner": owner, "selection": selection_ref,
              "error": repr(error), "new_neural_forwards": calls, "scope": "Preserve actual preparation without automatic retry."})
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("selection", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    prepare(arguments.selection, arguments.output)
