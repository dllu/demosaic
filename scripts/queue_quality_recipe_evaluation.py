"""Evaluate fixed recipe continuations after their exact training owners finish."""

import argparse
import hashlib
import os
import re
import shutil
import time
from pathlib import Path

import psutil
from evaluate_v43_quality_trial import CAMERAS, COLOR, PANEL, RAWNIND
from frozen_backbone_identity import (
    CONVNEXT_TINY_SHA256,
    sha256_identity,
    validate_backbone_identity,
)
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import live

REPO = Path(__file__).resolve().parents[1]
ARMS = ("V100", "V101")
TERMINAL = "completed-training-awaiting-model-comparisons"
KEYS = {f"{phase}-{arm}" for phase in ("CPU", "CUDA", "train") for arm in ARMS}
DINO_SHA = CONVNEXT_TINY_SHA256
MODEL_LABEL = r"V[1-9]\d*(?:-[a-z][a-z0-9]*)*"
HELPERS = (
    "frozen_backbone_identity.py",
    "queue_quality_recipe_evaluation.py",
    "evaluate_v43_quality_trial.py",
    "recover_v43_quality_trial.py",
    "train_v43_quality_trial.py",
    "train_directional_bank_trial.py",
    "profile_raw_kernel_inference.py",
    "audit_fresh_dino_statistics.py",
    "evaluate_texture_candidates.py",
    "diagnose_texture_response.py",
    "report_raw_pair.py",
    "evaluate_color_grid_cuda.py",
    "prepare_color_grid.py",
    "audit_colored_flats.py",
)


def phase_keys(arms):
    arms = tuple(arms)
    assert arms and len(set(arms)) == len(arms)
    assert all(re.fullmatch(r"V[1-9]\d*", arm) for arm in arms)
    return {f"{phase}-{arm}" for phase in ("CPU", "CUDA", "train") for arm in arms}


def training_ready(state, plan_ref, owner, *, arms=ARMS, is_live=live):
    keys = phase_keys(arms)
    assert state["plan"] == plan_ref, "Training plan changed"
    assert state["controller"] == owner, "Training owner changed"
    assert not state["status"].startswith("failed"), state.get("error", state["status"])
    assert set(state["completed"]) <= keys, "Unexpected training phase"
    if state["status"] != TERMINAL:
        assert is_live(owner), "Training controller exited before completion"
        return False
    assert set(state["completed"]) == keys, "Incomplete training coverage"
    return not is_live(owner) and not is_live(state["child"])


def reviewed_catalogue_source_boundary(results, training, phase):
    """An archived ROI catalogue is data; permit its declared bytes, never code drift."""
    import yaml

    snapshots, inputs = {}, []
    for arm, result in results.items():
        snapshot = Path(result["checkpoint"]["path"]).parent / "source" / result["source_sha256"]
        assert snapshot.is_dir(), "Missing actual training source archive"
        files = {p.name: ref(p) for p in snapshot.iterdir() if p.is_file()}
        config = yaml.safe_load(Path(training["arms"][arm][phase]).read_text())
        assert (
            files["reviewed-photo-rois.json"]["sha256"]
            == ref(config["reviewed_roi_catalogue"])["sha256"]
        ), "Archived catalogue differs from the frozen recipe"
        assert files["manifest.jsonl"]["sha256"] == ref(config["manifest"])["sha256"]
        # train.py hashes the named payloads before separately copying manifest.jsonl.
        digest = hashlib.sha256()
        for name in sorted(files):
            if name == "manifest.jsonl":
                continue
            digest.update(name.encode())
            with Path(files[name]["path"]).open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
        assert digest.hexdigest() == result["source_sha256"]
        snapshots[arm] = files
        inputs.extend(files.values())
    first = next(iter(snapshots.values()))
    assert all(set(files) == set(first) for files in snapshots.values())
    changed = {name for name in first if len({f[name]["sha256"] for f in snapshots.values()}) != 1}
    assert changed == {"reviewed-photo-rois.json"}, (
        "Training source/data drift beyond the declared ROI catalogue",
        changed,
    )
    for name in first:
        if name.endswith(".py"):
            assert (
                first[name]["sha256"]
                == ref(Path(training["work"]) / "src/demosaic" / name)["sha256"]
            )
    return inputs


