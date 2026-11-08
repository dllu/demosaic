"""Independent QR native spectra, sparse distance masks and Decimal summaries."""

import math
import os
import sys
import time
from collections import defaultdict
from decimal import Decimal, localcontext

import numpy as np
import psutil
from green_phase_spectrum import tapered_spectrum
from phase_admission_protocol import owner_live, read, ref
from report_native_alias_geometry import (
    METHODS,
    REPO,
    ROOT,
    fingerprint,
    guard,
    lines,
    resources,
    save,
)


def qr_native_power(signal):
    h, w = signal.shape[-2:]
    y, x = np.meshgrid(np.linspace(-1, 1, h), np.linspace(-1, 1, w), indexing="ij")
    window = np.hanning(h)[:, None] * np.hanning(w)[None, :]
    design = np.stack([np.ones_like(x), x, y], -1).reshape(-1, 3) * window.reshape(-1, 1)
    q = np.linalg.qr(design, mode="reduced")[0]
    power = np.zeros((h, w))
    for plane in signal[0]:
        weighted = (plane - plane[0, 0]).ravel() * window.ravel()
        residual = weighted - q @ (q.T @ weighted)
        power += abs(np.fft.fft2(residual.reshape(h, w), norm="ortho")) ** 2
    return power


def sparse_native_indices(shape, bins, radius, *, aliases):
    # Build native coordinates from fftfreq, then expand a Cartesian product of
    # unique axis neighborhoods. No production masks or signed-bin helper.
    axes = [np.rint(np.fft.fftfreq(n) * n).astype(int) for n in shape]
    indices = set()
    for y, x in bins:
        for ay in range(2 if aliases else 1):
            for ax in range(2 if aliases else 1):
                cy, cx = axes[0][y] + ay * shape[0], axes[1][x] + ax * shape[1]
                for sign in [-1, 1]:
                    ys = (sign * cy + np.arange(-radius, radius + 1)) % (2 * shape[0])
                    xs = (sign * cx + np.arange(-radius, radius + 1)) % (2 * shape[1])
                    indices.update((ys[:, None] * (2 * shape[1]) + xs[None, :]).ravel().tolist())
    return np.asarray(sorted(indices), dtype=int)


def reference_summary(power, shape, bins, radius):
    h, w = power.shape
    y = np.minimum(np.arange(h), h - np.arange(h))[:, None]
    x = np.minimum(np.arange(w), w - np.arange(w))[None, :]
    strict = (4 * y < h) & (4 * x < w)
    closed = (4 * y <= h) & (4 * x <= w)
    radial = (y / h) ** 2 + (x / w) ** 2
    total = math.fsum(power.ravel())
    principal = sparse_native_indices(shape, bins, radius, aliases=False)
    all_lifts = sparse_native_indices(shape, bins, radius, aliases=True)
    added = np.setdiff1d(all_lifts, principal)
    regions = {
        "strict_principal_square": strict,
        "quarter_cycle_boundary": closed & ~strict,
        "outside_closed_principal_square": ~closed,
        "native_radial_1over16_to_1over3": (radial >= (1 / 16) ** 2) & (radial <= (1 / 3) ** 2),
    }
    result = {key: float(power[mask].sum() / total) for key, mask in regions.items()}
    result.update(
        principal_carrier_proximity=float(power.ravel()[principal].sum() / total),
        four_lift_carrier_proximity=float(power.ravel()[all_lifts].sum() / total),
        added_alias_proximity=float(power.ravel()[added].sum() / total),
        principal_footprint_cells=len(principal),
        four_lift_footprint_cells=len(all_lifts),
    )
    return result


