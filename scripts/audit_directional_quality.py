"""Independent four-endpoint V195 stream, native RGB/wave, and strict-state audit."""

import hashlib
import json
from pathlib import Path

import numpy as np
from audit_coherent_pair_evidence_trial import validate_evidence, validate_summary
from directional_trial_protocol import MODES, factory, guard, save
from directional_trial_protocol import TRIAL as ROOT
from lossless_native import load_native
from pooled_wave_evidence_receipt import validate_pooled, validate_support
from review_directional_response import source_guard
from spatial_trial_protocol import open_text, owner_live, read, ref


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


def validate_stream(plan, scores, design, events, journal, inputs, baseline, frozen):
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
            validate_support(
                record["support"],
                data["packed_shape"],
                record["pooled"]["selection"],
                plan["module_config"],
            )
            validate_pooled(
                record["pooled"], data["packed_shape"], data["colors"], plan["module_config"]
            )
            if case["id"] in pooled:
                assert record["pooled"] == pooled[case["id"]]
            else:
                pooled[case["id"]] = record["pooled"]
            if case["id"] in support:
                assert record["support"] == support[case["id"]]
            else:
                support[case["id"]] = record["support"]
            if case["id"] in evidence:
                assert record["evidence"] == evidence[case["id"]]
            else:
                evidence[case["id"]] = record["evidence"]
        else:
            assert record["evidence"] is record["support"] is record["pooled"] is None
    assert counts == scores["counts"] == plan["expected_quality_counts"]
    assert (
        head_calls == scores["readout_calls"] == 3000
        and ADC == scores["ADC_outputs_exact_V169"] == 288
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
        "exact_input_only_four_endpoint_evidence_groups": len(evidence),
        "exact_input_only_four_endpoint_support_groups": len(support),
        "exact_input_only_four_endpoint_pooled_selection_wave_groups": len(pooled),
    }


def audit():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    seal = source_guard(plan)
    assert ref(__file__) == seal["auditor"] and seal["plan"] == ref(ROOT / "plan-v1.json")
    METHODS = {
        (mode, endpoint): method
        for mode in MODES
        for endpoint, method in plan["methods"][mode].items()
    }
    launch = read(ROOT / "review-v2-launch-v1.json")
    if owner_live(launch["owner"]):
        raise RuntimeError("Actual review is still live; no Torch import")
    assert not (ROOT / "review-v2-failure-v1.json").exists()
    scores = read(ROOT / "scores-v1.json")
    assert (
        scores["owner"] == launch["owner"]
        and scores["status"] == "completed-V195-four-endpoint-quality-awaiting-native-viewing"
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
            module = factory(plan["module_config"])
            module.load_state_dict(state["models"], strict=True)
            if endpoint == "EMA":
                load_ema(module, state["ema"])
            assert all(
                torch.equal(module.state_dict()[n], v) for n, v in initial["state_dict"].items()
            )
            assert inherited_hash(module) == plan["initializer"]["module_hash"]
            expected = scores["module_hashes"][method]
            assert expected["inherited"] == plan["initializer"]["module_hash"]
            assert (
                model_hash(module.frozen)
                == expected["frozen"]
                == plan["frozen_component"]["module_hash"]
            )
            assert model_hash(module) == expected["before"] == expected["after"]
            hashes[method] = model_hash(module)
    assert predictions == waves == 144 and not torch.cuda.is_initialized()
    save(
        ROOT / "quality-audit-v1.json",
        {
            "status": "pass-V195-four-endpoint-inputs-inherited-replays-native-additions-and-EMA",
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
            "inherited_tensor_comparisons": 756,
            "forward_journal": ref(event_path),
            "observation_journal": ref(journal_path),
            "actual_neural_forwards": 0,
            "new_sensor_source_draws": 0,
            "CUDA_initialized": False,
            "source": dict(ref(__file__), text=Path(__file__).read_text()),
        },
    )
    print(
        "PASS3288rows/6576inheritedReplayBindings/144RGB+144wave/",
        channels,
        "nativeAdditionChannels/",
        means,
        "means",
    )


if __name__ == "__main__":
    audit()
