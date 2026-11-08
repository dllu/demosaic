"""Full input-field bindings and sampled QR math; neither is confidence."""

import re
import numpy as np
from lossless_native import fingerprint


def geometry(shape, config):
    batch, _, height, width = shape
    length = config["dense_window"]
    stride = config["dense_stride"]
    r = length // 2
    axes = [np.unique([*range(0, n, stride), n - 1]).astype("<i8") for n in [height, width]]
    y, x = np.meshgrid(*axes, indexing="ij")
    centers = np.stack([y.ravel(), x.ravel()], 1)
    yy, xx = np.indices((length, length))
    iy = centers[:, 0, None, None] + yy
    ix = centers[:, 1, None, None] + xx
    fy, fx = np.meshgrid(np.fft.fftfreq(length) / 2, np.fft.fftfreq(length) / 2, indexing="ij")
    rad = np.hypot(fy, fx)
    eligible = (rad >= 1 / 16) & (rad <= 1 / 3)
    patches = sorted(set([0, (len(centers) - 1) // 2, len(centers) - 1]))
    coords = np.argwhere(eligible)
    coords = coords[np.linspace(0, len(coords) - 1, min(12, len(coords)), dtype=int)]
    fields = {
        "centers_y": axes[0],
        "centers_x": axes[1],
        "centers_yx": centers,
        "linear_indices": (iy * (width + 2 * r) + ix).astype("<i8"),
        "valid": (iy >= r) & (iy < height + r) & (ix >= r) & (ix < width + r),
        "eligible": eligible,
        "image_shape": np.array([height, width], dtype="<i8"),
        "windows": np.array([length, *config["dense_support_windows"]], dtype="<i8"),
        "stride": np.array(stride, dtype="<i8"),
    }
    return fields, patches, coords


def select(array, patches, coords):
    array = np.take(array, patches, axis=1)
    flat = coords[:, 0] * array.shape[-1] + coords[:, 1]
    return np.take(array.reshape(*array.shape[:-2], -1), flat, axis=-1)


def real_values(value):
    return np.stack([value.real, value.imag], -1) if np.iscomplexobj(value) else value


def describe_dense(aux):
    if aux["dense_spectrum"] is None:
        assert aux["dense_context"] is aux["dense_coefficient"] is None
        return None
    fields = {k: v.detach().cpu().numpy() for k, v in aux["dense_spectrum"].items()}
    context = aux["dense_context"].detach().cpu().numpy()
    coefficient = aux["dense_coefficient"].detach().cpu().numpy()
    b, p, _, l, _ = coefficient.shape
    config = {
        "dense_window": l,
        "dense_stride": int(fields["stride"]),
        "dense_support_windows": fields["windows"][1:].tolist(),
    }
    h, w = map(int, fields["image_shape"])
    _, patches, coords = geometry((b, 4, h, w), config)
    arrays = {
        "context": context.reshape(b, p, 18, l, l),
        "coefficient": coefficient,
        "aligned_spectra": fields["aligned_spectra"],
        "propagated_variance": fields["propagated_variance"],
    }
    assert all(np.isfinite(v).all() for v in arrays.values())
    return {
        "windows": fields["windows"].tolist(),
        "stride": int(fields["stride"]),
        "context": fingerprint(context),
        "coefficient": fingerprint(coefficient),
        "fields": {k: fingerprint(v) for k, v in fields.items()},
        "finite_fields": True,
        "patch_indices": patches,
        "frequency_yx": coords.tolist(),
        "samples": {k: real_values(select(v, patches, coords)).tolist() for k, v in arrays.items()},
        "scope": "Full hashes bind input-only execution/raw-EMA equality. Deterministic QR samples check math,not every full field value or restoration/safety.",
    }


def validate_dense(record, shape, colors, config):
    b, _, h, w = shape
    l = config["dense_window"]
    expected, patches, coords = geometry(shape, config)
    p = len(expected["centers_yx"])
    layout = np.broadcast_to(colors, (b, 4))
    expected["green_phase_indices"] = np.stack([np.flatnonzero(v == 1) for v in layout]).astype(
        "<i8"
    )
    assert (
        record["windows"] == [l, *config["dense_support_windows"]]
        and record["stride"] == config["dense_stride"]
        and record["finite_fields"] is True
    )
    for key, value in expected.items():
        assert record["fields"][key] == fingerprint(value), key
    floating = {
        "affine_basis": ([l, l, 3], "<f8"),
        "native_fy": ([l, l], "<f8"),
        "native_fx": ([l, l], "<f8"),
        "subpixel_phase": ([4, l, l], "<c16"),
        "synthesis_window": ([l, l], "<f8"),
        "normalization": ([h, w], "<f8"),
        "aligned_spectra": ([b, p, 3, 2, l, l], "<c16"),
        "propagated_variance": ([b, p, 3, 2, l, l], "<f8"),
    }
    assert set(record["fields"]) == set(expected) | set(floating)
    for key, (dimensions, dtype) in floating.items():
        value = record["fields"][key]
        assert (
            value["shape"] == dimensions
            and value["dtype"] == dtype
            and re.fullmatch("[0-9a-f]{64}", value["sha256"])
        )
    for key, dimensions, dtype in [
        ("context", [b * p, 18, l, l], "<f4"),
        ("coefficient", [b, p, 2, l, l], "<c8"),
    ]:
        value = record[key]
        assert (
            value["shape"] == dimensions
            and value["dtype"] == dtype
            and re.fullmatch("[0-9a-f]{64}", value["sha256"])
        )
    assert record["patch_indices"] == patches and record["frequency_yx"] == coords.tolist()
    samples = {
        "context": (b, len(patches), 18, len(coords)),
        "coefficient": (b, len(patches), 2, len(coords), 2),
        "aligned_spectra": (b, len(patches), 3, 2, len(coords), 2),
        "propagated_variance": (b, len(patches), 3, 2, len(coords)),
    }
    assert set(record["samples"]) == set(samples)
    for key, dimensions in samples.items():
        value = np.asarray(record["samples"][key])
        assert value.shape == dimensions and np.isfinite(value).all()
    assert (np.asarray(record["samples"]["propagated_variance"]) >= 0).all()


def audit_samples(record, packed, variance, colors, config):
    from dense_spectrum_reference import measurements

    fields, patches, coords = geometry(packed.shape, config)
    context, coefficient, eg = measurements(
        packed,
        variance,
        colors,
        window=config["dense_window"],
        stride=config["dense_stride"],
        support_windows=tuple(config["dense_support_windows"]),
        centers_yx=fields["centers_yx"][patches],
    )
    b, p, _, l, _ = coefficient.shape
    expected = {
        "context": context.reshape(b, p, 18, l, l),
        "coefficient": coefficient,
        "aligned_spectra": eg["aligned_spectra"],
        "propagated_variance": eg["propagated_variance"],
    }
    tolerances = {
        "context": (4e-6, 4e-6),
        "coefficient": (4e-6, 3e-8),
        "aligned_spectra": (2e-8, 3e-12),
        "propagated_variance": (2e-8, 3e-16),
    }
    checks = 0
    maxima = {}
    for key, value in expected.items():
        value = real_values(select(value, list(range(p)), coords))
        actual = np.asarray(record["samples"][key])
        rtol, atol = tolerances[key]
        np.testing.assert_allclose(actual, value, rtol=rtol, atol=atol)
        checks += value.size
        maxima[key] = float(abs(actual - value).max())
    return checks, maxima
