"""Independent QR/distance checks for V196; no inference or new selection design."""

import math
import sys
import time

import numpy as np
from audit_native_alias_geometry import qr_native_power, sparse_native_indices
from innovation_frequency_selection import VIEWS, pooled_score
from innovation_selection_reference import reference_score, reference_selection
from lossless_native import fingerprint, load_native
from phase_admission_protocol import owner_live
from report_innovation_selection import ROOT, checked_plan, lines, read, ref, save


def audit():
    plan = checked_plan()
    assert ref(__file__) == plan["auditor"]
    result = read(ROOT / "result-v1.json")
    closure = read(ROOT / "input-completion-v1.json")
    assert result["input_completion"] == ref(ROOT / "input-completion-v1.json")
    assert (
        result["input_journal"] == ref(ROOT / "input-selections-v2.jsonl.gz") == closure["journal"]
    )
    assert closure["new_target_array_accesses"] == closure["new_real_reference_accesses"] == 0
    assert not owner_live(closure["owner"])
    inputs = lines(result["input_journal"]["path"])
    assert len(inputs) == len(plan["cases"]) == 36
    coordinates = selected = region_checks = 0
    max_absolute = max_relative = 0.0
    saved = {}
    for item, row in zip(plan["cases"], inputs, strict=True):
        case = item["case"]
        assert row["id"] == case["id"] and row["prediction"] == item["prediction"]
        with np.load(case["arrays"]["path"], allow_pickle=False) as arrays:
            packed, variance, colors = [arrays[k] for k in ["packed", "variance", "colors"]]
        rgb = load_native(item["prediction"])
        prediction = np.empty_like(packed)
        for phase in range(4):
            prediction[:, phase] = rgb[:, int(colors[0, phase]), phase // 2 :: 2, phase % 2 :: 2]
        fields = {
            "RAW": packed.astype(np.float64),
            "innovation": packed.astype(np.float64) - prediction.astype(np.float64),
        }
        assert fingerprint(rgb) == row["restored"]
        for key, value in fields.items():
            assert fingerprint(value) == row["fields"][key]
            actual = pooled_score(value, variance, colors)
            expected = reference_score(value, variance, colors)
            np.testing.assert_allclose(actual, expected, rtol=5e-10, atol=1e-10)
            coordinates += actual.size
            max_absolute = max(max_absolute, float(abs(actual - expected).max()))
            max_relative = max(
                max_relative,
                float((abs(actual - expected) / np.maximum(abs(expected), 1e-8)).max()),
            )
            for name, (field, lower) in VIEWS.items():
                if field != key:
                    continue
                view = row["views"][name]
                assert fingerprint(actual) == view["score"]
                chosen = reference_selection(expected, lower)
                assert chosen == view["bins_yx_rank_order"]
                np.testing.assert_allclose(
                    [expected[y, x] for y, x in chosen],
                    view["nominal_scores"],
                    rtol=5e-10,
                    atol=1e-10,
                )
                low_count = 0
                for y, x in chosen:
                    fy = np.fft.fftfreq(actual.shape[0])[y] / 2
                    fx = np.fft.fftfreq(actual.shape[1])[x] / 2
                    low_count += math.hypot(fy, fx) < 1 / 16
                assert low_count == view["bins_below_old_lower"]
                selected += 1
        saved[row["id"]] = row
        print("audited", row["id"], flush=True)
    indexed = {(r["id"], r["view"], r["radius_native_bins"]): r for r in result["rows"]}
    assert len(indexed) == 16
    for item in plan["cases"]:
        case = item["case"]
        if case["id"] not in plan["geometry"]:
            continue
        row = saved[case["id"]]
        angles = plan["geometry"][case["id"]]["native_normals_radians"]
        with np.load(case["arrays"]["path"], allow_pickle=False) as arrays:
            template = arrays["target_present"].astype(np.float64) - arrays["target_empty"].astype(
                np.float64
            )
        power = qr_native_power(template)
        h, w = power.shape
        fy, fx = np.meshgrid(np.fft.fftfreq(h), np.fft.fftfreq(w), indexing="ij")
        direction = np.arctan2(fy, fx)
        labels = np.argmin(np.stack([abs(np.sin(direction - a)) for a in angles]), axis=0)
        labels[(fx == -0.5) | (fy == -0.5) | ((fx == 0) & (fy == 0))] = 2
        for name, view in row["views"].items():
            bins = view["bins_yx_rank_order"]
            for radius in [1, math.ceil(max(row["packed_shape"]) / 65)]:
                actual = indexed[case["id"], name, radius]
                assert actual["template"] == fingerprint(template)
                positions = sparse_native_indices(
                    tuple(row["packed_shape"]), bins, radius, aliases=False
                )
                proximity = np.zeros((h * w,), dtype=bool)
                proximity[positions] = True
                proximity = proximity.reshape(h, w)
                np.testing.assert_allclose(
                    actual["principal_proximity"],
                    float(power[proximity].sum() / power.sum()),
                    rtol=1e-10,
                    atol=1e-12,
                )
                for region in actual["regions"]:
                    mask = labels == region["region"]
                    energy = float(power[mask].sum())
                    np.testing.assert_allclose(
                        [region["GT_power_fraction"], region["principal_proximity"]],
                        [
                            energy / float(power.sum()),
                            float(power[mask & proximity].sum()) / energy,
                        ],
                        rtol=1e-9,
                        atol=1e-12,
                    )
                    region_checks += 2
                for index, (angle, period) in enumerate(
                    zip(angles, case["source"]["recipe"]["periods_final_pixels"], strict=True)
                ):
                    distances = []
                    for y, x in bins:
                        by = np.fft.fftfreq(h // 2)[y] * (h // 2)
                        bx = np.fft.fftfreq(w // 2)[x] * (w // 2)
                        for sign in [-1, 1]:
                            dy = (by - sign * h * math.sin(angle) / period + h / 2) % h - h / 2
                            dx = (bx - sign * w * math.cos(angle) / period + w / 2) % w - w / 2
                            distances.append(math.hypot(dy, dx))
                    np.testing.assert_allclose(
                        actual["fundamentals"][index]["minimum_distance_native_bins"],
                        min(distances),
                        rtol=1e-12,
                        atol=1e-12,
                    )
    assert selected == 144 and region_checks == 96 and "torch" not in sys.modules
    save(
        ROOT / "audit-v1.json",
        {
            "status": "pass144selectors72fullQRscoremaps16nativegeometryrows",
            "created_unix_UTC": time.time(),
            "plan": ref(ROOT / "plan-v2.json"),
            "result": ref(ROOT / "result-v1.json"),
            "input_completion": ref(ROOT / "input-completion-v1.json"),
            "score_coordinates": coordinates,
            "independent_QR_score_maps": 72,
            "independent_selected_bin_lists": selected,
            "independent_region_scalars": region_checks,
            "independent_fundamental_distances": 32,
            "maximum_score_absolute_difference": max_absolute,
            "maximum_score_relative_difference_with_1e-8_floor": max_relative,
            "all103_neural_hashes_unchanged": plan["neural103"],
            "new_neural_forwards": 0,
            "Torch_imported": False,
            "scope": plan["scope"],
        },
    )
    print("PASS144independent selections/72fullQRmaps/16geometry rows", flush=True)


if __name__ == "__main__":
    audit()
