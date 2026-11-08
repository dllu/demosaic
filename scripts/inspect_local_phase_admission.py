"""Independently inspect the terminal V180 CUDA admission on CPU."""

import json
from pathlib import Path

from phase_admission_protocol import owner_live, read, ref

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261107/V180-local-phase-admission-v1"


def inspect():
    plan = read(ROOT / "plan-v1.json")
    for phase in ["watch", "admission"]:
        owner = read(ROOT / f"{phase}-launch-v1.json")["owner"]
        assert not owner_live(owner)
        assert not (ROOT / f"{phase}-failure-v1.json").exists()
    result = read(ROOT / "admission-result-v1.json")
    assert result["owner"] == read(ROOT / "admission-launch-v1.json")["owner"]
    assert (
        result["status"]
        == "pass-V180-native-CUDA-initial-parity-real-gradients-restoration-and-local-ADC-invariants"
    )
    assert result["plan"] == ref(ROOT / "plan-v1.json")
    assert (
        result["operator_source"] == plan["operator_source"] == ref(plan["operator_source"]["path"])
    )
    assert result["component"] == "LateLocalPhaseEvidenceMatchingDetail"
    assert result["module_config"] == plan["module_config"]
    assert len(result["parity"]) == 14 and all(
        p["initial_output_bit_exact"] and p["baseline"] == p["candidate"] for p in result["parity"]
    )
    assert len(result["updates"]) == 2 and all(
        len(u["gradients"]) == 142 and all(g["nonzero"] > 0 for g in u["gradients"].values())
        for u in result["updates"]
    )
    assert all(
        u["gradients"]["phase_evidence_in.weight"]["nonzero"] == 3120 for u in result["updates"]
    )
    counts = {
        a: dict.fromkeys(["wrapper", "frozen", "network", "sampler", "projection"], 0)
        for a in ["old", "new"]
    }
    events = [
        json.loads(line) for line in (ROOT / "forward-events-v1.jsonl").read_text().splitlines()
    ]
    assert len(events) == 241
    for event in events:
        counts[event["component"]][event["kind"]] += 1
        assert event["counts"] == counts
    assert counts == result["counts"] and result["totals"] == {
        "wrapper": 32,
        "frozen": 32,
        "network": 27,
        "sampler": 135,
        "projection": 15,
    }
    restoration = read(ROOT / "restoration-v1.json")
    assert (
        restoration["Adam_moments_exact"]
        and restoration["CPU_CUDA_RNG_exact"]
        and restoration["replayed_updates"] == 0
    )
    assert (
        result["direct_constant_feature_maps_zero"]
        and result["measured_phase_cannot_change_selecting_phase_bins_or_power"]
    )
    for path, digest in plan["frozen_files"].items():
        assert ref(path)["sha256"] == digest
    for binding in plan["inputs"]:
        assert ref(binding["path"]) == binding

    import torch
    from profile_raw_kernel_inference import model_hash

    from demosaic.late_local_phase_evidence_matching import LateLocalPhaseEvidenceMatchingDetail

    assert not torch.cuda.is_initialized()
    torch.set_num_threads(1)
    initial = torch.load(plan["checkpoint"]["path"], map_location="cpu", weights_only=True)
    checked = []
    for update, binding in enumerate(result["post_update_checkpoints"], 1):
        assert ref(binding["path"]) == binding
        state = torch.load(binding["path"], map_location="cpu", weights_only=True)
        assert (
            state["updates"] == update
            and state["component"] == result["component"]
            and state["module_config"] == plan["module_config"]
        )
        assert state["plan"] == result["plan"]
        assert len(state["optimizer"]["state"]) == 142 and all(
            float(s["step"]) == update and all(torch.isfinite(v).all() for v in s.values())
            for s in state["optimizer"]["state"].values()
        )
        frozen = [k for k in state["models"] if k.startswith("frozen.")]
        assert len(frozen) == 47 and all(
            torch.equal(state["models"][k], initial["models"][k]) for k in frozen
        )
        assert state["models"]["phase_evidence_in.weight"].count_nonzero() == 3120
        module = LateLocalPhaseEvidenceMatchingDetail(**plan["module_config"]).eval()
        module.load_state_dict(state["models"], strict=True)
        assert model_hash(module) == result["updates"][update - 1]["model_hash"]
        assert model_hash(module.frozen) == result["frozen_module_hash"]
        checked.append(
            {
                "checkpoint": binding,
                "fresh_Adam_states": 142,
                "Adam_step": update,
                "frozen47_exact_initial": True,
                "module_hash": model_hash(module),
                "component": type(module).__name__,
            }
        )
        del module, state
    assert not torch.cuda.is_initialized()
    output = {
        "status": "pass-actual-terminal-V180-admission-journal-local-features-and-two-strict-CPU-checkpoints",
        "admission": ref(ROOT / "admission-result-v1.json"),
        "plan": ref(ROOT / "plan-v1.json"),
        "checkpoint_checks": checked,
        "component_events": 241,
        "initial_parity_rows": 14,
        "feature_coordinates_checked": sum(
            p.get("feature_coordinates_checked", 0) for p in result["parity"]
        ),
        "local_center_powers_checked": sum(
            p.get("local_center_powers_checked", 0) for p in result["parity"]
        ),
        "maximum_CPU_GPU_feature_difference": max(
            p.get("CPU_GPU_feature_maximum_difference", 0) for p in result["parity"]
        ),
        "maximum_CPU_GPU_local_power_difference": max(
            p.get("local_center_power_maximum_difference", 0) for p in result["parity"]
        ),
        "new_neural_forwards": 0,
        "new_updates": 0,
        "CUDA_initialized": False,
        "source": dict(ref(__file__), text=Path(__file__).read_text()),
        "scope": "Actual implementation probe,not trained quality. Fresh-Adam clocks1/2 do not replace V172 history for future training. No original capture or dataz access.",
    }
    with (ROOT / "CPU-inspection-v1.json").open("x") as stream:
        json.dump(output, stream, indent=2)
        stream.write("\n")
    print("PASS terminalV180/241events/14parity/2strictCPUcheckpoints;zeroCUDA/forwards")


if __name__ == "__main__":
    inspect()
