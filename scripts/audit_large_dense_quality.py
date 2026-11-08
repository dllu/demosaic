"""Audit saved readout quality, exact inherited replay and ordered additions."""

import hashlib
import json
from pathlib import Path

import numpy as np
from audit_coherent_pair_evidence_trial import validate_evidence, validate_summary
from dense_spectrum_evidence_receipt import audit_samples, validate_dense
from lossless_native import load_native
from spatial_trial_protocol import open_text, owner_live, read, ref
from train_large_dense_trial import METHODS, ROOT, factory, guard, save


def fingerprint(value):
    return {
        "shape": list(value.shape),
        "dtype": value.dtype.str,
        "sha256": hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest(),
    }


def native_addition(value, inherited, wave):
    if any(
        v.dtype != np.float32 or v.ndim != 4 or v.shape[1] != 3 or not np.isfinite(v).all()
        for v in [value, inherited, wave]
    ):
        raise ValueError("Expected finite native FP32 camera RGB and wave arrays")
    if value.shape != inherited.shape or wave.shape != value.shape:
        raise ValueError("Native arrays must have identical unresized shapes")
    np.testing.assert_array_equal(value, inherited + wave)
    return value.size


def validate_stream(plan, scores, design, events, journal, inputs, baseline, frozen):
    methods = list(METHODS.values())
    order = plan["processing_order"]
    assert len(events) == len(journal) == len(scores["rows"]) == 2 * len(design)
    scored = {(r["id"], r["method"]): r for r in scores["rows"]}
    assert len(scored) == len(scores["rows"])
    counts = dict.fromkeys(["wrapper", "frozen", "network", "sampler", "projection"], 0)
    head_calls = ADC = bindings = 0
    evidence = {}
    dense = {}
    for position, (event, record) in enumerate(zip(events, journal, strict=True)):
        endpoint, ordinal = divmod(position, len(order))
        index = order[ordinal]
        case = design[index]
        method = methods[endpoint]
        data = inputs[case["id"]]
        noisy = data["noisy"]
        row = scored[case["id"], method]
        assert event["index"] == record["index"] == row["index"] == index
        assert event["method"] == record["method"] == row["method"] == method
        assert (
            event["id"] == record["id"] == row["id"] == case["id"] and event["ordinal"] == ordinal
        )
        assert record["arrays"] == case["arrays"] and record["parent"] == case["parent"]
        assert record["inputs"] == data["fingerprints"]
        bindings += 4
        assert record["row"] == row and event["matching_evaluated"] == noisy
        assert (
            row["inherited_values"] == baseline[case["id"]]["values"]
            and row["frozen_values"] == frozen[case["id"]]["values"]
        )
        assert row["inherited_V183_EMA_replay_exact"] and row["frozen_V169_replay_exact"]
        assert (
            record["inherited_replay_exact"]
            and record["frozen_replay_exact"]
            and record["baseline_plus_wave_closure_exact"]
        )
        assert row["ADC_exact"] == (not noisy)
        if not noisy:
            assert row["values"] == row["inherited_values"] == row["frozen_values"]
            assert row["wave_correction_RMS_DN16"] == 0
            ADC += 1
        for key in counts:
            counts[key] += (
                5 * int(noisy)
                if key == "sampler"
                else (1 if key in ["wrapper", "frozen"] else int(noisy))
            )
        head_calls += int(noisy)
        assert event["counts"] == counts and event["readout_calls"] == head_calls
        if noisy:
            validate_evidence(
                record["evidence"], data["packed_shape"], data["colors"], plan["module_config"]
            )
            validate_dense(
                record["dense"], data["packed_shape"], data["colors"], plan["module_config"]
            )
            if case["id"] in dense:
                assert record["dense"] == dense[case["id"]]
            else:
                dense[case["id"]] = record["dense"]
            if case["id"] in evidence:
                assert record["evidence"] == evidence[case["id"]]
            else:
                evidence[case["id"]] = record["evidence"]
        else:
            assert record["evidence"] is record["dense"] is None
    assert counts == scores["counts"] == plan["expected_quality_counts"]
    assert (
        head_calls == scores["readout_calls"] == 1500
        and ADC == scores["ADC_outputs_exact_V169"] == 144
    )
    assert scores["exact_V183_EMA_replays"] == scores["exact_V169_replays"] == len(journal)
    assert scores["weights_unchanged"] and scores["RNG_unchanged"]
    return {
        "events": len(events),
        "input_fingerprints": bindings,
        "counts": counts,
        "readout_calls": head_calls,
        "V183_EMA_replay_bindings": len(events),
        "V169_replay_bindings": len(events),
        "ADC_outputs": ADC,
        "exact_input_only_raw_EMA_evidence_pairs": len(evidence),
        "exact_input_only_raw_EMA_dense_measurement_pairs": len(dense),
    }


