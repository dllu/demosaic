"""Audit retained precision gradients with chunked FP64/fsum and mirrored FFTs."""

import argparse
import hashlib
import math
import sys
from pathlib import Path

import numpy as np
from train_directional_bank_trial import guard, read, ref, save


def checked(binding):
    assert ref(binding["path"]) == binding
    return Path(binding["path"])


def block_pixels(value):
    assert value.shape == (1, 3, 256, 256)
    return np.stack(
        [
            value[0, :, y : y + 16, x : x + 16]
            for y in range(48, 208, 16)
            for x in range(48, 208, 16)
        ]
    ).astype(np.float64)


def dct_axis(values, axis):
    n = values.shape[axis]
    mirror = np.concatenate((values, np.flip(values, axis=axis)), axis=axis)
    transformed = np.take(np.fft.fft(mirror, axis=axis), np.arange(n), axis=axis)
    shape = [1] * values.ndim
    shape[axis] = n
    phase = np.exp(-1j * np.pi * np.arange(n) / (2 * n)).reshape(shape)
    scale = np.full(n, math.sqrt(2 / n) / 2)
    scale[0] /= math.sqrt(2)
    return (transformed * phase).real * scale.reshape(shape)


def annulus_values(blocks):
    ky, kx = np.indices((16, 16))
    radius_squared = (kx * kx + ky * ky) / 1024
    return dct_axis(dct_axis(blocks, -1), -2)[
        ..., (radius_squared >= 1 / 64) & (radius_squared < 1 / 9)
    ]


def dot(a, b):
    a, b = a.ravel(), b.ravel()
    return math.fsum(
        float(a[i : i + 65536].astype(np.float64) @ b[i : i + 65536].astype(np.float64))
        for i in range(0, len(a), 65536)
    )


def summaries(gram):
    nf, nb, nh = [math.sqrt(gram[i, i]) for i in range(3)]
    return {
        "gradient_cosine_BF16_FP32": gram[0, 1] / nf / nb,
        "BF16_gradient_relative_L2_difference": math.sqrt(
            max(gram[0, 0] + gram[1, 1] - 2 * gram[0, 1], 0)
        )
        / nf,
        "gradient_norm_BF16_over_FP32": nb / nf,
        "FP32_training_band_gradient_cosine": gram[0, 2] / nf / nh,
        "BF16_training_FP32_band_gradient_cosine": gram[1, 2] / nb / nh,
        "FP32_unit_step_band_error_derivative": -gram[0, 2] / nf,
        "BF16_unit_step_band_error_derivative": -gram[1, 2] / nb,
    }