def audit():
    plan, result = read(ROOT / "plan-v1.json"), read(ROOT / "result-v1.json")
    guard(plan)
    assert ref(__file__) == plan["auditor"] and result["plan"] == ref(ROOT / "plan-v1.json")
    assert (
        not owner_live(result["owner"])
        and result["owner"] == read(ROOT / "launch-v1.json")["owner"]
    )
    assert not (ROOT / "failure-v1.json").exists()
    assert not (ROOT / "verification-v1.json").exists()
    os.nice(10)
    os.sched_setaffinity(0, [8, 9])
    inputs = lines(result["input_journal"]["path"])
    rows = lines(result["template_journal"]["path"])
    completion = read(result["input_completion"]["path"])
    assert (
        completion["target_reads_before_close"] == 0
        and completion["journal"] == result["input_journal"]
    )
    for key in ["input_completion", "input_journal", "template_journal"]:
        assert ref(result[key]["path"]) == result[key]
    assert len(inputs) == 550 and len(rows) == 2048
    source = {}
    ids = {c["id"] for c in plan["cases"]}
    for method, label in METHODS.items():
        version = method.split("_")[0]
        source[method] = {
            r["id"]: r
            for r in lines(plan["dependency"][version + "_journal"]["path"])
            if r["method"] == label and r["id"] in ids
        }
    old = {r["id"]: r for r in lines(plan["dependency"]["diversity_inputs"]["path"])}
    indexed = {(r["id"], r["method"], r["neighborhood"]): r for r in rows}
    assert len(indexed) == 2048
    cache, max_error = {}, 0.0
    hashes = comparisons = 0
    with (ROOT / "audit-progress-v1.jsonl").open("x") as progress:
        for n, (case, selection) in enumerate(zip(plan["cases"], inputs, strict=True)):
            resources(plan)
            assert selection["id"] == case["id"] and selection["index"] == n
            assert ref(case["arrays"]["path"]) == case["arrays"] == selection["arrays"]
            with np.load(case["arrays"]["path"], allow_pickle=False) as a:
                for key in ["packed", "variance", "colors"]:
                    value = fingerprint(a[key])
                    assert value == selection["inputs"][key] == old[case["id"]]["inputs"][key]
                    assert all(value == source[m][case["id"]]["inputs"][key] for m in METHODS)
                    hashes += 1
                for method in METHODS:
                    s = source[method][case["id"]]["pooled"]["selection"]
                    expected = [
                        s["bin_yx"][0][direction][rank]
                        for rank in range(4)
                        for direction in range(2)
                    ]
                    assert (
                        selection["bins"][method]
                        == expected
                        == old[case["id"]]["bins"][
                            "V187_actual8" if method == "V187_actual8" else "spaced8"
                        ]
                    )
                if case["kind"] != "mesh":
                    continue
                # Independent spelling retains the same FP32 clipping boundary.
                present, empty = a["target_present"].copy(), a["target_empty"].copy()
                present[present <= 0] = 0
                empty[empty <= 0] = 0
                signal = present.astype(np.float64) - empty.astype(np.float64)
            signal_hash = fingerprint(signal)
            digest = signal_hash["sha256"]
            if digest not in cache:
                exact_power = sum(
                    abs(tapered_spectrum(plane)["spectrum"]) ** 2 for plane in signal[0]
                )
                cache[digest] = (qr_native_power(signal), fingerprint(exact_power))
            power, exact_power_hash = cache[digest]
            shape = tuple(selection["shape"])
            for method in METHODS:
                for label, radius in [("near1", 1), ("localwidth", (max(shape) + 64) // 65)]:
                    row = indexed[case["id"], method, label]
                    assert (
                        row["template_native_values"] == signal_hash
                        and row["present"] == case["present"]
                        and row["radius"] == radius
                        and row["native_power"] == exact_power_hash
                    )
                    expected = reference_summary(power, shape, selection["bins"][method], radius)
                    for field, value in expected.items():
                        error = abs(value - row[field])
                        max_error = max(max_error, error)
                        assert error <= 2e-12 * max(1, abs(value)), (
                            case["id"],
                            method,
                            label,
                            field,
                            value,
                            row[field],
                        )
                        comparisons += 1
                    assert (
                        abs(
                            row["principal_carrier_proximity"]
                            + row["added_alias_proximity"]
                            - row["four_lift_carrier_proximity"]
                        )
                        < 2e-14
                    )
            if (n + 1) % 100 == 0:
                progress.write(
                    __import__("json").dumps({"case": n + 1, "checks": comparisons}) + "\n"
                )
                progress.flush()
                print("audited-native-case", n + 1, flush=True)
    groups = defaultdict(list)
    for row in rows:
        groups[row["present"], row["method"], row["neighborhood"]].append(row)
    means = 0
    for group in result["summary"]:
        data = groups[group["present"], group["method"], group["neighborhood"]]
        assert len(data) == group["cases"] == 256
        for field, stats in group.items():
            if field in ["present", "method", "neighborhood", "cases"]:
                continue
            ordered = sorted(r[field] for r in data)
            with localcontext() as ctx:
                ctx.prec = 50
                mean = float(sum(Decimal(str(v)) for v in ordered) / len(ordered))
            assert abs(mean - stats["mean"]) <= 1e-12 * max(1, abs(mean))
            for label, q in [("median", 0.5), ("p10", 0.1), ("p90", 0.9)]:
                at = q * (len(ordered) - 1)
                lo, hi = math.floor(at), math.ceil(at)
                value = ordered[lo] + (at - lo) * (ordered[hi] - ordered[lo])
                assert abs(value - stats[label]) <= 1e-12 * max(1, abs(value))
            means += 1
    assert (
        len(cache) == result["unique_template_values"] and hashes == 1650 and comparisons == 18432
    )
    assert "torch" not in sys.modules and "rawpy" not in sys.modules
    guard(plan)
    save(
        ROOT / "verification-v1.json",
        {
            "status": "pass-independent-native-QR-spectra-all-footprints-and-Decimal-summaries",
            "plan": ref(ROOT / "plan-v1.json"),
            "result": ref(ROOT / "result-v1.json"),
            "source": dict(ref(__file__), text=__import__("pathlib").Path(__file__).read_text()),
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "input_fingerprints": hashes,
            "bound_saved_selection_bridges": 1100,
            "independent_native_template_case_records": 512,
            "unique_QR_native_template_values": len(cache),
            "independent_fraction_and_cell_checks": comparisons,
            "Decimal_summary_means": means,
            "maximum_fraction_or_cell_error": max_error,
            "new_neural_forwards": 0,
            "new_source_noise_draws": 0,
        },
    )
    print(
        f"PASS1650inputfingerprints/512QRtemplates/{comparisons}fraction-cell-checks/{means}Decimalmeans",
        flush=True,
    )


if __name__ == "__main__":
    audit()
