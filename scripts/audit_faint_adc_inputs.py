"""Independent high-precision audit of new faint-photographic ADC observations."""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
from train_directional_bank_trial import guard, read, ref, save


def audit(path):
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or "torch" in sys.modules:
        raise RuntimeError("Input audit requires CPU/NumPy without Torch")
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    plan = read(path)
    guard(plan)
    root = Path(plan["root"])
    (root / "input-audit.claim").open("x").close()
    patterns = {
        "RGGB": (0, 1, 1, 2),
        "BGGR": (2, 1, 1, 0),
        "GRBG": (1, 0, 2, 1),
        "GBRG": (1, 2, 0, 1),
    }
    count = target_values = packed_values = 0
    bins = []
    for case in plan["cases"]:
        original = case["original_target"]
        assert ref(original["path"]) == original and ref(case["target"]["path"]) == case["target"]
        with np.load(original["path"], allow_pickle=False) as data:
            source, wb, matrix = [data[k] for k in ("target", "wb", "matrix")]
        with np.load(case["target"]["path"], allow_pickle=False) as data:
            actual = data["target"]
            np.testing.assert_array_equal(wb, data["wb"])
            np.testing.assert_array_equal(matrix, data["matrix"])
        # Long-double scalar channel sums and rational contrast, independent of
        # the primary vectorized FP64 mean/contrast implementation.
        expected = np.empty_like(source)
        for channel in range(3):
            value = source[0, channel].astype(np.longdouble)
            dc = np.sum(value, dtype=np.longdouble) / (256 * 256)
            expected[0, channel] = (value / 40 + dc * np.longdouble(39) / 40).astype(np.float32)
        np.testing.assert_array_equal(actual, expected)
        target_values += actual.size
        assert np.isfinite(actual).all() and actual.shape == (1, 3, 256, 256)
        observations = [o for o in plan["observations"] if o["case_id"] == case["id"]]
        assert {o["pattern"] for o in observations} == set(patterns)
        for observation in observations:
            assert ref(observation["arrays"]["path"]) == observation["arrays"]
            with np.load(observation["arrays"]["path"], allow_pickle=False) as data:
                for phase, (y, x) in enumerate(((0, 0), (0, 1), (1, 0), (1, 1))):
                    channel = patterns[observation["pattern"]][phase]
                    signal = actual[0, channel, y::2, x::2].astype(np.longdouble)
                    adc = (signal * 97 + 3) / 100
                    code = np.floor(adc.clip(0, 1) * 65535 + np.longdouble("0.5"))
                    reconstructed = ((code * 100 / 65535 - 3) / 97).astype(np.float32)
                    np.testing.assert_array_equal(data["packed"][0, phase], reconstructed)
                np.testing.assert_array_equal(data["variance"], np.zeros_like(data["packed"]))
                np.testing.assert_array_equal(
                    data["colors"], np.array([patterns[observation["pattern"]]], np.int64)
                )
                np.testing.assert_array_equal(data["wb"], wb)
                np.testing.assert_array_equal(data["matrix"], matrix)
                packed_values += data["packed"].size
                assert data["packed"].dtype == np.float32 and data["packed"].shape == (
                    1,
                    4,
                    128,
                    128,
                )
            assert observation["noise"]["shot"] == observation["noise"]["read"] == 0
            assert (
                observation["ROI_xywh"] == [48, 48, 160, 160]
                and observation["display_exposure"] == 1
            )
            count += 1
        bins.append(
            {
                "case": case["id"],
                "source_id": case["source_id"],
                "reference_role": case["reference_role"],
            }
        )
    assert count == 16 and target_values == 786432 and packed_values == 1048576
    assert (
        plan["planned_new_root_forwards_total"] == plan["planned_new_encoder_forwards_total"] == 48
    )
    save(
        root / "input-audit-v1.json",
        {
            "status": "passed-independent-faint-target-and-ADC-preparation-audit",
            "plan": ref(path),
            "auditor": ref(__file__),
            "observations": count,
            "target_FP32_values_exact": target_values,
            "packed_ADC_FP32_values_exact": packed_values,
            "cases": bins,
            "new_neural_forwards": 0,
            "optimizer_updates": 0,
            "stochastic_noise_draws": 0,
            "RAW_decodes": 0,
            "Torch_imported": False,
            "scope": "Long-double rational DC/contrast and independently reconstructed ADC codes/FP32 normalization, every target/phase/site; CFA/WB/matrix/zero variance/ROI/exposure checked. Does not prove restoration quality or independence of conditions from one source.",
        },
    )
    print(
        {
            "observations": count,
            "target_values_exact": target_values,
            "ADC_values_exact": packed_values,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    audit(parser.parse_args().plan.resolve())
