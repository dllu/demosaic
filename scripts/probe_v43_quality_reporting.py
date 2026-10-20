"""CPU-only real-checkpoint integration proof for matched V43 score/crop reporting."""

import argparse
import json
import os
import shutil
from pathlib import Path

from train_directional_bank_trial import guard, read, ref, save

REPO = Path(__file__).resolve().parents[1]


def prepare(training_root, root):
    import yaml

    terminal = read(training_root / "status.json")
    assert terminal["status"] == "completed-discarded-CPU-launcher-proof"
    proof = read(training_root / "plan.json")
    guard(proof)
    checkpoints = [proof["parent"]]
    inputs = [ref(training_root / "status.json"), ref(training_root / "plan.json")]
    for arm in ("V93", "V94", "V95"):
        result_ref = terminal["completed"]["CPU-" + arm]
        assert ref(result_ref["path"]) == result_ref
        result = read(result_ref["path"])
        assert result["engineering_only"] and not result["CUDA_initialized"]
        checkpoints.append(result["checkpoint"])
        inputs.append(result_ref)
    root = root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    # Use the actual tested training modules and pinned report operators.
    trained = Path(proof["work"])
    sources = [*trained.glob("src/demosaic/*.py")]
    sources += [trained / n for n in ("pyproject.toml", "uv.lock")]
    sources += [
        REPO / "scripts" / name
        for name in (
            "probe_v43_quality_reporting.py",
            "profile_raw_kernel_inference.py",
            "train_directional_bank_trial.py",
            "audit_fresh_dino_statistics.py",
        )
    ]
    for source in sources:
        relative = (
            source.relative_to(trained)
            if source.is_relative_to(trained)
            else source.relative_to(REPO)
        )
        target = work / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    protocol_path = trained / "configs/evaluation.yaml"
    original = yaml.safe_load(protocol_path.read_text())
    protocol = dict(original)
    protocol["conditions"] = [
        c for c in original["conditions"] if c["name"] in ("adc-only", "iso12800-prior")
    ]
    protocol["patterns"] = ["RGGB", "BGGR"]
    config = work / "engineering-evaluation.yaml"
    config.write_text(yaml.safe_dump(protocol, sort_keys=False))
    manifest = Path("/mnt/external/demosaic/evaluation/manifests/common-8192-44732-val-v1.jsonl")
    rows = [
        r
        for r in (json.loads(line) for line in manifest.read_text().splitlines())
        if r["split"] == "val"
    ]
    assert len(rows) == 427
    selected = rows[:2]
    inputs += checkpoints + [ref(manifest), ref(protocol_path)]
    for row in selected:
        path = Path(row["cache"])
        if not path.is_absolute():
            path = manifest.parent / path
        item = ref(path)
        if "cache_sha256" in row:
            assert item["sha256"] == row["cache_sha256"]
        inputs.append(item)
    plan = {
        "root": str(root),
        "work": str(work),
        "checkpoints": checkpoints,
        "manifest": ref(manifest),
        "selected_photo_ids": [r["id"] for r in selected],
        "engineering_config": ref(config),
        "original_protocol": ref(protocol_path),
        "training_proof": ref(training_root / "independent-state-audit.json"),
        "inputs": inputs,
        "size": 176,
        "photo_count": 2,
        "synthetic_count": 1,
        "batch_size": 1,
        "expected_neural_forwards": 48,
        "expected_metric_rows": 84,
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "scope": "Discarded CPU reporting integration only: original V43 and three actual24-update engineering EMAs, 2 held-out photos plus1 procedural source,2 conditions/2CFAs,native176/B1,FP32. This is not the full427 panel, production training, model-quality comparison, CUDA qualification or timing result. Full production evaluation keeps the original7 conditions/4CFAs/native256.",
    }
    inputs.append(plan["training_proof"])
    save(root / "plan.json", plan)
    guard(plan)
    print(ref(root / "plan.json"))


