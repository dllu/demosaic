import copy
import json

import numpy as np
import pytest
from dense_spectrum_evidence_receipt import audit_samples, describe_dense, validate_dense
from dense_spectrum_reference import measurements
from test_late_dense_local_spectrum import fixture

from demosaic.late_dense_local_spectrum import dense_local_spectrum

CONFIG = {"dense_window": 9, "dense_stride": 4, "dense_support_windows": [7, 5]}


def example(pattern="RGGB"):
    import torch

    raw, var, colors = fixture(pattern, torch.float32)
    context, coefficient, fields = dense_local_spectrum(
        raw, var, colors, window=9, stride=4, support_windows=(7, 5)
    )
    aux = {"dense_context": context, "dense_coefficient": coefficient, "dense_spectrum": fields}
    return raw, var, colors, aux


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_JSON_receipt_geometry_and_independent_QR_samples(pattern):
    raw, var, colors, aux = example(pattern)
    record = json.loads(json.dumps(describe_dense(aux)))
    validate_dense(record, raw.shape, colors.numpy(), CONFIG)
    count, maxima = audit_samples(record, raw.numpy(), var.numpy(), colors.numpy(), CONFIG)
    assert count == 1440 and set(maxima) == set(record["samples"])
    assert "not every" in record["scope"]


@pytest.mark.parametrize(
    "change",
    [
        "windows",
        "stride",
        "patches",
        "frequency",
        "integer_hash",
        "context_shape",
        "complex_dtype",
        "spectral_shape",
        "missing_field",
        "sample_nan",
        "sample_math",
    ],
)
def test_corrupt_dense_receipts_are_rejected(change):
    raw, var, colors, aux = example()
    record = describe_dense(aux)
    if change == "windows":
        record["windows"][0] += 2
    if change == "stride":
        record["stride"] += 1
    if change == "patches":
        record["patch_indices"][1] = 0
    if change == "frequency":
        record["frequency_yx"][0] = [0, 0]
    if change == "integer_hash":
        record["fields"]["linear_indices"]["sha256"] = "0" * 64
    if change == "context_shape":
        record["context"]["shape"][1] = 17
    if change == "complex_dtype":
        record["coefficient"]["dtype"] = "<c16"
    if change == "spectral_shape":
        record["fields"]["aligned_spectra"]["shape"][2] = 2
    if change == "missing_field":
        record["fields"].pop("normalization")
    if change == "sample_nan":
        record["samples"]["propagated_variance"][0][0][0][0][0] = float("nan")
    if change == "sample_math":
        record["samples"]["coefficient"][0][0][0][0][0] += 0.01
    with pytest.raises(AssertionError):
        validate_dense(record, raw.shape, colors.numpy(), CONFIG)
        audit_samples(record, raw.numpy(), var.numpy(), colors.numpy(), CONFIG)


def test_ADC_and_selected_QR_centers():
    assert (
        describe_dense(dict(dense_context=None, dense_coefficient=None, dense_spectrum=None))
        is None
    )
    raw, var, colors, aux = example()
    full = measurements(
        raw.numpy(), var.numpy(), colors.numpy(), window=9, stride=4, support_windows=(7, 5)
    )
    subset = measurements(
        raw.numpy(),
        var.numpy(),
        colors.numpy(),
        window=9,
        stride=4,
        support_windows=(7, 5),
        centers_yx=aux["dense_spectrum"]["centers_yx"][[0, 5, 11]].numpy(),
    )
    np.testing.assert_array_equal(
        subset[0].reshape(1, 3, 18, 9, 9), full[0].reshape(1, 12, 18, 9, 9)[:, [0, 4, 8]]
    )
    with pytest.raises(ValueError):
        measurements(
            raw.numpy(),
            var.numpy(),
            colors.numpy(),
            window=9,
            stride=4,
            support_windows=(7, 5),
            centers_yx=[[123, 123]],
        )
