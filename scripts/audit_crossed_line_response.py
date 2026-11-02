"""Independent joint affine/template fits and native PNG check for mesh response."""

import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image
from train_directional_bank_trial import read, ref, save


def audit(root):
    result = read(root / "report-v1/result-v1.json")
    master = read(result["plan"]["path"])
    assert ref(result["plan"]["path"]) == result["plan"]
    plans, predictions = {}, {}
    for label, binding in master["models"].items():
        assert ref(binding["path"]) == binding
        plan = read(binding["path"])
        collection = read(Path(plan["root"]) / "collection-v1.json")
        assert collection["plan"] == binding
        plans[label] = plan
        predictions[label] = {o["id"]: o["prediction"] for o in collection["observations"]}
    observations = {o["id"]: o for o in next(iter(plans.values()))["observations"]}
    y, x = np.mgrid[-1:1:160j, -1:1:160j]
    plane = np.stack([np.ones_like(x), x, y], -1).reshape(-1, 3)
    design = np.zeros((3 * 160 * 160, 10))
    for c in range(3):
        design[c * 25600 : (c + 1) * 25600, c * 3 : c * 3 + 3] = plane
    checked, worst, channels = 0, 0.0, 0
    grouped = defaultdict(list)

    def prediction(label, identity, arrays):
        if label == "Noisy Malvar":
            from demosaic.archive_metrics import noisy_malvar

            return noisy_malvar(arrays)
        binding = predictions[label][identity]
        assert ref(binding["path"]) == binding
        return np.load(binding["path"], allow_pickle=False)

    for row in result["rows"]:
        observation = observations[row["id"]]
        assert ref(observation["arrays"]["path"]) == observation["arrays"]
        with np.load(observation["arrays"]["path"], allow_pickle=False) as archive:
            arrays = {k: archive[k] for k in archive.files}
        p = prediction(row["method"], row["id"], arrays).astype(np.float64)
        crop = (..., slice(48, 208), slice(48, 208))
        a, b = (arrays[k].astype(np.float64)[crop] for k in ("target_present", "target_empty"))
        design[:, 9] = (a - b).ravel()
        values = (p[crop] - b).ravel()
        coefficients = np.linalg.lstsq(design, values, rcond=None)[0]
        delta = abs(float(coefficients[9]) - row["known_mesh_gain"])
        worst = max(worst, delta)
        np.testing.assert_allclose(coefficients[9], row["known_mesh_gain"], atol=3e-9, rtol=2e-8)
        residual = values - design @ coefficients
        np.testing.assert_allclose(
            np.sqrt(np.mean(residual**2)), row["detrended_nonmesh_RMS"], atol=2e-14, rtol=1e-9
        )
        error = p[crop] - arrays["target"].astype(np.float64)[crop]
        dc = np.array([np.sum(error[:, c]) / 25600 for c in range(3)])
        np.testing.assert_allclose(dc, row["error"]["DC_RGB"], atol=2e-14, rtol=1e-9)
        np.testing.assert_allclose(
            np.sum(error**2) / error.size, row["error"]["MSE"], atol=2e-18, rtol=1e-12
        )
        grouped[(row["method"], row["noise"], row["present"])].append(row)
        checked += 1
    for row in result["summary"]:
        group = grouped[(row["method"], row["noise"], row["present"])]
        assert row["cases"] == len(group) == 16
        np.testing.assert_allclose(
            sum(r["known_mesh_gain"] for r in group) / 16,
            row["mean_known_mesh_gain"],
            atol=1e-14,
            rtol=1e-12,
        )
    for row in result["images"]:
        assert ref(row["image"]["path"]) == row["image"]
        observation = row["observation"]
        with np.load(observation["arrays"]["path"], allow_pickle=False) as archive:
            arrays = {k: archive[k] for k in archive.files}
        actual = np.asarray(Image.open(row["image"]["path"]))
        values = [
            prediction(label, observation["id"], arrays) for label in ["Noisy Malvar", *plans]
        ]
        values.append(arrays["target"])
        for i, value in enumerate(values):
            camera = value.astype(np.float64)[0, :, 48:208, 48:208].reshape(3, -1)
            linear = arrays["matrix"][0].astype(np.float64) @ (
                camera * 8 * arrays["wb"][0, :, None]
            )
            linear = linear.clip(0, 1)
            display = np.where(
                linear <= 0.0031308, linear * 12.92, 1.055 * linear ** (1 / 2.4) - 0.055
            )
            expected = np.rint(display.T.reshape(160, 160, 3) * 255).astype(np.uint8)
            np.testing.assert_array_equal(actual[24:184, 8 + 168 * i : 168 + 168 * i], expected)
            channels += expected.size
    assert checked == 256 and channels == 6144000
    save(
        root / "independent-audit-v1.json",
        {
            "status": "passed-independent-joint-template-and-native-PNG-audit",
            "operator": ref(__file__),
            "result": ref(root / "report-v1/result-v1.json"),
            "joint_10_column_least_squares_fits": checked,
            "maximum_absolute_gain_difference": worst,
            "PNG_channels_exact": channels,
            "new_model_calls": 0,
            "scope": "Joint9 affine nuisance+1 exact template coefficients independently check sequential plane-removal/projection metrics. Direct matrix product/gamma checks16 native five-way boards. Descriptive exact procedural cases, not real-photo quality or confidence intervals.",
        },
    )
    print({"fits": checked, "maximum_gain_difference": worst, "PNG_channels_exact": channels})


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    audit(p.parse_args().root.resolve())
