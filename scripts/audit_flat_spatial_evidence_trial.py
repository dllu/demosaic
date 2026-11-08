"""Audit matched training and saved quality evidence without neural forwards.

Pure validators can be exercised on explicitly labeled structural fixtures.
Actual audits require the terminal scientific owners and completed results.
"""

import argparse
import json
import math
from collections import Counter, defaultdict
from decimal import Decimal, localcontext
from pathlib import Path

import numpy as np
from phase_admission_protocol import owner_live, read, ref
from train_flat_spatial_evidence_trial import ARMS, METHODS, ROOT, factory, guard, save

TERMS = [
    "pixel",
    "gradient",
    "local_regret",
    "DC_regret",
    "flat_anchor",
    "pair_difference",
    "pair_common",
    "flat_spatial",
]


def loss_from_terms(terms, domain_weight):
    if set(terms) != set(TERMS) or not all(np.isfinite(v) for v in terms.values()):
        raise ValueError("Expected exactly eight finite loss terms")
    t = {key: np.float32(value) for key, value in terms.items()}
    value = np.float32(t["pixel"] + np.float32(0.25) * t["gradient"])
    for term in [
        t["local_regret"],
        t["DC_regret"],
        np.float32(0.25) * t["flat_anchor"],
        t["pair_difference"],
        t["pair_common"],
    ]:
        value = np.float32(value + term)
    # Preserve the original seven-term FP32 total before adding the new loss.
    base = np.float32(np.float32(domain_weight) * value)
    return float(np.float32(base + np.float32(0.25 * domain_weight) * t["flat_spatial"]))


def validate_training_trace(trace, cache, units, inherited_trace, plan, arm):
    """Check source bindings, independent FP32 totals, masks and call clocks."""
    assert (
        arm in ARMS
        and len(trace) == len(cache) == len(units) == len(inherited_trace) == plan["steps"]
    )
    counts = dict.fromkeys(["wrapper", "frozen", "network", "sampler", "projection"], 0)
    updates = skips = images = 0
    domains = Counter()
    for step, (row, item, unit, old) in enumerate(
        zip(trace, cache, units, inherited_trace, strict=True), 1
    ):
        assert row["step"] == item["step"] == unit["step"] == old["step"] == step
        assert row["batch"] == item["arrays"] == unit["batch"] == old["batch"]
        assert row["parent"] == item["parent"] == old["parent"]
        assert row["domain"] == item["metadata"]["domain"] == old["domain"]
        assert type(row["noisy"]) is bool and row["noisy"] == old["noisy"]
        domains[row["domain"]] += 1
        phase = max(0, step - plan["warmup"]) / (plan["steps"] - plan["warmup"])
        lr = (
            plan["lr"]
            * min(1, step / plan["warmup"])
            * (0.1 + 0.9 * (1 + math.cos(math.pi * phase)) / 2)
        )
        assert row["lr"] == lr
        if row["noisy"]:
            updates += 1
            images += item["inputs"]["packed"]["shape"][0]
            counts = {
                "wrapper": updates,
                "frozen": updates,
                "network": updates,
                "sampler": 5 * updates,
                "projection": updates if arm == "evidence" else 0,
            }
            assert row["loss"] == loss_from_terms(
                row["terms"], plan["domain_weights"][row["domain"]]
            )
            assert (
                row["flat_mask"] == old["flat_mask"]
                and row["flat_eligible_pixels"] == old["flat_eligible_pixels"]
            )
            assert np.isfinite(row["gradient_norm"]) and row["gradient_norm"] >= 0
            assert np.isfinite(row["correction_RMS_DN16"]) and row["correction_RMS_DN16"] >= 0
            total = plan["initial_updates"] + updates
            assert row["EMA_decay"] == min(plan["EMA_decay"], (1 + total) / (10 + total))
        else:
            skips += 1
            assert row["skipped"] == "zero variance;no matching,projection or optimizer call"
            assert not any(key in row for key in ["loss", "terms", "EMA_decay", "flat_mask"])
        assert row["updates"] == updates and row["counts"] == counts
        assert row["total_network_updates"] == plan["initial_updates"] + updates
    assert updates == plan["new_updates_per_arm"] and skips == plan["ADC_skips_per_arm"]
    assert images == plan["new_images_per_arm"]
    return {
        "rows": len(trace),
        "FP32_loss_totals": updates,
        "clean_masks": updates,
        "updates": updates,
        "ADC_skips": skips,
        "images": images,
        "counts": counts,
        "domains": dict(domains),
    }