def validate_reference_checkpoints(references, training, *, parent_label):
    """Bind optional fixed baselines independently from a derived initializer."""
    assert re.fullmatch(MODEL_LABEL, parent_label) and parent_label not in training["arms"]
    if not isinstance(references, (list, tuple)):
        raise TypeError("Reference checkpoints must be a list of explicit records")
    labels = {parent_label, *training["arms"]}
    hashes = {training["parent"]["sha256"]}
    records = []
    fields = {"arm", "path", "sha256", "expected_lineage", "expected_backbone"}
    for record in references:
        if not isinstance(record, dict) or set(record) != fields:
            raise ValueError(
                "Reference checkpoint requires label, file, step and backbone identity"
            )
        label = record["arm"]
        if not isinstance(label, str) or not re.fullmatch(MODEL_LABEL, label) or label in labels:
            raise ValueError("Reference checkpoint label is invalid or duplicated")
        digest = sha256_identity(record["sha256"])
        if digest in hashes:
            raise ValueError("Reference checkpoint duplicates another checkpoint hash")
        lineage = record["expected_lineage"]
        if (
            not isinstance(lineage, dict)
            or set(lineage) != {"step"}
            or type(lineage["step"]) is not int
            or lineage["step"] < 0
        ):
            raise ValueError("Reference checkpoint requires an explicit nonnegative integer step")
        identity = validate_backbone_identity(record["expected_backbone"])
        if ref(record["path"]) != {"path": record["path"], "sha256": digest}:
            raise ValueError("Reference checkpoint file differs from its absolute path/SHA256")
        records.append({**record, "expected_lineage": dict(lineage), "expected_backbone": identity})
        labels.add(label)
        hashes.add(digest)
    return records


def checkpoints(state, training, *, cpu_smoke, parent_label="V84", reference_checkpoints=()):
    phase = "CPU" if cpu_smoke else "train"
    updates = training["smoke_updates"] if cpu_smoke else training["train_updates"]
    parent = training["parent"]
    parent_step = training.get("parent_step", 20000)
    arms = tuple(training["arms"])
    phase_keys(arms)
    references = validate_reference_checkpoints(
        reference_checkpoints, training, parent_label=parent_label
    )
    parent_record = {"arm": parent_label, **parent, "expected_lineage": {"step": parent_step}}
    if "parent_backbone" in training:
        parent_record["expected_backbone"] = validate_backbone_identity(training["parent_backbone"])
    records = [*references, parent_record]
    backbones = training.get("backbones", {})
    if backbones:
        assert set(backbones) == set(arms), "Incomplete declared backbone identities"
    inputs = [{key: r[key] for key in ("path", "sha256")} for r in references]
    reference_hashes = {r["sha256"] for r in references}
    sources, results = set(), {}
    for arm in arms:
        item = state["completed"][f"{phase}-{arm}"]
        assert ref(item["path"]) == item
        result = read(item["path"])
        identity = validate_backbone_identity(backbones[arm]) if backbones else None
        assert result["status"] == "completed-quality-training-phase"
        assert (result["phase"], result["arm"], result["updates"]) == (phase, arm, updates)
        assert result["initialization"] == {
            "initial_EMA_exact": True,
            "DINO_sha256": identity["sha256"] if identity else DINO_SHA,
        }
        assert not live(result["owner"])
        assert ref(result["checkpoint"]["path"]) == result["checkpoint"]
        assert result["checkpoint"]["sha256"] not in reference_hashes, (
            "Reference duplicates a trained endpoint"
        )
        sources.add(result["source_sha256"])
        results[arm] = result
        inputs.extend((item, result["checkpoint"]))
        records.append(
            {
                "arm": arm,
                **result["checkpoint"],
                "expected_lineage": {
                    "step": updates,
                    "initialized_from": {**parent, "step": parent_step},
                },
            }
        )
        if identity:
            records[-1]["expected_backbone"] = identity
    if len(sources) != 1:
        inputs.extend(reviewed_catalogue_source_boundary(results, training, phase))
    return records, inputs


