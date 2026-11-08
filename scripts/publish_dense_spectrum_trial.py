"""Publish completed readout quality only after audits and actual native viewing."""

import argparse
import json
import os
import shutil
import time
from pathlib import Path

from audit_coherent_pair_evidence_trial import terminal
from spatial_trial_protocol import read, ref
from train_dense_spectrum_trial import METHODS, REPO, ROOT, factory, guard, save

STEM = "v191-dense-spectrum-v1"
INDEX = REPO / "docs/results/v191-dense-spectrum-final-v1.json"
REPORT = REPO / "docs/dense-local-spectrum-comparison.md"
IMAGES = REPO / "docs/images" / STEM
EVIDENCE = REPO / "docs/results" / STEM
VERIFICATION = REPO / "docs/results/v191-dense-spectrum-publication-verification-v1.json"


def completed_context(root, *, viewed=False):
    plan = read(root / "plan-v1.json")
    guard(plan)
    seal = read(root / "publication-source-v1.json")
    assert ref(__file__) == seal["publisher"], "Use the sealed publisher"
    for binding in seal["helpers"]:
        assert ref(binding["path"]) == {k: binding[k] for k in ["path", "sha256"]}
    training = terminal(root / "wave-train-result-v1.json")
    scores = terminal(root / "scores-v1.json")
    assert training["status"] == "completed-isolated-readout-one-pass-frozen-V183-EMA"
    assert (
        scores["status"]
        == "completed-two-endpoint-wave-readout-fixed-quality-awaiting-native-viewing"
    )
    binding = ref(root / "plan-v1.json")
    assert training["plan"] == scores["plan"] == binding
    for name in ["training-audit-v1.json", "quality-audit-v1.json"]:
        audit = read(root / name)
        assert audit["status"].startswith("pass-") and audit["plan"] == binding
    assert read(root / "quality-audit-v1.json")["scores"] == ref(root / "scores-v1.json")
    figures = read(root / "figures-v1.json")
    paired = read(root / "paired-comparisons-v1.json.gz")
    assert figures["fixture_only_no_actual_V191_quality"] is False
    assert figures["plan"] == paired["plan"] == binding and figures["scores"] == paired[
        "scores"
    ] == ref(root / "scores-v1.json")
    assert (
        figures["native_figures"] == 60
        and figures["native_triplets"] == 12
        and len(figures["images"]) == 60
    )
    assert sum(item["triplet"] for item in figures["images"]) == 12
    assert all(item["no_resize"] for item in figures["images"]) and len(figures["sheets"]) == 15
    assert sorted(i for sheet in figures["sheets"] for i in sheet["indices"]) == list(range(60))
    assert paired["methods"] == 29 and paired["metric_rows"] == 23838 and paired["contrasts"] == 54
    assert paired["primary_endpoint_contrasts"] == 2 and len(paired["table_cells"]) == 2058
    assert paired["real_references_scored"] is False
    if viewed:
        viewing = read(root / "native-viewing-completion-v1.json")
        assert viewing["figures"] == ref(root / "figures-v1.json") and viewing["indices"] == list(
            range(60)
        )
        assert ref(viewing["journal"]["path"]) == viewing["journal"]
    return plan, training, scores, figures, paired


