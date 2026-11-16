"""Audit each closed V131 numerical panel with the original independent CPU code."""

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text())


def ref(path):
    path = Path(path).absolute()
    with path.open("rb") as f:
        return {"path": str(path), "sha256": hashlib.file_digest(f, "sha256").hexdigest()}


def checked(binding):
    if ref(binding["path"])["sha256"] != binding["sha256"]:
        raise ValueError("Independent broad-review input changed")
    return Path(binding["path"])


def write(path, value, replace=False):
    path = Path(path)
    temp = path.with_name("." + path.name + ".tmp")
    with temp.open("x") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")
    try:
        if replace:
            temp.replace(path)
        else:
            os.link(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def prepare(root, producer):
    import psutil

    repo = Path.cwd()
    plan = read(producer / "plan.json")
    state = read(producer / "status.json")
    owner = psutil.Process(state["owner"]["pid"])
    if (
        owner.create_time() != state["owner"]["created"]
        or not owner.is_running()
        or state["plan"] != ref(producer / "plan.json")
        or state["status"].startswith("failed")
    ):
        raise ValueError("Require the exact live V131 evaluator")
    if (
        len(plan["checkpoints"]) != 1
        or plan["checkpoints"][0]["sha256"]
        != "4d78e6302f6e72d68acb03fe58eb7106763b8129ccb059747ef5d2cfbd3ec1e1"
    ):
        raise ValueError("Require completed V13120k only")
    original = (
        repo
        / ".cache/current-quality-20261023-v1/V120-V121-paired32-weak-detail-independent-audit-v1/queue-plan-v1.json"
    )
    old = read(original)
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    files = {}
    for source, digest in old["frozen_files"].items():
        p = checked({"path": source, "sha256": digest})
        target = work / p.relative_to(Path(old["work"]))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
        files[str(target)] = digest
    script = work / "scripts" / Path(__file__).name
    shutil.copyfile(__file__, script)
    files[str(script)] = ref(script)["sha256"]
    own = {
        "producer": str(producer),
        "producer_plan": ref(producer / "plan.json"),
        "expected_owner": state["owner"],
        "work": str(work),
        "output": str(work / "audit-output"),
        "script": ref(script),
        "python": sys.executable,
        "material_ids": [
            "0ae232278265dabbdd54f52c34045a3d03323aa7",
            "2b5a51667b9906eecead8f82e08c7ba11750f8c6",
        ],
        "baseline_sha256": "a9d9b6b4f974e24a6b11e5e740aab32314233a7f53c056cf37c7d2aac1c589fb",
        "inputs": [ref(producer / "plan.json"), ref(original)],
        "frozen_files": files,
        "scope": "Wait on exact V131 owner and audit each complete result/archive immediately, overlapping later GPU stages. Original independent NumPy64 reductions and original tolerances preserved; SSIM/masked metrics retain original evaluator implementation. All14190 observations/one endpoint required, zero inference/noise/RAW/optimizer work. Paired427-photo and4/5 camera-scene summaries against existing V120; photo triplets fixed to bark/fur ISO12800-prior/RGGB/native160. New writes inside frozen work, no signals/restarts or automatic retry/promotion.",
    }
    write(root / "plan.json", own)
    return root / "plan.json"


def verify(plan):
    for b in plan["inputs"]:
        checked(b)
    for path, digest in plan["frozen_files"].items():
        checked({"path": path, "sha256": digest})


def run(root):
    import psutil
    from audit_quality_archive import audit, paired_changes, read_rows

    own = read(root / "plan.json")
    verify(own)
    if ref(__file__) != own["script"] or "torch" in sys.modules:
        raise RuntimeError("Require frozen CPU auditor")
    (root / "run.claim").open("x").close()
    identity = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    write(root / "owner.json", identity)
    producer = Path(own["producer"])
    plan = read(checked(own["producer_plan"]))
    deadline = time.monotonic() + 14400
    output = Path(own["output"])
    output.mkdir()
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[-2:])
    results = {}
    for stage, spec in plan["stages"].items():
        result_path = Path(spec["output"]) / "result.json"
        while not result_path.exists():
            state = read(producer / "status.json")
            if (
                state["owner"] != own["expected_owner"]
                or state["plan"] != own["producer_plan"]
                or state["status"].startswith("failed")
            ):
                raise RuntimeError("Original V131 producer failed or changed")
            p = psutil.Process(own["expected_owner"]["pid"])
            if p.create_time() != own["expected_owner"]["created"] or not p.is_running():
                raise RuntimeError("Expected evaluator stopped without this stage")
            if time.monotonic() > deadline:
                raise TimeoutError("Bounded audit wait expired; no restart")
            write(
                root / "status.json",
                {"status": "waiting-for-exact-closed-stage", "stage": stage, "owner": identity},
                replace=True,
            )
            time.sleep(15)
        result = read(result_path)
        if (
            result["plan"] != own["producer_plan"]
            or result["source"] != plan["collector_source"]
            or result["stage"] != stage
            or len(result["invariants"]) != 1
        ):
            raise ValueError("Closed numerical-stage lineage differs")
        inv = result["invariants"][0]
        if (
            inv["calls"] != spec["calls_per_model"]
            or inv["encoder_calls"] != spec["calls_per_model"]
            or inv["observations"] != spec["observations_per_model"]
            or inv["checkpoint"] != plan["checkpoints"][0]
        ):
            raise ValueError("Complete declared neural/input coverage differs")
        if (
            psutil.virtual_memory().available < 16 * 2**30
            or shutil.disk_usage(root).free < 32 * 2**30
        ):
            raise RuntimeError("CPU audit reserve unavailable")
        checked(result["archive"])
        checked(result["report"])
        write(
            root / "status.json",
            {
                "status": "auditing-closed-stage",
                "stage": stage,
                "owner": identity,
                "result": ref(result_path),
            },
            replace=True,
        )
        value = audit(
            Path(result["archive"]["path"]),
            Path(result["report"]["path"]),
            output / stage,
            stage=stage,
            material_ids=own["material_ids"] if stage == "photo" else (),
            source_manifest=spec["manifest"]["path"] if stage == "photo" else None,
        )
        if (
            value["models"] != 1
            or value["observations"] != {"V131": spec["observations_per_model"]}
            or value["Torch_imported"]
            or value["new_neural_forwards"] != 0
        ):
            raise ValueError("Independent complete-panel coverage differs")
        results[stage] = {
            "producer_result": ref(result_path),
            "audit": ref(output / stage / "result.json"),
        }
        if stage in ["photo", "known", "unseen"]:
            current = read(checked(value["independent_rows"]))
            control = read(checked(plan["existing_controls"][stage]["report"]))
            label = next(
                m["label"] for m in control["models"] if m["sha256"] == own["baseline_sha256"]
            )
            row_file = Path(plan["existing_controls"][stage]["report"]["path"]).parent / (
                "per-image.jsonl" if stage == "photo" else "per-crop.jsonl"
            )
            controls = [r for r in read_rows(row_file) if r["model"] == label]
            metrics = (
                ["srgb_psnr", "linear_psnr", "chroma_mae", "gradient_mae"]
                if stage == "photo"
                else ["sensor_psnr", "ahd_srgb_psnr", "ahd_chroma_mae", "ahd_gradient_mae"]
            )
            comparisons = [
                paired_changes(current, controls, stage=stage, metric=m) for m in metrics
            ]
            if any(
                c["units"] != {"photo": 427, "known": 4, "unseen": 5}[stage] for c in comparisons
            ):
                raise ValueError("Source/scene balanced units differ")
            write(
                output / stage / "paired-V120.json",
                {
                    "audited_rows": value["independent_rows"],
                    "control_report": plan["existing_controls"][stage]["report"],
                    "control_rows": ref(row_file),
                    "comparisons": comparisons,
                    "scope": "Fixed paired sources/scenes; no training-seed or general-camera uncertainty.",
                },
            )
            results[stage]["paired_V120"] = ref(output / stage / "paired-V120.json")
        print(
            stage,
            value["observations"],
            "complete; maximum discrepancies",
            value["maximum_metric_discrepancies"],
            flush=True,
        )
    verify(own)
    if "torch" in sys.modules:
        raise RuntimeError("Independent auditor imported Torch")
    write(
        root / "completed.json",
        {
            "status": "completed-five-panel-independent-audit-awaiting-native-and-local-detail-review",
            "plan": ref(root / "plan.json"),
            "stages": results,
            "total_observations": sum(plan["stages"][s]["observations_per_model"] for s in results),
            "new_neural_forwards": 0,
            "scope": "Primary metrics and source/scene summaries independently checked. Native triplets await actual viewing; full local-detail/camera/color tails and protected-real adoption remain separate review.",
        },
    )
    write(
        root / "status.json",
        {
            "status": "completed-five-panel-independent-audit-awaiting-native-and-local-detail-review",
            "owner": identity,
            "completed": ref(root / "completed.json"),
        },
        replace=True,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=["prepare", "run"])
    p.add_argument("root", type=Path)
    p.add_argument("--producer", type=Path)
    args = p.parse_args()
    if args.mode == "prepare":
        print(prepare(args.root.resolve(), args.producer.resolve()))
    else:
        try:
            run(args.root.resolve())
        except BaseException as error:
            write(
                args.root.resolve() / "failure.json",
                {"error": repr(error), "no_training_or_inference_signals": True},
            )
            raise
