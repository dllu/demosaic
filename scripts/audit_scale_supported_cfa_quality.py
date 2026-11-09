"""Independent two-endpoint V200 stream, native RGB/wave, and strict-state audit."""

import hashlib
import json
from pathlib import Path

import numpy as np
from admit_scale_supported_cfa_wave import MODES, factory
from audit_coherent_pair_evidence_trial import validate_evidence, validate_summary
from cfa_wave_evidence_receipt import validate_cfa
from directional_trial_protocol import guard, save
from frequency_coverage import sample_camera_rgb
from lossless_native import load_native
from pooled_wave_evidence_receipt import validate_pooled, validate_support
from review_scale_supported_cfa_wave import load_new_ema, review_plan, source_guard
from scale_cfa_evidence_receipt import validate_scale_support
from spatial_trial_protocol import open_text, owner_live, read, ref
from train_scale_supported_cfa_wave import ROOT


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
        raise ValueError("Expected finite native FP32 RGB and wave arrays")
    assert value.shape == inherited.shape == wave.shape
    np.testing.assert_array_equal(value, inherited + wave)
    return value.size


def validate_stream(
    plan,
    scores,
    design,
    events,
    journal,
    inputs,
    baseline,
    frozen,
    v183,
    historical,
    historical_innovation,
    historical_cfa,
):
    methods = [method for mode in MODES for method in plan["methods"][mode].values()]
    order = plan["processing_order"]
    assert len(events) == len(journal) == len(scores["rows"]) == len(methods) * len(design)
    scored = {(r["id"], r["method"]): r for r in scores["rows"]}
    assert len(scored) == len(scores["rows"])
    counts = dict.fromkeys(["wrapper", "frozen", "network", "sampler", "projection"], 0)
    head_calls = ADC = bindings = 0
    evidence = {}
    support = {}
    pooled = {}
    scales = {}
    fields = {}
    anchor_groups = {}
    for position, (event, record) in enumerate(zip(events, journal, strict=True)):
        endpoint, ordinal = divmod(position, len(order))
        index = order[ordinal]
        case = design[index]
        method = methods[endpoint]
        mode = next(m for m in MODES if method in plan["methods"][m].values())
        assert record["mode"] == mode
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
        assert row["anchor_V195_EMA_replay_exact"] and row["frozen_V169_replay_exact"]
        assert row["V183_replay_exact"] and row["V183_values"] == v183[case["id"]]["values"]
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
        assert (
            event["counts"] == counts
            and event["readout_calls"] == event["anchor_readout_calls"] == head_calls
        )
        if noisy:
            validate_evidence(
                record["evidence"], data["packed_shape"], data["colors"], plan["module_config"]
            )
            validate_support(
                record["support"],
                data["packed_shape"],
                record["cfa"]["selection"],
                plan["module_config"],
            )
            validate_cfa(
                record["cfa"],
                data["packed_shape"],
                data["colors"],
                plan["module_config"],
                lower=plan["lower_native_frequency"],
            )
            validate_scale_support(
                record["scale_support"],
                data["packed_shape"],
                record["cfa"]["selection"],
                plan["module_config"],
                record["cfa"],
            )
            assert record["cfa"] == historical_cfa[case["id"]]["cfa"]
            assert record["support"] == historical_cfa[case["id"]]["support"]
            assert record["measurement_field"] == historical_cfa[case["id"]]["measurement_field"]
            validate_pooled(
                record["anchor_pooled"], data["packed_shape"], data["colors"], plan["module_config"]
            )
            validate_support(
                record["anchor_support"],
                data["packed_shape"],
                record["anchor_pooled"]["selection"],
                plan["module_config"],
            )
            old_innovation = historical_innovation[case["id"]]
            assert record["measurement_field"] == old_innovation["measurement_field"]
            assert record["cfa"]["selection"] == old_innovation["pooled"]["selection"]
            assert record["support"] == old_innovation["support"]
            assert (
                record["cfa"]["legacy_green_center_power"]
                == old_innovation["pooled"]["fields"]["local_center_power"]
            )
            for name in ["bin_yx", "valid", "centers_y", "centers_x", "boxes_xywh"]:
                assert record["cfa"]["fields"][name] == old_innovation["pooled"]["fields"][name]
            old = historical[case["id"]]
            assert record["evidence"] == old["evidence"]
            assert (
                record["anchor_pooled"] == old["pooled"]
                and record["anchor_support"] == old["support"]
            )
            assert record["measurement_field_CPU_checked"]
            field = record["measurement_field"]
            assert field["shape"] == list(data["packed_shape"]) and field["dtype"] == "<f4"
            expected = data["expected_fields"][mode]
            if expected is not None:
                assert field == expected
            group = (mode, case["id"])
            if group in fields:
                assert field == fields[group]
            else:
                fields[group] = field
            anchor_groups[case["id"]] = True
            if group in pooled:
                assert record["cfa"] == pooled[group]
            else:
                pooled[group] = record["cfa"]
            if group in scales:
                assert record["scale_support"] == scales[group]
            else:
                scales[group] = record["scale_support"]
            if group in support:
                assert record["support"] == support[group]
            else:
                support[group] = record["support"]
            if case["id"] in evidence:
                assert record["evidence"] == evidence[case["id"]]
            else:
                evidence[case["id"]] = record["evidence"]
        else:
            assert (
                record["evidence"]
                is record["support"]
                is record["cfa"]
                is record["scale_support"]
                is record["anchor_pooled"]
                is record["anchor_support"]
                is record["measurement_field"]
                is None
            )
            assert not record["measurement_field_CPU_checked"]
    assert counts == scores["counts"] == plan["expected_quality_counts"]
    assert (
        head_calls == scores["readout_calls"] == scores["anchor_readout_calls"] == 1500
        and ADC == scores["ADC_outputs_exact_V169"] == 144
    )
    assert (
        scores["exact_V195_EMA_replays"]
        == scores["exact_V183_EMA_replays"]
        == scores["exact_V169_replays"]
        == len(journal)
    )
    assert scores["weights_unchanged"] and scores["RNG_unchanged"]
    assert len(scales) == len(pooled) == len(fields) == 750
    return {
        "events": len(events),
        "input_fingerprints": bindings,
        "counts": counts,
        "readout_calls": head_calls,
        "V195_EMA_replay_bindings": len(events),
        "V183_EMA_replay_bindings": len(events),
        "V169_replay_bindings": len(events),
        "ADC_outputs": ADC,
        "exact_input_only_two_endpoint_evidence_groups": len(evidence),
        "independently_bridged_historical_anchor_measurement_groups": len(anchor_groups),
        "within_arm_exact_measurement_field_groups": len(fields),
        "exact_input_only_within_arm_raw_EMA_support_groups": len(support),
        "exact_input_only_raw_EMA_CFA_measurement_groups": len(pooled),
        "exact_raw_EMA_cross_scale_groups": len(scales),
        "exact_unchanged_V198_CFA_measurement_groups": len(pooled),
    }