def record_viewing(root, selected, notes):
    _, _, _, figures, _ = completed_context(root)
    if (
        not selected
        or len(selected) != len(set(selected))
        or not set(selected) <= set(range(15))
        or not notes.strip()
    ):
        raise ValueError("Expected distinct actual sheets0..14 and actual viewing notes")
    journal = root / "native-viewing-v1.jsonl"
    events = (
        [json.loads(line) for line in journal.read_text().splitlines()] if journal.exists() else []
    )
    seen = {i for event in events for i in event["sheets"]}
    if seen & set(selected):
        raise ValueError("Sheet viewing already recorded")
    for index in selected:
        binding = figures["sheets"][index]["image"]
        assert ref(binding["path"]) == binding
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
    from phase_wave_training_state import inherited_hash, load_ema
    from profile_raw_kernel_inference import model_hash
    from spatial_wave_training_state import expand_checkpoint

    assert not torch.cuda.is_initialized()
    directory = Path(plan["artifacts"]) / "exports"
    directory.mkdir(exist_ok=False)
    checkpoint = training["final_checkpoint"]
    assert ref(checkpoint["path"]) == checkpoint
    state = expand_checkpoint(torch.load(checkpoint["path"], map_location="cpu", weights_only=True))
    base = torch.load(
        plan["frozen_component"]["export"]["path"], map_location="cpu", weights_only=True
    )
    exports = {}
    for endpoint, method in METHODS.items():
        module = factory(plan["module_config"]).eval()
        module.load_state_dict(state["models"], strict=True)
        if endpoint == "EMA":
            load_ema(module, state["ema"])
        assert inherited_hash(module) == plan["initializer"]["module_hash"]
        expected = scores["module_hashes"][method]["before"]
        assert model_hash(module) == expected
        source = REPO / "src/demosaic/late_dense_local_spectrum.py"
        path = directory / f"dense-local-spectrum-{endpoint}-step1000.pt"
        payload = {
            "component": type(module).__name__,
            "module_config": plan["module_config"],
            "state_dict": module.state_dict(),
            "parent": base["parent"],
            "frozen_component": plan["frozen_component"],
            "sampling_library": plan["sampling_library"],
            "source": ref(source),
            "source_checkpoint": checkpoint,
            "endpoint": endpoint,
            "frozen_V183_initializer": plan["initializer"],
            "inherited_network_updates": 1800,
            "inherited_adapter_updates": 900,
            "new_readout_updates": 900,
            "training_plan": ref(ROOT / "plan-v1.json"),
        }
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
            "source": payload["source"],
            "frozen_V183_initializer": plan["initializer"],
            "full_state_tensors": 193,
        }
    assert not torch.cuda.is_initialized()
    return exports


def evidence_names():
    return [
        "plan-v1.json",
        "wave-train-result-v1.json",
        "wave-train-launch-v1.json",
        "wave-train-status-v1.json",
        "wave-train-trace-v1.jsonl",
        "wave-restoration-v1.json",
        "wave-train-v1.log",
        "training-audit-v1.json",
        "training-audit-v1.log",
        "training-audit-source-v1.json",
        "scores-v1.json",
        "quality-events-v1.jsonl",
        "quality-observations-v1.jsonl.gz",
        "review-launch-v1.json",
        "review-status-v1.json",
        "review-source-v1.json",
        "review-v1.log",
        "quality-audit-v1.json",
        "quality-audit-v1.log",
        "quality-audit-source-v1.json",
        "paired-comparisons-v1.json.gz",
        "comparison-tables-v1.md",
        "reduction-v1.log",
        "reduction-source-v1.json",
        "full-comparison-fixture-verification-v1.json",
        "render-source-v1.json",
        "render-v1.log",
        "figures-v1.json",
        "native-viewing-v1.jsonl",
        "native-viewing-completion-v1.json",
        "publication-source-v1.json",
    ]


def linked_copy(source, destination):
    """Publish a second path for a terminal immutable artifact, preserving bytes."""
    source, destination = Path(source), Path(destination)
    assert source.is_file() and not source.is_symlink() and not destination.exists()
    os.link(source, destination)
    assert (
        source.stat().st_ino == destination.stat().st_ino
        and ref(source)["sha256"] == ref(destination)["sha256"]
    )


