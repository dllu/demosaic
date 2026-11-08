"""Publish the completed matched trial only after audits and actual native viewing.

No model inference is performed. Checkpoint construction/loading is CPU-only
and starts after terminal-owner, audit, source and viewing checks.
"""

import argparse
import json
import shutil
import time
from pathlib import Path

from phase_admission_protocol import owner_live, read, ref
from train_coherent_pair_evidence_trial import ARMS, METHODS, REPO, ROOT, factory, guard, save

STEM = "v183-coherent-pair-evidence-v1"
INDEX = REPO / "docs/results/v183-coherent-pair-evidence-final-v1.json"
REPORT = REPO / "docs/coherent-pair-evidence-comparison.md"
IMAGES = REPO / "docs/images" / STEM
EVIDENCE = REPO / "docs/results" / STEM
VERIFICATION = REPO / "docs/results/v183-coherent-pair-evidence-publication-verification-v1.json"


def terminal_result(root, phase, filename, expected_status):
    launch = read(root / f"{phase}-launch-v1.json")
    if owner_live(launch["owner"]):
        raise RuntimeError(f"Actual {phase} owner is still live")
    if (root / f"{phase}-failure-v1.json").exists():
        raise RuntimeError(f"Preserved {phase} failure requires inspection")
    result = read(root / filename)
    if result["owner"] != launch["owner"] or result["status"] != expected_status:
        raise ValueError(f"Wrong terminal {phase} owner/status")
    return result


def completed_context(root, *, viewed=False):
    plan = read(root / "plan-v1.json")
    guard(plan)
    seal = read(root / "publication-source-v1.json")
    if ref(__file__) != seal["publisher"]:
        raise ValueError("Use the sealed publication entry")
    for binding in seal["helpers"]:
        if ref(binding["path"]) != {k: binding[k] for k in ["path", "sha256"]}:
            raise ValueError("Publication helper bytes changed")
    training = {
        arm: terminal_result(
            root,
            f"{arm}-train",
            f"{arm}-train-result-v1.json",
            "completed-matched-warmstart-one-pass",
        )
        for arm in ARMS
    }
    scores = terminal_result(
        root,
        "review",
        "scores-v1.json",
        "completed-two-endpoint-coherent-pair-fixed-quality-awaiting-native-viewing",
    )
    controller = terminal_result(
        root,
        "completion",
        "completion-result-v1.json",
        "completed-coherent-pair-training-quality-audits-tables-render-awaiting-actual-viewing",
    )
    binding = ref(root / "plan-v1.json")
    for result in [*training.values(), scores]:
        if result["plan"] != binding:
            raise ValueError("Actual results must bind the same plan")
    for name in ["training-audit-v1.json", "quality-audit-v1.json"]:
        audit = read(root / name)
        if not audit["status"].startswith("pass-") or audit["plan"] != binding:
            raise ValueError("Both actual audits must pass")
    if read(root / "quality-audit-v1.json")["scores"] != ref(root / "scores-v1.json"):
        raise ValueError("Quality audit binds different scores")
    figures = read(root / "figures-v1.json")
    if (
        figures.get("fixture_only_no_actual_V183_quality", True)
        or figures["plan"] != binding
        or figures["scores"] != ref(root / "scores-v1.json")
        or controller["figures"] != ref(root / "figures-v1.json")
        or figures["native_figures"] != 60
        or figures["native_triplets"] != 12
        or len(figures["images"]) != 60
        or sum(item["triplet"] for item in figures["images"]) != 12
        or not all(item["no_resize"] for item in figures["images"])
        or len(figures["sheets"]) != 15
        or sorted(i for s in figures["sheets"] for i in s["indices"]) != list(range(60))
    ):
        raise ValueError("Expected actual 60-figure render bound to terminal results")
    paired = read(root / "paired-comparisons-v1.json")
    if paired["plan"] != binding or paired["scores"] != ref(root / "scores-v1.json"):
        raise ValueError("Matched comparisons bind different actual results")
    if (
        len(paired["table_cells"]) != 1218
        or not paired["status"].startswith("completed-")
        or paired["methods"] != 19
        or paired["metric_rows"] != 15618
        or paired["matched_endpoint_contrasts"] != 2
        or paired["contrasts"] != 32
        or paired["real_references_scored"]
    ):
        raise ValueError("Expected all matched/context tables")
    if viewed:
        viewing = read(root / "native-viewing-completion-v1.json")
        if viewing["figures"] != ref(root / "figures-v1.json") or viewing["indices"] != list(
            range(60)
        ):
            raise ValueError("All actual native figures must have recorded viewing")
        if ref(viewing["journal"]["path"]) != viewing["journal"]:
            raise ValueError("Viewing journal changed")
    return plan, training, scores, figures, paired


