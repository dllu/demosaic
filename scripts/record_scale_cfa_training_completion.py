"""Archive completed V200 training and explicitly non-quality viewer checks.

No Torch import, neural forward or metric rerun. The live full-quality worker
continues independently; these receipts do not establish restoration quality.
"""

import gzip
import hashlib
import shutil
import sys
import time

from check_scale_supported_cfa_viewer_pixels import verify as verify_actual_browser
from directional_trial_protocol import REPO, guard, read, ref, save
from phase_admission_protocol import owner_live
from review_scale_supported_cfa_wave import review_plan, source_guard
from train_scale_supported_cfa_wave import ROOT

PUBLIC = REPO / "docs/results/v200-scale-supported-cfa-training-completed-v1"
INDEX = REPO / "docs/results/v200-scale-supported-cfa-training-completed-v1.json"


def record():
    assert "torch" not in sys.modules and not PUBLIC.exists() and not INDEX.exists()
    plan = review_plan()
    source_guard(plan)
    result = read(ROOT / "scale-train-result-v1.json")
    owner = read(ROOT / "scale-launch-v1.json")["owner"]
    assert result["owner"] == owner and not owner_live(owner)
    assert result["status"] == "completed-V200-CFA-wave-head-above-frozen-V195-WholeEMA"
    assert result["plan"] == ref(ROOT / "plan-v1.json")
    assert (
        result["updates"] == 900
        and result["training_images"] == 3600
        and result["ADC_skips"] == 100
    )
    assert result["anchor193_tensors_unchanged"] and result["RNG_unchanged"]
    assert result["counts"] == plan["expected_training_counts_per_arm"]
    assert result["final_Adam"] == {"tensors": 4, "states": 4, "steps": [900.0]}
    assert len(result["checkpoints"]) == 5 and len(result["trace"]) == 1000
    assert result["restoration"]["continued_at_row"] == 9
    assert result["restoration"]["repeated_prefix_forwards"] == 0
    for binding in result["checkpoints"]:
        assert ref(binding["path"]) == binding
    audit = read(ROOT / "training-audit-v1.json")
    assert audit["status"].startswith("pass-V200-full-CFA-trace")
    assert audit["plan"] == ref(ROOT / "plan-v1.json")
    assert audit["training"]["scale"] == ref(ROOT / "scale-train-result-v1.json")
    assert audit["frozen_tensor_comparisons"] == 1930 and len(audit["checkpoint_states"]) == 10
    assert (
        audit["checks"]["scale"]["FP32_ten_term_totals"]
        == audit["checks"]["scale"]["clean_masks"]
        == 900
    )
    assert audit["new_neural_forwards"] == 0 and not audit["CUDA_initialized"]
    training_controller = ROOT / "training-controller-v1"
    completed = read(training_controller / "watch-result-v1.json")
    assert not owner_live(completed["owner"])
    assert completed["training_audit"] == ref(ROOT / "training-audit-v1.json")
    assert not owner_live(completed["auditor_owner"])
    bridge = read(ROOT / "feature-bridge-v1.json")
    assert not owner_live(bridge["owner"]) and len(bridge["checks"]) == 4
    assert (
        bridge["actual_neural_forwards"]
        == bridge["new_source_noise_draws"]
        == bridge["protected_optimizer_inputs"]
        == 0
    )
    fixture = ROOT / "viewer-fixture-v1"
    guard(read(fixture / "plan-v1.json"))
    verified = read(fixture / "browser-fixture-verification-v1.json")
    assert verified["fixture_only_no_V200_quality"] is True
    assert verified["native_captures"] == 210 and verified["exact_RGB_channels"] == 16128000
    assert ref(verified["browser_records"]["path"]) == verified["browser_records"]
    # Exercise the real actual-quality boundary using actual fixture records.
    unexpected = fixture / "must-not-create-actual-quality-verification.json"
    assert not unexpected.exists()
    try:
        verify_actual_browser(fixture / "browser-v1", unexpected)
    except AssertionError:
        rejected = True
    else:
        rejected = False
    assert rejected and not unexpected.exists()
    neural = read(REPO / "docs/results/v200-scale-supported-CFA-preparation-v1.json")[
        "all107_current_neural_sources"
    ]
    assert len(neural) == 107
    for name, digest in neural.items():
        assert ref(REPO / "src/demosaic" / name)["sha256"] == digest
    for name in ["publication-source-v1.json", "verification-source-v1.json"]:
        seal = read(ROOT / name)
        for path, digest in seal["frozen_files"].items():
            assert ref(path)["sha256"] == digest
    review_owner = read(ROOT / "review-launch-v1.json")["owner"]
    live = owner_live(review_owner)
    if not live:
        assert read(ROOT / "scores-v1.json")["owner"] == review_owner
    assert not (ROOT / "review-failure-v1.json").exists()
    PUBLIC.mkdir()
    copies = []
    for source, name in [
        *[
            (ROOT / n, n)
            for n in [
                "scale-train-result-v1.json",
                "scale-train-trace-v1.jsonl",
                "training-audit-v1.json",
                "scale-initial-state-v1.json",
                "scale-restoration-v1.json",
                "feature-bridge-v1.json",
                "publication-source-v1.json",
                "verification-source-v1.json",
                "report-source-v1.json",
            ]
        ],
        (training_controller / "watch-result-v1.json", "training-controller-result-v1.json"),
        (training_controller / "audit-v1.log", "training-audit-v1.log"),
        (fixture / "plan-v1.json", "viewer-fixture-plan-v1.json"),
        (fixture / "browser-fixture-verification-v1.json", "browser-fixture-verification-v1.json"),
        (fixture / "verification-v1.log", "browser-fixture-verification-v1.log"),
        (fixture / "browser-v1.log", "browser-fixture-v1.log"),
    ]:
        original = ref(source)
        if source.stat().st_size > 200000:
            target = PUBLIC / (name + ".gz")
            with source.open("rb") as src, gzip.open(target, "xb") as dst:
                shutil.copyfileobj(src, dst)
            with gzip.open(target, "rb") as stream:
                assert hashlib.file_digest(stream, "sha256").hexdigest() == original["sha256"]
            copies.append(
                {
                    "original": original,
                    "public_gzip": ref(target),
                    "decompressed_SHA256": original["sha256"],
                }
            )
        else:
            target = PUBLIC / name
            with target.open("xb") as stream:
                stream.write(source.read_bytes())
            assert ref(target)["sha256"] == original["sha256"]
            copies.append({"original": original, "public": ref(target)})
    save(
        PUBLIC / "quality-owner-observation-v1.json",
        {
            "observed_unix_UTC": time.time(),
            "owner": review_owner,
            "live": live,
            "progress": read(ROOT / "review-status-v1.json"),
            "scope": "Timestamped quality execution observation,not audited quality completion.",
        },
    )
    assert "torch" not in sys.modules
    save(
        INDEX,
        {
            "status": "completed-V200-900-update-training-audited-quality-review-running",
            "created_unix_UTC": time.time(),
            "training_plan": ref(ROOT / "plan-v1.json"),
            "training_result": ref(ROOT / "scale-train-result-v1.json"),
            "training_owner_terminal": owner,
            "training_audit": ref(ROOT / "training-audit-v1.json"),
            "updates": 900,
            "training_images": 3600,
            "ADC_skips": 100,
            "full_trace_rows": 1000,
            "independent_loss_total_and_mask_checks_each": 900,
            "factored_checkpoints": result["checkpoints"],
            "strict_raw_EMA_states": 10,
            "unchanged_anchor_tensor_comparisons": 1930,
            "all107_neural_hashes_unchanged": neural,
            "browser_fixture": ref(fixture / "browser-fixture-verification-v1.json"),
            "fixture_captures": 210,
            "fixture_exact_RGB_channels": 16128000,
            "actual_quality_verifier_rejects_fixture_records": True,
            "fixture_first_screen_actually_viewed_at_original_detail": ref(
                fixture / "browser-v1/screen-first.png"
            ),
            "quality_observation": ref(PUBLIC / "quality-owner-observation-v1.json"),
            "public_evidence": copies,
            "source": ref(__file__),
            "new_neural_forwards_by_recording": 0,
            "scope": "Completed fresh643parameter-stage training,not image quality. Full raw/EMA all822 review is separate. "
            "Four CUDA input-only support bridges passed without module forwards. Seven-state UI fixture uses six reusedV198boards with explicitly labeledV200 aliases,not candidate predictions. "
            "Actual viewer/fullcase PNG checks,native viewing,interpretation and final publication remain pending. No new data/noise/RAW decode,original/dataz access or external writes. All existing107neural sources/checkpoints/evidence preserved.",
        },
    )
    print(
        "PASS900updates/1000rows/5checkpoints/1930anchorchecks/210fixturecaptures;actual-quality-pending"
    )


if __name__ == "__main__":
    record()
