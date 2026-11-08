"""Independent CPU inspection of V182 arrays, gradients and signed geometry."""

import math
import sys
from pathlib import Path

import numpy as np
from phase_admission_protocol import owner_live, read, ref
from probe_flat_spatial_loss_geometry import ROOT, guard, save

LABELS = ["baseline", "flat_spatial", "pair_difference", "pair_common", "pair_response"]


def flat_fields(output, target, window=17):
    """NumPy separable extrema and prefix sums, independent of Torch pooling."""
    radius = window // 2
    low, high = target.copy(), target.copy()
    for axis in [-1, -2]:
        old_low, old_high = low.copy(), high.copy()
        for offset in range(1, min(radius + 1, target.shape[axis])):
            first, second = [slice(None)] * 4, [slice(None)] * 4
            first[axis], second[axis] = slice(offset, None), slice(None, -offset)
            first, second = tuple(first), tuple(second)
            for a, b in [(first, second), (second, first)]:
                np.minimum(low[a], old_low[b], out=low[a])
                np.maximum(high[a], old_high[b], out=high[a])
    mask = ((high - low) <= np.float32(1 / 65535)).all(1, keepdims=True)

    def mean(a):
        for axis in [-1, -2]:
            length = a.shape[axis]
            first = np.maximum(np.arange(length) - radius, 0)
            end = np.minimum(np.arange(length) + radius + 1, length)
            pads = [(0, 0)] * 4
            pads[axis] = (1, 0)
            integral = np.pad(np.cumsum(a, axis=axis, dtype=np.float64), pads)
            shape = [1] * 4
            shape[axis] = length
            a = (np.take(integral, end, axis=axis) - np.take(integral, first, axis=axis)) / (
                end - first
            ).reshape(shape)
        return a

    error = (output.astype(np.float64) - target.astype(np.float64)) / (4 / 65535)
    z = error - error[..., :1, :1]
    variance = np.maximum(mean(z * z) - mean(z) ** 2, 0)
    return mask, float(np.mean(mask * variance / (np.sqrt(1 + variance) + 1)))


def inspect_geometry(g, observed):
    g = np.array(g, np.float64)
    assert g.shape == (5, 5) and np.isfinite(g).all() and np.array_equal(g, g.T)
    assert observed["labels"] == LABELS and (g.diagonal() >= 0).all()
    norms = [math.sqrt(v) for v in g.diagonal()]
    for i, name in enumerate(LABELS):
        assert math.isclose(observed["norms"][name], norms[i], rel_tol=1e-12, abs_tol=1e-12)
        for j in range(5):
            if norms[i] == 0 or norms[j] == 0:
                assert observed["cosines"][i][j] is None
            else:
                expected = g[i, j] / norms[i] / norms[j]
                assert abs(expected) <= 1 + 1e-10
                assert math.isclose(
                    observed["cosines"][i][j], expected, rel_tol=1e-11, abs_tol=1e-12
                )
    ratio = observed["spatial_to_baseline_norm"]
    if norms[0]:
        assert math.isclose(ratio, norms[1] / norms[0], rel_tol=1e-12, abs_tol=1e-12)
    else:
        assert ratio is None
    for direction, indices in [
        ("negative_baseline", [0]),
        ("negative_spatial", [1]),
        ("negative_sum", [0, 1]),
    ]:
        for field, row in [
            ("pair_difference_loss_slope", 2),
            ("spatial_loss_slope", 1),
            ("pair_response_slope", 4),
        ]:
            expected = -math.fsum(g[row, i] for i in indices)
            assert math.isclose(
                observed["directions"][direction][field], expected, rel_tol=1e-11, abs_tol=1e-12
            )


