"""Freeze the shared-profile CUDA probe behind the current fixed quality work."""

import argparse
import shutil
from pathlib import Path

from queue_tf32x3_cuda import alive, dependencies_ready
from train_directional_bank_trial import read, ref, save

REPO = Path(__file__).resolve().parents[1]
BASE = Path("/mnt/external/demosaic")
TRAIN = BASE / "experiments/late-rgb-v90-v91-original4k-v1"
REVIEW = BASE / "experiments/late-rgb-v90-v91-original4k-review-v1"


def main(root):
    root = root.resolve()
    assert root.is_relative_to(BASE / "experiments") and not root.exists()
    proof_path = BASE / "experiments/uniform-physics-CPU-v1/receipt.json"
    proof = read(proof_path)
    assert proof["component_fields_exact"] and proof["full_model_fields_exact"]
    assert proof["CUDA_initialized"] is False and proof["component_cases"] == 48
    assert ref(REPO / "scripts/probe_uniform_physics_cpu.py")["sha256"] == proof["driver"]["sha256"]
    training = read(TRAIN / "status.json")
    queue = read(REVIEW / "queue-launch.json")
    package = read(REVIEW / "report-assets-status.json")
    owners = [
        training["controller"],
        training["child"],
        *[queue[k] for k in ["review_owner", "closure_owner", "reference_owner"]],
        package["controller"],
    ]
    assert len(owners) == 6 and all(alive(o) for o in owners)
    fixture_path = BASE / "benchmarks/packed-isotropic-compilation-inputs-v1/inputs.json"
    fixture = read(fixture_path)
    # Fixed genuine checkpoint/source identities from the completed mature trial.
    old = read(REPO / "docs/results/mature-TF32x3-CUDA-complete-v1.json")
    checkpoints = {c["model"]: c["checkpoint"] for c in old["accuracy_cases"]}
    assert set(checkpoints) == {"V43", "V63"}
    fixtures = [
        {
            "label": f"photo{i}-native256",
            "observation": photo["observation"],
            "conditioning": photo["metadata"]["condition"],
            "metadata": photo["metadata"],
        }
        for i, photo in enumerate(fixture["photos"])
    ]
    fixtures += [
        {
            "label": label,
            "observation": case["observation"],
            "conditioning": condition,
        }
        for label, case, condition in zip(
            ["GFX-four-native512", "analytic-four-CFA-native512"],
            fixture["serving_probes"],
            [fixture["conditioning"], fixture["analytic_condition"]],
            strict=True,
        )
    ]
    assert len(fixtures) == 4
    for item in [*checkpoints.values(), *[f["observation"] for f in fixtures]]:
        assert ref(item["path"]) == item
    root.mkdir(parents=True)
    work = root / "work"
    shutil.copytree(REPO / "src", work / "src", ignore=shutil.ignore_patterns("__pycache__"))
    scripts = work / "scripts"
    scripts.mkdir()
    names = [
        "prepare_uniform_physics_cuda.py",
        "probe_uniform_physics_cpu.py",
        "probe_uniform_physics_cuda.py",
        "queue_uniform_physics_cuda.py",
        "queue_tf32x3_cuda.py",
        "train_directional_bank_trial.py",
        "profile_raw_kernel_inference.py",
    ]
    for name in names:
        shutil.copy2(REPO / "scripts" / name, scripts / name)
    source_files = sorted((work / "src/demosaic").glob("*.py"))
    expected = {Path(p["path"]).name: p["sha256"] for p in proof["model_sources"]}
    assert len(source_files) == len(expected) == 47
    assert all(ref(p)["sha256"] == expected[p.name] for p in source_files)
    dependencies = []
    for path, expected_status in [
        (
            TRAIN / "status.json",
            "completed-late-rgb-original4000-awaiting-full-quality-and-native-review",
        ),
        (
            REVIEW / "status.json",
            "completed-directional-bank-inference-awaiting-statistical-and-manual-native-closure",
        ),
        (
            REVIEW / "closure-status.json",
            "completed-CPU-numerical-and-native-board-preparation-awaiting-manual-review",
        ),
        (
            REVIEW / "report-assets-status.json",
            "prepared-native-report-assets-awaiting-manual-inspection",
        ),
    ]:
        state = read(path)
        dependencies.append(
            {
                "path": str(path),
                "controller": state["controller"],
                "plan": state["plan"],
                "status": expected_status,
            }
        )
    files = [
        *source_files,
        *[scripts / n for n in names],
        proof_path,
        fixture_path,
        *[Path(c["path"]) for c in checkpoints.values()],
        *[Path(f["observation"]["path"]) for f in fixtures],
        *[Path(d["plan"]["path"]) for d in dependencies],
        REVIEW / "queue-launch.json",
    ]
    inputs = [ref(p) for p in dict.fromkeys(files)]
    gpu = {
        "worker": ref(scripts / "probe_uniform_physics_cuda.py"),
        "controller": ref(scripts / "queue_uniform_physics_cuda.py"),
        "python": str(REPO / ".venv/bin/python3"),
        "work": str(work),
        "inputs": inputs,
        "output": str(root / "GPU-output"),
        "CPU_output": str(root / "CPU-preflight"),
        "checkpoints": checkpoints,
        "fixtures": fixtures,
        "blocking_owners": owners,
        "completed_dependencies": dependencies,
        "required_completed_receipts": [
            {
                "path": str(REVIEW / "work/outputs/reference-closure/receipt.json"),
                "status": "prepared-directional-working-reference-boards-awaiting-manual-review",
            },
            {
                "path": str(REVIEW / "work/outputs/report-assets-v1/index.json"),
                "status": "prepared-native-report-assets-manual-review-pending",
            },
        ],
        "scope": "Isolated unchanged V43/V63 EMA inference. Scalar-profile GAT/MHC/inverse batching only; source/model/noise/precision unchanged. IEEE FP32, channels-last, cuDNN search16GiB cap. Eight full-output array pairs: two fixed256px photos, four standing native512 GFX contexts and an all-CFA low/high-signal512px field per model. Compare unquantized unclipped values against1DN16 max/.25DN16 RMS; no relaxed gates. Exact repeats/original restoration and model/DINO/parameter/RNG identities required. Only after all eight gates pass: three warmups and four synchronized samples per policy in reversed order at B4/native512. Shared-machine resident timings exclude loading/search/transfers/tiling/blending/decode/export. No training, promotion, default integration, GT/GFX scoring or full-frame speed claim; independent arrays/native views remain required.",
    }
    assert not dependencies_ready(gpu)
    save(root / "GPU-plan.json", gpu)
    save(
        root / "preparation.json",
        {
            "status": "prepared-source-frozen-uniform-physics-probe-awaiting-CPU-worker-preflight",
            "plan": ref(root / "GPU-plan.json"),
            "CPU_component_and_V63_proof": ref(proof_path),
            "all_six_blocking_owners_verified_live": True,
            "preparation_source": ref(__file__),
        },
    )
    print(ref(root / "GPU-plan.json"))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    main(p.parse_args().output)
