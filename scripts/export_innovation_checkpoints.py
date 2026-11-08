"""Four strict standalone V197 exports with measurement configuration and fresh-head history."""

from pathlib import Path

from admit_innovation_wave import MODES, factory
from directional_trial_protocol import REPO, read, ref, save
from phase_admission_protocol import owner_live
from review_innovation_wave import load_new_ema, review_plan, source_guard
from train_innovation_wave import ROOT


def export():
    plan = review_plan()
    seal = source_guard(plan)
    assert seal["exporter"] == ref(__file__) and seal["plan"] == ref(ROOT / "plan-v1.json")
    scores = read(ROOT / "scores-v1.json")
    assert not owner_live(scores["owner"])
    assert read(ROOT / "quality-audit-v1.json")["status"].startswith("pass-V197-four-endpoint")
    import torch
    from innovation_wave_state import anchor_hash
    from innovation_wave_state import expand as expand_checkpoint
    from profile_raw_kernel_inference import model_hash

    from demosaic.late_innovation_wave import LateInnovationWaveDetail

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
            module = factory(plan, mode).eval()
            module.load_state_dict(state["models"], strict=True)
            if endpoint == "EMA":
                load_new_ema(module, state["ema"])
            expected = scores["module_hashes"][method]["before"]
            assert model_hash(module) == expected
            assert anchor_hash(module) == plan["initializer"]["module_hash"]
            assert all(torch.equal(module.state_dict()[n], v) for n, v in inherited.items())
            source = ref(REPO / "src/demosaic/late_innovation_wave.py")
            payload = {
                "component": type(module).__name__,
                "module_config": dict(
                    plan["module_config"], measurement=mode, lower=plan["lower_native_frequency"]
                ),
                "state_dict": module.state_dict(),
                "parent": base["parent"],
                "frozen_component": plan["frozen_component"],
                "sampling_library": plan["sampling_library"],
                "source": source,
                "source_checkpoint": checkpoint,
                "endpoint": endpoint,
                "method": method,
                "frozen_V195_anchor": plan["initializer"],
                "new_head_initialization": "fresh zero-output 508-parameter head;not inherited trained readout",
                "measurement": mode,
                "prior_anchor_readout_updates": 1800,
                "new_readout_updates": 900,
                "fresh_head_Adam_initial_updates": 0,
                "head_Adam_updates": 900,
                "training_plan": ref(ROOT / "plan-v1.json"),
                "history_scope": "Fresh zero-output new head with900updates above all193 frozen trainedV195WholeEMA tensors. Anchor wave history is V187900 then V195900 separately;new head never inherits their Adam/EMA clocks. Measurement changes selectionandlocalfeatures together.",
            }
            path = directory / f"innovation-{mode}-{endpoint}-step1000.pt"
            with path.open("xb") as stream:
                torch.save(payload, stream)
            restored = torch.load(path, map_location="cpu", weights_only=True)
            fresh = LateInnovationWaveDetail(**restored["module_config"]).eval()
            fresh.load_state_dict(restored["state_dict"], strict=True)
            assert model_hash(fresh) == expected and len(fresh.state_dict()) == 197
            exports[method] = {
                "export": ref(path),
                "source_checkpoint": checkpoint,
                "state": endpoint,
                "module_hash": expected,
                "component": payload["component"],
                "module_config": dict(
                    plan["module_config"], measurement=mode, lower=plan["lower_native_frequency"]
                ),
                "source": source,
                "frozen_V195_anchor": plan["initializer"],
                "anchor_export": plan["anchor"]["export"],
                "measurement": mode,
                "full_state_tensors": 197,
            }
    assert len(exports) == 4 and not torch.cuda.is_initialized()
    save(
        ROOT / "exports-v1.json",
        {
            "status": "pass-four-strict-CPU-V197-exports-raw-EMA-and-explicit-donor-history",
            "plan": ref(ROOT / "plan-v1.json"),
            "scores": ref(ROOT / "scores-v1.json"),
            "exports": exports,
            "export_source": ref(ROOT / "review-source-v1.json"),
            "strict_CPU_export_loads": 4,
            "frozen_anchor_tensor_comparisons": 772,
            "new_module_forwards": 0,
            "CUDA_initialized": False,
            "source": dict(ref(__file__), text=Path(__file__).read_text()),
            "scope": "Exported candidates are not automatically promoted. Actual native viewing,comparison interpretation,browser pixel verification and publication remain separate requirements.",
        },
    )
    print("PASS: four strict exports /772 frozen anchor comparisons /explicit fresh-stage history")


if __name__ == "__main__":
    export()