def record_viewing(root, selected, notes):
    _, _, _, figures, _ = completed_context(root)
    if (
        not selected
        or not notes.strip()
        or len(selected) != len(set(selected))
        or not set(selected) <= set(range(15))
    ):
        raise ValueError("Expected distinct actual sheet indices0..14 and viewing notes")
    journal = root / "native-viewing-v1.jsonl"
    events = (
        [json.loads(line) for line in journal.read_text().splitlines()] if journal.exists() else []
    )
    seen = {i for event in events for i in event["sheets"]}
    if seen & set(selected):
        raise ValueError("A sheet viewing is already recorded")
    for index in selected:
        binding = figures["sheets"][index]["image"]
        if ref(binding["path"]) != binding:
            raise ValueError("Viewed sheet bytes differ from render")
    event = {
        "recorded_unix_UTC": time.time(),
        "sheets": selected,
        "detail": "original",
        "notes": notes,
    }
    with journal.open("a") as stream:
        stream.write(json.dumps(event) + "\n")
    events.append(event)
    seen.update(selected)
    if seen == set(range(15)):
        save(
            root / "native-viewing-completion-v1.json",
            {
                "status": "actually-viewed60-native-figures-in15-original-detail-sheets",
                "figures": ref(root / "figures-v1.json"),
                "journal": ref(journal),
                "events": events,
                "indices": list(range(60)),
                "native_figures": 60,
                "native_triplets": 12,
                "no_resize": True,
            },
        )
    print(f"Recorded sheets{selected};viewed{len(seen)}/15")


def export_checkpoints(plan, training, scores):
    import torch
    from phase_evidence_training_state import load_matching_ema
    from profile_raw_kernel_inference import model_hash

    assert not torch.cuda.is_initialized()
    directory = Path(plan["artifacts"]) / "exports"
    directory.mkdir(exist_ok=False)
    base = torch.load(
        plan["frozen_component"]["export"]["path"], map_location="cpu", weights_only=True
    )
    exports = {}
    for arm in ARMS:
        checkpoint = training[arm]["final_checkpoint"]
        assert ref(checkpoint["path"]) == checkpoint
        state = torch.load(checkpoint["path"], map_location="cpu", weights_only=True)
        for endpoint in ["raw", "EMA"]:
            module = factory(arm, plan["module_config"]).eval()
            module.load_state_dict(state["models"], strict=True)
            if endpoint == "EMA":
                load_matching_ema(module, state["ema"])
            method = METHODS[arm][endpoint]
            expected = scores["module_hashes"][method]["before"]
            assert model_hash(module) == expected
            assert model_hash(module.frozen) == plan["frozen_component"]["module_hash"]
            config = dict(plan["module_config"])
            if arm == "control":
                config.pop("evidence_peaks")
            source = REPO / "src/demosaic/late_local_phase_evidence_matching.py"
            path = directory / f"local-phase-{arm}-{endpoint}-step1000.pt"
            with path.open("xb") as stream:
                torch.save(
                    {
                        "component": type(module).__name__,
                        "module_config": config,
                        "state_dict": module.state_dict(),
                        "parent": base["parent"],
                        "frozen_component": plan["frozen_component"],
                        "sampling_library": plan["sampling_library"],
                        "source": ref(source),
                        "source_checkpoint": checkpoint,
                        "arm": arm,
                        "endpoint": endpoint,
                        "initial_checkpoint": plan["initial_checkpoint"],
                        "old_network_updates": 1800,
                        "new_optimizer_updates": 900,
                        "adapter_updates": 900 if arm == "evidence" else 0,
                        "training_plan": ref(Path(plan["root"]) / "plan-v1.json"),
                    },
                    stream,
                )
            restored = torch.load(path, map_location="cpu", weights_only=True)
            fresh = factory(arm, plan["module_config"]).eval()
            fresh.load_state_dict(restored["state_dict"], strict=True)
            assert model_hash(fresh) == expected
            exports[method] = {
                "export": ref(path),
                "source_checkpoint": checkpoint,
                "state": endpoint,
                "arm": arm,
                "module_hash": expected,
                "component": restored["component"],
                "module_config": config,
                "source": restored["source"],
                "full_state_tensors": len(fresh.state_dict()),
            }
            del module, fresh, restored
        del state
    assert not torch.cuda.is_initialized()
    return exports