def validate_evidence(evidence, packed_shape, colors, config):
    peaks = config["evidence_peaks"]
    batch, phases, height, width = packed_shape
    assert phases == 4 and set(evidence) == {
        "green_phase_indices",
        "bin_yx",
        "global_nominal_power",
        "valid",
        "local_center_power",
        "centers_y",
        "centers_x",
        "boxes_xywh",
    }
    green = np.asarray(evidence["green_phase_indices"])
    layout = np.asarray(colors)
    if layout.ndim == 1:
        layout = np.broadcast_to(layout, (batch, 4))
    assert layout.shape == (batch, 4)
    assert np.array_equal(green, np.where(layout == 1)[1].reshape(batch, 2))
    bins = np.asarray(evidence["bin_yx"])
    power = np.asarray(evidence["global_nominal_power"])
    valid = np.asarray(evidence["valid"])
    assert bins.shape == power.shape == (batch, 2, peaks, 2)
    assert np.issubdtype(bins.dtype, np.integer)
    assert valid.shape == (batch, 2, peaks) and valid.dtype == bool and valid.all()
    assert ((bins[..., 0] >= 0) & (bins[..., 0] < height)).all()
    assert ((bins[..., 1] >= 0) & (bins[..., 1] < width)).all()
    assert np.isfinite(power).all() and (power >= 0).all()
    window, stride = config["evidence_window"], config["evidence_stride"]
    assert type(window) is int and window >= 3 and window % 2 == 1
    assert type(stride) is int and 1 <= stride <= 512
    axes = []
    for length, key in [(height, "centers_y"), (width, "centers_x")]:
        expected = list(range(0, length, stride))
        if expected[-1] != length - 1:
            expected.append(length - 1)
        observed = np.asarray(evidence[key])
        assert np.issubdtype(observed.dtype, np.integer)
        assert np.array_equal(observed, expected)
        axes.append(expected)
    expected_boxes = []
    for y in axes[0]:
        for x in axes[1]:
            left, top = max(0, x - window // 2), max(0, y - window // 2)
            right, bottom = min(width, x + window // 2 + 1), min(height, y + window // 2 + 1)
            expected_boxes.append([left, top, right - left, bottom - top])
    boxes = np.asarray(evidence["boxes_xywh"])
    assert np.issubdtype(boxes.dtype, np.integer) and np.array_equal(boxes, expected_boxes)
    local = np.asarray(evidence["local_center_power"])
    assert local.shape == (batch, 2, peaks, 2, len(axes[0]), len(axes[1]))
    assert np.isfinite(local).all() and (local >= 0).all()
    fy = np.fft.fftfreq(height)[bins[..., 0]] / 2
    fx = np.fft.fftfreq(width)[bins[..., 1]] / 2
    radius = np.hypot(fy, fx)
    # The selector evaluates these band boundaries in FP32.
    assert ((radius >= 1 / 16 - 2e-8) & (radius <= 1 / 3 + 2e-8)).all()
    assert ((fy > 0) | ((fy == 0) & (fx > 0))).all()
    for rank in range(peaks):
        for earlier in range(rank):
            for selected in [bins[..., earlier, :], (-bins[..., earlier, :]) % [height, width]]:
                delta = np.abs(bins[..., rank, :] - selected)
                distance = np.minimum(delta, np.array([height, width]) - delta)
                assert (distance.max(axis=-1) > 1).all()


def validate_quality_stream(plan, scores, design, events, journal, case_inputs, frozen_rows):
    """Verify every durable row against actual cached inputs and frozen records."""
    methods = [METHODS[arm][endpoint] for arm in ARMS for endpoint in ["raw", "EMA"]]
    size = len(plan["processing_order"])
    assert len(events) == len(journal) == len(scores["rows"]) == len(methods) * size
    rows = {(row["id"], row["method"]): row for row in scores["rows"]}
    assert len(rows) == len(scores["rows"])
    counts = dict.fromkeys(["wrapper", "frozen", "network", "sampler", "projection"], 0)
    evidence_by_case = {}
    ADC = evidence_rows = input_fingerprints = 0
    for position, (event, record) in enumerate(zip(events, journal, strict=True)):
        method = methods[position // size]
        ordinal = position % size
        index = plan["processing_order"][ordinal]
        case = design[index]
        inputs = case_inputs[case["id"]]
        noisy = inputs["noisy"]
        candidate = method.startswith("V181-flat-spatial-")
        row = rows[case["id"], method]
        assert event["method"] == record["method"] == method
        assert event["index"] == record["index"] == index and event["ordinal"] == ordinal
        assert event["id"] == record["id"] == case["id"]
        assert record["row"] == row and row["index"] == index
        assert record["arrays"] == case["arrays"] and record["parent"] == case["parent"]
        assert record["inputs"] == inputs["fingerprints"]
        input_fingerprints += len(record["inputs"])
        assert type(event["matching_evaluated"]) is bool and event["matching_evaluated"] == noisy
        assert type(row["ADC_exact"]) is bool and row["ADC_exact"] == (not noisy)
        assert row["kind"] == case["kind"] and row["cohort"] == case.get("cohort")
        if case["kind"] == "mesh":
            assert row["present"] == case["present"] and row["seed"] == case["seed"]
        elif case["kind"] == "photo":
            assert row["variant"] == case["variant"]["name"]
        elif case["kind"] in ["flat", "mixed-quiet"]:
            assert row["noise"] == case["noise"]["name"]
        assert row["frozen_values"] == frozen_rows[case["id"]]["values"]
        assert (
            row["frozen_replay_exact"] and record["frozen_replay_exact"] and record["closure_exact"]
        )
        if case["kind"] == "real":
            assert row["reference_scored"] is False
            assert set(row) <= {
                "id",
                "index",
                "kind",
                "cohort",
                "method",
                "values",
                "frozen_values",
                "ADC_exact",
                "frozen_replay_exact",
                "reference_scored",
                "correction_RMS_DN16",
                "changed",
                "nonlocal_correction_values",
                "nonlocal_correction_RMS_DN16",
                "prediction",
            }
        if not noisy:
            assert row["values"] == row["frozen_values"]
            ADC += 1
        counts["wrapper"] += 1
        counts["frozen"] += 1
        counts["network"] += int(noisy)
        counts["sampler"] += 5 * int(noisy)
        counts["projection"] += int(candidate and noisy)
        assert event["counts"] == counts
        if candidate and noisy:
            validate_evidence(
                record["evidence"],
                inputs["packed_shape"],
                inputs["colors"],
                plan["module_config"],
            )
            if case["id"] in evidence_by_case:
                assert record["evidence"] == evidence_by_case[case["id"]]
            else:
                evidence_by_case[case["id"]] = record["evidence"]
            evidence_rows += 1
        else:
            assert record["evidence"] is None
    assert counts == scores["counts"] == plan["expected_quality_counts"]
    assert scores["exact_V169_replays"] == len(events) and scores["ADC_outputs_exact_V169"] == ADC
    assert scores["weights_unchanged"] and scores["RNG_unchanged"]
    return {
        "events": len(events),
        "input_fingerprints": input_fingerprints,
        "counts": counts,
        "exact_frozen_replay_bindings": len(events),
        "ADC_outputs": ADC,
        "evidence_rows": evidence_rows,
        "exact_input_only_raw_EMA_evidence_pairs": len(evidence_by_case),
    }


def validate_summary(rows, summary):
    groups = defaultdict(list)
    for row in rows:
        groups[
            row["kind"],
            row.get("present", row.get("variant", row.get("noise"))),
            row.get("cohort"),
            row["method"],
        ].append(row)
    assert len(summary) == len(groups)
    seen = set()
    checks = 0
    for row in summary:
        key = row["kind"], row["condition"], row["cohort"], row["method"]
        assert key not in seen
        seen.add(key)
        selected = groups[key]
        assert row["cases"] == len(selected)
        numeric = {
            field
            for field in selected[0]
            if field.endswith(("DN16", "gain", "error"))
            and all(
                isinstance(r.get(field), (int, float)) and not isinstance(r.get(field), bool)
                for r in selected
            )
        }
        assert set(row) == numeric | {"kind", "condition", "cohort", "method", "cases"}
        for field in numeric:
            with localcontext() as context:
                context.prec = 60
                value = float(
                    sum(Decimal.from_float(float(r[field])) for r in selected)
                    / Decimal(len(selected))
                )
            assert abs(row[field] - value) < 1e-10
            checks += 1
    return checks


def terminal(path):
    path = Path(path)
    phase = "review" if path.name == "scores-v1.json" else path.name.removesuffix("-result-v1.json")
    launch = read(path.parent / f"{phase}-launch-v1.json")
    assert not owner_live(launch["owner"])
    assert not (path.parent / f"{phase}-failure-v1.json").exists()
    result = read(path)
    assert result["owner"] == launch["owner"] and result["status"].startswith("completed")
    return result


def restore_on_CPU(module, state, *, lr, weight_decay):
    """Restore actual Adam/EMA while treating saved CUDA RNG as bytes only."""
    from phase_evidence_training_state import restore_matching_state

    return restore_matching_state(
        module, {**state, "CUDA_RNG": None}, lr=lr, weight_decay=weight_decay
    )


def audit_source(root, plan):
    seal = read(root / "audit-source-v1.json")
    assert ref(__file__) == seal["auditor"]
    assert seal["plan"] == ref(root / "plan-v1.json")
    assert seal["training_engine"] == plan["training_engine"]
    for binding in seal["helpers"]:
        assert ref(binding["path"]) == binding


def training_audit(root):
    plan = read(root / "plan-v1.json")
    guard(plan)
    audit_source(root, plan)
    for arm in ARMS:
        terminal(root / f"{arm}-train-result-v1.json")
    import torch
    from phase_evidence_training_state import adam_clocks, load_matching_ema
    from profile_raw_kernel_inference import model_hash

    assert not torch.cuda.is_initialized()
    plan = read(root / "plan-v1.json")
    guard(plan)
    audit_source(root, plan)
    initial = torch.load(plan["initial_checkpoint"]["path"], map_location="cpu", weights_only=True)
    # The retained V172 trace contains the same cached targets and masks.
    v172 = Path(plan["initial_checkpoint"]["path"]).parent.parent
    local_v172 = root.parent / v172.name
    parent_training = read(local_v172 / "train-result-v1.json")
    assert parent_training["final_checkpoint"] == plan["initial_checkpoint"]
    assert ref(parent_training["plan"]["path"]) == parent_training["plan"]
    inherited = read(parent_training["plan"]["path"])
    assert inherited["cache"] == plan["cache"] and inherited["pair_units"] == plan["pair_units"]
    cache = read(plan["cache"]["path"])["batches"]
    units = read(plan["pair_units"]["path"])["rows"]
    checked = {}
    for arm in ARMS:
        result = terminal(root / f"{arm}-train-result-v1.json")
        assert not (root / f"{arm}-train-failure-v1.json").exists()
        trace_path = root / f"{arm}-train-trace-v1.jsonl"
        trace = [json.loads(line) for line in trace_path.read_text().splitlines()]
        assert trace == result["trace"] and result["plan"] == ref(root / "plan-v1.json")
        check = validate_training_trace(trace, cache, units, parent_training["trace"], plan, arm)
        assert result["counts"] == check["counts"] and result["updates"] == check["updates"]
        assert (
            result["skipped_ADC"] == check["ADC_skips"]
            and result["training_images"] == check["images"]
        )
        assert result["initial_updates"] == plan["initial_updates"]
        assert result["frozen_unchanged"] and result["RNG_unchanged"]
        restoration = read(root / f"{arm}-restoration-v1.json")
        assert restoration == result["restoration"] and restoration["continued_at_row"] == 9
        assert restoration["repeated_prefix_forwards"] == 0
        assert all(
            restoration[k]
            for k in [
                "model_loaded_strictly",
                "Adam_exact",
                "EMA_exact",
                "CPU_RNG_exact",
                "CUDA_RNG_exact",
            ]
        )
        assert (
            len(result["checkpoints"]) == 5
            and result["final_checkpoint"] == result["checkpoints"][-1]
        )
        RNG = None
        for step, binding in zip([8, 250, 500, 750, 1000], result["checkpoints"], strict=True):
            assert ref(binding["path"]) == binding
            state = torch.load(binding["path"], map_location="cpu", weights_only=True)
            assert (
                state["arm"] == arm
                and state["step"] == step
                and state["updates"] == trace[step - 1]["updates"]
            )
            assert (
                state["initial_updates"] == plan["initial_updates"]
                and state["counts"] == trace[step - 1]["counts"]
            )
            assert (
                state["plan"] == ref(root / "plan-v1.json")
                and state["module_config"] == plan["module_config"]
            )
            assert all(
                torch.isfinite(v).all() for v in [*state["models"].values(), *state["ema"].values()]
            )
            frozen = [key for key in state["models"] if key.startswith("frozen.")]
            assert len(frozen) == 47 and all(
                torch.equal(state["models"][key], initial["models"][key]) for key in frozen
            )
            module = factory(arm, plan["module_config"])
            optimizer, ema, restored = restore_on_CPU(
                module, state, lr=plan["lr"], weight_decay=plan["weight_decay"]
            )
            assert (
                restored["Adam_exact"]
                and restored["CPU_RNG_exact"]
                and restored["CUDA_RNG_exact"] is None
            )
            # CPU audit must never restore CUDA RNG through a CUDA API.
            # CUDA_RNG is checked as saved bytes instead, below.
            raw_hash = model_hash(module)
            load_matching_ema(module, ema)
            EMA_hash = model_hash(module)
            assert (
                model_hash(module.frozen)
                == result["frozen_module_hash"]
                == plan["frozen_component"]["module_hash"]
            )
            clocks = adam_clocks(module, optimizer)
            if RNG is None:
                RNG = state["CPU_RNG"].clone(), state["CUDA_RNG"].clone()
            assert torch.equal(RNG[0], state["CPU_RNG"]) and torch.equal(RNG[1], state["CUDA_RNG"])
            if step == 1000:
                assert clocks == result["final_Adam_clocks"]
                check.update(
                    raw_module_hash=raw_hash, EMA_module_hash=EMA_hash, final_Adam_clocks=clocks
                )
            del module, optimizer, ema, state
        checked[arm] = dict(
            check, training=ref(root / f"{arm}-train-result-v1.json"), trace=ref(trace_path)
        )
    assert not torch.cuda.is_initialized()
    save(
        root / "training-audit-v1.json",
        {
            "status": "pass-flat-spatial-terminal-training-trace-five-checkpoints-clocks-and-EMA",
            "plan": ref(root / "plan-v1.json"),
            "arms": checked,
            "actual_neural_forwards": 0,
            "new_sensor_draws": 0,
            "CUDA_initialized": False,
            "source": dict(ref(__file__), text=Path(__file__).read_text()),
            "scope": "One full trace and five actual checkpoints checked without retraining or forward inference. Cached source bytes were checked by the actual worker; independent trace checks bind each row/unit/mask to inherited records. Adam/EMA/raw/frozen states are loaded strictly on CPU; saved CUDA RNG is compared as bytes.",
        },
    )


def quality_audit(root):
    plan = read(root / "plan-v1.json")
    guard(plan)
    audit_source(root, plan)
    terminal(root / "scores-v1.json")
    import torch
    from balanced_spatial_metrics import DetailMetrics
    from phase_evidence_training_state import load_matching_ema
    from profile_raw_kernel_inference import model_hash

    from demosaic.prediction_archive import fingerprint

    assert not torch.cuda.is_initialized()
    plan = read(root / "plan-v1.json")
    guard(plan)
    audit_source(root, plan)
    scores = terminal(root / "scores-v1.json")
    assert scores["plan"] == ref(root / "plan-v1.json")
    assert not (root / "review-failure-v1.json").exists()
    design = read(plan["design"]["path"])["observations"]
    assert len(design) == len(plan["processing_order"]) == 822
    assert len(set(plan["processing_order"])) == len({case["id"] for case in design}) == 822
    prior = read(plan["prior_scores"]["path"])
    frozen_rows = {row["id"]: row for row in prior["rows"] if row["method"] == "balanced-EMA"}
    events_path, journal_path = (
        root / "quality-events-v1.jsonl",
        root / "quality-observations-v1.jsonl",
    )
    events = [json.loads(line) for line in events_path.read_text().splitlines()]
    journal = [json.loads(line) for line in journal_path.read_text().splitlines()]
    metrics = DetailMetrics(plan["metrics_sources"])
    rows = {(row["id"], row["method"]): row for row in scores["rows"]}
    inputs = {}
    predictions = corrections = channels = scalars = 0
    methods = [METHODS[arm][endpoint] for arm in ARMS for endpoint in ["raw", "EMA"]]
    for index in plan["processing_order"]:
        case = design[index]
        assert (
            ref(case["arrays"]["path"]) == case["arrays"]
            and ref(case["parent"]["path"]) == case["parent"]
        )
        arrays = dict(np.load(case["arrays"]["path"], allow_pickle=False))
        base = np.load(case["parent"]["path"], allow_pickle=False)
        inputs[case["id"]] = {
            "noisy": bool(np.any(arrays["variance"] > 0)),
            "fingerprints": {
                key: fingerprint(arrays[key]) for key in ["packed", "variance", "colors", "wb"]
            },
            "packed_shape": arrays["packed"].shape,
            "colors": arrays["colors"].tolist(),
        }
        if case["id"] not in plan["native_cases"]:
            continue
        bindings = scores["native_predictions"][case["id"]]
        assert set(bindings) == set(methods) | {m + "-correction" for m in methods}
        frozen_binding = prior["native_predictions"][case["id"]]["balanced-EMA"]
        assert ref(frozen_binding["path"]) == frozen_binding
        frozen = np.load(frozen_binding["path"], allow_pickle=False)
        assert fingerprint(frozen) == frozen_rows[case["id"]]["values"]
        for method in methods:
            row = rows[case["id"], method]
            for key in [method, method + "-correction"]:
                assert ref(bindings[key]["path"]) == bindings[key]
            value = np.load(bindings[method]["path"], allow_pickle=False)
            correction = np.load(bindings[method + "-correction"]["path"], allow_pickle=False)
            assert (
                fingerprint(value) == row["values"]
                and fingerprint(correction) == row["nonlocal_correction_values"]
            )
            assert row["prediction"] == bindings[method]
            np.testing.assert_array_equal(value, frozen + correction)
            channels += value.size
            predictions += 1
            corrections += 1
            measured = metrics.measure(case, arrays, base, value)
            for field, observed in measured.items():
                if isinstance(observed, (float, int)) and not isinstance(observed, bool):
                    assert abs(observed - row[field]) < 1e-10
                    scalars += 1
                else:
                    assert observed == row[field]
            RMS = float(np.sqrt(np.mean(correction.astype(np.float64) ** 2))) * 65535
            assert abs(RMS - row["nonlocal_correction_RMS_DN16"]) < 1e-10
            scalars += 1
    assert (
        set(scores["native_predictions"]) == set(plan["native_cases"])
        and predictions == corrections == 72
    )
    checked = validate_quality_stream(plan, scores, design, events, journal, inputs, frozen_rows)
    means = validate_summary(scores["rows"], scores["summary"])
    endpoint_hashes = {}
    for arm in ARMS:
        training = terminal(root / f"{arm}-train-result-v1.json")
        binding = scores["checkpoints"][arm]
        assert binding == training["final_checkpoint"] and ref(binding["path"]) == binding
        state = torch.load(binding["path"], map_location="cpu", weights_only=True)
        module = factory(arm, plan["module_config"])
        module.load_state_dict(state["models"], strict=True)
        for endpoint in ["raw", "EMA"]:
            if endpoint == "EMA":
                load_matching_ema(module, state["ema"])
            method = METHODS[arm][endpoint]
            hashes = scores["module_hashes"][method]
            assert model_hash(module) == hashes["before"] == hashes["after"]
            assert (
                model_hash(module.frozen)
                == hashes["frozen"]
                == plan["frozen_component"]["module_hash"]
            )
            endpoint_hashes[method] = hashes["before"]
        del module, state
    assert not torch.cuda.is_initialized()
    save(
        root / "quality-audit-v1.json",
        {
            "status": "pass-flat-spatial-two-endpoint-stream-bindings-native-arrays-EMA-and-evidence",
            "plan": ref(root / "plan-v1.json"),
            "scores": ref(root / "scores-v1.json"),
            "stream": checked,
            "native_RGB_arrays": predictions,
            "native_residual_arrays": corrections,
            "independent_native_addition_channels": channels,
            "independently_recomputed_native_metric_scalars": scalars,
            "independent_Decimal_summary_means": means,
            "endpoint_hashes": endpoint_hashes,
            "forward_journal": ref(events_path),
            "observation_journal": ref(journal_path),
            "actual_neural_forwards": 0,
            "new_sensor_draws": 0,
            "CUDA_initialized": False,
            "source": dict(ref(__file__), text=Path(__file__).read_text()),
            "scope": "All 1644 actual durable method/input/frozen/ADC bindings checked. 72 native RGB plus 72 residual arrays independently remeasured; other outputs have journaled fingerprints/in-process metrics, not a full posthoc array archive. Input-only local-grid/global-selection metadata agrees exactly between raw/EMA for every noisy case; this is not independent spectral recomputation, confidence calibration or a quality/safety claim. Real ISO100 references remain unscored.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["training", "quality"])
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    {"training": training_audit, "quality": quality_audit}[args.phase](args.root)
