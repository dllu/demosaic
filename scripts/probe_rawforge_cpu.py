"""Fixed signed RawForge JDD CPU-port pilot on saved photo/GFX observations."""

import argparse
import ast
import json
import math
from pathlib import Path

import numpy as np
import torch
from audit_colored_flats import sha

from demosaic.cfa import PATTERNS, color_indices, malvar
from demosaic.metrics import quality_metrics
from demosaic.reporting import display_crop, save_triplet
from demosaic.safety import writable_path

REPO = Path("/home/dllu/proj/demosaic")
GFX = Path("/mnt/external/demosaic/evaluation/gfx-3879-3880-v43-none10k-cpu-contexts-v1")


def read(path):
    return json.loads(Path(path).read_text())


def six_channels(packed, pattern, black, white, adc_white, subtract_black):
    """Reconstruct integer ADC samples, then follow the publisher's sparse/mask path."""
    assert packed.dtype == np.float32 and packed.shape[0:2] == (1, 4)
    assert len(black) == len(white) == 4 and all(w == adc_white for w in white)
    assert all(0 <= b < w for b, w in zip(black, white))
    labels = np.array(PATTERNS[pattern]).reshape(2, 2)
    h, w = packed.shape[-2:]
    raw = np.empty((h * 2, w * 2), dtype=np.float64)
    for phase in range(4):
        b, top = black[phase], white[phase]
        dn = np.rint(packed[0, phase].astype(np.float64) * (top - b) + b)
        assert dn.min() >= 0 and dn.max() <= 65535
        raw[phase // 2 :: 2, phase % 2 :: 2] = dn - b if subtract_black else dn
    mask = np.tile(labels, (h, w))[None] == np.arange(3)[:, None, None]
    sparse = raw[None] * mask / adc_white
    return (
        np.concatenate([np.clip(sparse, 0, 1), mask], axis=0)[None]
        .astype(np.float16)
        .astype(np.float32)
    )


def validate_publisher_sparse(root):
    """Compare all CFA layouts against the independently packaged upstream helper."""
    path = root / "RawHandler-0.2.2/RawHandler/utils.py"
    function = next(
        n
        for n in ast.parse(path.read_text()).body
        if isinstance(n, ast.FunctionDef) and n.name == "sparse_representation_and_mask"
    )
    namespace = {"np": np}
    # Compile only the reviewed sparse/mask function from the pinned wheel.
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), "exec"), namespace)  # noqa: S102
    upstream = namespace[function.name]
    checked = 0
    # Include below-black samples and both ADC endpoints. Neither tensors nor
    # source RAW files are modified.
    dn = np.arange(16 * 20, dtype=np.float64).reshape(16, 20) * 200
    dn[-1, -1] = 65535
    black = [4101.0, 4098.0, 4104.0, 4106.0]
    white = [65535.0] * 4
    for pattern, colors in PATTERNS.items():
        packed = np.stack(
            [
                (dn[y::2, x::2] - black[2 * y + x]) / (65535 - black[2 * y + x])
                for y in range(2)
                for x in range(2)
            ]
        )[None].astype(np.float32)
        for subtract in [False, True]:
            raw = dn.copy()
            if subtract:
                for phase in range(4):
                    raw[phase // 2 :: 2, phase % 2 :: 2] -= black[phase]
            sparse, mask = upstream(raw, np.array(colors).reshape(2, 2).copy())
            expected = (
                np.concatenate([np.clip(sparse / 65535, 0, 1), mask], axis=0)[None]
                .astype(np.float16)
                .astype(np.float32)
            )
            np.testing.assert_array_equal(
                six_channels(packed, pattern, black, white, 65535.0, subtract), expected
            )
            checked += 1
    return {
        "helper": str(path),
        "helper_sha256": sha(path),
        "all4CFAs_both_black_policies_match_publisher_F16_inputs_exactly": checked,
    }


def cases():
    old = read(REPO / "docs/results/nonlocal-matchfilter-cpu-probe.json")
    result = []
    for i, source in enumerate(old["probe_plan"]["sources"]):
        result.append(
            {
                "id": "photo-" + str(i),
                "kind": "synthetic-photo",
                "source": source,
                "observation": source["path"],
                "observation_sha256": source["sha256"],
                "pattern": source["source_crop"]["pattern"],
                "roi_xywh": [48, 48, 160, 160],
                "black": [65535 * 0.03] * 4,
                "white": [65535.0] * 4,
                "adc_white": 65535.0,
                "display_exposure": 1.0,
                "reference": "Exact simulated clean target from a binned Commons photo. CPU-generated observation, distinct from full427 CUDA draws.",
            }
        )
    gfx = read(GFX / "report.json")
    metadata = next(s["metadata"] for s in gfx["sources"] if s["role"] == "noisy")
    for noisy in gfx["float_contexts"]:
        if noisy["role"] != "noisy-packed":
            continue
        name = noisy["region"]["name"]
        ref = next(
            r
            for r in gfx["float_contexts"]
            if r["role"] == "reference-rgb" and r["region"] == noisy["region"]
        )
        crop = next(c for c in gfx["native_crops"] if c["region"] == noisy["region"])
        result.append(
            {
                "id": "gfx-" + name,
                "kind": "real-GFX-context",
                "source": noisy,
                "observation": str(GFX / noisy["image"]),
                "observation_sha256": noisy["sha256"],
                "pattern": noisy["pattern"],
                "roi_xywh": [176, 176, 160, 160],
                "black": metadata["black_levels"],
                "white": metadata["white_levels"],
                "adc_white": metadata["adc_white_level"],
                "display_exposure": 4.0,
                "reference": "DSCF3880 ISO100 f/5.6, independently AHD demosaiced; not GT, no pixelwise score.",
                "reference_array": str(GFX / ref["image"]),
                "reference_array_sha256": ref["sha256"],
                "wb": crop["shared_wb"],
                "matrix": crop["shared_matrix"],
                "original_crop_receipt": crop,
            }
        )
    assert len(result) == 6
    return result


@torch.inference_mode()
def main(root, inspection, output):
    assert not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    output = writable_path(output)
    if output.exists():
        raise ValueError("RawForge pilot exists; choose a new output")
    reviewed = read(inspection)
    assert (
        reviewed["status"]
        == "completed-signed-RAWForge-JDD-export-inspection-and-explicit-CPU-port"
    )
    checked = validate_publisher_sparse(root)
    prepared = cases()
    for c in prepared:
        assert sha(c["observation"]) == c["observation_sha256"]
        if "reference_array" in c:
            assert sha(c["reference_array"]) == c["reference_array_sha256"]
    output.mkdir(parents=True, exist_ok=False)
    (output / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    plan = {
        "models": reviewed["models"],
        "inspection": str(inspection),
        "inspection_sha256": sha(inspection),
        "cases": prepared,
        "preprocessing_fixture": checked,
        "driver_sha256": sha(__file__),
        "physical_units": "Restore integer16 ADC from known per-phase levels; apply publisher per-phase black subtraction only for JDD256, sparse RGB+mask, clip, F16-round then expand to F32. Output publisher clipping then metadata-only nominal-white conversion; JDD uses publisher mean-black subtraction. Nonuniform real phase blacks use the publisher global mean convention, not a fitted per-color correction.",
        "execution": "CPU F32 with the explicitly device-only port. Blind models: supplied protocol shot/read describe observations but are not network conditioning. Photo256px; GFX512px contexts. Native160px ROI. No original RAW decode, new noise draw, output fitting or model training; no GPU parity or serving-speed claim.",
    }
    (output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    results, arrays, crops = [], [], []
    for record in reviewed["models"]:
        assert sha(record["CPU_port"]) == record["CPU_port_sha256"]
        network = torch.jit.load(record["CPU_port"], map_location="cpu").eval()
        subtract = record["registry"]["subtract_bl"]
        for case in prepared:
            if case["kind"] == "synthetic-photo":
                with np.load(case["observation"], allow_pickle=False) as data:
                    b = {k: torch.from_numpy(data[k].copy()) for k in data.files}
                target, wb, matrix = b["target"], b["wb"], b["matrix"]
            else:
                b = {
                    "packed": torch.from_numpy(np.load(case["observation"], allow_pickle=False)),
                    "colors": color_indices(case["pattern"])[None],
                }
                target = torch.from_numpy(np.load(case["reference_array"], allow_pickle=False))
                wb = torch.tensor(case["wb"], dtype=torch.float32).reshape(1, 3)
                matrix = torch.tensor(case["matrix"], dtype=torch.float32).reshape(1, 3, 3)
            x = torch.from_numpy(
                six_channels(
                    b["packed"].numpy(),
                    case["pattern"],
                    case["black"],
                    case["white"],
                    case["adc_white"],
                    subtract,
                )
            )
            y = network(x)
            assert (
                y.shape == (1, 3, *x.shape[-2:])
                and y.dtype == torch.float32
                and torch.isfinite(y).all()
            )
            mean_black = float(np.mean(case["black"])) / case["adc_white"]
            p = (y.clamp(0, 1) - (0 if subtract else mean_black)) / (1 - mean_black)
            files = {}
            for label, tensor in [
                ("input-six-f32", x),
                ("raw-network-f32", y),
                ("normalized-RGB-f32", p),
            ]:
                path = output / (record["name"] + "-" + case["id"] + "-" + label + ".npy")
                np.save(path, tensor.numpy(), allow_pickle=False)
                files[label] = {
                    "path": str(path),
                    "sha256": sha(path),
                    "shape": list(tensor.shape),
                    "dtype": "float32",
                }
            arrays.append({"model": record["name"], "case": case["id"], "files": files})
            roi = case["roi_xywh"]
            noisy = malvar(b["packed"], b["colors"], wb)
            exact = case["kind"] == "synthetic-photo"
            target_roi = roi if exact else [0, 0, 160, 160]
            scores = None
            if exact:
                x0, y0, w, h = roi
                scores = {
                    k: (float(v[0]) if math.isfinite(float(v[0])) else None)
                    for k, v in quality_metrics(
                        p[..., y0 : y0 + h, x0 : x0 + w],
                        target[..., y0 : y0 + h, x0 : x0 + w],
                        wb,
                        matrix,
                    ).items()
                }
            results.append({"model": record["name"], "case": case["id"], "metrics": scores})
            crops.append(
                save_triplet(
                    output,
                    record["name"] + ":" + case["id"],
                    [
                        (
                            label,
                            display_crop(
                                rgb, wb, matrix, region, exposure=case["display_exposure"]
                            ),
                        )
                        for label, rgb, region in [
                            ("Noisy (Malvar)", noisy, roi),
                            ("RawForge / CPU port", p, roi),
                            (
                                "GT (synthetic)" if exact else "ISO100 ref (not GT)",
                                target,
                                target_roi,
                            ),
                        ]
                    ],
                    caption=record["name"] + " / " + case["id"],
                    metadata={
                        "case": case,
                        "model": {
                            k: record[k]
                            for k in [
                                "name",
                                "original",
                                "original_sha256",
                                "CPU_port",
                                "CPU_port_sha256",
                            ]
                        },
                        "ROI_xywh": roi,
                        "white_balance": wb.tolist(),
                        "camera_to_srgb": matrix.tolist(),
                        "display_exposure": case["display_exposure"],
                        "reference": case["reference"],
                        "conditioning": "Blind: no noise/ISO input per publisher registry",
                        "compute_precision": "CPU F32; F16-rounded six-channel input; positional Device constant ported explicitly; GPU parity pending",
                    },
                )
            )
            print(
                json.dumps({"model": record["name"], "case": case["id"], "completed": True}),
                flush=True,
            )
        del network
    assert len(results) == len(arrays) == len(crops) == 12 and not torch.cuda.is_initialized()
    report = {
        "status": "completed-small-RawForge-CPU-port-pilot-awaiting-numerical-and-native-review",
        "plan": str(output / "plan.json"),
        "plan_sha256": sha(output / "plan.json"),
        "results": results,
        "arrays": arrays,
        "native_crops": crops,
        "CUDA_initialized": False,
        "limitations": "Two fixed synthetic photo observations and four standing GFX contexts, not a full benchmark or a model's registered768px serving run. Explicit CPU device port and F16-rounded/F32 arithmetic; original-CUDA parity remains pending. Reference training membership and separate weight license unspecified. GFX ISO100 is a qualitative reference, not GT. No promotion/SOTA/broad superiority/speed claim.",
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--inspection", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    main(a.root, a.inspection, a.output)
