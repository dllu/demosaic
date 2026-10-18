"""Freeze a fresh V80/V81 candidate-context comparison after genuine execution checks."""

import argparse
import json
import shutil
from pathlib import Path

import yaml
from train_directional_interval_trial import ref, save, sha


def main(root):
    root = root.absolute()
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    work.mkdir()
    cpu = Path(".cache/experiments/directional-bank-CPU-preflight-v2/receipt.json")
    cuda = Path(".cache/experiments/directional-bank-CUDA-preflight-v1/receipt.json")
    assert json.loads(cpu.read_text())["status"] == "completed-directional-bank-CPU-preflight"
    assert json.loads(cuda.read_text())["status"] == "completed-directional-bank-CUDA-B16-preflight"
    files = [*Path("src/demosaic").glob("*.py"), *Path("scripts").glob("*.py")]
    files += [
        Path(p)
        for p in [
            "pyproject.toml",
            "uv.lock",
            "configs/evaluation.yaml",
            "third_party/gaussian/Noise2VST-LICENSE",
            "third_party/gaussian/KAIR-LICENSE",
            "third_party/dinov3/LICENSE.md",
            "docs/directional-bank-v80-v81.md",
        ]
    ]
    for source in files:
        target = work / source
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    arms, recipes, originals = [], [], []
    for name, version, enabled in [("control", 80, False), ("bank", 81, True)]:
        source = (
            Path("configs")
            / f"dino-convnext-directional-bank-{'control' if not enabled else 'context'}-v{version}.yaml"
        )
        cfg = yaml.safe_load(source.read_text())
        assert cfg["reference_interval_weight"] == 0
        assert cfg["model"]["raw_directional_bank_context"] is enabled
        assert cfg["training_execution"] == "deterministic-v1"
        cfg["run"] = str(work / "runs" / source.stem)
        target = work / source
        target.write_text(yaml.safe_dump(cfg))
        recipes.append(cfg)
        originals.append(source)
        arms.append(
            {
                "name": name,
                "version": version,
                "reference_interval_weight": 0.0,
                "bank_context": enabled,
                "config": str(target),
                "run": cfg["run"],
            }
        )
    a, b = [
        {
            **{k: v for k, v in c.items() if k not in ("run", "model")},
            "model": {k: v for k, v in c["model"].items() if k != "raw_directional_bank_context"},
        }
        for c in recipes
    ]
    assert a == b, "Matched arms may differ only in output location and bank context"
    parent = Path(
        "/mnt/external/demosaic/models/dino-convnext-wide-long-control-b16-v63-step20000.pt"
    )
    assert sha(parent) == "ed70952dd33c5d7da39199bf1306b58b579862920fb0cccd6b222f19871bc9b5"
    manifests = [
        Path(recipes[0][k])
        for k in ("manifest", "validation_manifest", "paired_manifest", "raw_clean_manifest")
    ]
    assert sha(manifests[0]) == "952977c6af9a1b0d7428c25e2b9cf4f1338d90e3295de33b552cbeb8153be502"
    # Bind the exact package bytes executed by both discarded preflights.
    for receipt in (cpu, cuda):
        plan = json.loads(Path(json.loads(receipt.read_text())["plan"]["path"]).read_text())
        for source, digest in plan["source_files"].items():
            assert sha(source) == digest
            assert sha(work / "src/demosaic" / Path(source).name) == digest
    inputs = [
        parent,
        cpu,
        cuda,
        *originals,
        *manifests,
        Path("docs/directional-bank-v80-v81.md"),
    ]
    plan = {
        "status": "frozen-directional-bank-original4000-no-automatic-extension",
        "root": str(root),
        "work": str(work),
        "python": str(Path(".venv/bin/python3").absolute()),
        "HF_HOME": str(Path(".cache/huggingface").absolute()),
        "parent": ref(parent),
        "worker": ref(work / "scripts/train_directional_bank_trial.py"),
        "arms": arms,
        "planned_updates": 4000,
        "boundary_updates": 4000,
        "per_arm_timeout_seconds": 10800,
        "training_manifest_sha256": sha(manifests[0]),
        "training_counts": {"train": 84867, "val": 2303, "test": 2255},
        "inputs": [ref(p) for p in inputs],
        "frozen_files": {str(p): sha(p) for p in sorted(work.rglob("*")) if p.is_file()},
        "quality_review_plan": {
            "predeclared_snapshot": ref(work / "docs/directional-bank-v80-v81.md"),
            "primary": "Each arm eligible only if known4/unseen5 CFA gains >=.05dB vs fresh genuine V63, each with positive scene95% bounds; full427 rendered PSNR gain>=.05dB/positive source95% bounds; SSIM loss<=.0001.",
            "bank_effect": "V81-minus-V80 positive full427 PSNR interval; known/unseen losses<=.03dB each; each fixed dark/bright weak-carrier gain improves>=.05, corresponding flat spatial-luma RMS<=1.25x control; no new visible failure.",
            "additional": "All fixed conditions/CFAs, procedural16,418/416 sensitivities,hue/highlight/analytic groups,>=2 native100% GT triplets per checkpoint,cached GFX sky/building/foliage/fence/highlights with independent ISO100 labels; compare working V43/RawNIND too. No visible new failure.",
            "action": "Full original4000 budget, no automatic extension or promotion. Only eligible candidates get separate full101.996MP FP32/export16/native/timing review. Protected-final scenes closed; old studies stay closed.",
        },
        "limits": "24GiB CUDA cap,40GiB launch RAM headroom,128GiB root/500GiB external reserves;10800s/arm;exact owned child termination only. Single-seed engineering/training completion cannot establish SOTA, convergence or100MP/10s. Finite preflight updates discarded.",
    }
    save(root / "plan.json", plan)
    print(json.dumps({"plan": ref(root / "plan.json"), "frozen_files": len(plan["frozen_files"])}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.output)
