"""CPU checks of the completed shared-edge cache and exact saved-prefix adoption."""

import json
from collections import Counter

import numpy as np
from directional_trial_protocol import REPO, guard, read, ref, save
from phase_admission_protocol import owner_live
from prepare_shared_edge_cache import ROOT

from demosaic.prediction_archive import fingerprint


def audit():
    plan = read(ROOT / "plan-v1.json")
    execution = read(ROOT / "resume-plan-v2.json")
    guard(plan)
    guard(execution)
    launch = read(ROOT / "resume2-cache-launch-v1.json")
    assert not owner_live(launch["owner"])
    result = read(ROOT / "cache-result-v1.json")
    assert result["owner"] == launch["owner"]
    assert result["status"] == "completed156-shared-edge-parent-batches-and844-exact-adoptions"
    assert result["execution_plan"] == ref(ROOT / "resume-plan-v2.json")
    assert result["prefix_adopted_without_source_or_parent_replay"] == [4]
    assert result["parent_roots_in_this_segment"] == 155
    assert all(v == 157 for v in result["counts"].values())
    assert result["parent_before"] == result["parent_after"] == plan["parent_module_hash"]
    assert result["DINO_before"] == result["DINO_after"] == plan["DINO_module_hash"]
    old = read(plan["cache"]["path"])
    old_units = read(plan["old_pair_units"]["path"])["rows"]
    units = read(result["pair_units"]["path"])["rows"]
    assert len(result["batches"]) == len(old["batches"]) == len(units) == 1000
    selected = {r["step"] for r in plan["selected"]}
    events = [
        json.loads(line)
        for line in (ROOT / "resume2-cache-trace-v1.jsonl").read_text().splitlines()
    ]
    completed = [e for e in events if e["event"] == "completed"]
    assert len(completed) == 155
    assert [e["counts"]["parent_returned"] for e in completed] == list(range(3, 158))
    assert events[0]["event"] == "adopted-completed-prefix" and events[0]["step"] == 4
    assert all(e["step"] != 4 for e in completed)
    prefix = json.loads((ROOT / "cache-trace-v1.jsonl").read_text().splitlines()[-1])["record"]
    assert result["batches"][3] == prefix
    unchanged = changed = parents = sensor_values = 0
    controls = Counter()
    domains = Counter()
    delta_rms = []
    shapes = Counter()
    for previous, row, unit, prior_unit in zip(
        old["batches"], result["batches"], units, old_units, strict=True
    ):
        step = row["step"]
        assert unit["step"] == step and unit["batch"] == row["arrays"]
        if step not in selected:
            assert row == previous and unit == prior_unit
            unchanged += 1
            continue
        changed += 1
        assert row["metadata"]["domain"] == previous["metadata"]["domain"] == "mixed"
        assert row["metadata"]["noise"] == previous["metadata"]["noise"]
        noise = row["metadata"]["noise"]
        noisy = noise["shot"] > 0 or noise["read"] > 0
        domains["noisy" if noisy else "ADC"] += 1
        assert row["metadata"]["coupled_pairs"] == 2
        for binding in [row["arrays"], row["parent"]]:
            assert ref(binding["path"]) == binding
        with np.load(row["arrays"]["path"], allow_pickle=False) as f:
            arrays = {k: f[k] for k in f.files}
        assert {k: fingerprint(v) for k, v in arrays.items()} == row["inputs"]
        assert arrays["target"].shape == (4, 3, 512, 512)
        assert arrays["packed"].shape == arrays["variance"].shape == (4, 4, 256, 256)
        np.testing.assert_array_equal(arrays["pair_indices"], [[0, 1], [2, 3]])
        expected_variance = np.maximum(arrays["packed"], 0) * noise["shot"] + noise["read"]
        np.testing.assert_array_equal(arrays["variance"], expected_variance)
        assert ref(previous["arrays"]["path"]) == previous["arrays"]
        with np.load(previous["arrays"]["path"], allow_pickle=False) as f:
            for key in ["wb", "matrix", "colors"]:
                np.testing.assert_array_equal(arrays[key], f[key][[0, 0, 2, 2]])
        clean = [
            np.stack(
                [
                    np.stack([rgb[int(c), k // 2 :: 2, k % 2 :: 2] for k, c in enumerate(colors)])
                    for rgb, colors in zip(
                        arrays["target"][p::2], arrays["colors"][p::2], strict=True
                    )
                ]
            )
            for p in (0, 1)
        ]
        for p, key in enumerate(["clean_packed_a", "clean_packed_b"]):
            assert fingerprint(clean[p]) == row["metadata"]["sensor"][key]
            sensor_values += clean[p].size
        expected = np.maximum(
            np.sqrt(
                np.mean(
                    noise["shot"] * np.abs(clean[0].astype(np.float64) - clean[1]), axis=(1, 2, 3)
                )
            ),
            16 / 65535,
        )
        np.testing.assert_allclose(
            arrays["pair_units"].reshape(-1), expected, rtol=3e-7, atol=1e-12
        )
        np.testing.assert_allclose(unit["candidate_units_FP32"], expected, rtol=3e-7, atol=1e-12)
        for pair in range(2):
            source = row["metadata"]["cases"][2 * pair]["source"]
            shapes[source["background"]["kind"]] += 1
            present = source["mesh"]["present"]
            controls["present" if present else "no-increment"] += 1
            controls[
                ("noisy-" if noisy else "ADC-") + ("present" if present else "no-increment")
            ] += 1
            delta = arrays["target"][2 * pair].astype(np.float64) - arrays["target"][2 * pair + 1]
            delta_rms.append(float(np.sqrt(np.mean(delta**2)) * 65535))
            same = clean[0][pair] == clean[1][pair]
            assert same.sum() > same.size // 5
            np.testing.assert_array_equal(
                arrays["packed"][2 * pair][same], arrays["packed"][2 * pair + 1][same]
            )
            if not present:
                assert delta_rms[-1] == 0
                np.testing.assert_array_equal(
                    arrays["packed"][2 * pair], arrays["packed"][2 * pair + 1]
                )
            else:
                assert delta_rms[-1] > 0
        parent = np.load(row["parent"]["path"], allow_pickle=False)
        assert parent.shape == arrays["target"].shape and np.isfinite(parent).all()
        assert fingerprint(parent) == row["parent_values"]
        parents += parent.size
    assert unchanged == 844 and changed == 156
    assert domains == {"noisy": 139, "ADC": 17}
    assert controls["no-increment"] == 63 and controls["present"] == 249
    assert parents == 490733568 and sensor_values == 163577856
    for name, digest in plan["all107_neural_hashes"].items():
        assert ref(REPO / "src/demosaic" / name)["sha256"] == digest
    nonzero = [v for v in delta_rms if v > 0]
    receipt = {
        "status": "pass-all156-new-shared-edge-rows-and844-exact-adoptions",
        "cache": ref(ROOT / "cache-result-v1.json"),
        "execution_plan": ref(ROOT / "resume-plan-v2.json"),
        "source": dict(ref(__file__), text=__import__("pathlib").Path(__file__).read_text()),
        "unchanged_array_parent_unit_records": unchanged,
        "independently_checked_new_rows": changed,
        "mixed_noise_rows": dict(domains),
        "pair_presence_counts": dict(controls),
        "shape_counts": dict(shapes),
        "parent_RGB_values_checked": parents,
        "independent_clean_Bayer_values_checked": sensor_values,
        "positive_increment_RMS_DN16": {
            "minimum": min(nonzero),
            "median": float(np.median(nonzero)),
            "maximum": max(nonzero),
        },
        "all107_neural_sources_unchanged": True,
        "adopted_completed_step4_without_replay": True,
        "new_parent_DINO_forwards_by_audit": 0,
        "all_module_forwards_rejected_during_audit": True,
        "CUDA_initialized": False,
        "new_source_noise_draws_by_audit": 0,
        "scope": "Training-data contracts only; no newly trained model or held-out quality result. Nominal sensor units are pre-ADC proxies, not restored RGB covariance. Broad shape/level/context and coupling change together.",
    }
    save(ROOT / "cache-audit-v1.json", receipt)
    print(
        "PASS156new/844reused rows;312pairs/63controls;490733568parent RGB values;zero new model calls"
    )


if __name__ == "__main__":
    import torch

    assert not torch.cuda.is_initialized()
    original = torch.nn.Module._call_impl

    def forbidden(*args, **kwargs):
        raise RuntimeError("No neural module forward during cache audit")

    torch.nn.Module._call_impl = forbidden
    try:
        audit()
    finally:
        torch.nn.Module._call_impl = original
    assert not torch.cuda.is_initialized()
