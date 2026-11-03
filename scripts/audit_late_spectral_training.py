"""Audit the completed late-spectral source trace, states and endpoint exports."""

import argparse
from collections import Counter
from pathlib import Path

import torch
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import live


def main(root):
    plan = read(root / "plan-v1.json")
    guard(plan)
    result = read(root / "train-result-v1.json")
    smoke = read(root / "smoke-result-v1.json")
    assert result["plan"] == ref(root / "plan-v1.json")
    assert not live(result["owner"]) and not live(smoke["owner"])
    assert result["steps"] == 1000 and result["counts"] == {
        "parent_root": 990,
        "DINO": 990,
        "module_training": 1000,
        "optimizer_updates": 1000,
        "adopted_parent_batches": 10,
    }
    assert result["parent_model_before"] == result["parent_model_after"]
    assert (
        result["DINO_before"]
        == result["DINO_after"]
        == "691963f0f796aac860d818d59d9d14287a4675612829fbe9467c7f5df8ce5b14"
    )
    assert result["parent_all_gradients_absent"] and result["initial_output_exact_parent"]
    assert (
        len(result["parameter_maximum_gradients"]) == 12
        and min(result["parameter_maximum_gradients"].values()) > 0
    )
    states = {}
    for step in (250, 500, 750, 1000):
        path = root / f"checkpoints/train-step{step:04d}.pt"
        s = torch.load(path, map_location="cpu", weights_only=True)
        assert s["step"] == step and s["horizon"] == 1000 and s["parent"] == plan["parent"]
        assert s["module_config"] == {"max_window": 256}
        assert len(s["model"]) == len(s["ema"]) == len(s["optimizer"]["state"]) == 12
        assert sum(v.numel() for v in s["model"].values()) == 30402
        assert all(torch.isfinite(v).all() for key in ("model", "ema") for v in s[key].values())
        assert all(
            float(v["step"]) == step and all(torch.isfinite(t).all() for t in v.values())
            for v in s["optimizer"]["state"].values()
        )
        assert s["counts"]["optimizer_updates"] == s["counts"]["module_training"] == step
        assert s["counts"]["parent_root"] == s["counts"]["DINO"] == step - 10
        states[step] = s
    assert all(
        torch.equal(states[250][key], s[key])
        for key in ("torch_CPU_RNG", "torch_CUDA_RNG")
        for s in states.values()
    )
    source = states[1000]["config"]["manifest"]
    rows = [__import__("json").loads(line) for line in Path(source).read_text().splitlines()]
    eligible = {row["id"]: row for row in rows if row["split"] == "train"}
    assert len(eligible) == 90782
    heldout = {
        o["source"]["sha1"]
        for o in read(root / "quality-design-v1.json")["observations"]
        if o["kind"] == "photo"
    }
    assert len(heldout) == 16 and not heldout.intersection(eligible)
    trace = result["trace"]
    assert [r["step"] for r in trace] == list(range(1, 1001))
    domains, photo_ids, mesh_present = Counter(), Counter(), Counter()
    faint = reviewed = 0
    identities = set()
    for row in trace:
        metadata = row["metadata"]
        domain = metadata["domain"]
        domains[domain] += 1
        size = 256 if domain == "photo" else 512
        assert metadata["native_size"] == size and metadata["step"] == row["step"]
        assert row["inputs"]["target"]["shape"] == [4, 3, size, size]
        assert (
            row["inputs"]["packed"]["shape"]
            == row["inputs"]["variance"]["shape"]
            == [4, 4, size // 2, size // 2]
        )
        assert len(metadata["cases"]) == 4 and {c["pattern"] for c in metadata["cases"]} == {
            "RGGB",
            "BGGR",
            "GRBG",
            "GBRG",
        }
        for i, case in enumerate(metadata["cases"]):
            assert (
                case["id"] == f"V147-train-{row['step']:04d}-{i}" and case["id"] not in identities
            )
            identities.add(case["id"])
            record = case["source"]
            assert record["kind"] == domain
            if domain == "photo":
                provenance = record["source"]
                identity = provenance["source_id"]
                assert identity in eligible and identity not in heldout
                assert (
                    min(provenance["cache_xywh"][2:]) >= 512
                    and provenance["augmentation_downsample"] == 2
                )
                assert provenance["draw_index"] == (row["step"] - 1) * 4 + i
                original = eligible[identity]
                assert (
                    original["bin_factor"] == 4
                    and original["cache_sha256"] == provenance["cache_sha256"]
                )
                assert (Path(source).parent / original["cache"]).absolute() == Path(
                    provenance["cache"]
                )
                assert record["contrast"] == 1 or 0.005 <= record["contrast"] <= 0.2
                photo_ids[identity] += 1
                faint += record["contrast"] < 1
                reviewed += provenance["reviewed_roi_xywh"] is not None
            elif domain == "mesh":
                mesh_present[record["recipe"]["present"]] += 1
    assert len(identities) == 4000
    prefix = []
    for a, b in zip(trace[:10], smoke["trace"], strict=True):
        assert a["inputs"] == b["inputs"] and a["loss"] == b["loss"]
        prefix.append(
            {
                "step": a["step"],
                "inputs_exact": True,
                "total_loss_exact": True,
                "maximum_component_difference": max(
                    abs(a[k] - b[k])
                    for k in ("pixel", "gradient", "spectral", "gradient_norm", "lr")
                ),
            }
        )
    endpoints = {}
    for label, binding in read(root / "review-result-v1.json")["collections"].items():
        c = read(binding["path"])
        export = torch.load(c["export"]["path"], map_location="cpu", weights_only=True)
        key = "model" if label.startswith("raw") else "ema"
        assert export["endpoint"] == key and export["step"] == 1000
        assert (
            export["parent"] == plan["parent"]
            and export["training_checkpoint"] == result["checkpoint"]
        )
        assert all(torch.equal(v, states[1000][key][n]) for n, v in export["state_dict"].items())
        endpoints[label] = c["export"]
    dest = root / "independent-training-audit-v1.json"
    assert not dest.exists()
    save(
        dest,
        {
            "status": "pass-completed-training-trace-state-and-export-audit",
            "training_result": ref(root / "train-result-v1.json"),
            "auditor": ref(__file__),
            "checkpoints": [ref(root / f"checkpoints/train-step{x:04d}.pt") for x in states],
            "endpoints": endpoints,
            "metadata_domain_batches": dict(domains),
            "targets_per_domain": {k: 4 * v for k, v in domains.items()},
            "mesh_present_targets": mesh_present[True],
            "mesh_absent_targets": mesh_present[False],
            "photo_unique_sources": len(photo_ids),
            "photo_faint_targets": faint,
            "photo_reviewed_ROI_targets": reviewed,
            "photo_manifest_eligible_pool": 90782,
            "heldout16_excluded_from_pool_and_actual_photo_trace": True,
            "prefix": prefix,
            "global_CPU_CUDA_RNG_exact_at_all_four_checkpoints": True,
            "all12_Adam_states_at_each_recorded_step": True,
            "all_weights_moments_finite": True,
            "recorded_parent_and_DINO_hashes_unchanged": True,
            "original_worker_exited": True,
            "unique_training_observation_IDs": 4000,
            "new_forwards": 0,
            "new_noise_draws": 0,
            "scope": "Audits actual metadata/fingerprints, manifest membership, four saved optimizer states and both exports. Does not redraw/reexecute training, rehash all original photograph cache files, or claim a bit-exact independent uninterrupted trajectory. All10 prefix total losses match; one FP32 component differs at about1e-9.",
        },
    )
    print(
        "PASS completed training audit",
        dict(domains),
        "photo sources",
        len(photo_ids),
        "present/absent meshes",
        dict(mesh_present),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    main(parser.parse_args().root.resolve())