def prepare(
    training_root,
    root,
    evaluation_root,
    artifact_root,
    *,
    cpu_smoke=False,
    parent_label="V84",
    references=None,
):
    import json

    import yaml

    training_root, root = training_root.resolve(), root.resolve()
    evaluation_root, artifact_root = evaluation_root.resolve(), artifact_root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    assert evaluation_root.is_relative_to(REPO / ".cache") and not evaluation_root.exists()
    assert artifact_root.is_relative_to(Path("/mnt/external/demosaic"))
    assert not artifact_root.exists() and os.path.ismount("/mnt/external")
    training_ref, launch_ref = ref(training_root / "plan.json"), ref(training_root / "launch.json")
    training, launch = read(training_ref["path"]), read(launch_ref["path"])
    arms = tuple(training["arms"])
    phase_keys(arms)
    assert re.fullmatch(MODEL_LABEL, parent_label) and parent_label not in arms
    assert training["train_updates"] >= training["smoke_updates"] == 8
    assert launch["plan"] == training_ref
    guard(training)
    reference_input = ref(references) if references is not None else None
    reference_records = validate_reference_checkpoints(
        read(references) if references is not None else (), training, parent_label=parent_label
    )
    if reference_input is not None:
        assert ref(references) == reference_input, "Reference manifest changed during preparation"
    state = read(training_root / "status.json")
    if cpu_smoke:
        checkpoints(
            state,
            training,
            cpu_smoke=True,
            parent_label=parent_label,
            reference_checkpoints=reference_records,
        )
    else:
        training_ready(state, training_ref, launch["controller"], arms=arms)
    root.mkdir(parents=True, exist_ok=False)
    work, trained = root / "work", Path(training["work"])
    files = [*trained.glob("src/demosaic/*.py")]
    files += [trained / p for p in ("pyproject.toml", "uv.lock", "configs/evaluation.yaml")]
    files += [REPO / "scripts" / name for name in HELPERS]
    files += [REPO / p for p in ("LICENSE", "third_party/dinov3/LICENSE.md")]
    for source in files:
        relative = source.relative_to(trained if source.is_relative_to(trained) else REPO)
        destination = work / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    protocol = yaml.safe_load((work / "configs/evaluation.yaml").read_text())
    assert len(protocol["conditions"]) == 7 and len(protocol["patterns"]) == 4
    if cpu_smoke:
        protocol["conditions"] = [
            c for c in protocol["conditions"] if c["name"] in ("adc-only", "iso12800-prior")
        ]
        protocol["patterns"] = ["RGGB", "BGGR"]
        (work / "configs/smoke-evaluation.yaml").write_text(yaml.safe_dump(protocol))
    inputs = [training_ref, launch_ref, training["parent"], ref(PANEL)]
    if references is not None:
        inputs.append(reference_input)
        inputs.extend({key: r[key] for key in ("path", "sha256")} for r in reference_records)
    rows = [json.loads(line) for line in PANEL.read_text().splitlines()]
    rows = [row for row in rows if row["split"] == "val"]
    assert len(rows) == len({row["id"] for row in rows}) == 427
    for row in rows[:2] if cpu_smoke else rows:
        path = Path(row["cache"])
        item = ref(path if path.is_absolute() else PANEL.parent / path)
        assert item["sha256"] == row["cache_sha256"]
        inputs.append(item)
    gfx = {}
    if not cpu_smoke:
        for name, path in CAMERAS.items():
            data = read(path)
            assert len({c["scene"] for c in data["cases"]}) == (4 if name == "known" else 5)
            assert sum(len(c["crops"]) for c in data["cases"]) == (72 if name == "known" else 90)
            inputs.append(ref(path))
            for case in data["cases"]:
                for crop in case["crops"]:
                    item = ref(path.parent / crop["path"])
                    assert item["sha256"] == crop["sha256"]
                    inputs.append(item)
        for name in ("utnet2-bayer.pt", "raw_denoiser.py", "LICENSE", "provenance.json"):
            inputs.append(ref(RAWNIND / name))
        inputs.append(ref(COLOR))
        for case in read(COLOR)["cases"]:
            item = ref(case["arrays"])
            assert item["sha256"] == case["sha256"]
            inputs.append(item)
        for stage, name in (
            ("gfx", "gfx-qualitative-20231231.json"),
            ("gfx-highlights", "gfx-qualitative-20231231-highlights.json"),
        ):
            original = REPO / "configs" / name
            selected = read(original)
            inputs.append(ref(original))
            for role in ("noisy", "reference"):
                path = (REPO / selected[role]).resolve()
                assert path.is_relative_to(REPO / ".cache/gfx-qualitative-20231231")
                inputs.append(ref(path))
                selected[role] = str(path)
            destination = work / "configs" / name
            save(destination, selected)
            gfx[stage] = str(destination)
    inputs = list({(r["path"], r["sha256"]): r for r in inputs}.values())
    plan = {
        "root": str(root),
        "work": str(work),
        "training_root": str(training_root),
        "training_plan": training_ref,
        "training_controller": launch["controller"],
        "training_arms": list(arms),
        "parent_label": parent_label,
        "evaluation_root": str(evaluation_root),
        "artifact_root": str(artifact_root),
        "cpu_smoke": cpu_smoke,
        "python": training["python"],
        "cache_environment": {
            key: value
            for key, value in os.environ.items()
            if key
            in {
                "HF_HOME",
                "TORCH_HOME",
                "UV_CACHE_DIR",
                "XDG_CACHE_HOME",
                "XDG_CONFIG_HOME",
                "MPLCONFIGDIR",
                "TMPDIR",
                "CUDA_CACHE_PATH",
                "TORCHINDUCTOR_CACHE_DIR",
                "TRITON_CACHE_DIR",
            }
        },
        "photo_manifest": ref(PANEL),
        "photo_ids": [row["id"] for row in (rows[:2] if cpu_smoke else rows)],
        "camera_manifests": {k: ref(p) for k, p in CAMERAS.items()} if not cpu_smoke else {},
        "rawnind": str(RAWNIND),
        "color": str(COLOR),
        "gfx": gfx,
        "dependency_wait_seconds": 86400,
        "disk_reserves": {"root_reserve_gib": 32, "external_reserve_gib": 256},
        "external_device": Path("/mnt/external").stat().st_dev,
        "inputs": inputs,
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "scope": f"Discarded CPU reporting integration using {parent_label} and {', '.join(arms)} eight-update CPU smokes; not a production quality result."
        if cpu_smoke
        else f"{parent_label} step{training.get('parent_step', 20000)} versus fixed {', '.join(arms)} step{training['train_updates']} EMAs. Fresh IEEE FP32 full427/16-procedural/7-condition/4-CFA, known/unseen measured-CFA, weak-detail/color and standing GFX plus highlights. Same observations and display metadata; no checkpoint selection or automatic promotion. Report useful gains and tradeoffs, then update current recommendations and native comparisons.",
    }
    if references is not None:
        plan["reference_checkpoints"] = reference_records
        plan["scope"] += (
            " Additional fixed references: " + ", ".join(r["arm"] for r in reference_records) + "."
        )
    save(root / "plan.json", plan)
    guard(plan)
    return root / "plan.json"


