"""Publish byte-exact V151 receipts after independent audit and native viewing."""

import argparse
import shutil
import time
from pathlib import Path

from train_directional_bank_trial import guard, read, ref, save

REPO = Path(__file__).resolve().parents[1]


def main(root):
    plan = read(root / "plan-v1.json")
    guard(plan)
    guard(read(root / "postprocess-plan-v1.json"))
    figures = read(root / "figures-v1.json")
    viewing = read(root / "native-viewing-v1.json")
    assert viewing["primary_figures_covered"] == 84 and viewing["sheets_viewed"] == 21
    assert viewing["no_resize"] and viewing["figure_manifest"] == ref(root / "figures-v1.json")
    assert read(root / "independent-metrics-audit-v1.json")["status"] == "pass"
    assert (
        read(root / "independent-training-audit-v1.json")["native_control_predictions_exact"]
        == 1644
    )
    assert read(root / "execution-completion-v1.json")["recorded_owner_count"] == 9
    assert read(root / "execution-completion-v1.json")["status"] == "all9-primary-owners-terminal"
    destination = REPO / "docs/results/v151-noisy-objective-v1"
    assets = REPO / "docs/images/v151-noisy-objective-v1"
    destination.mkdir(exist_ok=False)
    assets.mkdir(exist_ok=False)
    names = {
        "training-result.json": "train-result-v1.json",
        "training-audit.json": "independent-training-audit-v1.json",
        "training-state-audit.json": "independent-training-state-audit-v1.json",
        "training-routing.json": "training-routing-summary-v1.json",
        "proposal-support.json": "proposal-support-summary-v1.json",
        "review-result.json": "review-result-v1.json",
        "scores.json": "scores-v1.json",
        "metric-audit.json": "independent-metrics-audit-v1.json",
        "figures.json": "figures-v1.json",
        "native-viewing.json": "native-viewing-v1.json",
        "execution-completion.json": "execution-completion-v1.json",
        "training-completion.json": "status-v1.json",
        "postprocess-completion.json": "postprocess-status-v1.json",
    }
    sources = {name: root / original for name, original in names.items()}
    review = read(root / "review-result-v1.json")
    assert len(review["collections"]) == 6 and review["component_forwards"] == 4932
    for label, binding in review["collections"].items():
        sources[f"{label}-collection.json"] = Path(binding["path"])
    copies = {}
    for name, original in sources.items():
        public = destination / name
        shutil.copyfile(original, public)
        before, after = ref(original), ref(public)
        assert before["sha256"] == after["sha256"]
        copies[name] = {"original": before, "public": after}
    images = []
    for item in figures["images"]:
        original = Path(item["image"]["path"])
        assert ref(original) == item["image"]
        public = assets / original.name
        shutil.copyfile(original, public)
        assert ref(public)["sha256"] == item["image"]["sha256"]
        images.append({**item, "original_image": item["image"], "image": ref(public)})
    assert len(images) == 84 and sum("triplet_source_board" in item for item in images) == 36
    save(
        assets / "manifest-v1.json",
        {
            "status": "published-byte-exact-native-comparisons-after-actual-viewing",
            "source_manifest": ref(root / "figures-v1.json"),
            "native_viewing": ref(root / "native-viewing-v1.json"),
            "checkpoints": figures["checkpoints"],
            "parent": figures["parent"],
            "images": images,
            "primary_images": 84,
            "triplets": 36,
            "no_resize": True,
            "independently_checked_RGB_channels": figures["all_RGB_channels_checked"],
            "scope": "All six fixed final raw/EMA endpoints on 822 cases, including 24 ADC controls, with identical source arrays, ROI, noise conditioning, exposure, anchor/contrast. All 160x160 native cells, no resize. Both standing real scenes/priors/windows/JPEGs included; independent ISO100/AHD/JPEG references are qualitative, not exact GT. Triplets repeat existing comparison pixels, not observations.",
        },
    )
    neural = {p: sha for p, sha in plan["frozen_files"].items() if "/src/demosaic/" in p}
    assert len(neural) == 85
    extra = [REPO / "scripts/audit_noisy_objective_training.py", Path(__file__)]
    save(
        destination / "source-bundle.json",
        {
            "preparation": ref(REPO / "docs/results/v151-noisy-objective-preparation-v1.json"),
            "frozen_neural_file_count": 85,
            "frozen_neural_source_hashes": neural,
            "additional_sources": [dict(ref(p), text=p.read_text()) for p in extra],
            "scope": "Original preparation binds frozen neural,training,review and scoring/rendering sources. This adds the posthoc endpoint-state/control auditor and publication driver. No scientific operator,input,loss or endpoint changed after the fixed design.",
        },
    )
    save(
        destination / "summary.json",
        {
            "scores": ref(root / "scores-v1.json"),
            "groups": read(root / "scores-v1.json")["summary"],
            "scope": "Mean per-observation errors on the adaptive retained cohort. Four CFA placements of a recipe are related, not independent scenes. Actual blank/DC/spatial errors accompany correction energy; real references remain unscored.",
        },
    )
    save(
        REPO / "docs/results/v151-noisy-objective-final-v1.json",
        {
            "status": "completed-six-fixed-endpoints-audited-and-natively-viewed",
            "recorded_unix_UTC": time.time(),
            "copies": copies,
            "preparation": ref(REPO / "docs/results/v151-noisy-objective-preparation-v1.json"),
            "source_bundle": ref(destination / "source-bundle.json"),
            "summary": ref(destination / "summary.json"),
            "figures": ref(assets / "manifest-v1.json"),
            "checkpoint": read(root / "train-result-v1.json")["checkpoint"],
            "endpoints": figures["checkpoints"],
            "steps_per_arm": 1000,
            "arms": 3,
            "quality_component_forwards": 4932,
            "training_component_forwards": 3000,
            "discarded_smoke_component_forwards": 30,
            "compatibility_forward_function_evaluations": 56,
            "total_tracked_component_forward_function_evaluations": 8018,
            "adopted_training_observations": 4000,
            "new_parent_DINO_forwards_in_training_and_review": 0,
            "separate_ADC_parent_forwards": 0,
            "separate_ADC_DINO_forwards": 0,
            "new_noise_draws": 0,
            "floor16_control_predictions_exact_V150": 1644,
            "native_primary_figures": 84,
            "native_sheets_actually_viewed": 21,
            "independently_checked_RGB_channels": figures["all_RGB_channels_checked"],
            "recorded_terminal_primary_owners": 9,
            "scope": "All three fresh matched 1k arms and six prospectively fixed final endpoints are reported, with no early epoch selection. Counts exclude component unit tests. The 16 DN control reproduces V150 floor16 exactly on all 1644 predictions, including the 24 ADC cases. All training/review arrays and parents are adopted without new noise or parent/DINO calls. Human quality conclusions belong in the current report; completion of this finite experiment does not complete the user's broader fine-detail/clean-sky objective.",
        },
    )
    print(f"Published {len(copies)} byte-exact receipts and {len(images)} native comparisons")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    main(parser.parse_args().root.absolute())
