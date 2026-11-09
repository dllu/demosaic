"""Record frozen V200 review/preflight readiness and actual process observations.

No Torch import, neural forward, metric rerun, artifact rendering or promotion.
Original receipts remain untouched; this archives a preparation-time snapshot.
"""

import sys
import time
from pathlib import Path

from directional_trial_protocol import REPO, guard, read, ref, save
from phase_admission_protocol import owner_live
from review_scale_supported_cfa_wave import review_plan, source_guard
from train_scale_supported_cfa_wave import ROOT

PUBLIC = REPO / "docs/results/v200-scale-CFA-quality-readiness-v1"
INDEX = REPO / "docs/results/v200-scale-CFA-quality-readiness-v1.json"


def record():
    assert "torch" not in sys.modules and not PUBLIC.exists() and not INDEX.exists()
    plan = review_plan()
    seal = source_guard(plan)
    stage = ROOT / "quality-controller-v1"
    controller = read(stage / "plan-v1.json")
    guard(controller)
    assert controller["work"] == seal["work"]
    assert (
        ref(seal["reviewer"]["path"])["sha256"]
        == ref(REPO / "scripts/review_scale_supported_cfa_wave.py")["sha256"]
    )
    metric = read(ROOT / "metric-preflight-v1.json")
    layouts = read(ROOT / "input-layout-preflight-v1.json")
    display = read(ROOT / "reference-display-preflight-v1.json")
    assert metric["review_source"] == ref(ROOT / "review-source-v1.json")
    assert metric["cases"] == 36 and metric["numeric_scalars_within_1e-10"] == 255
    assert metric["new_module_forwards"] == 0 and not metric["CUDA_initialized"]
    assert (
        sum(layouts["color_layout_counts"].values()) == 822 and layouts["target_arrays_read"] == 0
    )
    assert (
        display["exact_GT_panels_checked"] == 52
        and display["native_RGB_channels_checked"] == 3993600
    )
    assert display["new_neural_forwards"] == display["new_images_written"] == 0
    assert "35 passed" in Path(seal["CPU_contracts"]["path"]).read_text()
    assert "35 passed" in (ROOT / "frozen-evidence-CPU-tests-v1.log").read_text()
    neural = read(REPO / "docs/results/v200-scale-supported-CFA-preparation-v1.json")[
        "all107_current_neural_sources"
    ]
    for name, digest in neural.items():
        assert ref(REPO / "src/demosaic" / name)["sha256"] == digest
        assert ref(Path(seal["work"]) / "src/demosaic" / name)["sha256"] == digest
    assert len(neural) == 107
    for name in ("test_scale_cfa_evidence_receipt.py", "test_cfa_wave_evidence_receipt.py"):
        assert (
            ref(Path(seal["work"]) / "tests" / name)["sha256"]
            == ref(REPO / "tests" / name)["sha256"]
        )
    owners = {}
    for name, launch in [
        ("training", ROOT / "scale-launch-v1.json"),
        ("training-controller", ROOT / "training-controller-v1/watch-launch-v1.json"),
        ("quality-controller", stage / "watch-launch-v1.json"),
    ]:
        owner = read(launch)["owner"]
        owners[name] = {"owner": owner, "live": owner_live(owner), "launch": ref(launch)}
    assert owners["quality-controller"]["live"]
    assert not (stage / "watch-failure-v1.json").exists()
    PUBLIC.mkdir()
    copies = []
    for source, name in [
        (ROOT / "review-source-v1.json", "review-source-v1.json"),
        (ROOT / "metric-preflight-v1.json", "metric-preflight-v1.json"),
        (ROOT / "metric-preflight-v1.log", "metric-preflight-v1.log"),
        (ROOT / "input-layout-preflight-v1.json", "input-layout-preflight-v1.json"),
        (ROOT / "reference-display-preflight-v1.json", "reference-display-preflight-v1.json"),
        (ROOT / "display-preflight-v1.log", "display-preflight-v1.log"),
        (ROOT / "frozen-evidence-CPU-tests-v1.log", "frozen-evidence-CPU-tests-v1.log"),
        (Path(seal["CPU_contracts"]["path"]), "evidence-CPU-tests-v1.log"),
        (stage / "plan-v1.json", "controller-plan-v1.json"),
        (stage / "watch-launch-v1.json", "controller-launch-v1.json"),
    ]:
        target = PUBLIC / name
        with target.open("xb") as stream:
            stream.write(source.read_bytes())
        assert ref(source)["sha256"] == ref(target)["sha256"]
        copies.append({"original": ref(source), "public": ref(target)})
    save(
        PUBLIC / "owner-observation-v1.json",
        {
            "observed_unix_UTC": time.time(),
            "registered_owners": owners,
            "training_progress": read(ROOT / "scale-status-v1.json"),
            "quality_controller_progress": read(stage / "watch-status-v1.json"),
            "scope": "Process observations at this instant; not training/quality completion.",
        },
    )
    assert "torch" not in sys.modules
    save(
        INDEX,
        {
            "status": "pass-frozen-V200-quality-preflight-controller-registered-quality-pending",
            "created_unix_UTC": time.time(),
            "training_plan": ref(ROOT / "plan-v1.json"),
            "review_source": ref(ROOT / "review-source-v1.json"),
            "CPU_contract_tests": 35,
            "frozen_copy_contract_tests": 35,
            "baseline_metric_cases": 36,
            "baseline_metric_scalars": 255,
            "cached_layouts": 822,
            "existing_exact_GT_panels": 52,
            "existing_reference_RGB_channels_checked": 3993600,
            "all107_neural_sources": neural,
            "public_evidence": copies,
            "owner_observation": ref(PUBLIC / "owner-observation-v1.json"),
            "planned_candidate_endpoints": 2,
            "planned_cases_per_endpoint": 822,
            "planned_combined_comparison_methods": 11,
            "planned_combined_metric_rows": 9042,
            "planned_native_figures": 60,
            "planned_native_triplets": 12,
            "planned_old_V198_measurement_groups_to_check": 750,
            "new_neural_forwards_by_readiness_record": 0,
            "torch_imported": False,
            "source": ref(__file__),
            "scope": "Preparation only. Controller follows original training owner/audit,then one feature-only CUDA bridge and one two-endpoint full review,CPU audit/reduction/exports/directional checks/native rendering. "
            "No restarted scientific prefix on observation timeout. New support receipts bind 36channels,12agreement coordinates,three amplitude/covariance geometries/trace bounds and rawEMA identity;oldV198basis/24contexts/selection/support must replay exactly. "
            "Real ISO100/AHD/JPEG references remain independent/not exactGT,never scored. Both protected capture families/siblings/JPEGs heldout. Actual quality and viewing pending;no promotion,new data/noise/RAW decode,original/dataz access or external writes. Existing2GiB local trial budget retained.",
        },
    )
    print(
        "PASS35contracts+35frozen/36metriccases255scalars/822layouts/52GTpanels3993600RGB;registeredreview-pending"
    )


if __name__ == "__main__":
    record()
