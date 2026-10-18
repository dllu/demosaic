"""Isolated publisher-default JDD reference on six existing photo/GFX observations."""

import argparse
import ast
import hashlib
import json
import math
import os
import shutil
import sys
from pathlib import Path

import numpy as np
import psutil
import torch
import yaml
from probe_rawforge_cpu import cases

from demosaic.cfa import malvar
from demosaic.metrics import quality_metrics
from demosaic.reporting import display_crop, save_triplet

BASE = Path("/mnt/external/demosaic")
REPO = Path("/home/dllu/proj/demosaic")
PUB = BASE / "references/unified-demosaicing/native-CPU-preparation-v1"
ROOT = BASE / "benchmarks/unified-ISO3200-CPU-pilot-v1"
OUTPUT = BASE / "evaluation/unified-ISO3200-native-CPU-pilot-v1"
WHITE = 13496


def read(path):
    return json.loads(Path(path).read_text())


def ref(path):
    with Path(path).open("rb") as stream:
        sha = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(Path(path).resolve()), "sha256": sha}


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def guard(plan):
    for path, digest in {**plan["inputs"], **plan["guards"]}.items():
        assert ref(path)["sha256"] == digest, path


def from_codes(raw):
    assert raw.ndim == 4 and raw.shape[:2] == (1, 1)
    height, width = raw.shape[-2:]
    assert height % 2 == width % 2 == 0
    colors = torch.tensor([[0, 1], [1, 2]]).repeat(height // 2, width // 2)
    masks = torch.nn.functional.one_hot(colors, 3).permute(2, 0, 1)[None].float() * WHITE
    four = (torch.cat([raw.float(), masks], 1) / WHITE - 0.5) / 0.5
    return torch.cat([four, four, four], 1)


def frontend(packed):
    raw = torch.nn.functional.pixel_shuffle(packed, 2)
    # Explicit nominal-unit transfer into the publisher's integer input range.
    codes = (raw.double() * WHITE).clamp(0, WHITE).floor().float()
    return from_codes(codes), {
        "below_zero_samples_clipped": int((raw < 0).sum()),
        "above_one_samples_clipped": int((raw > 1).sum()),
        "input_code_range": [int(codes.min()), int(codes.max())],
    }


def publisher_functions():
    utilities = PUB / "PyTorch/utilities/utils.py"
    wanted = {"build_pattern", "construct_mosaic", "output_rescaling_quantization"}
    selected = [
        n
        for n in ast.parse(utilities.read_text()).body
        if isinstance(n, ast.FunctionDef) and n.name in wanted
    ]
    dataset = PUB / "PyTorch/utilities/dataset.py"
    cls = next(
        n
        for n in ast.parse(dataset.read_text()).body
        if isinstance(n, ast.ClassDef) and n.name == "BasicDataset"
    )
    preprocess = next(
        n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "preprocess"
    )
    preprocess.decorator_list = []
    scope = {"torch": torch, "np": np}
    # Execute only reviewed, pinned pure tensor helpers, avoiding the upstream
    # utility module's DNG decode, wandb and filesystem initialization.
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(utilities), "exec"), scope)  # noqa: S102
    exec(compile(ast.Module(body=[preprocess], type_ignores=[]), str(dataset), "exec"), scope)  # noqa: S102
    return scope