def worker(plan_path):
    import random

    import numpy as np
    import psutil
    import torch
    from audit_fresh_dino_statistics import compare_summary
    from PIL import Image
    from profile_raw_kernel_inference import model_hash

    from demosaic import suite

    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not torch.cuda.is_initialized()
    plan = read(plan_path)
    guard(plan)
    root = Path(plan["root"])
    (root / "worker.claim").open("x").close()
    save(root / "owner.json", {"pid": os.getpid(), "created": psutil.Process().create_time()})
    assert psutil.virtual_memory().available > 32 * 2**30
    assert shutil.disk_usage(root).free > 64 * 2**30
    torch.set_num_threads(2)
    loader = suite.load_checkpoint
    models, calls, dino_calls, identities = [], [], [], []
    rng = {}

    def observed_loader(*args, **kwargs):
        model, state = loader(*args, **kwargs)
        index = len(models)
        models.append(
            (model, model_hash(model), model_hash(model.context.backbone), model.config.to_dict())
        )
        identities.append([id(p) for p in model.parameters()])
        calls.append(0)
        dino_calls.append(0)

        def before(_module, args, kwargs):
            assert len(args) == 5 and not kwargs
            assert all(isinstance(x, torch.Tensor) and x.device.type == "cpu" for x in args)
            if not rng:
                rng.update(torch=torch.get_rng_state(), python=random.getstate())
            calls[index] += 1

        def after(_module, _args, output):
            assert output.shape == (1, 3, 176, 176) and output.dtype == torch.float32
            assert torch.isfinite(output).all()

        def dino(*_):
            dino_calls[index] += 1

        model.register_forward_pre_hook(before, with_kwargs=True)
        model.register_forward_hook(after)
        model.context.backbone.register_forward_hook(dino)
        return model, state

    suite.load_checkpoint = observed_loader
    output = Path(plan["work"]) / "reporting-output"
    suite.run_suite(
        [Path(c["path"]) for c in plan["checkpoints"]],
        Path(plan["manifest"]["path"]),
        output,
        Path(plan["engineering_config"]["path"]),
        device="cpu",
        precision="float32",
        patch_size=plan["size"],
        batch_size=1,
        limit=2,
        synthetic_count=1,
    )
    assert calls == dino_calls == [12] * 4 and sum(calls) == plan["expected_neural_forwards"]
    assert torch.equal(torch.get_rng_state(), rng["torch"]) and random.getstate() == rng["python"]
    for i, (model, before, dino, config) in enumerate(models):
        assert model_hash(model) == before and model_hash(model.context.backbone) == dino
        assert model.config.to_dict() == config and identities[i] == [
            id(p) for p in model.parameters()
        ]
    summary_path = output / "summary.json"
    summary = read(summary_path)
    summary.update(engineering_only=True, scope=plan["scope"])
    save(summary_path, summary)
    report = output / "report.md"
    report.write_text(
        "**CPU reporting integration only; no model-quality result.**\n\n"
        + plan["scope"]
        + "\n\n"
        + report.read_text()
    )
    records = [json.loads(line) for line in (output / "per-image.jsonl").read_text().splitlines()]
    assert len(records) == plan["expected_metric_rows"]
    ids = {("photo", x) for x in plan["selected_photo_ids"]} | {("synthetic", "synthetic-0")}
    expected = {
        (model, kind, identity, condition, pattern)
        for model in {r["model"] for r in records}
        for kind, identity in ids
        for condition in ("adc-only", "iso12800-prior")
        for pattern in ("RGGB", "BGGR")
    }
    actual = [(r["model"], r["kind"], r["id"], r["condition"], r["pattern"]) for r in records]
    assert len(set(actual)) == len(actual) and set(actual) == expected
    arithmetic = compare_summary(records, summary)
    crops = summary["native_crops"]
    assert len(crops) == 8
    common, images = {}, []
    for crop in crops:
        path = output / crop["image"]
        assert ref(path)["sha256"] == crop["png_sha256"]
        assert crop["pixel_scale"] == "1 image pixel = 1 PNG pixel; open original at 100%"
        assert crop["reference"] == "Exact synthetic clean target"
        assert crop["display_exposure"] == 1 and crop["condition"]["name"] == "iso12800-prior"
        assert crop["model"]["sha256"] in {c["sha256"] for c in plan["checkpoints"]}
        image = Image.open(path).convert("RGB")
        pixels = np.asarray(image)
        panels = []
        for panel in crop["panels"]:
            x, y, w, h = panel["png_xywh"]
            assert w == h == 160
            panels.append(pixels[y : y + h, x : x + w].copy())
        key = crop["source_id"]
        if key in common:
            assert np.array_equal(common[key][0], panels[0]) and np.array_equal(
                common[key][1], panels[2]
            )
        else:
            common[key] = panels[0], panels[2]
        images.append(image)
    assert set(common) == set(plan["selected_photo_ids"])
    board = Image.new("RGB", (images[0].width * 2, images[0].height * 4), "white")
    for i, image in enumerate(images):
        board.paste(image, ((i % 2) * image.width, (i // 2) * image.height))
    board_path = output / "all-eight-native-triplets.png"
    board.save(board_path)
    assert not torch.cuda.is_initialized()
    guard(plan)
    save(
        root / "receipt.json",
        {
            "status": "completed-CPU-reporting-integration-awaiting-actual-view",
            "plan": ref(plan_path),
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "actual_neural_forwards": sum(calls),
            "DINO_calls": sum(dino_calls),
            "metric_rows": len(records),
            "native_triplets": len(crops),
            "native_panels": 24,
            "native_size": 160,
            "common_noisy_and_GT_panel_bytes_exact": True,
            "state_config_parameter_identities_RNG_and_inputs_preserved": True,
            "summary_arithmetic": arithmetic,
            "summary": ref(summary_path),
            "per_image": ref(output / "per-image.jsonl"),
            "board": ref(board_path),
            "engineering_only": True,
            "CUDA_initialized": False,
            "scope": plan["scope"],
        },
    )
    print(ref(root / "receipt.json"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "worker"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        assert args.output
        prepare(args.path.resolve(), args.output)
    else:
        worker(args.path.resolve())
