"""CPU-only checks of closed masked-neural fields, arguments and CFA withholding."""

import argparse
import sys
from pathlib import Path

import numpy as np

from demosaic.experiments.artifacts import checked, read_json, reference, write_json
from demosaic.neural_nuisance import masked_packed_input
from demosaic.prediction_archive import fingerprint


def independent_imputation(raw, mask):
    """Explicit finite Gaussian stencil, independent of scipy.ndimage filtering."""
    kernel = np.exp(-(np.arange(-3, 4, dtype=np.float64) ** 2) / 2)
    kernel /= kernel.sum()

    def blur(a):
        for axis in (0, 1):
            pads = [(0, 0), (0, 0)]
            pads[axis] = (3, 3)
            padded = np.pad(a, pads)
            a = sum(
                weight
                * padded[
                    tuple(
                        slice(i, i + n) if j == axis else slice(None) for j, n in enumerate(a.shape)
                    )
                ]
                for i, weight in enumerate(kernel)
            )
        return a

    result = []
    for y in range(2):
        for x in range(2):
            values, selected = raw[y::2, x::2], mask[y::2, x::2]
            numerator = blur(np.where(selected, values, 0).astype(np.float64))
            denominator = blur(selected.astype(np.float64))
            fill = np.divide(
                numerator,
                denominator,
                out=np.full(values.shape, float(values[selected].mean())),
                where=denominator > 0,
            )
            result.append(np.where(selected, values, fill).astype(raw.dtype))
    return np.stack(result)


def audit(root, output):
    assert "torch" not in sys.modules
    plan = read_json(root / "plan.json")
    cache = read_json(root / "backgrounds-collection.json")
    assert cache["plan"] == reference(root / "plan.json")
    assert cache["all91_restoration_and_backbone_tensors_unchanged"]
    assert cache["background_configuration"] == plan["background_configuration"]
    rows = {r["id"]: r for r in cache["rows"]}
    assert len(rows) == len(plan["rows"])
    cases = []
    maximum = 0.0
    fields = channels = fresh = 0
    for row in plan["rows"]:
        record = rows[row["id"]]
        with np.load(checked(row["arrays"]), allow_pickle=False) as z:
            sample = row["sample"]
            data = {
                "packed": z["packed"][sample],
                "colors": z["colors"][sample],
                "wb": z["wb"][sample : sample + 1],
                "matrix": z["matrix"][sample : sample + 1],
            }
        assert record["input_fingerprints"] == {k: fingerprint(v) for k, v in data.items()}
        assert record["noise"] == row["noise"]
        zero = row["noise"]["shot"] + row["noise"]["read"] == 0
        assert record["identity_zero_noise"] == zero
        if zero:
            assert not record["fields"]
            cases.append({"id": row["id"], "zero_noise_bypass": True})
            continue
        raw = np.empty(tuple(n * 2 for n in data["packed"].shape[1:]), np.float32)
        for phase in range(4):
            raw[phase // 2 :: 2, phase % 2 :: 2] = data["packed"][phase]
        mask = np.load(checked(record["mask_A"]))
        assert mask.dtype == bool and mask.shape == raw.shape
        assert len(record["fields"]) == len(record["argument_fingerprints"]) == 2
        fold_checks = []
        for fold, selected in enumerate((mask, ~mask)):
            # These exact production-transform arguments are compared with their
            # saved fingerprints and separately with the independent stencil.
            packed = masked_packed_input(raw, selected)
            withheld = raw.copy()
            withheld[~selected] = np.nan
            np.testing.assert_array_equal(masked_packed_input(withheld, selected), packed)
            independent = independent_imputation(withheld, selected)
            error = float(np.max(np.abs(packed.astype(np.float64) - independent)))
            maximum = max(maximum, error)
            np.testing.assert_allclose(packed, independent, rtol=0, atol=6e-8)
            for phase in range(4):
                chosen = selected[phase // 2 :: 2, phase % 2 :: 2]
                assert 0 < chosen.mean() < 1
                np.testing.assert_array_equal(packed[phase][chosen], data["packed"][phase][chosen])
            args = {
                "packed": packed[None],
                "variance": (packed.clip(0) * row["noise"]["shot"] + row["noise"]["read"])[None],
                "colors": data["colors"][None],
                "wb": data["wb"],
                "matrix": data["matrix"],
            }
            assert {k: fingerprint(v) for k, v in args.items()} == record["argument_fingerprints"][
                fold
            ]
            field = np.load(checked(record["fields"][fold]))
            assert field.dtype == np.float32 and field.shape == (3, *raw.shape)
            assert np.isfinite(field).all()
            fields += 1
            channels += field.size
            fold_checks.append(
                {
                    "fold": fold,
                    "independent_imputation_max_abs": error,
                    "arguments_exact": True,
                    "withheld_NaNs_invariant": True,
                }
            )
        fresh += 2 * (record["adopted_from"] is None)
        cases.append({"id": row["id"], "folds": fold_checks})
    assert fresh == cache["new_root_forwards"] == cache["new_encoder_forwards"]
    assert fields == cache["complete_background_fields"] == plan["background_field_count"]
    assert "torch" not in sys.modules
    write_json(
        output,
        {
            "status": "passed-independent-masked-input-and-neural-field-audit",
            "plan": reference(root / "plan.json"),
            "backgrounds": reference(root / "backgrounds-collection.json"),
            "script": reference(__file__),
            "cases": cases,
            "background_fields": fields,
            "finite_FP32_channels_checked": channels,
            "independent_imputation_max_abs": maximum,
            "new_neural_forwards": 0,
            "Torch_imported": False,
            "GT_reference_or_parent_arrays_loaded": 0,
            "scope": "Exact source/argument hashes, discovery retained exactly in every CFA phase, actual NaN withholding, independent explicit Gaussian stencil and complete finite native fields. Frozen producer asserts checkpoint/backbone unchanged and counts root/encoder calls; this audit does not replay or independently verify model execution.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    audit(args.root.resolve(), args.output.resolve())
