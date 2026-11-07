"""Measure trained phase-input removal on the prospectively fixed twelve inputs."""

import argparse
import json
import os
from pathlib import Path

import numpy as np
import psutil
import torch
from profile_raw_kernel_inference import model_hash
from train_directional_bank_trial import guard, read, ref, save
from train_harmonic_phase_trial import classes, resource_check, runtime

from demosaic.prediction_archive import fingerprint


def main(root):
    plan = read(root / "plan-v1.json")
    guard(plan)
    runtime(plan)
    (root / "phase-removal.claim").open("x").close()
    review = read(root / "review-result-v1.json")
    design = read(root / "quality-design-v1.json")
    recipe = design["phase_removal"]
    cases = {c["id"]: c for c in design["observations"]}
    assert len(recipe["case_ids"]) == 12 and recipe["new_head_calls"] == 48
    dest = Path(plan["external_quality_root"]) / "phase-removal-v1"
    dest.mkdir(exist_ok=False)
    counts = total = 0
    records = []
    cpu_rng, cuda_rng = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
    forward_journal = (root / "phase-removal-forward-events-v1.jsonl").open("x")
    observation_journal = (root / "phase-removal-observations-v1.jsonl").open("x")
    for label in recipe["endpoints"]:
        binding = review["collections"][label]
        assert ref(binding["path"]) == binding
        collection = read(binding["path"])
        assert ref(collection["export"]["path"]) == collection["export"]
        export = torch.load(collection["export"]["path"], map_location="cpu", weights_only=True)
        module = classes()["harmonic-phase"](**export["module_config"]).cuda().eval()
        module.load_state_dict(export["state_dict"], strict=True)
        before = model_hash(module)
        assert before == collection["module_before"] == collection["module_after"]
        weight = module.phase_in.weight.detach().clone()
        assert weight.count_nonzero() > 0
        archived = {r["id"]: r["prediction"] for r in collection["observations"]}

        def observe(*args):
            nonlocal counts
            counts += 1

        module.register_forward_hook(observe)
        for index, identity in enumerate(recipe["case_ids"]):
            resource_check(root)
            case = cases[identity]
            assert ref(case["arrays"]["path"]) == case["arrays"]
            assert ref(case["parent"]["path"]) == case["parent"]
            arrays = dict(np.load(case["arrays"]["path"]))
            base = torch.from_numpy(np.load(case["parent"]["path"])).cuda()
            batch = {
                k: torch.from_numpy(arrays[k]).cuda()
                for k in ["packed", "variance", "colors", "wb"]
            }
            values, spatial = [], []
            for active in [True, False]:
                with torch.no_grad():
                    module.phase_in.weight.copy_(weight if active else torch.zeros_like(weight))
                with torch.inference_mode():
                    output, aux = module(base, **batch, return_aux=True)
                forward_journal.write(
                    json.dumps(
                        {
                            "endpoint": label,
                            "id": identity,
                            "active": active,
                            "returned_forwards": counts,
                        }
                    )
                    + "\n"
                )
                forward_journal.flush()
                values.append(output.cpu().numpy())
                spatial.append(aux["spatial_correction"].cpu().numpy())
                del output, aux
            with torch.no_grad():
                module.phase_in.weight.copy_(weight)
            assert before == model_hash(module)
            on, off = values
            assert on.dtype == off.dtype == np.float32 and np.isfinite(off).all()
            assert ref(archived[identity]["path"]) == archived[identity]
            assert fingerprint(on) == fingerprint(np.load(archived[identity]["path"]))
            np.testing.assert_array_equal(spatial[0], spatial[1])
            path = dest / f"{label}-off-{index:02d}.npy"
            with path.open("xb") as stream:
                np.save(stream, off, allow_pickle=False)
            effect = (on.astype(np.float64) - off.astype(np.float64)) * 65535
            rms = float(np.sqrt(np.mean(effect**2)))
            assert abs(rms - np.linalg.norm(effect.ravel()) / np.sqrt(effect.size)) < 1e-10
            record = {
                "endpoint": label,
                "id": identity,
                "kind": case["kind"],
                "case": case,
                "export": collection["export"],
                "on_prediction": archived[identity],
                "off_prediction": ref(path),
                "off_values": fingerprint(off),
                "effect_RMS_DN16": rms,
                "effect_maximum_abs_DN16": float(np.abs(effect).max()),
                "on_replayed_bit_exact": True,
                "direct_spatial_path_bit_exact": True,
                "module_before_after_restored": before,
                "head_calls": 2,
            }
            records.append(record)
            observation_journal.write(json.dumps(record, allow_nan=False) + "\n")
            observation_journal.flush()
            total += 1
            del base, batch, arrays, values, spatial, on, off, effect
        del module, weight
    forward_journal.close()
    observation_journal.close()
    assert total == 24 and counts == 48
    assert torch.equal(cpu_rng, torch.get_rng_state()) and torch.equal(
        cuda_rng, torch.cuda.get_rng_state()
    )
    assert (
        sum(Path(r["off_prediction"]["path"]).stat().st_size for r in records)
        == recipe["expected_bytes"]
    )
    guard(plan)
    save(
        root / "phase-removal-result-v1.json",
        {
            "status": "completed-fixed-phase-removal-diagnostic",
            "plan": ref(root / "plan-v1.json"),
            "records": records,
            "head_calls": counts,
            "new_prediction_arrays": total,
            "forward_journal": ref(root / "phase-removal-forward-events-v1.jsonl"),
            "observation_journal": ref(root / "phase-removal-observations-v1.jsonl"),
            "RNG_unchanged": True,
            "CUDA_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "new_parent_DINO_calls": 0,
            "new_noise_draws": 0,
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "scope": "12 prospectively fixed inputs at both candidate endpoints;24 on/off pairs and48 actual head calls. On values replay full review exactly;only phase adapter zeroed for off,then restored. Direct RGB path output stays exact. Displacement measures trained phase-adapter contribution,not improved accuracy or an isolated account of training dynamics. Real references remain qualitative,not GT.",
        },
    )
    print("Completed48 fixed on/off calls;24 off arrays retained,24 on archive replays exact")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    main(parser.parse_args().root.resolve())
