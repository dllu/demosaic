"""Independently check saved feature losses/gradients using mirrored FFTs and fsum."""

import argparse
import math
from pathlib import Path

import numpy as np
from train_directional_bank_trial import guard, read, ref, save


def checked(binding):
    assert ref(binding["path"]) == binding
    return Path(binding["path"])


def dct_axis(values, axis):
    n = values.shape[axis]
    mirrored = np.concatenate((values, np.flip(values, axis=axis)), axis=axis)
    transformed = np.take(np.fft.fft(mirrored, axis=axis), np.arange(n), axis=axis)
    shape = [1] * values.ndim
    shape[axis] = n
    phase = np.exp(-1j * np.pi * np.arange(n) / (2 * n)).reshape(shape)
    scale = np.full(n, math.sqrt(2 / n) / 2)
    scale[0] /= math.sqrt(2)
    return (transformed * phase).real * scale.reshape(shape)


def native_blocks(values):
    values = np.asarray(values, np.float64)
    if values.shape[-2:] == (256, 256):
        values = values[..., 48:208, 48:208]
    assert values.shape == (1, 3, 160, 160) and np.isfinite(values).all()
    # Explicit indexing avoids sharing the production reshape/transposition.
    return np.stack(
        [values[0, :, y : y + 16, x : x + 16] for y in range(0, 160, 16) for x in range(0, 160, 16)]
    )


def selected_coefficients(values):
    values = native_blocks(values)
    transformed = dct_axis(dct_axis(values, -1), -2)
    ky, kx = np.indices((16, 16))
    radius_squared = (ky * ky + kx * kx) / 1024
    return transformed[..., (radius_squared >= 1 / 64) & (radius_squared < 1 / 9)]


def dot(a, b):
    return math.fsum(float(x) for x in (a * b).ravel())


def projection(gradient, prediction, target, mask):
    g, p, t = [selected_coefficients(v)[mask] for v in (gradient, prediction, target)]
    error = p - t
    g2, e2, t2 = dot(g, g), dot(error, error), dot(t, t)
    cross = dot(g, error)
    return {
        "blocks": int(mask.sum()),
        "directional_derivative_toward_true_band": -cross,
        "descent_cosine_to_true_band_correction": cross / math.sqrt(g2 * e2) if g2 and e2 else None,
        "negative_gradient_target_gain_slope": -dot(g, t) / t2,
        "target_band_projection_gain": dot(p, t) / t2,
        "gradient_band_L2": math.sqrt(g2),
        "band_error_L2": math.sqrt(e2),
    }