def audit(root):
    assert "torch" not in sys.modules
    plan, collection = read(root / "plan-v1.json"), read(root / "collection-v1.json")
    guard(plan)
    assert collection["plan"] == ref(root / "plan-v1.json")
    assert collection["counts"] == {
        "root": 16,
        "encoder": 16,
        "training_gradients": 16,
        "band_gradients": 8,
    }
    assert collection["model_backbone_config_and_rng_unchanged"]
    assert collection["model_hash"] == plan["model"]["expected_full_model_sha256"]
    assert collection["backbone_hash"] == plan["model"]["expected_backbone"]["sha256"]
    assert (
        collection["optimizer_updates"]
        == collection["new_noise_observations"]
        == collection["RAW_decodes"]
        == 0
    )
    layers_checked = full_values = full_gram_fields = q_values = summary_fields = 0
    full_cases = []
    for row in collection["rows"]:
        case = row["case"]
        assert case == plan["cases"][case["index"]]
        with np.load(checked(case["arrays"]), allow_pickle=False) as data:
            target, wb, matrix, mask = [
                data[k] for k in ("sensor_target", "wb", "matrix", "reference_block_mask")
            ]
        rgb = np.stack(
            [
                sum(
                    target[:, j].astype(np.float64) * float(wb[0, j]) * float(matrix[0, i, j])
                    for j in range(3)
                )
                for i in range(3)
            ],
            axis=1,
        )
        color = block_pixels(rgb)
        luma = sum(color[:, i] * w for i, w in enumerate((0.2126, 0.7152, 0.0722)))
        values = annulus_values(luma)
        means = luma.mean((-1, -2))
        rms = np.sqrt(np.sum(values * values, -1) / 256)
        independent_mask = (
            ((color >= 0) & (color <= 1)).all((1, 2, 3))
            & (means >= 0.02)
            & (means <= 0.9)
            & (rms >= 1e-5)
        )
        np.testing.assert_array_equal(mask, independent_mask)
        assert int(mask.sum()) == case["blocks"]
        t = annulus_values(block_pixels(target))[mask]
        for precision in ("float32", "bfloat16"):
            observation = row["observations"][precision]
            prediction = np.load(checked(observation["prediction"]), allow_pickle=False)
            p = annulus_values(block_pixels(prediction))[mask]
            q = 0.5 * dot(p - t, p - t) / dot(t, t)
            np.testing.assert_allclose(
                q, observation["relative_band_error"], rtol=2e-10, atol=2e-12
            )
            assert observation["dtypes"]["head"] == observation["dtypes"]["tail"] == "torch.float32"
            assert observation["dtypes"]["hidden_conv"] == "torch." + precision
            q_values += 1
        assert len(row["layers"]) == 89
        gram = np.array(
            [
                [math.fsum(layer["Gram_F64"][i][j] for layer in row["layers"]) for j in range(3)]
                for i in range(3)
            ]
        )
        np.testing.assert_allclose(gram, row["Gram_F64"], rtol=2e-10, atol=2e-10)
        for name, value in summaries(gram).items():
            np.testing.assert_allclose(value, row["summary"][name], rtol=2e-10, atol=2e-10)
            summary_fields += 1
        for layer in row["layers"]:
            local = np.array(layer["Gram_F64"])
            np.testing.assert_allclose(local, local.T, rtol=2e-12, atol=2e-12)
            assert np.linalg.eigvalsh(local).min() >= -1e-10 * max(float(np.trace(local)), 1)
            layers_checked += 1
        if binding := row["full_gradients"]:
            full_cases.append(case["index"])
            with np.load(checked(binding), allow_pickle=False) as data:
                assert len(data.files) == 3 * 89
                for j, layer in enumerate(row["layers"]):
                    arrays = [data[f"g{i}_{j}"] for i in range(3)]
                    for key, array in zip(("float32", "bfloat16", "band"), arrays, strict=True):
                        assert (
                            array.dtype == np.float32
                            and list(array.shape) == layer["shape"]
                            and np.isfinite(array).all()
                        )
                        assert (
                            hashlib.sha256(array.tobytes()).hexdigest()
                            == layer["gradients_sha256"][key]
                        )
                        full_values += array.size
                    local = np.array([[dot(a, b) for b in arrays] for a in arrays])
                    np.testing.assert_allclose(local, layer["Gram_F64"], rtol=2e-9, atol=2e-9)
                    full_gram_fields += 6
    assert full_cases == plan["retained_full_gradient_cases"] == [0, 4]
    result = {
        "status": "passed-independent-native-band-and-retained-parameter-gradient-audit",
        "plan": ref(root / "plan-v1.json"),
        "collection": ref(root / "collection-v1.json"),
        "auditor": ref(__file__),
        "native_band_values_checked": q_values,
        "streamed_layer_records_checked": layers_checked,
        "summary_fields_checked": summary_fields,
        "retained_gradient_cases": full_cases,
        "retained_gradient_FP32_values_reopened": full_values,
        "independent_retained_Gram_fields": full_gram_fields,
        "new_neural_forwards": 0,
        "new_noise_observations": 0,
        "RAW_decodes": 0,
        "optimizer_updates": 0,
        "Torch_imported": False,
        "scope": "Independent FFT band values/masks, fsum aggregation, summary geometry and chunked FP64 dot products for retained two faint ADC cases. Other raw gradient arrays were not retained; their two live reductions/hashes remain recorded. No independent differentiation through the neural model or trained-quality conclusion.",
    }
    assert not (root / "independent-audit-v1.json").exists()
    save(root / "independent-audit-v1.json", result)
    print(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    audit(parser.parse_args().root.resolve())
