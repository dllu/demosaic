"""Freeze a prospective linear-RGB uniform-field grid on CPU, without inference."""

import argparse
import colorsys
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import psutil
import torch
import yaml

from demosaic.safety import writable_path
from demosaic.suite import observation

SUITE = "linear-RGB-flat-grid-v1"
LEVELS = [0.02, 0.18, 0.9]
SATURATIONS = [0.5, 0.98]
PATTERNS = ["RGGB", "BGGR", "GRBG", "GBRG"]
CONDITIONS = ["adc-only", "iso12800-prior"]
COEFFICIENTS = {"adc-only": (0.0, 0.0), "iso12800-prior": (0.00256, 0.0000262144)}


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def palette():
    colors = []
    for level in LEVELS:
        colors.append(
            {
                "id": f"gray-l{level:.2f}",
                "hue_degrees": None,
                "saturation": 0.0,
                "peak": level,
                "linear_srgb": [level] * 3,
            }
        )
        for saturation in SATURATIONS:
            for degrees in range(0, 360, 15):
                colors.append(
                    {
                        "id": f"h{degrees:03d}-s{saturation:.2f}-l{level:.2f}",
                        "hue_degrees": degrees,
                        "saturation": saturation,
                        "peak": level,
                        "linear_srgb": list(colorsys.hsv_to_rgb(degrees / 360, saturation, level)),
                    }
                )
    assert len(colors) == 147
    return colors


def validate(plan):
    assert (
        plan["suite"] == SUITE
        and plan["native_patch"] == 256
        and plan["roi_xywh"] == [48, 48, 160, 160]
    )
    expected = {
        (r["id"], condition, pattern)
        for r in palette()
        for condition in CONDITIONS
        for pattern in PATTERNS
    }
    actual = {(r["id"], r["condition"]["name"], r["pattern"]) for r in plan["cases"]}
    assert len(actual) == len(plan["cases"]) == 1176 and actual == expected
    colors = {r["id"]: r for r in palette()}
    for case in plan["cases"]:
        assert case["palette"] == case["id"] and case["source"] == colors[case["id"]]
        assert case["draws_per_pattern"] == 1 and case["condition"]["exposure"] == 1
        assert (case["condition"]["shot"], case["condition"]["read"]) == COEFFICIENTS[
            case["condition"]["name"]
        ]
    assert plan["adc_bits"] == 16 and plan["adc_black"] == 0.03
    assert len(set(plan["native_preview_cases"])) == 3
    for i in plan["native_preview_cases"]:
        case = plan["cases"][i]
        assert case["pattern"] == "RGGB" and case["condition"]["name"] == "iso12800-prior"
    assert {plan["cases"][i]["id"] for i in plan["native_preview_cases"]} == {
        "h030-s0.98-l0.90",
        "h315-s0.98-l0.90",
        "gray-l0.18",
    }


def prior_snapshot(workflow):
    if workflow is None:
        return None
    data = json.loads(Path(workflow).read_text())
    owner = data["controller"]
    p = psutil.Process(owner["pid"])
    assert abs(p.create_time() - owner["created"]) < 0.01 and p.status() != psutil.STATUS_ZOMBIE
    assert data["status"] in [
        "training-control-to1000",
        "trained-control-1000",
        "training-wide-to1000",
        "trained-wide-1000",
        "both1000-observations-checked",
    ]
    assert all(
        not (Path(p) / name).exists()
        for p in data["outputs"].values()
        for name in ["summary.json", "report.json"]
    )
    return {
        "path": str(workflow),
        "sha256": sha(workflow),
        "snapshot": data,
        "no_training_trial_score_outputs_exist": True,
    }


