"""Audit saved training metadata and completed trace; never read image arrays."""

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def read(path):
    return json.loads(Path(path).read_text())


def ref(path):
    path = Path(path).resolve()
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path), "sha256": digest}


def bounds(values):
    assert values and all(math.isfinite(v) for v in values)
    return {"count": len(values), "minimum": min(values), "maximum": max(values)}


def audit(repository, trial):
    plan_path = trial / "plan-v1.json"
    plan = read(plan_path)
    cache_binding = plan["cache"]
    assert ref(cache_binding["path"]) == cache_binding
    cache = read(cache_binding["path"])
    result_path = trial / "scale-train-result-v1.json"
    result = read(result_path)
    assert result["status"].startswith("completed") and result["updates"] == 900
    trace = result["trace"]
    batches = cache["batches"]
    assert len(trace) == len(batches) == 1000
    bindings = [ref(plan_path), cache_binding, ref(result_path), ref(__file__)]
    by_domain = defaultdict(Counter)
    sizes = defaultdict(Counter)
    photo_contrasts, mixed_levels, mixed_widths = [], [], []
    mixed_pairs = Counter()
    backgrounds = defaultdict(Counter)
    for expected_step, (item, row) in enumerate(zip(batches, trace, strict=True), 1):
        metadata = item["metadata"]
        domain = metadata["domain"]
        noise = metadata["noise"]
        noisy = noise["shot"] > 0 or noise["read"] > 0
        assert item["step"] == metadata["step"] == row["step"] == expected_step
        assert row["batch"] == item["arrays"] and row["domain"] == domain
        assert row["noisy"] == noisy
        cases = metadata["cases"]
        assert len(cases) == 4
        by_domain[domain]["total_batches"] += 1
        by_domain[domain]["noisy_updates" if noisy else "ADC_skips"] += 1
        if not noisy:
            continue
        by_domain[domain]["noisy_images"] += len(cases)
        by_domain[domain]["coupled_pairs"] += metadata["coupled_pairs"]
        sizes[domain][metadata["native_size"]] += 1
        if domain == "mixed":
            mixed_pairs[metadata["coupled_pairs"]] += 1
        for case in cases:
            source = case["source"]
            if domain == "mixed":
                mixed_levels.append(source["level"])
                mixed_widths.append(source["width"])
            if case.get("role") == "present":
                background = source.get("background_recipe", {}).get("kind")
                if background is None:
                    background = source.get("counterfactual", "not-described")
                backgrounds[domain][background] += 1
                if domain == "photo":
                    contrast = source["contrast"]
                    assert 0 < contrast <= 1
                    photo_contrasts.append(contrast)
    assert sum(v["noisy_updates"] for v in by_domain.values()) == 900
    assert sum(v["ADC_skips"] for v in by_domain.values()) == 100
    assert sum(v["noisy_images"] for v in by_domain.values()) == 3600
    assert len(photo_contrasts) == 2 * by_domain["photo"]["noisy_updates"]
    assert set(mixed_pairs) == {0}
    domains = {}
    for domain in sorted(by_domain):
        values = dict(by_domain[domain])
        values["domain_weight"] = plan["domain_weights"][domain]
        values["nominal_weighted_update_count"] = (
            values["noisy_updates"] * values["domain_weight"]
        )
        values["native_size_update_histogram"] = dict(sizes[domain])
        values["present_pair_background_descriptions"] = dict(backgrounds[domain])
        domains[domain] = values
    assert "torch" not in sys.modules
    assert all(ref(binding["path"]) == binding for binding in bindings)
    return {
        "status": "pass-full-saved-training-metadata-and-trace-coverage-audit",
        "created_local": datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(),
        "inputs": bindings[:-1],
        "source": dict(bindings[-1], text=Path(__file__).read_text()),
        "repository": str(repository),
        "matched_trace_rows": len(trace),
        "domains": domains,
        "photo_present_pair_contrasts": {
            **bounds(photo_contrasts),
            "full_contrast": sum(v == 1 for v in photo_contrasts),
            "reduced_contrast": sum(v < 1 for v in photo_contrasts),
            "reduced_contrast_range": bounds([v for v in photo_contrasts if v < 1]),
        },
        "mixed_nominal_scene_levels": bounds(mixed_levels),
        "mixed_nominal_bar_half_width_pixels": bounds(mixed_widths),
        "mixed_coupled_pair_count_histogram": dict(mixed_pairs),
        "new_image_array_reads": 0,
        "new_noise_source_draws": 0,
        "new_model_forwards": 0,
        "Torch_imported": False,
        "external_bytes_written": 0,
        "limits": "Metadata/trace coverage only. Nominal scene levels and widths precede geometry/camera transport; they do not bound realized camera-RGB gradients. Weighted update counts are sampling/loss-weight descriptions, not gradient magnitudes or causal quality evidence. Full-contrast photos already include edges; no claim that strong edges are absent from all training. No new quality measurement or loss ablation.",
        "next_test_rationale": "Noisy flats and reduced-contrast photos already exist. Mixed edge/quiet batches have zero coupled pairs, unlike detail/background domains. Test training-only paired scenes sharing a stronger edge/background with and without a faint mesh increment, preserving the broad scene in the counterfactual. Keep generic flat and no-increment controls, held-out evaluation and both protected real-photo families. Improvement requires actual trained raw/EMA comparisons, not this coverage audit.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--trial", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evidence = audit(args.repository.resolve(), args.trial.resolve())
    with args.output.open("x") as stream:
        json.dump(evidence, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print("PASS:1000metadata/trace rows;900updates/3600images;no image/model reads")