def audit(root):
    plan = read(root / "plan-v1.json")
    guard(plan)
    collection = read(root / "collection-v1.json")
    analysis = read(root / "analysis-v1.json")
    assert collection["plan"] == analysis["plan"] == ref(root / "plan-v1.json")
    assert analysis["collection"] == ref(root / "collection-v1.json")
    assert collection["new_encoder_forwards"] == len(collection["encoder_calls"]) == 26
    assert len({r["input_sha256"] for r in collection["encoder_calls"]}) == 26
    assert collection["new_restoration_forwards"] == collection["new_noise_observations"] == 0
    assert collection["optimizer_updates"] == collection["RAW_decodes"] == 0
    assert collection["frozen_parameter_gradients_absent"] and collection["Torch_RNG_unchanged"]
    assert not collection["CUDA_initialized"]
    assert collection["model_hash_before_after"] == plan["backbone"]["sha256"]
    records = {(r["case_id"], r["variant"]): r for r in collection["records"]}
    arrays, masks, checks = {}, {}, 0
    for case in plan["cases"]:
        cid = case["id"]
        with np.load(checked(case["target"])) as data:
            target, wb, matrix = [data[k].astype(np.float64) for k in ("target", "wb", "matrix")]
        rgb = np.einsum("bij,bjhw->bihw", matrix, target * wb[..., None, None])
        color = native_blocks(rgb)
        luma = np.einsum("c,bchw->bhw", [0.2126, 0.7152, 0.0722], color)
        ky, kx = np.indices((16, 16))
        radius_squared = (ky * ky + kx * kx) / 1024
        band = dct_axis(dct_axis(luma, -1), -2)[
            ..., (radius_squared >= 1 / 64) & (radius_squared < 1 / 9)
        ]
        means = luma.mean((-1, -2))
        rms = np.sqrt(np.sum(band * band, axis=-1) / 256)
        valid = ((color >= 0) & (color <= 1)).all((1, 2, 3))
        valid &= (means >= 0.02) & (means <= 0.9) & (rms >= 1e-5)
        low, high = np.array([0, 0.02, 0.05, 0.1, 0.2, np.inf])[
            case["contrast_bin"] : case["contrast_bin"] + 2
        ]
        contrast = rms / np.maximum(means, 1e-12)
        mask = valid & (contrast >= low) & (contrast < high)
        with np.load(checked(case["controls"])) as data:
            assert np.array_equal(mask, data["mask"])
            true, wrong = [selected_coefficients(data[k]) for k in ("true_band", "orthogonal_band")]
        desired = selected_coefficients(target)
        desired[~mask] = 0
        np.testing.assert_allclose(true, desired, atol=2e-14, rtol=1e-10)
        np.testing.assert_allclose(np.sum(true * wrong, -1), 0, atol=2e-14)
        np.testing.assert_allclose(np.sum(true * true, -1), np.sum(wrong * wrong, -1), atol=2e-14)
        masks[cid], arrays[cid] = mask, target
        checks += 4
    losses_checked, projections_checked = 0, 0
    for row in analysis["rows"]:
        cid, method = row["case"], row["variant"]
        record = records[cid, method]
        prediction = np.load(checked(record["values"]))
        if row["objective"] == "existing-reconstruction":
            case = next(c for c in plan["cases"] if c["id"] == cid)
            saved = np.load(checked(case["baseline_gradients"][method]), mmap_mode="r")
            gradient = saved[:, 0].astype(np.float64).sum(0)[None]
        else:
            stage = {"DINO-stride4-MSE": 0, "DINO-stride8-MSE": 1}[row["objective"]]
            with np.load(checked(record["artifact"])) as data:
                feature = data[f"feature_{stage}"].astype(np.float64)
                gradient = data[f"gradient_{stage}"]
            reference_record = records[cid, "reference"]
            with np.load(checked(reference_record["artifact"])) as data:
                reference = data[f"feature_{stage}"].astype(np.float64)
            assert list(feature.shape) == record["feature_shapes"][stage]
            independent_loss = dot(feature - reference, feature - reference) / feature.size
            np.testing.assert_allclose(independent_loss, row["feature_loss"], rtol=2e-7, atol=1e-12)
            losses_checked += 1
        observed = projection(gradient, prediction, arrays[cid], masks[cid])
        for key, expected in observed.items():
            if expected is None:
                assert row[key] is None
            else:
                np.testing.assert_allclose(row[key], expected, rtol=2e-9, atol=2e-13)
            projections_checked += 1
    direction = np.load(checked(plan["finite_difference"]["direction"]))
    base = records["raccoon-fur", "V120"]
    minus, plus = [
        next(r for r in collection["records"] if r.get("finite_difference") == s) for s in (-1, 1)
    ]
    for row in analysis["finite_differences"]:
        stage = row["stage"]
        with np.load(checked(base["artifact"])) as data:
            derivative = dot(data[f"gradient_{stage}"].astype(np.float64), direction)
        numeric = (plus["losses"][stage] - minus["losses"][stage]) / (
            2 * plan["finite_difference"]["step"]
        )
        relative = abs(derivative - numeric) / (abs(derivative) + abs(numeric) + 1e-8)
        np.testing.assert_allclose(derivative, row["autograd_directional_derivative"], rtol=2e-12)
        np.testing.assert_allclose(numeric, row["central_difference"], rtol=2e-12)
        np.testing.assert_allclose(relative, row["symmetric_relative_error"], rtol=2e-12)
        assert (
            row["passes_declared_tolerance"]
            and relative <= plan["finite_difference"]["maximum_symmetric_relative_error"]
        )
    assert len(analysis["rows"]) == 56 and losses_checked == 48
    result = {
        "status": "passed-independent-mirrored-FFT-fsum-feature-audit",
        "analysis": ref(root / "analysis-v1.json"),
        "collection": ref(root / "collection-v1.json"),
        "audit_source": ref(__file__),
        "control_checks": checks,
        "saved_feature_losses_checked": losses_checked,
        "projection_fields_checked": projections_checked,
        "finite_difference_checks": 2,
        "new_encoder_forwards": 0,
        "new_restoration_forwards": 0,
        "new_noise_observations": 0,
    }
    dest = root / "independent-audit-v1.json"
    assert not dest.exists()
    save(dest, result)
    print(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    audit(parser.parse_args().root.resolve())
