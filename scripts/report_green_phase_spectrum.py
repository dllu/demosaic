"""Saved-array diagnostic; no training, restoration or camera-noise fitting.

The JSON plan fixes inputs, windows and input-only peak selection before this
process loads numerical arrays. Reconstructed/reference spectra are descriptive;
they cannot establish photographic ground truth or restoration transfer gain.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import matplotlib
import numpy as np
from green_phase_spectrum import green_pair

matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.colors import SymLogNorm


def binding(path):
    path = Path(path).resolve()
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def verify(record):
    if binding(record["path"])["sha256"] != record["sha256"]:
        raise ValueError(f"Changed bound file: {record['path']}")
    return Path(record["path"])


def choose_peaks(result):
    """Fixed union: four absolute cross peaks and four phase-power peaks.

    Principal-band native radial frequencies 1/16..1/3 cycles/pixel; one
    conjugate half-plane. A selected bin excludes its 3x3 neighborhood and
    conjugate neighborhood within each ranking. The two rankings are separate.
    """
    fx, fy = result["native_fx"], result["native_fy"]
    radius = np.hypot(fx, fy)
    eligible = (radius >= 1 / 16) & (radius <= 1 / 3) & ((fy > 0) | ((fy == 0) & (fx > 0)))
    selected = {}
    for kind, values in (
        ("absolute_cross", np.abs(result["noise_units_signed_cross"])),
        ("phase_power", result["noise_units_mean_phase_power"]),
    ):
        available = eligible.copy()
        for _ in range(4):
            score = np.where(available, values, -np.inf)
            flat = int(np.argmax(score))
            if not np.isfinite(score.ravel()[flat]):
                break
            y, x = np.unravel_index(flat, score.shape)
            selected.setdefault((int(y), int(x)), []).append(kind)
            for cy, cx in ((y, x), ((-y) % score.shape[0], (-x) % score.shape[1])):
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        available[(cy + dy) % score.shape[0], (cx + dx) % score.shape[1]] = False
    return [{"bin_yx": list(point), "selected_by": kinds} for point, kinds in selected.items()]


def sample_green(rgb, xywh):
    x, y, width, height = xywh
    field = rgb[0, 1, y : y + height, x : x + width]
    return np.stack([field[dy::2, dx::2] for dy, dx in ((0, 0), (0, 1), (1, 0), (1, 1))])


def describe(result):
    return {
        key: result[key]
        for key in (
            "power",
            "average_cross",
            "signed_coherence",
            "noise_units_signed_cross",
            "noise_units_mean_phase_power",
            "noise_variance",
            "removed_planes",
        )
    }


def execute(plan_path, output):
    plan_path = Path(plan_path).resolve()
    plan = json.loads(plan_path.read_text())
    if plan["algorithm"] != "green-phase-cross-spectrum-v1":
        raise ValueError("Unsupported fixed plan")
    executed = {
        Path(__file__).resolve(),
        Path(sys.modules[green_pair.__module__].__file__).resolve(),
    }
    bound_code = {verify(record).resolve() for record in plan["code"]}
    if not executed <= bound_code:
        raise ValueError("Executing code is not bound by the plan")
    for record in plan["receipts"]:
        verify(record)
    input_path = verify(plan["inputs"])
    for method in plan["methods"]:
        verify(method["prediction"])
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / "started.json").write_text(json.dumps({"plan": binding(plan_path)}, indent=2) + "\n")
    with np.load(input_path, allow_pickle=False) as source:
        packed, variance, colors = source["packed"][0], source["variance"][0], source["colors"][0]
        # No reference arrays are accessed until the two input-only selections finish.
        inputs = []
        for case in plan["windows"]:
            x, y, width, height = case["context_xywh"]
            if (x | y | width | height) % 2 or min(width, height) < 16:
                raise ValueError("Window must have even origin and dimensions")
            field = packed[:, y // 2 : (y + height) // 2, x // 2 : (x + width) // 2]
            noise = variance[:, y // 2 : (y + height) // 2, x // 2 : (x + width) // 2]
            if field.shape != (4, height // 2, width // 2):
                raise ValueError("Window extends outside retained context")
            result = green_pair(field, noise, colors)
            inputs.append((case, noise, result, choose_peaks(result)))
        selection = [{"name": case["name"], "peaks": peaks} for case, _, _, peaks in inputs]
        (output / "input-only-selection.json").write_text(json.dumps(selection, indent=2) + "\n")
        reference = source["reference_rgb"].copy()
    predictions = {
        method["label"]: np.load(method["prediction"]["path"], mmap_mode="r", allow_pickle=False)
        for method in plan["methods"]
    }
    if reference.shape != (1, 3, 768, 768) or any(
        array.shape != reference.shape or not np.isfinite(array).all()
        for array in predictions.values()
    ):
        raise ValueError("Expected finite retained 768px camera-RGB predictions")
    arrays, cases = {}, []
    figure, axes = plt.subplots(len(inputs), 4, figsize=(15, 4.1 * len(inputs)), squeeze=False)
    for row, (case, noise, result, peaks) in enumerate(inputs):
        name, xywh = case["name"], case["context_xywh"]
        spectra = {"observed": result}
        for label, rgb in [*predictions.items(), ("independent_ISO100_AHD", reference)]:
            # Sample the reconstructed green field at the same physical green sites.
            spectra[label] = green_pair(sample_green(rgb, xywh), noise, colors)
        for label, spectral in spectra.items():
            for key, values in describe(spectral).items():
                arrays[f"{name}__{label}__{key}"] = values
        cases.append({**case, "peaks": []})
        # Nearby 3x3 bins are correlated by the Hann taper; no significance test.
        for peak in peaks:
            y, x = peak["bin_yx"]
            raw_power = float(result["noise_units_mean_phase_power"][y, x])
            item = {
                **peak,
                "native_frequency_xy": [
                    float(result["native_fx"][y, x]),
                    float(result["native_fy"][y, x]),
                ],
                "conditional_noise_units_cross": float(result["noise_units_signed_cross"][y, x]),
                "conditional_noise_units_phase_power": raw_power,
                "signed_coherence": float(result["signed_coherence"][y, x]),
                "saved_model_power_over_observed_power": {
                    label: float(spectra[label]["noise_units_mean_phase_power"][y, x] / raw_power)
                    for label in predictions
                },
            }
            # ISO100 has independent exposure/aperture/blur; compare only shape.
            ref = spectra["independent_ISO100_AHD"]
            noisy_mean = float(np.mean(result["removed_planes"][:, 0]))
            ref_mean = float(np.mean(ref["removed_planes"][:, 0]))
            item["reference_shape_power_over_observed_power_own_mean_normalized"] = float(
                ref["noise_units_mean_phase_power"][y, x] / raw_power * (noisy_mean / ref_mean) ** 2
            )
            cases[-1]["peaks"].append(item)
        # imshow extent describes edges; FFT frequencies describe bin centers.
        step_y, step_x = 0.5 / result["power"].shape[-2], 0.5 / result["power"].shape[-1]
        extent = [-0.25 - step_x / 2, 0.25 - step_x / 2, -0.25 - step_y / 2, 0.25 - step_y / 2]
        maps = (
            (
                np.log10(result["noise_units_mean_phase_power"]),
                "log10 phase power / noise",
                "viridis",
                None,
            ),
            (
                result["noise_units_signed_cross"],
                "signed cross / conditional noise",
                "coolwarm",
                SymLogNorm(1, vmin=-100, vmax=100),
            ),
            (result["signed_coherence"], "signed coherence (not confidence)", "coolwarm", None),
        )
        for column, (values, title, cmap, norm) in enumerate(maps):
            options = {"vmin": -1, "vmax": 1} if column == 2 else {}
            if column == 0:
                options = {"vmin": -0.5, "vmax": 2.5}
            image = axes[row, column].imshow(
                np.fft.fftshift(values),
                origin="lower",
                extent=extent,
                cmap=cmap,
                norm=norm,
                interpolation="nearest",
                **options,
            )
            axes[row, column].set_title(f"{name}\n{title}", fontsize=10)
            axes[row, column].set_xlabel("native cycles / pixel, x")
            figure.colorbar(image, ax=axes[row, column], shrink=0.72)
            for number, peak in enumerate(cases[-1]["peaks"]):
                fx, fy = peak["native_frequency_xy"]
                axes[row, column].plot(fx, fy, "o", fillstyle="none", color="black", ms=7)
                axes[row, column].annotate(str(number + 1), (fx, fy), fontsize=8)
        for label in predictions:
            axes[row, 3].plot(
                np.arange(1, len(peaks) + 1),
                [p["saved_model_power_over_observed_power"][label] for p in cases[-1]["peaks"]],
                "o-",
                label=label,
            )
        axes[row, 3].set_yscale("log")
        axes[row, 3].set_xlabel("input-only selected frequency")
        axes[row, 3].set_title(
            "Saved green power / observed power\nincludes observed noise; not transfer gain",
            fontsize=10,
        )
        axes[row, 3].legend()
        axes[row, 3].grid(alpha=0.3)
    figure.suptitle(
        "DSCF3842 RAW green phases; fixed nearby profile; saved arrays only", fontsize=12
    )
    figure.tight_layout()
    figure.savefig(output / "phase-diagnostic.png", dpi=150)
    figure.savefig(output / "phase-diagnostic.pdf")
    plt.close(figure)
    np.savez_compressed(output / "spectra.npz", **arrays)
    if any(
        name.split(".")[0] in {"torch", "rawpy", "transformers", "demosaic"} for name in sys.modules
    ):
        raise RuntimeError("Neural/camera libraries unexpectedly imported")
    result = {
        "status": "complete-saved-array-diagnostic",
        "plan": binding(plan_path),
        "cases": cases,
        "artifacts": [
            binding(output / name)
            for name in (
                "input-only-selection.json",
                "spectra.npz",
                "phase-diagnostic.png",
                "phase-diagnostic.pdf",
            )
        ],
        "new_neural_forwards": 0,
        "new_noise_observations": 0,
        "RAW_decodes": 0,
        "optimizer_updates": 0,
        "limitations": plan["limitations"],
    }
    (output / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "result": binding(output / "result.json")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    execute(args.plan, args.output)
