"""CPU-only strict raw/EMA snapshots, all frozen anchor tensors and Adam clocks."""

import time

from admit_cfa_innovation_wave import ROOT, factory, guard, read, ref, save
from phase_admission_protocol import owner_live


def inspect():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    assert ref(__file__) == plan["inspector"]
    result = read(ROOT / "admission-result-v1.json")
    assert not owner_live(result["owner"])
    assert result["plan"] == ref(ROOT / "plan-v1.json")
    assert not (ROOT / "admission-failure-v1.json").exists()
    import torch
    from cfa_innovation_state import PREFIX, anchor_hash, clocks, expand, fresh, parameters
    from profile_raw_kernel_inference import model_hash
    from train_local_noise_matching_trial import tree_equal

    assert not torch.cuda.is_initialized()
    source = torch.load(plan["anchor"]["export"]["path"], map_location="cpu", weights_only=True)[
        "state_dict"
    ]
    records = {(r["mode"], r["update"]): r for r in result["records"]}
    assert len(records) == 2 and len(result["checkpoints"]) == 2
    checks = []
    frozen_comparisons = 0
    for binding in result["checkpoints"]:
        assert ref(binding["path"]) == binding
        saved = torch.load(binding["path"], map_location="cpu", weights_only=True)
        payload = expand(saved)
        mode, updates = payload["measurement"], payload["updates"]
        model = factory(plan, mode)
        model.load_state_dict(payload["models"], strict=True)
        assert len(model.state_dict()) == 197
        assert model_hash(model) == records[mode, updates]["module_hash"]
        optimizer, _ = fresh(model)
        optimizer.load_state_dict(payload["optimizer"])
        assert tree_equal(optimizer.state_dict(), payload["optimizer"])
        assert clocks(model, optimizer) == {"tensors": 4, "states": 4, "steps": [float(updates)]}
        assert set(parameters(model)) == set(saved["head"]) == set(payload["ema"])
        assert len(saved["head"]) == 4
        for state in ["raw", "EMA"]:
            if state == "EMA":
                model.load_state_dict(dict(payload["models"], **payload["ema"]), strict=True)
            assert anchor_hash(model) == plan["anchor"]["module_hash"]
            current = model.state_dict()
            for name, value in source.items():
                assert torch.equal(value, current[name]) and value.dtype == current[name].dtype
                frozen_comparisons += 1
            assert all(torch.isfinite(v).all() for n, v in current.items() if n.startswith(PREFIX))
            checks.append(
                {
                    "measurement": mode,
                    "update": updates,
                    "state": state,
                    "module_hash": model_hash(model),
                    "strict_tensors": 197,
                    "frozen_tensors": 193,
                    "head_parameters": 451,
                }
            )
    assert frozen_comparisons == 772 and len(checks) == 4 and not torch.cuda.is_initialized()
    for name, digest in plan["neural104"].items():
        assert ref(ROOT.parents[2] / "src/demosaic" / name)["sha256"] == digest
    save(
        ROOT / "CPU-inspection-v1.json",
        {
            "status": "pass-V198-four-strict-CPU-raw-EMA-loads772frozen-tensors-Adam",
            "created_unix_UTC": time.time(),
            "admission": ref(ROOT / "admission-result-v1.json"),
            "plan": ref(ROOT / "plan-v1.json"),
            "checks": checks,
            "frozen_tensor_comparisons": frozen_comparisons,
            "new_neural_forwards": 0,
            "CUDA_initialized": False,
        },
    )
    print("PASS4strictCPUloads/772frozencomparisons/2Adamstates", flush=True)


if __name__ == "__main__":
    inspect()