def audit():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    seal = read(ROOT / "quality-audit-source-v1.json")
    assert ref(__file__) == seal["auditor"] and seal["plan"] == ref(ROOT / "plan-v1.json")
    for binding in seal["helpers"]:
        assert ref(binding["path"]) == binding
    launch = read(ROOT / "review-launch-v1.json")
    if owner_live(launch["owner"]):
        raise RuntimeError("Actual review is still live; no Torch import")
    assert not (ROOT / "review-failure-v1.json").exists()
    scores = read(ROOT / "scores-v1.json")
    assert (
        scores["owner"] == launch["owner"]
        and scores["status"]
        == "completed-two-endpoint-wave-readout-fixed-quality-awaiting-native-viewing"
    )
    assert scores["plan"] == ref(ROOT / "plan-v1.json")
    assert not (ROOT / "quality-audit-v1.json").exists()
    import torch
    from balanced_spatial_metrics import DetailMetrics
    from phase_wave_training_state import inherited_hash, load_ema
    from profile_raw_kernel_inference import model_hash
    from spatial_wave_training_state import expand_checkpoint

    assert not torch.cuda.is_initialized()
    torch.set_num_threads(1)
    baseline_scores = read(plan["baseline_scores"]["path"])
    baseline = {
        r["id"]: r for r in baseline_scores["rows"] if r["method"] == "V183-coherent-pair-EMA"
    }
    frozen = {
        r["id"]: r
        for r in read(plan["prior_scores"]["path"])["rows"]
        if r["method"] == "balanced-EMA"
    }
    design = read(plan["design"]["path"])["observations"]
    metric = DetailMetrics(plan["metrics_sources"])
    rows = {(r["id"], r["method"]): r for r in scores["rows"]}
    assert len(baseline) == len(frozen) == len(design) == 822
    assert sorted(plan["processing_order"]) == list(range(822))
    inputs = {}
    channels = predictions = waves = scalars = wave_scalars = 0
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
                k: fingerprint(arrays[k]) for k in ["packed", "variance", "colors", "wb"]
            },
            "packed_shape": arrays["packed"].shape,
            "colors": arrays["colors"].tolist(),
        }
        if case["id"] not in plan["native_cases"]:
            continue
        bindings = scores["native_predictions"][case["id"]]
        assert set(bindings) == set(METHODS.values()) | {m + "-wave" for m in METHODS.values()}
        inherited_binding = baseline_scores["native_predictions"][case["id"]][
            "V183-coherent-pair-EMA"
        ]
        assert ref(inherited_binding["path"]) == inherited_binding
        inherited = np.load(inherited_binding["path"], allow_pickle=False)
        assert fingerprint(inherited) == baseline[case["id"]]["values"]
        for method in METHODS.values():
            row = rows[case["id"], method]
            for key in [method, method + "-wave"]:
                assert ref(bindings[key]["path"]) == bindings[key]
            value = load_native(bindings[method])
            wave = load_native(bindings[method + "-wave"])
            assert (
                fingerprint(value) == row["values"]
                and fingerprint(wave) == row["wave_correction_values"]
            )
            assert row["prediction"] == bindings[method]
            channels += native_addition(value, inherited, wave)
            predictions += 1
            waves += 1
            rms = float(np.sqrt(np.mean(wave.astype(np.float64) ** 2))) * 65535
            assert abs(rms - row["wave_correction_RMS_DN16"]) < 1e-10
            wave_scalars += 1
            if not inputs[case["id"]]["noisy"]:
                assert not np.any(wave) and np.array_equal(value, inherited)
            measured = metric.measure(case, arrays, base, value)
            for field, observed in measured.items():
                if isinstance(observed, (float, int)) and not isinstance(observed, bool):
                    assert abs(observed - row[field]) < 1e-10
                    scalars += 1
                else:
                    assert observed == row[field]
    event_path, journal_path = (
        ROOT / "quality-events-v1.jsonl",
        ROOT / "quality-observations-v1.jsonl.gz",
    )
    events = [json.loads(line) for line in event_path.read_text().splitlines()]
    with open_text(journal_path) as stream:
        journal = [json.loads(line) for line in stream]
    stream = validate_stream(plan, scores, design, events, journal, inputs, baseline, frozen)
    sample_cases = sample_values = 0
    sample_errors = {}
    cases_by_id = {case["id"]: case for case in design}
    for record in journal:
        if record["method"] != METHODS["raw"] or record["dense"] is None:
            continue
        case = cases_by_id[record["id"]]
        with np.load(case["arrays"]["path"], allow_pickle=False) as archive:
            raw, var, colors = [archive[k] for k in ["packed", "variance", "colors"]]
        count, errors = audit_samples(record["dense"], raw, var, colors, plan["module_config"])
        sample_cases += 1
        sample_values += count
        for key, value in errors.items():
            sample_errors[key] = max(sample_errors.get(key, 0), value)
        if sample_cases % 100 == 0:
            print("independent-QR-dense-samples", sample_cases, flush=True)
    assert sample_cases == 750
    means = validate_summary(scores["rows"], scores["summary"])
    training = read(ROOT / "wave-train-result-v1.json")
    assert (
        scores["checkpoint"] == training["final_checkpoint"]
        and ref(scores["checkpoint"]["path"]) == scores["checkpoint"]
    )
    state = expand_checkpoint(
        torch.load(scores["checkpoint"]["path"], map_location="cpu", weights_only=True)
    )
    initial = torch.load(
        plan["initializer"]["export"]["path"], map_location="cpu", weights_only=True
    )
    hashes = {}
    for endpoint, method in METHODS.items():
        module = factory(plan["module_config"])
        module.load_state_dict(state["models"], strict=True)
        if endpoint == "EMA":
            load_ema(module, state["ema"])
        assert all(torch.equal(module.state_dict()[n], v) for n, v in initial["state_dict"].items())
        assert inherited_hash(module) == plan["initializer"]["module_hash"]
        assert scores["module_hashes"][method]["inherited"] == plan["initializer"]["module_hash"]
        assert (
            model_hash(module.frozen)
            == scores["module_hashes"][method]["frozen"]
            == plan["frozen_component"]["module_hash"]
        )
        assert (
            model_hash(module)
            == scores["module_hashes"][method]["before"]
            == scores["module_hashes"][method]["after"]
        )
        hashes[method] = model_hash(module)
    assert predictions == waves == 72 and not torch.cuda.is_initialized()
    save(
        ROOT / "quality-audit-v1.json",
        {
            "status": "pass-wave-readout-two-endpoint-inputs-inherited-replays-native-additions-and-EMA",
            "plan": ref(ROOT / "plan-v1.json"),
            "scores": ref(ROOT / "scores-v1.json"),
            "stream": stream,
            "independent_QR_sample_cases": sample_cases,
            "independent_QR_sample_real_coordinates": sample_values,
            "maximum_QR_sample_errors": sample_errors,
            "sample_scope": "Three deterministic patch centers and twelve eligible frequencies per input; fullfieldhashes bind raw/EMA input-only equality,not a claim of fullfieldQR recomputation.",
            "native_RGB_arrays": predictions,
            "native_wave_arrays": waves,
            "independent_native_baseline_plus_wave_channels": channels,
            "native_metric_scalars_recomputed": scalars,
            "native_wave_RMS_scalars_recomputed": wave_scalars,
            "independent_Decimal_summary_means": means,
            "endpoint_hashes": hashes,
            "inherited_tensor_comparisons": 378,
            "forward_journal": ref(event_path),
            "observation_journal": ref(journal_path),
            "actual_neural_forwards": 0,
            "new_sensor_source_draws": 0,
            "CUDA_initialized": False,
            "source": dict(ref(__file__), text=Path(__file__).read_text()),
        },
    )
    print(
        "PASS1644rows/3288inheritedReplayBindings/72RGB+72wave/",
        channels,
        "nativeAdditionChannels/",
        means,
        "means",
    )


if __name__ == "__main__":
    audit()
