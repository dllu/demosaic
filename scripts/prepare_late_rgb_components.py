"""Freeze analytic inputs and actual training code for the component diagnosis."""

import argparse
import ast
import itertools
import shutil
from pathlib import Path

import numpy as np
import torch
import yaml
from train_directional_bank_trial import read, ref, save

from demosaic.suite import observation

REPO = Path(__file__).resolve().parents[1]
REVIEW = Path("/mnt/external/demosaic/experiments/late-rgb-v90-v91-original4k-review-v1")


def fixture(rgb, ids, condition, pattern, protocol):
    return observation(
        rgb,
        ids,
        condition,
        pattern,
        protocol["white_balance"],
        protocol["camera_to_srgb"],
        20261016,
    )


def main(root):
    assert not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    root = root.resolve()
    root.mkdir(exist_ok=False)
    work = root / "work"
    shutil.copytree(
        REVIEW / "work/src", work / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
    scripts = work / "scripts"
    scripts.mkdir()
    candidates = {p.stem: p for p in (REVIEW / "work/scripts").glob("*.py")}
    for name in [
        "late_rgb_component_tools",
        "diagnose_late_rgb_components",
        "prepare_late_rgb_components",
        "run_late_rgb_component_probe",
    ]:
        candidates[name] = REPO / "scripts" / (name + ".py")
    pending = [
        candidates[name]
        for name in [
            "diagnose_late_rgb_components",
            "prepare_late_rgb_components",
            "run_late_rgb_component_probe",
            "diagnose_texture_response",
        ]
    ]
    copied = set()
    while pending:
        source = pending.pop()
        if source.stem in copied:
            continue
        shutil.copyfile(source, scripts / source.name)
        copied.add(source.stem)
        for node in ast.walk(ast.parse(source.read_text())):
            names = (
                [n.name for n in node.names]
                if isinstance(node, ast.Import)
                else ([node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            )
            pending.extend(
                candidates[n.split(".")[0]] for n in names if n.split(".")[0] in candidates
            )
    (work / "configs").mkdir()
    protocol_path = work / "configs/evaluation.yaml"
    shutil.copyfile(REVIEW / "work/configs/evaluation.yaml", protocol_path)
    (work / "docs").mkdir()
    shutil.copyfile(REPO / "docs/late-rgb-detail-decomposition.md", work / "docs/protocol.md")
    shutil.copyfile(
        REPO / "tests/test_late_rgb_components.py", root / "test_late_rgb_components.py"
    )
    shutil.copyfile("/mnt/external/demosaic/late-rgb-component-tests-v1.xml", root / "tests.xml")
    protocol = yaml.safe_load(protocol_path.read_text())
    fixtures, folder = [], root / "inputs"
    folder.mkdir()
    x = torch.arange(256, dtype=torch.float32)
    specs = [
        (l, c, p, "adc-only")
        for l, c, p in itertools.product([0.01, 0.18], [0.02, 0.10], [4, 8, 16])
    ]
    specs += [
        (0.01, 0.10, 8, "iso12800-prior"),
        (0.18, 0.02, 16, "iso12800-prior"),
        (0.18, 0, None, "iso12800-prior"),
    ]
    for level, contrast, period, name in specs:
        condition = next(c for c in protocol["conditions"] if c["name"] == name)
        kind = "flat" if period is None else "carrier"
        rgb = (
            torch.full((4, 3, 256, 256), level)
            if period is None
            else (
                (level * (1 + contrast * (x * (2 * __import__("math").pi / period)).cos()))[
                    None, None, None
                ]
                .expand(4, 3, 256, 256)
                .clone()
            )
        )
        prefix = f"flat-l{level}" if kind == "flat" else f"carrier-l{level}-c{contrast}-p{period}"
        ids = [f"{prefix}-draw{i}" for i in range(4)]
        patterns = protocol["patterns"]
        batches = []
        for pattern in patterns:
            data = fixture(rgb, ids, condition, pattern, protocol)
            if name == "adc-only":
                assert all(torch.equal(v[:1].expand_as(v), v) for v in data.values())
                batches.append({k: v[:1] for k, v in data.items()})
            else:
                batches.append(data)
        for i, pattern in enumerate(patterns if name != "adc-only" else ["all-CFAs"]):
            data = (
                batches[i]
                if name != "adc-only"
                else {k: torch.cat([b[k] for b in batches]) for k in batches[0]}
            )
            cases = [
                {
                    "level": level,
                    "contrast": contrast,
                    "period": period,
                    "pattern": p,
                    "draw": j,
                    "id": ids[j],
                }
                for p, j in (
                    [(p, 0) for p in patterns]
                    if name == "adc-only"
                    else [(pattern, j) for j in range(4)]
                )
            ]
            key = f"{name}-{kind}-{level}-{contrast}-{period}-{pattern}"
            path = folder / (key + ".npz")
            np.savez(path, **{k: v.numpy() for k, v in data.items()})
            fixtures.append(
                {
                    "id": key,
                    "kind": kind,
                    "condition": condition,
                    "cases": cases,
                    "arrays": ref(path),
                }
            )
    assert len(fixtures) == 24 and sum(len(f["cases"]) for f in fixtures) == 96
    boundary = read(REVIEW / "training-boundary.json")
    original = read(REVIEW / "plan.json")
    checkpoints = {
        "parent": {k: original["parent"][k] for k in ["path", "sha256"]},
        **{
            role: boundary["evidence"][i]["retained"]
            for i, role in enumerate(["global", "spatial"])
        },
    }
    owners = []
    for directory, filename in [
        (REVIEW, "status.json"),
        (REVIEW, "closure-status.json"),
        (REVIEW, "report-assets-recovery-status.json"),
        (root.parent / "uniform-physics-CUDA-v2", "status.json"),
        (root.parent / "uniform-physics-CUDA-review-v3", "status.json"),
    ]:
        state = read(directory / filename)
        owners += [state[k] for k in ["controller", "child"] if k in state]
    inputs = [
        ref(p)
        for p in [
            protocol_path,
            work / "docs/protocol.md",
            root / "tests.xml",
            root / "test_late_rgb_components.py",
            REVIEW / "manual-native-review-before-statistics.json",
            REVIEW / "final-quality-review.json",
            REVIEW / "work/outputs/analytic/per-case.jsonl",
            REVIEW / "work/outputs/analytic/summary.json",
        ]
    ]
    inputs += list(checkpoints.values()) + [f["arrays"] for f in fixtures]
    files = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    plan_path = root / "plan.json"
    save(
        plan_path,
        {
            "root": str(root),
            "path": str(plan_path),
            "work": str(work),
            "python": str(REPO / ".venv/bin/python3"),
            "HF_HOME": original["HF_HOME"],
            "worker": ref(scripts / "diagnose_late_rgb_components.py"),
            "controller": ref(scripts / "run_late_rgb_component_probe.py"),
            "CPU_output": str(root / "CPU-output"),
            "GPU_output": str(root / "GPU-output"),
            "fixtures": fixtures,
            "checkpoints": checkpoints,
            "frozen_files": files,
            "inputs": inputs,
            "blocking_owners": owners,
            "capture_cases": [
                [0.01, 0.02, 4, "adc-only"],
                [0.18, 0.02, 4, "adc-only"],
                [0.01, 0.10, 8, "iso12800-prior"],
                [0.18, 0.02, 16, "iso12800-prior"],
            ],
            "original_analytic_cases": ref(REVIEW / "work/outputs/analytic/per-case.jsonl"),
            "metric_replay_gain_tolerance": 1e-6,
            "metric_replay_absolute_tolerance": 1e-8,
            "scope": "Fixed96 analytic observations, six frozen diagnostic methods. Actual full-output/tail/head parity, one common encoder per captured forward and reused variants. No training, target-forward, policy export, photo-quality improvement or promotion. All32 native cells must be actually viewed before interpreting new component metrics; preserve all cases and original checkpoint scalar replay.",
        },
    )
    print(
        {
            "plan": ref(plan_path),
            "model_modules": len(list((work / "src/demosaic").glob("*.py"))),
            "fixtures": len(fixtures),
            "distinct_observations": 96,
            "frozen_files": len(files),
        }
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    main(p.parse_args().root)
