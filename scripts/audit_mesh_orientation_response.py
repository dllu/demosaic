"""Independent spatial-projector audit of fixed native directional projections."""

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from lossless_native import load_native
from phase_admission_protocol import owner_live, read, ref

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261108/V194-orientation-response-v1"


def reference(value, target, empty, angles):
    h, w = target.shape[-2:]
    x, y = np.linspace(-1, 1, w)[None, :], np.linspace(-1, 1, h)[:, None]

    def residual(v):
        v = np.asarray(v, dtype=np.float64) - empty
        constant = v.mean((-2, -1), keepdims=True)
        bx = (v * x).sum((-2, -1), keepdims=True) / (h * np.sum(x * x))
        by = (v * y).sum((-2, -1), keepdims=True) / (w * np.sum(y * y))
        return v - constant - bx * x - by * y

    t, v = residual(target), residual(value)
    fy, fx = np.meshgrid(np.fft.fftfreq(h), np.fft.fftfreq(w), indexing="ij")
    direction = np.arctan2(fy, fx)
    # Angular distance, rather than production dot-power scores.
    labels = np.argmin(np.stack([np.abs(np.sin(direction - a)) for a in angles]), axis=0)
    labels[(fx == -0.5) | (fy == -0.5) | ((fx == 0) & (fy == 0))] = 2
    spectrum = np.fft.fft2(t)
    total = np.sum(t * t)
    rows = []
    reconstruction = np.zeros_like(t)
    for sector in range(3):
        mask = labels == sector
        sub = np.fft.ifft2(spectrum * mask)
        assert np.max(np.abs(sub.imag)) < 1e-13
        sub = sub.real
        reconstruction += sub
        energy = float(np.sum(sub * sub))
        numerator = float(np.sum(v * sub))
        rows.append(
            {
                "sector": sector,
                "template_energy_fraction": energy / total,
                "template_energy": energy,
                "projection_numerator": numerator,
                "gain": numerator / energy if energy else None,
            }
        )
    np.testing.assert_allclose(reconstruction, t, rtol=2e-12, atol=2e-12)
    return float(np.sum(v * t) / total), rows


def audit():
    plan = read(ROOT / "plan-v2.json")
    result = read(ROOT / "result-v1.json")
    assert result["plan"] == ref(ROOT / "plan-v2.json") and not owner_live(result["owner"])
    assert not (ROOT / "audit-v1.json").exists()
    for source in plan["sources"]:
        assert ref(source["path"]) == {k: source[k] for k in ["path", "sha256"]}
    for binding in plan["inputs"]:
        assert ref(binding["path"]) == binding
    measured = {(r["id"], r["method"]): r for r in result["rows"]}
    maximum = dict.fromkeys(["gain", "energy_fraction", "whole_gain"], 0.0)
    checks = []
    for item in plan["cases"]:
        case, geometry = item["case"], item["geometry"]
        y, x = np.mgrid[:32, :32]
        grid = np.rot90(np.stack([x, y]), geometry["rotation90_CCW"], axes=(-2, -1))
        if geometry["horizontal_flip_after_rotation"]:
            grid = grid[..., ::-1]
        jacobian = np.stack([grid[:, 0, 1] - grid[:, 0, 0], grid[:, 1, 0] - grid[:, 0, 0]], axis=1)
        carried = []
        for recipe in geometry["recipe_normals_radians"]:
            vector = jacobian.T @ [math.cos(recipe), math.sin(recipe)]
            carried.append(math.atan2(vector[1], vector[0]) % math.pi)
        np.testing.assert_allclose(carried, geometry["native_normals_radians"], atol=1e-14)
        with np.load(case["arrays"]["path"], allow_pickle=False) as arrays:
            present, empty = [
                arrays[k][0].astype(np.float64) for k in ["target_present", "target_empty"]
            ]
        for entry in item["methods"]:
            value = load_native(entry["prediction"])[0].astype(np.float64)
            whole, regions = reference(value, present, empty, carried)
            old = measured[case["id"], entry["method"]]
            for key in ["whole_template_gain", "spatial_whole_template_gain", "recomposed_gain"]:
                assert abs(old[key] - whole) < 2e-12
                maximum["whole_gain"] = max(maximum["whole_gain"], abs(old[key] - whole))
            assert abs(whole - entry["prior_whole_template_gain"]) < 2e-12
            for expected, actual in zip(regions, old["sectors"], strict=True):
                assert expected["sector"] == actual["sector"]
                for key in [
                    "template_energy_fraction",
                    "template_energy",
                    "projection_numerator",
                    "gain",
                ]:
                    np.testing.assert_allclose(actual[key], expected[key], rtol=2e-8, atol=2e-12)
                maximum["gain"] = max(maximum["gain"], abs(actual["gain"] - expected["gain"]))
                maximum["energy_fraction"] = max(
                    maximum["energy_fraction"],
                    abs(actual["template_energy_fraction"] - expected["template_energy_fraction"]),
                )
            checks.append(
                {
                    "id": case["id"],
                    "method": entry["method"],
                    "whole": whole,
                    "reference_sectors": regions,
                }
            )
    assert len(checks) == 16 and "torch" not in sys.modules
    for name, digest in plan["neural103"].items():
        assert ref(REPO / "src/demosaic" / name)["sha256"] == digest
    audit = {
        "status": "pass-16-native-projections-independent-plane-removal-spatial-projectors-and-D4-normals",
        "created_unix_UTC": time.time(),
        "plan": ref(ROOT / "plan-v2.json"),
        "result": ref(ROOT / "result-v1.json"),
        "checks": checks,
        "sector_scalar_checks": 192,
        "whole_scalar_checks": 48,
        "old_metric_bridges": 16,
        "native_normal_checks": 4,
        "maximum_absolute_errors": maximum,
        "neural103_unchanged": True,
        "Torch_imported": False,
        "new_neural_forwards": 0,
        "source": dict(ref(__file__), text=Path(__file__).read_text()),
        "scope": "Independent centered-coordinate affine sums, angular-distance regions, inverse-FFT real subtemplates and spatial inner products. Same fixed two development examples; no literal family separation or population/flat-safety claim.",
    }
    with (ROOT / "audit-v1.json").open("x") as stream:
        json.dump(audit, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print("PASS16native/192sectorScalars/48wholeScalars/16priorBridges/4D4normals", maximum)


if __name__ == "__main__":
    audit()