def evidence_names():
    names = [
        "plan-v1.json",
        "completion-result-v1.json",
        "training-audit-v1.json",
        "quality-audit-v1.json",
        "scores-v1.json",
        "quality-events-v1.jsonl",
        "quality-observations-v1.jsonl",
        "review-launch-v1.json",
        "review-status-v1.json",
        "paired-comparisons-v1.json",
        "comparison-tables-v1.md",
        "figures-v1.json",
        "native-viewing-v1.jsonl",
        "native-viewing-completion-v1.json",
        "audit-source-v1.json",
        "render-source-v1.json",
        "reduction-source-v1.json",
        "publication-source-v1.json",
        "completion-source-v1.json",
        "completion-launch-v1.json",
        "completion-owner-v1.json",
        "completion-v1.log",
        "evidence-train-v1.log",
        "review-v1.log",
    ]
    for stage in ["training-audit", "launch-review", "quality-audit", "reduce", "render"]:
        names += [f"completion-{stage}-v1.log", f"completion-{stage}-launch-v1.json"]
    for arm in ARMS:
        names.extend(
            f"{arm}-{suffix}"
            for suffix in [
                "train-result-v1.json",
                "train-launch-v1.json",
                "train-status-v1.json",
                "train-trace-v1.jsonl",
                "restoration-v1.json",
                "warmstart-v1.json",
            ]
        )
    return names