def publish(root, notes):
    plan, training, scores, figures, paired = completed_context(root, viewed=True)
    if not notes.is_file() or len(notes.read_text()) < 300:
        raise ValueError("Actual human quality notes required")
    for path in [INDEX, REPORT, IMAGES, EVIDENCE, Path(plan["artifacts"]) / "exports"]:
        if path.exists():
            raise FileExistsError(path)
    assert all((root / name).is_file() for name in evidence_names())
    assert shutil.disk_usage(REPO).free > (40 + 0.04) * 2**30
    exports = export_checkpoints(plan, training, scores)
    previous_index = REPO / "docs/results/v189-spaced-pooled-final-v1.json"
    previous = read(previous_index)
    viewer_methods = dict(previous["viewer_method_checkpoints"], **exports)
    prior = read(previous["figures"]["path"])
    old_images = {item["original_image"]["path"]: item for item in prior["images"]}
    IMAGES.mkdir()
    EVIDENCE.mkdir()
    images = []
    for item in figures["images"]:
        source = Path(item["image"]["path"])
        destination = IMAGES / source.name
        assert ref(source) == item["image"]
        linked_copy(source, destination)
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
            "frozen_V183_initializer": plan["initializer"],
            "scope": plan["scope"],
        },
    )
    copies = {}
    for name in evidence_names():
        source = root / name
        destination = EVIDENCE / name
        linked_copy(source, destination)
        copies[name] = {"original": ref(source), "public": ref(destination)}
    note_copy = EVIDENCE / "human-quality-notes-v1.md"
    linked_copy(notes, note_copy)
    text = "# Dense local spectral readout: completed quality\n\n" + notes.read_text().strip()
    text += "\n\n[Exact evidence](results/v191-dense-spectrum-final-v1.json) · [Native-pixel viewer](images/v191-dense-spectrum-v1/native-viewer.html).\n\n"
    text += (root / "comparison-tables-v1.md").read_text().rstrip() + "\n\n"
    text += "RMS is camera-RGB DN16; template gain1 means exact constructed amplitude. Primary V191raw/V187raw andV191EMA/V187EMA comparisons each train900newheadupdates above fresh frozenV183EMA at508parameters. Dense/local representation,raw-coefficient units andHannOLA synthesis change together. Reused development inputs are not blind validation or calibrated noisy-sky safety. ISO100/AHD/JPEG references are qualitative,not exactGT.\n\n"
    text += "## Native comparisons\n\nAll cells retain160×160 source pixels without resizing. The manifest binds source/ROI, checkpoint/state, noise and display exposure/contrast/anchor. Both protected GFX families/JPEGs/siblings remain excluded from training.\n\n"
    for triplet, title in [
        (False, "Comparison boards"),
        (True, "Noisy, restored and exact constructed GT"),
    ]:
        text += f"### {title}\n\n"
        for item in images:
            if item["triplet"] != triplet:
                continue
            text += f"{item['case']['id']}; ROI `{item['ROI_xywh']}`, exposure{item['exposure']:g}, contrast{item['contrast']:g}.\n\n"
            text += f"![Native comparison](images/{STEM}/{Path(item['image']['path']).name})\n\n"
    text += "[Publication verification](results/v191-dense-spectrum-publication-verification-v1.json).\n"
    with REPORT.open("x") as stream:
        stream.write(text)
    save(
        INDEX,
        {
            "status": "completed-isolated-readout-audited-actually-viewed-and-two-strict-exports",
            "plan": ref(root / "plan-v1.json"),
            "copies": copies,
            "notes": ref(note_copy),
            "report": ref(REPORT),
            "figures": ref(manifest),
            "checkpoints": exports,
            "viewer_method_checkpoints": viewer_methods,
            "baseline_publication": ref(previous_index),
            "table_cells": 2058,
            "native_figures": 60,
            "native_triplets": 12,
            "publication_source": ref(root / "publication-source-v1.json"),
            "publication_storage": "Public receipt/PNG paths hardlink their closed private artifacts after all owners are terminal. Every path/byte remains; hashes bind both. No redundant receipt/image copies.",
            "execution": {
                "new_training_rows": 1000,
                "new_optimizer_updates": 900,
                "new_training_images": 3600,
                "train_counts": training["counts"],
                "quality_counts": scores["counts"],
                "quality_readout_calls": 1500,
                "V183_EMA_replays": 1644,
                "V169_replays": 1644,
                "ADC_exact": 144,
            },
            "actual_new_neural_forwards": 0,
            "new_sensor_noise_draws": 0,
            "scope": paired["scope"],
        },
    )
    print("Published60nativefigures/2058cells/2strictCPUexports/20viewerMethods;zero new inference")


if __name__ == "__main__":
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
