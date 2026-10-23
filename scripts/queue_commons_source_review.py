"""Render complete4x source sheets with explicit accounting for reviewed failures."""

import argparse
import importlib.util
import json
import os
import shutil
import time
from pathlib import Path

import psutil
from commons_preparation_review import load_failure_review, read, ref, validate_coverage


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def alive(owner):
    try:
        p = psutil.Process(owner["pid"])
        return p.create_time() == owner["created"] and p.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def freeze(producer, root, *, reserve_gib=548, failure_review=None):
    from render_commons_contact_sheets import resources

    repo = Path(__file__).resolve().parents[1]
    root = Path(root).resolve()
    if root.exists() or not root.is_relative_to("/mnt/external/demosaic"):
        raise ValueError("Use a fresh external source-review root")
    resources(root.parent, reserve_gib)
    production = read(producer)
    selection = read(production["selection"]["path"])
    if len(selection) != production["selected_originals"]:
        raise ValueError("Original source selection count differs")
    reviewed = load_failure_review(failure_review, ref(producer), production["selection"])
    valid = [r for r in selection if r["sha1_hex"] not in reviewed["errors"]]
    root.mkdir(parents=True)
    for name, source in [
        ("queue.py", Path(__file__)),
        ("renderer.py", repo / "scripts/render_commons_contact_sheets.py"),
        ("commons_preparation_review.py", repo / "scripts/commons_preparation_review.py"),
    ]:
        shutil.copyfile(source, root / name)
    save(root / "selected-valid-source-records.json", valid)
    plan = {
        "root": str(root),
        "producer": ref(producer),
        "owner": read(Path(producer).parent / "status.json")["owner"],
        "original_selection": production["selection"],
        "original_selected": len(selection),
        "selection": ref(root / "selected-valid-source-records.json"),
        "selected": len(valid),
        "failure_review": ref(failure_review) if failure_review else None,
        "inputs": reviewed["inputs"],
        "reserve_gib": reserve_gib,
        "sources": [
            ref(root / name)
            for name in ["queue.py", "renderer.py", "commons_preparation_review.py"]
        ],
        "maximum_wait_seconds": 14400,
        "scope": "Complete finalized4x cache population only; every missing source must be one exact manually reviewed withheld failure. No source repair, profile bypass, source-quality approval or training admission. Original producer and error receipts stay unchanged.",
    }
    save(root / "plan.json", plan)
    return ref(root / "plan.json")


def run(path):
    plan = read(path)
    root = Path(plan["root"])
    (root / ".run-claimed").touch(exist_ok=False)
    binding = ref(path)
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    os.nice(10)

    def status(value, **fields):
        save(
            root / "status.json",
            {
                "status": value,
                "owner": owner,
                "plan": binding,
                "updated_unix": time.time(),
                **fields,
            },
        )

    def unchanged():
        for item in [
            plan["producer"],
            plan["original_selection"],
            plan["selection"],
            *plan["inputs"],
            *plan["sources"],
            binding,
        ]:
            if ref(item["path"]) != item:
                raise ValueError("Frozen source-review input changed")

    try:
        assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
        unchanged()
        assert ref(__file__) in plan["sources"]
        status("waiting-for-complete4x-source-manifest")
        manifest = Path(plan["producer"]["path"]).parent / "work/outputs/prepared4/manifest.jsonl"
        began = time.monotonic()
        while not all(
            (manifest.parent / n).exists()
            for n in ["manifest.jsonl", "errors.jsonl", "summary.json"]
        ):
            assert time.monotonic() - began < plan["maximum_wait_seconds"]
            assert alive(plan["owner"]), "Producer exited before complete4x output"
            time.sleep(15)
        reviewed = load_failure_review(
            plan["failure_review"]["path"] if plan["failure_review"] else None,
            plan["producer"],
            plan["original_selection"],
        )
        original = read(plan["original_selection"]["path"])
        prepared, failed = rows(manifest), rows(manifest.parent / "errors.jsonl")
        accepted = validate_coverage(original, {"4": prepared}, {"4": failed}, reviewed["errors"])
        assert accepted == {r["sha1_hex"] for r in read(plan["selection"]["path"])}
        summary = read(manifest.parent / "summary.json")
        assert summary["failed"] == len(reviewed["errors"]) and summary["unlicensed"] == 0
        assert sum(summary.get(k, 0) for k in ["train", "val", "test"]) == len(accepted)
        unchanged()
        status(
            "rendering-complete4x-source-thumbnails",
            sources=len(accepted),
            withheld_failures=len(failed),
        )
        spec = importlib.util.spec_from_file_location(
            "frozen_source_renderer", root / "renderer.py"
        )
        renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(renderer)
        renderer.render(
            manifest,
            Path(plan["selection"]["path"]),
            root / "content",
            reserve_gib=plan["reserve_gib"],
        )
        inventory = read(root / "content/inventory.json")
        assert inventory["count"] == plan["selected"] and not inventory["training_admission"]
        unchanged()
        status(
            "prepared-complete4x-source-thumbnails-awaiting-actual-review",
            inventory=ref(root / "content/inventory.json"),
            withheld_failure_ids=sorted(reviewed["errors"]),
        )
    except BaseException as error:
        status("failed-source-contact-queue-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    command = sub.add_parser("freeze")
    for name in ["producer", "root"]:
        command.add_argument("--" + name, type=Path, required=True)
    command.add_argument("--reserve-gib", type=int, default=548)
    command.add_argument("--failure-review", type=Path)
    command = sub.add_parser("run")
    command.add_argument("plan", type=Path)
    args = parser.parse_args()
    if args.mode == "freeze":
        print(
            json.dumps(
                freeze(
                    args.producer,
                    args.root,
                    reserve_gib=args.reserve_gib,
                    failure_review=args.failure_review,
                )
            )
        )
    else:
        run(args.plan)