def publish(root, notes):
    plan, training, scores, figures, paired = completed_context(root, viewed=True)
    if not notes.is_file() or len(notes.read_text()) < 300:
        raise ValueError("Actual human quality notes are required")
    for path in [INDEX, REPORT, IMAGES, EVIDENCE, Path(plan["artifacts"]) / "exports"]:
        if path.exists():
            raise FileExistsError(path)
    names = evidence_names()
    if not all((root / name).is_file() for name in names):
        raise FileNotFoundError("Required actual evidence is missing")
    for item in figures["images"]:
        if ref(item["image"]["path"]) != item["image"]:
            raise ValueError("Native image bytes changed")
    needed = sum((root / name).stat().st_size for name in names)
    needed += sum(Path(item["image"]["path"]).stat().st_size for item in figures["images"])
    # Includes strict exports, index/report/source metadata and a publication margin.
    needed += 128 * 2**20
    if shutil.disk_usage(REPO).free < (48 + 0.5) * 2**30 + needed:
        raise RuntimeError("Insufficient reserved local publication space")
    exports = export_checkpoints(plan, training, scores)
    matched_index = REPO / "docs/results/v181-flat-spatial-evidence-final-v1.json"
    matched = read(matched_index)
    viewer_methods = dict(matched["viewer_method_checkpoints"], **exports)
    for entry in viewer_methods.values():
        assert ref(entry["export"]["path"]) == entry["export"]
    prior = read(matched["figures"]["path"])
    old_images = {item["original_image"]["path"]: item for item in prior["images"]}
    IMAGES.mkdir()
    EVIDENCE.mkdir()
    images = []
    for item in figures["images"]:
        source = Path(item["image"]["path"])
        destination = IMAGES / source.name
        shutil.copyfile(source, destination)
        assert destination.read_bytes() == source.read_bytes()
        record = dict(item, original_image=item["image"], image=ref(destination))
        if not item["triplet"]:
            record["predictions"] = dict(
                old_images[item["source_figure"]["path"]]["predictions"], **item["predictions"]
            )
        images.append(record)
    manifest = IMAGES / "manifest-v1.json"
    save(
        manifest,
        {
            "images": images,
            "method_checkpoints": viewer_methods,
            "source": ref(root / "figures-v1.json"),
            "native_figures": 60,
            "native_triplets": 12,
            "no_resize": True,
            "fixture": False,
            "frozen_component": plan["frozen_component"],
            "scope": plan["scope"],
        },
    )
    copies = {}
    for name in names:
        source = root / name
        destination = EVIDENCE / name
        shutil.copyfile(source, destination)
        assert source.read_bytes() == destination.read_bytes()
        copies[name] = {"original": ref(source), "public": ref(destination)}
    note_copy = EVIDENCE / "human-quality-notes-v1.md"
    shutil.copyfile(notes, note_copy)
    text = "# Coherent pair-response trial: completed quality\n\n" + notes.read_text().strip()
    text += "\n\n[Exact evidence](results/v183-coherent-pair-evidence-final-v1.json) · "
    text += "[Native-pixel viewer](images/v183-coherent-pair-evidence-v1/native-viewer.html).\n\n"
    text += (root / "comparison-tables-v1.md").read_text().rstrip() + "\n\n"
    text += "RMS is camera-RGB DN16; template gain1 means exact constructed amplitude. "
    text += "The added coherent-response term is the intended change versus V181; completed V178/V180/V181 outputs are reused. V175 has a larger "
    text += "fresh-noise budget. Reused inputs do not establish blind generalization, seed "
    text += (
        "uncertainty or noisy-sky safety. ISO100/AHD/JPEG references are qualitative, not GT.\n\n"
    )
    text += "## Native comparisons\n\nAll cells retain160×160 source pixels without resizing. "
    text += "The manifest records source/ROI, checkpoint/state, physical noise, exposure, "
    text += "contrast, anchor and qualified references for every view. Both protected GFX "
    text += "families/JPEGs/siblings remain excluded from training.\n\n"
    for triplet, title in [
        (False, "Comparison boards"),
        (True, "Noisy, restored and exact constructed GT"),
    ]:
        text += f"### {title}\n\n"
        for item in images:
            if item["triplet"] != triplet:
                continue
            text += f"{item['case']['id']}; ROI `{item['ROI_xywh']}`, "
            text += f"exposure{item['exposure']:g}, contrast{item['contrast']:g}.\n\n"
            text += f"![Native comparison](images/{STEM}/{Path(item['image']['path']).name})\n\n"
    text += "[Publication verification](results/v183-coherent-pair-evidence-publication-verification-v1.json).\n"
    with REPORT.open("x") as stream:
        stream.write(text)
    save(
        INDEX,
        {
            "status": "completed-matched-trial-audited-actually-viewed-and-two-strict-exports",
            "plan": ref(root / "plan-v1.json"),
            "copies": copies,
            "notes": ref(note_copy),
            "report": ref(REPORT),
            "figures": ref(manifest),
            "checkpoints": exports,
            "viewer_method_checkpoints": viewer_methods,
            "matched_publication": ref(matched_index),
            "admission_inspection": plan["admission_inspection"],
            "table_cells": 1218,
            "native_figures": 60,
            "native_triplets": 12,
            "execution": {
                "new_training_rows": sum(len(value["trace"]) for value in training.values()),
                "new_optimizer_updates": sum(value["updates"] for value in training.values()),
                "new_training_images": sum(value["training_images"] for value in training.values()),
                "training_counts": {arm: value["counts"] for arm, value in training.items()},
                "quality_counts": scores["counts"],
                "quality_ADC_exact": scores["ADC_outputs_exact_V169"],
                "quality_frozen_replays": scores["exact_V169_replays"],
                "new_parent_DINO_calls": 0,
                "new_sensor_source_draws": 0,
                "admission_is_a_separate_completed_probe": True,
            },
            "publication_source": ref(root / "publication-source-v1.json"),
            "actual_new_neural_forwards": 0,
            "new_sensor_noise_draws": 0,
            "scope": paired["scope"],
        },
    )
    print("Published60nativefigures/1218tablecells/2strictCPUexports;zero model forwards")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="phase", required=True)
    viewing = sub.add_parser("record-viewing")
    viewing.add_argument("--sheets", required=True)
    viewing.add_argument("--notes", required=True)
    publishing = sub.add_parser("publish")
    publishing.add_argument("--notes", type=Path, required=True)
    args = parser.parse_args()
    if args.phase == "record-viewing":
        record_viewing(ROOT, [int(n) for n in args.sheets.split(",")], args.notes)
    else:
        publish(ROOT, args.notes)


if __name__ == "__main__":
    main()
