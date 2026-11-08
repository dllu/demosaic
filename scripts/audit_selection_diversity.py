"""Audit closed V188 inputs, sorted QR selections, template fractions and local powers."""

import json
import math
import sys
from collections import defaultdict
from decimal import Decimal, localcontext
from pathlib import Path

import numpy as np
from frequency_coverage_reference import direct_local_power, independent_footprint
from phase_admission_protocol import owner_live, read, ref
from report_selection_diversity import METHODS, ROOT, fingerprint, lines, save
from selection_diversity_reference import (
    qr_pooled,
    qr_template_power,
    reference_proximity,
    sorted_pooled,
)


def sample(rgb, colors):
    return np.stack(
        [
            np.stack([v[int(c), i // 2 :: 2, i % 2 :: 2] for i, c in enumerate(layout)])
            for v, layout in zip(rgb, colors, strict=True)
        ]
    )


def decimal_summary(rows, keys, expected):
    groups = defaultdict(list)
    for r in rows:
        groups[tuple(r[k] for k in keys)].append(r)
    assert len(groups) == len(expected)
    checks = 0
    for entry in expected:
        key = tuple(entry[k] for k in keys)
        group = groups[key]
        assert entry["cases"] == len(group)
        for field, stats in entry.items():
            if field in keys or field == "cases":
                continue
            values = [r[field] for r in group]
            ordered = sorted(values)
            n = len(ordered)
            with localcontext() as ctx:
                ctx.prec = 50
                mean = float(sum(Decimal(str(v)) for v in values) / Decimal(n))
            assert abs(mean - stats["mean"]) < 1e-11 * max(1, abs(mean))
            for label, q in [("median", 0.5), ("p10", 0.1), ("p90", 0.9)]:
                at = q * (n - 1)
                lo = math.floor(at)
                hi = math.ceil(at)
                v = ordered[lo] + (at - lo) * (ordered[hi] - ordered[lo])
                assert abs(v - stats[label]) < 1e-11 * max(1, abs(v))
            checks += 1
    return checks


def audit():
    p = read(ROOT / "plan-v1.json")
    r = read(ROOT / "result-v1.json")
    seal = read(ROOT / "audit-source-v1.json")
    assert not owner_live(r["owner"]) and r["owner"] == read(ROOT / "launch-v1.json")["owner"]
    assert r["status"].startswith("completed-550input") and not (ROOT / "failure-v1.json").exists()
    assert seal["auditor"] == ref(__file__) and seal["plan"] == r["plan"] == ref(
        ROOT / "plan-v1.json"
    )
    for b in seal["helpers"] + p["sources"]:
        assert ref(b["path"]) == {k: b[k] for k in ["path", "sha256"]}
    for k in ["input_completion", "input_journal", "template_journal", "control_journal"]:
        assert ref(r[k]["path"]) == r[k]
    completion = read(r["input_completion"]["path"])
    assert completion["target_reads_before_close"] == 0
    inputs = lines(r["input_journal"]["path"])
    templates = lines(r["template_journal"]["path"])
    controls = lines(r["control_journal"]["path"])
    assert len(inputs) == 550 and len(templates) == 5120 and len(controls) == 200
    cases = {c["id"]: c for c in p["cases"]}
    source = {}
    import gzip

    with gzip.open(p["dependency"]["actual_selection_journal"]["path"], "rt") as f:
        for line in f:
            q = json.loads(line)
            if q["method"] == "V187-pooled-wave-raw" and q["id"] in cases:
                source[q["id"]] = q
    old = {q["id"]: q for q in lines(p["dependency"]["old_inputs"]["path"])}
    by_id = {q["id"]: q for q in inputs}
    assert len(source) == len(old) == len(by_id) == 550
    fingerprints = selections = 0
    max_power = max_score = max_fraction = max_local = 0.0
    qr_bins = qr_phase_values = 0
    subset = set(p["independent_case_ids"])
    with (ROOT / "audit-progress-v1.jsonl").open("x") as progress:
        for n, q in enumerate(inputs):
            c = cases[q["id"]]
            assert q["index"] == n and ref(c["arrays"]["path"]) == c["arrays"] == q["arrays"]
            with np.load(c["arrays"]["path"], allow_pickle=False) as a:
                raw, var, col = [a[k] for k in ["packed", "variance", "colors"]]
            assert q["inputs"] == {
                k: fingerprint(v)
                for k, v in zip(["packed", "variance", "colors"], [raw, var, col], strict=True)
            }
            assert all(
                v == source[c["id"]]["inputs"][k] == old[c["id"]]["inputs"][k]
                for k, v in q["inputs"].items()
            )
            fingerprints += 3
            assert (
                q["bins"]["V187_actual8"]
                == np.asarray(source[c["id"]]["pooled"]["selection"]["bin_yx"])[0]
                .transpose(1, 0, 2)
                .reshape(-1, 2)
                .tolist()
            )
            assert (
                q["bins"]["V185_actual8slots"]
                == np.asarray(old[c["id"]]["bins"]["actual_high4"]).reshape(-1, 2).tolist()
            )
            assert q["actual_FP64_bins_exact"] == (
                q["bins"]["V187_actual8"] == q["bins"]["FP64_pooled8"]
            )
            h, w = q["shape"]
            fy, fx = [np.fft.fftfreq(s) / 2 for s in (h, w)]
            for method in METHODS:
                bins = q["bins"][method]
                assert len(bins) == 8
                selections += 8
                for y, x in bins:
                    assert 1 / 16 - 1e-15 <= math.hypot(fy[y], fx[x]) <= 1 / 3 + 1e-15 and (
                        fy[y] > 0 or (fy[y] == 0 and fx[x] > 0)
                    )
                for label, radius in [("near1", 1), ("localwidth", math.ceil(max(h, w) / 65))]:
                    mask = independent_footprint((h, w), bins, radius)
                    geometry = q["stats"][method]["geometry_" + label]
                    assert geometry["footprint_cells"] == int(mask.sum())
                    assert geometry["slots"] == 8 and geometry["unique_bins"] == len(
                        set(map(tuple, bins))
                    )
                    assert (
                        abs(
                            geometry["overlap_fraction_of_unclipped_sum"]
                            - (1 - mask.sum() / (16 * (2 * radius + 1) ** 2))
                        )
                        < 1e-14
                    )
                    sectors = [
                        min(int((math.atan2(fy[y], fx[x]) % math.pi) / (math.pi / 4)), 3)
                        for y, x in bins
                    ]
                    assert geometry["occupied_sectors"] == len(set(sectors))
                if method == "sector8":
                    sector = [
                        min(int((math.atan2(fy[y], fx[x]) % math.pi) / (math.pi / 4)), 3)
                        for y, x in bins
                    ]
                    assert [sector.count(s) for s in range(4)] == [2] * 4
                if method in ["FP64_pooled8", "spaced8", "sector8"]:
                    radius = math.ceil(max(h, w) / 65) if method == "spaced8" else 1
                    for i, (y, x) in enumerate(bins):
                        for by, bx in bins[:i]:
                            for cy, cx in [(by, bx), ((-by) % h, (-bx) % w)]:
                                assert (
                                    min(abs(y - cy), h - abs(y - cy)) > radius
                                    or min(abs(x - cx), w - abs(x - cx)) > radius
                                )
            if q["id"] in subset:
                greens = np.flatnonzero(col[0] == 1)
                score, powers = qr_pooled(raw[0], var[0], greens)
                for method, radius, quota in [
                    ("FP64_pooled8", 1, None),
                    ("spaced8", math.ceil(max(h, w) / 65), None),
                    ("sector8", 1, 2),
                ]:
                    assert sorted_pooled(score, radius, quota) == q["bins"][method]
                    qr_bins += 8
                for method in METHODS:
                    y, x = np.asarray(q["bins"][method]).T
                    observed = np.asarray(q["stats"][method]["global_two_phase_power"])
                    expected = powers[:, y, x].T
                    max_power = max(max_power, float(abs(expected - observed).max()))
                    np.testing.assert_allclose(expected, observed, rtol=2e-10, atol=2e-10)
                    qr_phase_values += expected.size
                    expected = score[y, x]
                    observed = np.asarray(q["stats"][method]["pooled_scores"])
                    max_score = max(max_score, float(abs(expected - observed).max()))
                    np.testing.assert_allclose(expected, observed, rtol=2e-10, atol=2e-10)
            if (n + 1) % 100 == 0:
                print("audit-inputs", n + 1, flush=True)
        lookup = {(q["id"], q["method"], q["neighborhood"]): q for q in templates}
        assert len(lookup) == len(templates)
        checked_templates = sector_values = 0
        for c in p["cases"]:
            if c["kind"] != "mesh":
                continue
            with np.load(c["arrays"]["path"], allow_pickle=False) as a:
                col = a["colors"]
                present = np.maximum(a["target_present"], np.float32(0))
                empty = np.maximum(a["target_empty"], np.float32(0))
            signal = sample(present, col).astype(float) - sample(empty, col).astype(float)
            greens = np.flatnonzero(col[0] == 1)
            power = qr_template_power(signal[0], greens)
            for method in METHODS:
                for label, radius in [
                    ("near1", 1),
                    ("localwidth", math.ceil(max(power.shape) / 65)),
                ]:
                    q = lookup[c["id"], method, label]
                    assert (
                        q["present"] == c["present"]
                        and q["radius"] == radius
                        and q["template_sensor_values"] == fingerprint(signal)
                    )
                    fraction, details = reference_proximity(
                        power, by_id[c["id"]]["bins"][method], radius
                    )
                    err = abs(fraction - q["template_fraction"])
                    max_fraction = max(max_fraction, err)
                    assert err < 2e-11
                    for degree, fields in details.items():
                        for field, expected in fields.items():
                            actual = q["sector_details"][degree][field]
                            np.testing.assert_allclose(actual, expected, rtol=2e-10, atol=2e-11)
                            sector_values += np.asarray(expected).size
                    assert (
                        q["minimum_substantial_sector_fraction_0"]
                        == q["sector_details"]["0"][
                            "minimum_proximity_among_sectors_with_at_least_5percent_power"
                        ]
                    )
                    assert (
                        q["minimum_substantial_sector_fraction_22p5"]
                        == q["sector_details"]["22.5"][
                            "minimum_proximity_among_sectors_with_at_least_5percent_power"
                        ]
                    )
                    checked_templates += 1
            if checked_templates % 500 == 0:
                print("audit-template-fractions", checked_templates, flush=True)
        local_count = 0
        cache = {}
        current = None
        arrays = None
        for q in controls:
            c = cases[q["id"]]
            if current != q["id"]:
                with np.load(c["arrays"]["path"], allow_pickle=False) as a:
                    arrays = {k: a[k] for k in ["packed", "variance", "colors"]}
                cache = {}
                current = q["id"]
            raw, var, col = [arrays[k] for k in ["packed", "variance", "colors"]]
            greens = np.flatnonzero(col[0] == 1)
            assert q["bins"] == by_id[q["id"]]["bins"][q["method"]]
            regions = (
                [{"name": c["id"], "ROI_xywh": c["ROI_xywh"]}]
                if "ROI_xywh" in c
                else c["source"]["cases"]
            )
            region = next(v for v in regions if v["name"] == q["ROI_name"])
            assert q["ROI_xywh"] == region["ROI_xywh"]
            x, y, w, h = q["ROI_xywh"]
            center = [(y + h // 2) // 2, (x + w // 2) // 2]
            assert q["center_packed_yx"] == [center] and q["window"] == 65
            for j, bin_yx in enumerate(q["bins"]):
                for phase, g in enumerate(greens):
                    key = (q["ROI_name"], int(g), *bin_yx)
                    if key not in cache:
                        cache[key] = direct_local_power(raw[0, g], var[0, g], bin_yx, center, 65)
                    value = cache[key]
                    actual = q["local_two_phase_power"][j][phase]
                    err = abs(value - actual)
                    max_local = max(max_local, err)
                    assert err < 2e-8 * max(1, abs(value))
                    local_count += 1
            assert q["local_max_min_phase_power"] == float(
                np.asarray(q["local_two_phase_power"]).min(1).max()
            )
            assert (
                q["global_max_min_phase_power"]
                == by_id[q["id"]]["stats"][q["method"]]["global_max_min_phase_power"]
            )
        means = decimal_summary(
            templates, ["method", "present", "neighborhood"], r["template_summary"]
        ) + decimal_summary(controls, ["method", "kind"], r["control_summary"])
        pairs = []
        for candidate, baseline in [
            ("V187_actual8", "V185_actual8slots"),
            ("spaced8", "V187_actual8"),
            ("sector8", "V187_actual8"),
        ]:
            for present in [True, False]:
                for neighborhood in ["near1", "localwidth"]:
                    rows = [
                        q
                        for q in templates
                        if q["method"] == candidate
                        and q["present"] == present
                        and q["neighborhood"] == neighborhood
                    ]
                    for field in [
                        "template_fraction",
                        "minimum_substantial_sector_fraction_0",
                        "minimum_substantial_sector_fraction_22p5",
                    ]:
                        a = [q[field] for q in rows]
                        b = [lookup[q["id"], baseline, neighborhood][field] for q in rows]
                        diff = [x - y for x, y in zip(a, b, strict=True)]
                        pairs.append(
                            {
                                "candidate": candidate,
                                "baseline": baseline,
                                "present": present,
                                "neighborhood": neighborhood,
                                "field": field,
                                "cases": len(rows),
                                "mean_candidate": math.fsum(a) / len(a),
                                "mean_baseline": math.fsum(b) / len(b),
                                "mean_difference": math.fsum(diff) / len(diff),
                                "increased": sum(v > 0 for v in diff),
                                "decreased": sum(v < 0 for v in diff),
                                "equal": sum(v == 0 for v in diff),
                            }
                        )
        progress.write(
            json.dumps(
                {
                    "checked_inputs": 550,
                    "checked_template_fractions": checked_templates,
                    "checked_local_powers": local_count,
                }
            )
            + "\n"
        )
    assert "torch" not in sys.modules and "rawpy" not in sys.modules
    proof = {
        "status": "pass-closed-inputs-independent-sorted-QR-template-proximity-local-powers-and-Decimal-summaries",
        "plan": r["plan"],
        "result": ref(ROOT / "result-v1.json"),
        "source": dict(ref(__file__), text=Path(__file__).read_text()),
        "input_fingerprints": fingerprints,
        "actual_and_counterfactual_bin_records_bound": selections,
        "independent_QR_ranked_bins_first12cases": qr_bins,
        "independent_QR_global_phase_powers_first12cases": qr_phase_values,
        "all512_independent_QR_template_fractions": checked_templates,
        "independent_sector_summary_values": sector_values,
        "all_independent_ROI_powers": local_count,
        "independent_Decimal_means": means,
        "maximum_global_phase_power_error": max_power,
        "maximum_pooled_score_error": max_score,
        "maximum_template_fraction_error": max_fraction,
        "maximum_local_power_error": max_local,
        "paired_template_contrasts": pairs,
        "new_neural_forwards": 0,
        "new_source_noise_draws": 0,
    }
    save(ROOT / "verification-v1.json", proof)
    print(
        "PASS550inputs/288QRbins/5120QRfractions/3200ROI-powers/", means, "Decimalmeans", flush=True
    )


if __name__ == "__main__":
    audit()