def audit():
    plan = review_plan()
    guard(plan)
    seal = source_guard(plan)
    assert ref(__file__) == seal["auditor"] and seal["plan"] == ref(ROOT / "plan-v1.json")
    METHODS = {
        (mode, endpoint): method
        for mode in MODES
        for endpoint, method in plan["methods"][mode].items()
    }
    launch = read(ROOT / "review-launch-v1.json")
    if owner_live(launch["owner"]):
        raise RuntimeError("Actual review is still live; no Torch import")
    assert not (ROOT / "review-failure-v1.json").exists()
    scores = read(ROOT / "scores-v1.json")
    assert (
        scores["owner"] == launch["owner"]
        and scores["status"] == "completed-V200-two-endpoint-quality-awaiting-native-viewing"
    )
    assert scores["plan"] == ref(ROOT / "plan-v1.json")
    assert not (ROOT / "quality-audit-v1.json").exists()
    import torch
    from balanced_spatial_metrics import DetailMetrics
    from cfa_scale_state import anchor_hash
    from cfa_scale_state import expand as expand_checkpoint
    from profile_raw_kernel_inference import model_hash

    assert not torch.cuda.is_initialized()
    torch.set_num_threads(1)
    baseline_scores = read(plan["baseline_scores"]["path"])
    baseline = {
        r["id"]: r for r in baseline_scores["rows"] if r["method"] == "V195-whole-response-EMA"
    }
    frozen = {
        r["id"]: r
        for r in read(plan["prior_scores"]["path"])["rows"]
        if r["method"] == "balanced-EMA"
    }
    v183 = {
        r["id"]: r
        for r in read(plan["V183_scores"]["path"])["rows"]
        if r["method"] == "V183-coherent-pair-EMA"
    }
    with open_text(plan["anchor_journal"]["path"]) as historical_stream:
        historical = {
            r["id"]: r
            for r in map(json.loads, historical_stream)
            if r["method"] == "V195-whole-response-EMA"
        }
    assert len(historical) == 822
    historical_innovation = {}
    with open_text(plan["innovation_journal"]["path"]) as historical_stream:
        for record in map(json.loads, historical_stream):
            if record["mode"] == "innovation":
                if record["id"] in historical_innovation:
                    previous = historical_innovation[record["id"]]
                    for key in ["measurement_field", "pooled", "support"]:
                        assert previous[key] == record[key]
                historical_innovation[record["id"]] = record
    assert len(historical_innovation) == 822
    historical_cfa = {}
    with open_text(plan["V198_journal"]["path"]) as historical_stream:
        for record in map(json.loads, historical_stream):
            if record["id"] in historical_cfa:
                previous = historical_cfa[record["id"]]
                for key in ["cfa", "support", "measurement_field"]:
                    assert record[key] == previous[key]
            historical_cfa[record["id"]] = record
    assert len(historical_cfa) == 822
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
            "expected_fields": {"scale": None},
        }
        if case["id"] not in plan["native_cases"]:
            continue
        bindings = scores["native_predictions"][case["id"]]
        assert set(bindings) == set(METHODS.values()) | {m + "-wave" for m in METHODS.values()}
        inherited_binding = baseline_scores["native_predictions"][case["id"]][
            "V195-whole-response-EMA"
        ]
        assert ref(inherited_binding["path"]) == inherited_binding
        inherited = load_native(inherited_binding)
        inputs[case["id"]]["expected_fields"]["scale"] = fingerprint(
            np.subtract(
                arrays["packed"], sample_camera_rgb(inherited, arrays["colors"]), dtype=np.float32
            )
        )
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
    stream = validate_stream(
        plan,
        scores,
        design,
        events,
        journal,
        inputs,
        baseline,
        frozen,
        v183,
        historical,
        historical_innovation,
        historical_cfa,
    )
    means = validate_summary(scores["rows"], scores["summary"])
    initial = torch.load(
        plan["initializer"]["export"]["path"], map_location="cpu", weights_only=True
    )
    hashes = {}
    for mode in MODES:
        training = read(ROOT / f"{mode}-train-result-v1.json")
        checkpoint = scores["checkpoints"][mode]
        assert checkpoint == training["final_checkpoint"] and ref(checkpoint["path"]) == checkpoint
        state = expand_checkpoint(
            torch.load(checkpoint["path"], map_location="cpu", weights_only=True)
        )
        for endpoint, method in plan["methods"][mode].items():
            module = factory(plan, mode)
            module.load_state_dict(state["models"], strict=True)
            if endpoint == "EMA":
                load_new_ema(module, state["ema"])
            assert all(
                torch.equal(module.state_dict()[n], v) for n, v in initial["state_dict"].items()
            )
            assert anchor_hash(module) == plan["initializer"]["module_hash"]
            expected = scores["module_hashes"][method]
            assert expected["inherited"] == plan["initializer"]["module_hash"]
            assert (
                model_hash(module.frozen)
                == expected["frozen"]
                == plan["frozen_component"]["module_hash"]
            )
            assert model_hash(module) == expected["before"] == expected["after"]
            hashes[method] = model_hash(module)
    assert predictions == waves == 72 and not torch.cuda.is_initialized()
    save(
        ROOT / "quality-audit-v1.json",
        {
            "status": "pass-V200-two-endpoint-inputs-inherited-replays-native-additions-and-EMA",
            "plan": ref(ROOT / "plan-v1.json"),
            "scores": ref(ROOT / "scores-v1.json"),
            "stream": stream,
            "native_RGB_arrays": predictions,
            "native_wave_arrays": waves,
            "independent_native_baseline_plus_wave_channels": channels,
            "native_metric_scalars_recomputed": scalars,
            "native_wave_RMS_scalars_recomputed": wave_scalars,
            "independent_Decimal_summary_means": means,
            "endpoint_hashes": hashes,
            "frozen_anchor_tensor_comparisons": 386,
            "forward_journal": ref(event_path),
            "observation_journal": ref(journal_path),
            "actual_neural_forwards": 0,
            "new_sensor_source_draws": 0,
            "CUDA_initialized": False,
            "source": dict(ref(__file__), text=Path(__file__).read_text()),
        },
    )
    print(
        "PASS1644rows/4932inheritedReplayBindings/72RGB+72wave/",
        channels,
        "nativeAdditionChannels/",
        means,
        "means",
    )


if __name__ == "__main__":
    audit()
