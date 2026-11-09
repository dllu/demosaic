"""Verify V200 engineering receipts and snapshot the launched training state.

No Torch imports, neural forwards or measurement reruns. Existing receipts and
source bytes remain unchanged. A live-owner observation is a timestamped fact,
not a claim that training or quality has completed.
"""

import shutil
import sys
import time
from pathlib import Path

from directional_trial_protocol import REPO, guard, read, ref, save
from phase_admission_protocol import owner_live

ADMISSION = REPO / ".cache/quality-20261108/V200-scale-supported-CFA-admission-v1"
TRIAL = REPO / ".cache/quality-20261108/V200-scale-supported-CFA-trial-v1"
PUBLIC = REPO / "docs/results/v200-scale-supported-CFA-preparation-v1"
INDEX = REPO / "docs/results/v200-scale-supported-CFA-preparation-v1.json"


def main():
    assert "torch" not in sys.modules and not PUBLIC.exists() and not INDEX.exists()
    admission, trial = [read(p / "plan-v1.json") for p in (ADMISSION, TRIAL)]
    guard(admission)
    guard(trial)
    result, inspected = [
        read(ADMISSION / n) for n in ("admission-result-v1.json", "CPU-inspection-v1.json")
    ]
    assert result["plan"] == ref(ADMISSION / "plan-v1.json")
    assert result["owner"] == read(ADMISSION / "probe-launch-v1.json")["owner"]
    assert (
        not owner_live(result["owner"]) and not (ADMISSION / "admission-failure-v1.json").exists()
    )
    assert result["status"].startswith("pass-V200-scale-supported-CFA")
    assert inspected["admission"] == ref(ADMISSION / "admission-result-v1.json")
    assert inspected["frozen_tensor_comparisons"] == 772 and len(inspected["checks"]) == 4
    assert all(
        c["head_parameters"] == 643 and c["strict_tensors"] == 197 for c in inspected["checks"]
    )
    assert not inspected["CUDA_initialized"]
    assert len(result["parities"]) == 8 and all(
        p["anchor_initial_bit_exact"] for p in result["parities"]
    )
    assert len(result["records"]) == 2 and len(result["restorations"]) == 1
    assert result["records"][1]["extra_support_weight_nonzero_gradient_coordinates"] == 192
    assert result["restorations"][0]["strict_model_Adam_EMA_CPU_CUDA_RNG_exact"]
    assert result["protected_optimizer_inputs"] == result["new_source_noise_draws"] == 0
    old = admission["neural105"]
    assert len(old) == 105
    for name, digest in old.items():
        assert ref(REPO / "src/demosaic" / name)["sha256"] == digest
    neural = {**old, **{Path(b["path"]).name: b["sha256"] for b in admission["new_sources"]}}
    assert len(neural) == 107
    for name, digest in neural.items():
        assert ref(REPO / "src/demosaic" / name)["sha256"] == digest
    assert "34 passed" in Path(admission["CPU_tests"]["path"]).read_text()
    initial = read(TRIAL / "scale-initial-state-v1.json")
    assert initial["module_hash"] == trial["CPU_initialization"]["full_module_hash"]
    assert initial["anchor_hash"] == admission["anchor"]["module_hash"]
    assert initial["Adam"] == {"tensors": 4, "states": 0, "steps": []}
    assert initial["EMA_equals_fresh_head"] and initial["new_module_forwards"] == 0
    restored = read(TRIAL / "scale-restoration-v1.json")
    assert restored["model_Adam_EMA_CPU_CUDA_RNG_exact"]
    assert restored["continued_at_row"] == 9 and restored["repeated_prefix_forwards"] == 0
    worker = read(TRIAL / "scale-launch-v1.json")["owner"]
    controller = read(TRIAL / "training-controller-v1/watch-launch-v1.json")["owner"]
    assert owner_live(worker) and owner_live(controller)
    observed = read(TRIAL / "scale-status-v1.json")
    assert observed["owner"] == worker and observed["updates"] > 8
    assert not (TRIAL / "scale-train-failure-v1.json").exists()
    PUBLIC.mkdir()
    copies = []

    def copy(source, name):
        target = PUBLIC / name
        shutil.copyfile(source, target)
        assert ref(source)["sha256"] == ref(target)["sha256"]
        copies.append({"original": ref(source), "public": ref(target)})

    for name in [
        "plan-v1.json",
        "probe-launch-v1.json",
        "admission-result-v1.json",
        "CPU-inspection-v1.json",
        "probe-v1.log",
        "CPU-inspection-v1.log",
    ]:
        copy(ADMISSION / name, "admission-" + name)
    for name in [
        "plan-v1.json",
        "scale-launch-v1.json",
        "scale-initial-state-v1.json",
        "scale-restoration-v1.json",
    ]:
        copy(TRIAL / name, "training-" + name)
    for name in ["plan-v1.json", "watch-launch-v1.json"]:
        copy(TRIAL / "training-controller-v1" / name, "controller-" + name)
    for name in [
        "v200-cfa-scale-support-math-tests-v1.log",
        "v200-scale-supported-CFA-CPU-tests-v1.log",
        "v200-scale-supported-CFA-CPU-tests-v2.log",
    ]:
        copy(REPO / ".cache" / name, name)
    copy(REPO / "docs/scale-supported-cfa-wave.md", "architecture-at-admission.md")
    save(
        PUBLIC / "training-observed-v1.json",
        {
            "observed_unix_UTC": time.time(),
            "worker": worker,
            "controller": controller,
            "both_owners_confirmed_live": True,
            "progress": observed,
            "scope": "Timestamped live-owner observation; training and quality pending.",
        },
    )
    counts = {
        k: sum(p.get(k, 0) for p in result["parities"])
        for k in [
            "native_values",
            "independently_checked_context_values",
            "independently_checked_physical_wave_values",
            "independently_checked_nominal_covariance_values",
            "extra_support_coordinates",
        ]
    }
    assert counts["independently_checked_context_values"] == 325582848
    assert counts["independently_checked_physical_wave_values"] == 54263808
    assert counts["independently_checked_nominal_covariance_values"] == 4993152
    assert "torch" not in sys.modules
    save(
        INDEX,
        {
            "status": "pass-V200-CPU-GPU-engineering-fresh-trial-launched-quality-pending",
            "created_unix_UTC": time.time(),
            "admission": ref(ADMISSION / "plan-v1.json"),
            "admission_result": ref(ADMISSION / "admission-result-v1.json"),
            "CPU_inspection": ref(ADMISSION / "CPU-inspection-v1.json"),
            "terminal_admission_owner": result["owner"],
            "CPU_GPU_compared_coordinates": counts,
            "CPU_tests": admission["CPU_tests"],
            "CPU_test_count": 34,
            "all105_previous_neural_sources_unchanged": old,
            "all107_current_neural_sources": neural,
            "anchor": admission["anchor"],
            "training_plan": ref(TRIAL / "plan-v1.json"),
            "training_initial_full_module_hash": initial["module_hash"],
            "training_Adam_initial_steps": 0,
            "training_EMA_initial_steps": 0,
            "training_observation": ref(PUBLIC / "training-observed-v1.json"),
            "public_evidence": copies,
            "source": ref(__file__),
            "new_neural_forwards_by_publication": 0,
            "torch_imported_by_publication": False,
            "scope": "Engineering admission only; paired training-only probes and fresh full trial have separate clocks. "
            "No trained quality gain or flat safety claim. Both endpoints/all822 cases and required native/real comparisons pending. "
            "Nominal covariance/interpolation bounds omit correlated anchor/selection effects and are not calibrated confidence. "
            "Twelve context coordinates and192parameters are added together; existing105neural sources/checkpoints unchanged. "
            "No new data/noise/source draws, RAW decode, original/dataz access or external writes.",
        },
    )
    print(
        "PASS34CPUtests/8actualparities/7CPU-GPUmaps-heads/2restoredprobes/4CPUstates;freshtrial-live"
    )


if __name__ == "__main__":
    main()