def validate_contract():
    functions = publisher_functions()
    generator = torch.Generator().manual_seed(20261018)
    rgb = torch.randint(0, WHITE + 1, (48, 48, 3), generator=generator).float()
    pattern, raw = functions["construct_mosaic"](rgb, order="RGGB", filter_size=1)
    labels = pattern[..., 0]
    code4 = torch.cat([raw[..., None], torch.nn.functional.one_hot(labels, 3).float() * WHITE], 2)
    expected = functions["preprocess"](
        None, code4.repeat(1, 1, 3), -1, (-1, -1), False, "single_quad_nona"
    )[None]
    assert torch.equal(from_codes(raw[None, None]), expected)
    # Include both tails and endpoints in a separate float64 quantization oracle.
    nominal = np.array([-0.1, 0, 0.01, 0.5, 1, 1.1, 0.25, 0.9], dtype=np.float32).reshape(
        1, 4, 1, 2
    )
    generated, _ = frontend(torch.from_numpy(nominal))
    raw_numpy = np.empty((2, 4), dtype=np.float32)
    for i in range(4):
        raw_numpy[i // 2 :: 2, i % 2 :: 2] = nominal[0, i]
    codes = np.clip(raw_numpy.astype(np.float64) * WHITE, 0, WHITE).astype(np.uint16)
    oracle = from_codes(torch.from_numpy(codes.astype(np.float32))[None, None])
    assert torch.equal(generated, oracle)
    return {
        "publisher_mosaic_mask_and_normalization_exact": True,
        "independent_quantization_endpoint_fixture_exact": True,
        "helpers": [ref(PUB / "PyTorch/utilities" / name) for name in ["utils.py", "dataset.py"]],
    }


def prepare():
    assert not ROOT.exists() and not OUTPUT.exists()
    assert not torch.cuda.is_initialized()
    compatible = read(PUB / "CPU-preflight.json")
    official = yaml.safe_load((PUB / "configs/unified_test.yaml").read_text())
    assert official["load"] == "PyTorch/models/iso3200.pth" and official["model"] == "simp_multi"
    selected = next(
        a for a in compatible["arms"] if Path(a["checkpoint"]["path"]).name == "iso3200.pth"
    )
    assert selected["state_tensors_exactly_matched"] == 336
    checked = validate_contract()
    prepared = cases()
    inputs = [
        PUB / "CPU-preflight.json",
        PUB / "configs/unified_test.yaml",
        Path(selected["checkpoint"]["path"]),
        REPO / "docs/results/nonlocal-matchfilter-cpu-probe.json",
    ]
    for case in prepared:
        assert case["pattern"] == "RGGB"
        inputs.append(Path(case["observation"]))
        assert ref(case["observation"])["sha256"] == case["observation_sha256"]
        if "reference_array" in case:
            inputs.append(Path(case["reference_array"]))
            assert ref(case["reference_array"])["sha256"] == case["reference_array_sha256"]
        crop = (
            case["source"]["source_crop"]
            if case["kind"] == "synthetic-photo"
            else case["original_crop_receipt"]
        )
        control = Path(case["observation"]).parent / crop["image"]
        assert ref(control)["sha256"] == crop["png_sha256"]
        case["unchanged_V43_triplet"] = ref(control)
        inputs.append(control)
    ROOT.mkdir()
    work, tools = ROOT / "work", ROOT / "tools"
    (work / "src").mkdir(parents=True)
    shutil.copytree(
        REPO / "src/demosaic", work / "src/demosaic", ignore=shutil.ignore_patterns("__pycache__")
    )
    tools.mkdir()
    for name in ["probe_rawforge_cpu.py", "audit_colored_flats.py"]:
        shutil.copyfile(REPO / "scripts" / name, tools / name)
    shutil.copyfile(__file__, ROOT / "driver.py")
    source = {str(p): ref(p)["sha256"] for p in (PUB / "PyTorch").rglob("*.py")}
    plan = {
        "publisher_commit": compatible["commit"],
        "publisher_root": str(PUB),
        "official_test_config": ref(PUB / "configs/unified_test.yaml"),
        "checkpoint": selected["checkpoint"],
        "preparation": ref(PUB / "CPU-preflight.json"),
        "contract_preflight": checked,
        "cases": prepared,
        "output": str(OUTPUT),
        "work": str(work),
        "tools": str(tools),
        "inputs": {str(p): ref(p)["sha256"] for p in inputs},
        "guards": {**source, **{str(p): ref(p)["sha256"] for p in ROOT.rglob("*") if p.is_file()}},
        "scope": "Fixed publisher-default ISO3200 checkpoint, chosen by official test YAML before any photo outputs. Original full12-channel/three-output forward, retaining RGGB output; other slots repeat the same input. All six observations are RGGB, no geometry or CFA permutation. Nominal black-subtracted RAW0..1 maps to clipped/truncated integer0..13496, then original mosaic+RGB-mask normalization; original output clipping/uint16 truncation and divide13496 return nominal linear RGB. Fixed publisher ISO profile has no per-input shot/read conditioning; its calibration need not match synthetic ISO12800/GFX ISO6400. CPU FP32/two threads/low priority, no GPU/speed/broad ranking or production/training incorporation. Source remains under its published noncommercial terms in isolated reference cache. Native160px triplets, fixed display exposure1/4 and WB/matrix; real ISO100 independently demosaiced reference is not GT/no pixelwise score. Two photo scores separately on160 and240px ROIs; no source bootstrap or model selection. Numerical/native review required before a quality conclusion.",
    }
    save(ROOT / "plan.json", plan)
    guard(plan)
    print(
        json.dumps(
            {
                "plan": ref(ROOT / "plan.json"),
                "contract_checked": True,
                "inputs": len(plan["inputs"]),
                "guards": len(plan["guards"]),
            }
        ),
        flush=True,
    )


def model_hash(model):
    digest = hashlib.sha256()
    for name, value in model.state_dict().items():
        digest.update(name.encode() + value.detach().contiguous().numpy().tobytes())
    return digest.hexdigest()


@torch.inference_mode()
def run():
    assert not OUTPUT.exists() and not torch.cuda.is_initialized() and not torch.cuda.is_available()
    os.nice(10)
    torch.set_num_threads(2)
    plan = read(ROOT / "plan.json")
    guard(plan)
    OUTPUT.mkdir()
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    save(
        ROOT / "status.json",
        {
            "status": "running-isolated-CPU-reference",
            "owner": owner,
            "plan": ref(ROOT / "plan.json"),
        },
    )
    sys.path.insert(0, str(PUB / "PyTorch"))
    from arch.simple_multi_head_jd_model import SIMP_MULTI_JD

    model = SIMP_MULTI_JD().eval()
    state = torch.load(plan["checkpoint"]["path"], map_location="cpu", weights_only=True)[
        "net_state_dict"
    ]
    keys = {k.removeprefix("module."): v for k, v in state.items()}
    assert keys.keys() == model.state_dict().keys() and len(keys) == 336
    model.load_state_dict(keys, strict=True)
    assert all(torch.equal(v, keys[k]) for k, v in model.state_dict().items())
    del state, keys
    before, rng = model_hash(model), torch.get_rng_state().clone()
    functions = publisher_functions()
    results, arrays, crops = [], [], []
    for case in plan["cases"]:
        assert psutil.virtual_memory().available > 32 * 2**30
        guard(plan)
        if case["kind"] == "synthetic-photo":
            with np.load(case["observation"], allow_pickle=False) as data:
                b = {k: torch.from_numpy(data[k].copy()) for k in data.files}
            target, wb, matrix = b["target"], b["wb"], b["matrix"]
        else:
            b = {
                "packed": torch.from_numpy(np.load(case["observation"], allow_pickle=False)),
                "colors": torch.tensor([[0, 1, 1, 2]]),
            }
            target = torch.from_numpy(np.load(case["reference_array"], allow_pickle=False))
            wb = torch.tensor(case["wb"], dtype=torch.float32).reshape(1, 3)
            matrix = torch.tensor(case["matrix"], dtype=torch.float32).reshape(1, 3, 3)
        values, input_stats = frontend(b["packed"])
        original = values.clone()
        outputs = model(values)
        assert len(outputs) == 3
        assert all(
            v.shape == (1, 3, *values.shape[-2:]) and torch.isfinite(v).all() for v in outputs
        )
        raw_output = outputs[0]
        if not results:
            assert all(torch.equal(a, b) for a, b in zip(outputs, model(values), strict=True))
        codes = functions["output_rescaling_quantization"](raw_output)
        restored = codes.float() / WHITE
        files = {}
        for name, value in [
            ("input12-f32", values),
            ("raw-network-f32", raw_output),
            ("publisher-codes-u16", codes.to(torch.uint16)),
            ("linear-RGB-f32", restored),
        ]:
            path = OUTPUT / (case["id"] + "-" + name + ".npy")
            np.save(path, value.numpy(), allow_pickle=False)
            files[name] = {
                **ref(path),
                "shape": list(value.shape),
                "dtype": str(value.numpy().dtype),
            }
        arrays.append({"case": case["id"], "files": files})
        assert torch.equal(values, original) and model_hash(model) == before
        assert torch.equal(torch.get_rng_state(), rng)
        scores = {}
        if case["kind"] == "synthetic-photo":
            for label, roi in [
                ("native160", case["roi_xywh"]),
                ("border8-context240", [8, 8, 240, 240]),
            ]:
                x, y, w, h = roi
                scores[label] = {
                    k: float(v[0]) if math.isfinite(float(v[0])) else None
                    for k, v in quality_metrics(
                        restored[..., y : y + h, x : x + w],
                        target[..., y : y + h, x : x + w],
                        wb,
                        matrix,
                    ).items()
                }
        roi = case["roi_xywh"]
        target_roi = roi if case["kind"] == "synthetic-photo" else [0, 0, 160, 160]
        noisy = malvar(b["packed"], b["colors"], wb)
        crops.append(
            save_triplet(
                OUTPUT,
                "Samsung-ISO3200:" + case["id"],
                [
                    (
                        label,
                        display_crop(value, wb, matrix, region, exposure=case["display_exposure"]),
                    )
                    for label, value, region in [
                        ("Noisy (Malvar)", noisy, roi),
                        ("Publisher ISO3200", restored, roi),
                        (
                            "GT (synthetic)"
                            if case["kind"] == "synthetic-photo"
                            else "ISO100 ref (not GT)",
                            target,
                            target_roi,
                        ),
                    ]
                ],
                caption="Publisher default ISO3200 / " + case["id"],
                metadata={
                    "case": case,
                    "checkpoint": plan["checkpoint"],
                    "ROI_xywh": roi,
                    "white_balance": wb.tolist(),
                    "camera_to_srgb": matrix.tolist(),
                    "display_exposure": case["display_exposure"],
                    "reference": case["reference"],
                    "conditioning": "Fixed publisher ISO3200 checkpoint; no supplied noise map/ISO/shot/read input. Test observation metadata retained separately.",
                    "compute_precision": "Original CPU float32 model; publisher integer13496-code input/output transfer",
                    "display_encoding": "8-bit sRGB preview; scores use publisher13496-code RGB normalized to float32",
                    "input_transfer_statistics": input_stats,
                },
            )
        )
        results.append(
            {"case": case["id"], "scores": scores, "input_transfer_statistics": input_stats}
        )
        save(
            ROOT / "status.json",
            {
                "status": "running-isolated-CPU-reference",
                "owner": owner,
                "plan": ref(ROOT / "plan.json"),
                "completed_cases": [r["case"] for r in results],
            },
        )
        print(json.dumps({"case": case["id"], "completed": True}), flush=True)
        del outputs, raw_output, values, original, restored, codes
    guard(plan)
    assert len(results) == len(arrays) == len(crops) == 6 and not torch.cuda.is_initialized()
    report = {
        "status": "completed-isolated-ISO3200-CPU-reference-awaiting-numerical-and-native-review",
        "plan": ref(ROOT / "plan.json"),
        "owner": owner,
        "checkpoint": plan["checkpoint"],
        "results": results,
        "arrays": arrays,
        "native_crops": crops,
        "model_and_input_and_RNG_unchanged": True,
        "model_state_sha256": before,
        "CUDA_initialized": False,
        "scope": plan["scope"],
    }
    save(OUTPUT / "report.json", report)
    save(
        ROOT / "status.json",
        {"status": report["status"], "owner": owner, "report": ref(OUTPUT / "report.json")},
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "run"])
    args = parser.parse_args()
    prepare() if args.mode == "prepare" else run()