def audit():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    seal = read(ROOT / "audit-source-v2.json")
    assert seal["auditor"] == ref(__file__) and seal["plan"] == ref(ROOT / "plan-v1.json")
    owner = read(ROOT / "launch-v1.json")["owner"]
    assert not owner_live(owner) and not (ROOT / "failure-v1.json").exists()
    result = read(ROOT / "result-v1.json")
    assert result["owner"] == owner and result["plan"] == ref(ROOT / "plan-v1.json")
    assert (
        result["status"]
        == "completed-training-gradient-geometry-zero-updates-awaiting-independent-inspection"
    )
    assert (
        result["counts"] == plan["expected_forwards"]
        and result["parameter_backward_evaluations"] == 76
    )
    assert result["all_model_frozen_state_and_RNG_unchanged"] and result["optimizer_updates"] == 0
    assert result["independent_Torch_NumPy_Gram_checks"] == 5700
    events = [
        __import__("json").loads(line)
        for line in (ROOT / "events-v1.jsonl").read_text().splitlines()
    ]
    assert len(events) == len(result["rows"]) == 20
    rows = result["rows"]
    unit_rows = read(plan["pair_units"]["path"])["rows"]
    assert [(r["method"], r["step"]) for r in rows] == [
        (s["method"], c["step"]) for s in plan["states"] for c in plan["cases"]
    ]

    import torch
    from phase_evidence_training_state import matching_parameters, optimizer_for
    from profile_raw_kernel_inference import model_hash
    from train_flat_spatial_evidence_trial import factory

    from demosaic.prediction_archive import fingerprint

    assert not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    moments = {}
    for state in plan["states"]:
        checkpoint = torch.load(state["checkpoint"]["path"], map_location="cpu", weights_only=True)
        module = factory("evidence", plan["module_config"])
        module.load_state_dict(checkpoint["models"], strict=True)
        assert model_hash(module) == state["module_hash"]
        optimizer = optimizer_for(module, lr=1e-4, weight_decay=0.01)
        optimizer.load_state_dict(checkpoint["optimizer"])
        mapping = {}
        for name, parameter in matching_parameters(module).items():
            saved = optimizer.state[parameter]
            group = next(
                g for g in optimizer.param_groups if any(p is parameter for p in g["params"])
            )
            beta, eps, step = group["betas"][1], group["eps"], float(saved["step"])
            assert step == (1800 if name.startswith("network.") else 900)
            variance = saved["exp_avg_sq"].numpy().copy()
            diagonal = np.reciprocal(np.sqrt(variance.astype(np.float64) / (1 - beta**step)) + eps)
            assert (diagonal > 0).all() and np.isfinite(diagonal).all()
            mapping[name] = (variance, diagonal, step, beta, eps)
        assert len(mapping) == 142
        moments[state["method"]] = mapping
        del optimizer, module, checkpoint
    counts = {k: 0 for k in result["counts"]}
    backwards = geometry_checks = retained_layers = native_channels = 0
    maximum_flat_error = maximum_pair_error = maximum_response_error = 0.0
    for event, row in zip(events, rows, strict=True):
        assert all(event[k] == row[k] for k in ["method", "case_index", "step"])
        assert ref(event["row"]["path"]) == event["row"] and read(event["row"]["path"]) == row
        case = plan["cases"][row["case_index"]]
        assert row["labels"] == LABELS and row["pair_units"] == unit_rows[case["step"] - 1]
        assert row["domain"] == case["metadata"]["domain"] and row["selection"] == case["selection"]
        assert row["batch"] == case["arrays"] and row["parent"] == case["parent"]
        assert row["counts_before"] == counts
        counts = {k: v + (5 if k == "sampler" else 1) for k, v in counts.items()}
        assert row["counts_after"] == event["counts"] == counts
        arrays = dict(np.load(case["arrays"]["path"], allow_pickle=False))
        assert {k: fingerprint(v) for k, v in arrays.items()} == case["inputs"] == row["inputs"]
        parent = np.load(case["parent"]["path"], allow_pickle=False)
        assert fingerprint(parent) == row["parent_values"] == case["parent_values"]
        assert ref(row["output"]["path"]) == {k: row["output"][k] for k in ["path", "sha256"]}
        output = np.load(row["output"]["path"], allow_pickle=False)
        assert (
            fingerprint(output) == row["output"]["values"]
            and output.shape == arrays["target"].shape
        )
        native_channels += output.size
        mask, spatial = flat_fields(output, arrays["target"])
        assert fingerprint(mask) == row["flat_mask"] and float(mask.mean()) == row["flat_coverage"]
        error = abs(spatial - row["loss_terms"]["flat_spatial"])
        maximum_flat_error = max(maximum_flat_error, error)
        assert math.isclose(spatial, row["loss_terms"]["flat_spatial"], rel_tol=2e-6, abs_tol=1e-7)
        t = {k: np.float32(v) for k, v in row["loss_terms"].items()}
        base = np.float32(t["pixel"] + np.float32(0.25) * t["gradient"])
        for term in [
            t["local_regret"],
            t["DC_regret"],
            np.float32(0.25) * t["flat_anchor"],
            t["pair_difference"],
            t["pair_common"],
        ]:
            base = np.float32(base + term)
        base = np.float32(np.float32(row["domain_weight"]) * base)
        assert float(base) == row["old_loss"]
        assert (
            float(np.float32(base + np.float32(0.25 * row["domain_weight"]) * t["flat_spatial"]))
            == row["eight_term_total"]
        )
        pair_count = len(arrays["pair_indices"])
        if pair_count:
            first, second = arrays["pair_indices"].T
            delta = arrays["target"][first].astype(np.float64) - arrays["target"][second].astype(
                np.float64
            )
            energies = np.sum(delta**2, axis=(1, 2, 3))
            np.testing.assert_allclose(
                energies, row["pair_target_energies"], rtol=1e-12, atol=1e-18
            )
            response = np.mean(
                np.sum(
                    (output[first].astype(np.float64) - output[second].astype(np.float64)) * delta,
                    axis=(1, 2, 3),
                )
                / energies
            )
            maximum_response_error = max(
                maximum_response_error, abs(response - row["pair_response"])
            )
            assert math.isclose(response, row["pair_response"], rel_tol=1e-10, abs_tol=1e-12)
            units = np.asarray(row["pair_units"]["candidate_units_FP32"], np.float32).reshape(
                -1, 1, 1, 1
            )
            residual = (
                (output[first] - output[second])
                - (arrays["target"][first] - arrays["target"][second])
            ) / units
            error_field = output - arrays["target"]
            common = (error_field[first] + error_field[second]) / np.float32(32 / 65535)
            for field, value, epsilon in [
                ("pair_difference", residual, 0.003),
                ("pair_common", common, 1),
            ]:
                power = value**2
                expected = float(
                    np.mean(
                        power / (np.sqrt(power + np.float32(epsilon**2)) + np.float32(epsilon)),
                        dtype=np.float64,
                    )
                )
                maximum_pair_error = max(
                    maximum_pair_error, abs(expected - row["loss_terms"][field])
                )
                assert math.isclose(expected, row["loss_terms"][field], rel_tol=2e-6, abs_tol=1e-7)
        else:
            assert row["pair_response"] == 0 and not row["pair_target_energies"]
            assert np.count_nonzero(np.asarray(row["output_Gram"])[2:]) == 0
        backwards += 5 if pair_count else 2
        assert (
            row["parameter_backward_evaluations"] == (5 if pair_count else 2)
            and event["backwards"] == backwards
        )
        inspect_geometry(row["output_Gram"], row["output_geometry"])
        geometry_checks += 1
        for group in ["all", "network", "adapter"]:
            for gram_key, geom_key in [
                ("parameter_Grams", "parameter_geometry"),
                ("fixed_Adam_Grams", "fixed_Adam_geometry"),
            ]:
                selected = [
                    l["fixed_Adam_Gram" if gram_key.startswith("fixed") else "Gram"]
                    for l in row["layers"]
                    if group == "all"
                    or (
                        l["name"].startswith("network.")
                        if group == "network"
                        else l["name"].startswith("phase_evidence_in.")
                    )
                ]
                np.testing.assert_array_equal(np.sum(selected, axis=0), row[gram_key][group])
                inspect_geometry(row[gram_key][group], row[geom_key][group])
                geometry_checks += 1
        mapping = moments[row["method"]]
        assert [l["name"] for l in row["layers"]] == list(mapping)
        for name, (variance, diagonal, step, beta, eps) in mapping.items():
            assert row["denominator_state"][name] == {
                "step": step,
                "beta2": beta,
                "epsilon": eps,
                "exp_avg_sq": fingerprint(variance),
            }
        retained = row["retained_full_parameter_gradients"]
        if retained:
            assert row["case_index"] == 0 and ref(retained["path"]) == retained
            archive = dict(np.load(retained["path"], allow_pickle=False))
            vectors, diagonal = archive["gradients"], archive["fixed_Adam_diagonal"]
            assert vectors.shape == (5, 2092026) and diagonal.shape == (2092026,)
            start = 0
            for layer in row["layers"]:
                size = math.prod(layer["shape"])
                end = start + size
                block = vectors[:, start:end].astype(np.float64)
                for i in range(5):
                    assert (
                        fingerprint(vectors[i, start:end].reshape(layer["shape"]))
                        == layer["gradients"][i]
                    )
                np.testing.assert_array_equal(
                    diagonal[start:end], mapping[layer["name"]][1].ravel()
                )
                for key, d in [("Gram", np.ones(size)), ("fixed_Adam_Gram", diagonal[start:end])]:
                    actual = np.einsum("ik,jk,k->ij", block, block, d, optimize=False)
                    expected = np.asarray(layer[key])
                    bound = (
                        1e-10 * np.sqrt(np.outer(expected.diagonal(), expected.diagonal())) + 1e-12
                    )
                    assert (np.abs(actual - expected) <= bound).all()
                start = end
                retained_layers += 1
            assert start == 2092026
        else:
            assert row["case_index"] != 0
    assert (
        counts == result["counts"]
        and backwards == 76
        and retained_layers == 284
        and geometry_checks == 140
    )
    assert not torch.cuda.is_initialized()
    guard(plan)
    save(
        ROOT / "independent-audit-v2.json",
        {
            "status": "pass-V182-terminal-input-output-loss-Gram-Adam-and-retained-gradient-inspection",
            "plan": ref(ROOT / "plan-v1.json"),
            "result": ref(ROOT / "result-v1.json"),
            "source": dict(ref(__file__), text=Path(__file__).read_text()),
            "rows": 20,
            "native_RGB_channels": native_channels,
            "eight_term_FP32_totals": 20,
            "native_flat_masks_and_spatial_losses": 20,
            "native_paired_losses": 24,
            "paired_response_functionals": 12,
            "maximum_flat_loss_error": maximum_flat_error,
            "maximum_paired_loss_error": maximum_pair_error,
            "maximum_response_error": maximum_response_error,
            "geometry_matrices": geometry_checks,
            "strict_CPU_checkpoints": 2,
            "Adam_denominators": 284,
            "retained_gradient_layers": retained_layers,
            "retained_layer_Gram_matrices": 568,
            "independent_neural_forwards": 0,
            "new_optimizer_updates": 0,
            "CUDA_initialized": False,
            "scope": "All20saved training-only outputs/inputbindings/FP32totals/flatmasks/spatiallosses and12pairedloss/responsecases independently remeasured. All140geometrymatrices and layeraggregates checked. Two strict CPUrawstates and all284savedAdamdenominators verified. Full retained firstmesh gradients at both checkpoints reproduce284layerfingerprints and568Grams. Other vectors have fingerprints and5700in-process independent NumPy/Torch checks,not full posthoc vectors. No new neural or optimizer work;diagnostic metric omits actualAdamstep dynamics and proves no quality gain.",
        },
    )
    assert "torch" in sys.modules
    print(
        "PASS20nativebatches/20FP32totals/140geometries/284Adamdenominators/568retainedGrams;zero new neural/CUDA/updates"
    )


if __name__ == "__main__":
    audit()
