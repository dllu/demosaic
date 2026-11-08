"""Four strict CPU V195 exports, preserving explicit fresh-stage/donor history."""

import argparse
from pathlib import Path

from directional_trial_protocol import MODES, REPO, factory, read, ref, save
from directional_trial_protocol import TRIAL as ROOT
from phase_admission_protocol import owner_live
from review_directional_response import source_guard


def export():
    plan = read(ROOT / "plan-v1.json")
    source_guard(plan)
    seal = read(ROOT / "export-source-v1.json")
    assert seal["runner"] == ref(__file__) and seal["plan"] == ref(ROOT / "plan-v1.json")
    scores = read(ROOT / "scores-v1.json")
    assert not owner_live(scores["owner"])
    assert read(ROOT / "quality-audit-v1.json")["status"].startswith("pass-V195-four-endpoint")
    import torch
    from phase_wave_training_state import inherited_hash, load_ema
    from profile_raw_kernel_inference import model_hash
    from spatial_wave_training_state import expand_checkpoint

    assert not torch.cuda.is_initialized()
    torch.set_num_threads(1)
    directory = Path(plan["artifacts"]) / "exports"
    directory.mkdir()
    base = torch.load(
        plan["frozen_component"]["export"]["path"], map_location="cpu", weights_only=True
    )
    inherited = torch.load(
        plan["initializer"]["export"]["path"], map_location="cpu", weights_only=True
    )["state_dict"]
    exports = {}
    for mode in MODES:
        checkpoint = scores["checkpoints"][mode]
        assert ref(checkpoint["path"]) == checkpoint
        state = expand_checkpoint(
            torch.load(checkpoint["path"], map_location="cpu", weights_only=True)
        )
        for endpoint, method in plan["methods"][mode].items():
            module = factory(plan["module_config"]).eval()
            module.load_state_dict(state["models"], strict=True)
            if endpoint == "EMA":
                load_ema(module, state["ema"])
            expected = scores["module_hashes"][method]["before"]
            assert model_hash(module) == expected
            assert inherited_hash(module) == plan["initializer"]["module_hash"]
            assert all(torch.equal(module.state_dict()[n], v) for n, v in inherited.items())
            source = ref(REPO / "src/demosaic/late_pooled_phase_wave.py")
            payload = {
                "component": type(module).__name__,
                "module_config": plan["module_config"],
                "state_dict": module.state_dict(),
                "parent": base["parent"],
                "frozen_component": plan["frozen_component"],
                "sampling_library": plan["sampling_library"],
                "source": source,
                "source_checkpoint": checkpoint,
                "endpoint": endpoint,
                "method": method,
                "frozen_V183_initializer": plan["initializer"],
                "trained_head_donor": plan["donor"],
                "response_mode": mode,
                "inherited_network_updates": 1800,
                "inherited_adapter_updates": 900,
                "prior_donor_readout_updates": 900,
                "new_readout_updates": 900,
                "fresh_head_Adam_initial_updates": 0,
                "head_Adam_updates": 900,
                "training_plan": ref(ROOT / "plan-v1.json"),
                "history_scope": "Fresh matched head Adam/EMA stage from completed V187 EMA weights; no old Adam moments or uninterrupted EMA clock claimed.",
            }
            path = directory / f"response-{mode}-{endpoint}-step1000.pt"
            with path.open("xb") as stream:
                torch.save(payload, stream)
            restored = torch.load(path, map_location="cpu", weights_only=True)
            fresh = factory(plan["module_config"]).eval()
            fresh.load_state_dict(restored["state_dict"], strict=True)
            assert model_hash(fresh) == expected and len(fresh.state_dict()) == 193
            exports[method] = {
                "export": ref(path),
                "source_checkpoint": checkpoint,
                "state": endpoint,
                "module_hash": expected,
                "component": payload["component"],
                "module_config": plan["module_config"],
                "source": source,
                "frozen_V183_initializer": plan["initializer"],
                "trained_head_donor": plan["donor"]["export"],
                "response_mode": mode,
                "full_state_tensors": 193,
            }
    assert len(exports) == 4 and not torch.cuda.is_initialized()
    save(
        ROOT / "exports-v1.json",
        {
            "status": "pass-four-strict-CPU-V195-exports-raw-EMA-and-explicit-donor-history",
            "plan": ref(ROOT / "plan-v1.json"),
            "scores": ref(ROOT / "scores-v1.json"),
            "exports": exports,
            "strict_CPU_export_loads": 4,
            "inherited_tensor_comparisons": 756,
            "new_module_forwards": 0,
            "CUDA_initialized": False,
            "source": dict(ref(__file__), text=Path(__file__).read_text()),
            "scope": "Exported candidates are not automatically promoted. Actual native viewing,comparison interpretation,browser pixel verification and publication remain separate requirements.",
        },
    )
    print("PASS: four strict exports /756 inherited comparisons /explicit fresh-stage history")


def prepare():
    plan = read(ROOT / "plan-v1.json")
    source_guard(plan)
    runner = ROOT / "exporter-v1.py"
    with runner.open("x") as stream:
        stream.write(Path(__file__).read_text())
    save(
        ROOT / "export-source-v1.json",
        {
            "status": "prepared-four-strict-exports-quality-audit-required",
            "runner": ref(runner),
            "plan": ref(ROOT / "plan-v1.json"),
            "review_source": ref(ROOT / "review-source-v1.json"),
            "scope": "Use the sealed runner with review-work source imports. Preparation only; exports and promotion not performed.",
        },
    )
    print("Prepared sealed four-export helper; actual quality audit required")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "export"])
    prepare() if parser.parse_args().phase == "prepare" else export()