@torch.inference_mode()
def main(output, workflow):
    os.nice(5)
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    before = prior_snapshot(workflow)
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    archive = output / "source"
    archive.mkdir()
    sources = {str(p): sha(p) for p in Path("src/demosaic").glob("*.py")}
    for p in [*Path("src/demosaic").glob("*.py"), Path(__file__), Path("configs/evaluation.yaml")]:
        (archive / p.name).write_bytes(p.read_bytes())
    protocol = yaml.safe_load(Path("configs/evaluation.yaml").read_text())
    conditions = [
        next(c for c in protocol["conditions"] if c["name"] == name) for name in CONDITIONS
    ]
    seed = 20261017
    cases = []
    previews = []
    for source in palette():
        rgb = (
            torch.tensor(source["linear_srgb"], dtype=torch.float32)[None, :, None, None]
            .expand(1, 3, 256, 256)
            .clone()
        )
        for condition in conditions:
            for pattern in PATTERNS:
                batch = observation(
                    rgb,
                    [source["id"]],
                    condition,
                    pattern,
                    protocol["white_balance"],
                    protocol["camera_to_srgb"],
                    seed,
                )
                assert batch["target"].shape == (1, 3, 256, 256) and batch["packed"].shape == (
                    1,
                    4,
                    128,
                    128,
                )
                assert float(batch["target"].min()) > 0 and float(batch["target"].max()) < 1
                assert all(torch.isfinite(v).all() for v in batch.values())
                assert torch.equal(
                    batch["target"], batch["target"][..., :1, :1].expand_as(batch["target"])
                )
                filename = source["id"] + "-" + condition["name"] + "-" + pattern + ".npz"
                path = output / filename
                np.savez_compressed(path, **{k: v.numpy() for k, v in batch.items()})
                record = {
                    "id": source["id"],
                    "palette": source["id"],
                    "source": source,
                    "condition": condition,
                    "pattern": pattern,
                    "arrays": str(path),
                    "sha256": sha(path),
                    "target_camera_RGB": batch["target"][0, :, 0, 0].tolist(),
                    "draws_per_pattern": 1,
                }
                if (
                    source["id"] in ["h030-s0.98-l0.90", "h315-s0.98-l0.90", "gray-l0.18"]
                    and condition["name"] == "iso12800-prior"
                    and pattern == "RGGB"
                ):
                    previews.append(len(cases))
                cases.append(record)
        if len(cases) % 96 == 0:
            print(json.dumps({"completed_observations": len(cases), "total": 1176}), flush=True)
    after = prior_snapshot(workflow)
    assert sources == {str(p): sha(p) for p in Path("src/demosaic").glob("*.py")}
    plan = {
        "suite": SUITE,
        "native_patch": 256,
        "roi_xywh": [48, 48, 160, 160],
        "white_balance": protocol["white_balance"],
        "camera_to_srgb": protocol["camera_to_srgb"],
        "seed": seed,
        "adc_bits": 16,
        "adc_black": 0.03,
        "protocol_sha256": sha("configs/evaluation.yaml"),
        "cases": cases,
        "native_preview_cases": previews,
        "source_files": sources,
        "driver_sha256": sha(__file__),
        "workflow_before": before,
        "workflow_after": after,
        "CUDA_initialized": False,
        "scope": "24 fixed scene-linear HSV hues at15degree intervals, saturation.5/.98, peak.02/.18/.9, plus3grays; two noise conditions and4CFAs, one draw/case. Fixed WB/camera, no clipping, original16bit ADC/black.03. Chosen after parent color failures but frozen before treatment scoring when workflow supplied; finite diagnostic grid, not a natural-photo ranking or independent training-repeat sample.",
    }
    validate(plan)
    assert not torch.cuda.is_initialized()
    (output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    print(
        json.dumps(
            {
                "plan": str(output / "plan.json"),
                "sha256": sha(output / "plan.json"),
                "observations": len(cases),
                "sources": 147,
                "bytes": sum(Path(c["arrays"]).stat().st_size for c in cases),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--before-workflow-scoring", type=Path)
    a = p.parse_args()
    main(a.output, a.before_workflow_scoring)