def prepare_evaluation(plan, state):
    root, work = Path(plan["evaluation_root"]), Path(plan["work"])
    training = read(plan["training_plan"]["path"])
    guard(training)
    records, inputs = checkpoints(
        state,
        training,
        cpu_smoke=plan["cpu_smoke"],
        parent_label=plan.get("parent_label", "V84"),
        reference_checkpoints=plan.get("reference_checkpoints", ()),
    )
    root.mkdir(parents=True, exist_ok=False)
    Path(plan["artifact_root"]).mkdir(parents=True, exist_ok=False)
    save(root / "training-boundary.json", state)
    evaluation = {
        **plan,
        "root": str(root),
        "training_status": ref(root / "training-boundary.json"),
        "checkpoints": records,
        "cpu_proof": plan["cpu_smoke"],
        "stages": ["photo"]
        if plan["cpu_smoke"]
        else ["photo", "known", "unseen", "texture", "color", "gfx", "gfx-highlights"],
        "size": 176 if plan["cpu_smoke"] else 256,
        "batch_size": 1 if plan["cpu_smoke"] else 4,
        "photo_count": 2 if plan["cpu_smoke"] else 427,
        "synthetic_count": 1 if plan["cpu_smoke"] else 16,
        "protocol": str(
            work / "configs" / ("smoke-evaluation.yaml" if plan["cpu_smoke"] else "evaluation.yaml")
        ),
        "precision": "float32",
        "DINO_SHA256": DINO_SHA,
        "stable_seconds": 2 if plan["cpu_smoke"] else 15,
        "wait_seconds": 7200,
        "stage_timeout_seconds": 1200 if plan["cpu_smoke"] else 43200,
        "inputs": [*plan["inputs"], *inputs, ref(root / "training-boundary.json")],
    }
    save(root / "plan.json", evaluation)
    guard(evaluation)
    return root / "plan.json"


def controller(path):
    import evaluate_v43_quality_trial as evaluation

    plan = read(path)
    guard(plan)
    root = Path(plan["root"])
    (root / "controller.claim").open("x").close()
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}

    def record(status, **details):
        save(
            root / "status.json",
            {
                "plan": ref(path),
                "controller": owner,
                "status": status,
                "updated_unix": time.time(),
                **details,
            },
        )

    try:
        record("waiting-for-owned-quality-training")
        started = time.monotonic()
        while True:
            state = read(Path(plan["training_root"]) / "status.json")
            if plan["cpu_smoke"] or training_ready(
                state,
                plan["training_plan"],
                plan["training_controller"],
                arms=plan.get("training_arms", ARMS),
            ):
                break
            assert time.monotonic() - started < plan["dependency_wait_seconds"]
            time.sleep(15)
        guard(plan)
        evaluation_plan = prepare_evaluation(plan, state)
        record("running-quality-recipe-evaluation", evaluation_plan=ref(evaluation_plan))
        evaluation.controller(evaluation_plan)
        record(
            "completed-quality-recipe-evaluation-awaiting-image-review",
            evaluation_plan=ref(evaluation_plan),
        )
    except BaseException as error:
        record("failed-quality-recipe-evaluation-preserved", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--training-root", type=Path)
    parser.add_argument("--evaluation-root", type=Path)
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--cpu-smoke", action="store_true")
    parser.add_argument("--parent-label", default="V84")
    parser.add_argument(
        "--references", type=Path, help="JSON list of fixed baseline checkpoint identity records"
    )
    args = parser.parse_args()
    if args.mode == "prepare":
        print(
            prepare(
                args.training_root,
                args.path,
                args.evaluation_root,
                args.artifacts,
                cpu_smoke=args.cpu_smoke,
                parent_label=args.parent_label,
                references=args.references,
            )
        )
    else:
        controller(args.path.resolve())
