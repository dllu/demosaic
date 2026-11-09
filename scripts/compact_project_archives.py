"""Extend the historical compactor to inactive, project-owned external archives.

The original compactor and its historical receipts stay unchanged. A required
sidecar binds this policy, the original engine, and the complete hashed plan.
All paths and bytes survive; consolidated copies become read-only. Copy shared
artifacts to a new writable inode before changing them or resuming training.
"""

import argparse
import os
from pathlib import Path

import compact_historical_cache as engine

REPO = Path(__file__).resolve().parents[1]
EXTERNAL = Path("/mnt/external/demosaic")
SUFFIXES = engine.SUFFIXES | {".pth", ".tif", ".jpg", ".jpeg"}
SUFFIXES |= {value.upper() for value in SUFFIXES}


def checked_root(value):
    path = Path(os.path.abspath(value))
    cache = REPO / ".cache"
    local = path.is_relative_to(cache) and path != cache
    external = path.is_relative_to(EXTERNAL)
    if not (local or external):
        raise ValueError("Select explicit .cache subdirectories or /mnt/external/demosaic")
    if local and path.relative_to(cache).parts[0].startswith("gfx-"):
        raise ValueError("Protected GFX photo caches are excluded")
    if path.resolve() != path or not path.is_dir():
        raise ValueError(f"Root must be a real directory without symlink ancestors: {path}")
    return path


def policy_path(plan):
    return Path(str(plan) + ".policy.json")


def binding(path):
    return {"path": str(Path(path).resolve()), "sha256": engine.sha(path)}


def plan(args):
    if policy_path(args.output).exists():
        raise FileExistsError(policy_path(args.output))
    engine.plan(args)
    engine.save(
        policy_path(args.output),
        {
            "status": "bound-inactive-project-archive-policy",
            "adapter": binding(__file__),
            "engine": binding(engine.__file__),
            "plan": binding(args.output),
            "suffixes": sorted(SUFFIXES),
            "roots": [str(checked_root(value)) for value in args.root],
            "external_scope": str(EXTERNAL),
            "protected_GFX_caches_excluded": True,
        },
    )


def apply(args):
    policy = engine.read(policy_path(args.plan))
    assert policy["status"] == "bound-inactive-project-archive-policy"
    assert policy["adapter"] == binding(__file__)
    assert policy["engine"] == binding(engine.__file__)
    assert policy["plan"] == binding(args.plan)
    assert policy["suffixes"] == sorted(SUFFIXES)
    assert policy["roots"] == engine.read(args.plan)["roots"]
    engine.apply(args)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prepare = sub.add_parser("plan")
    prepare.add_argument("--root", action="append", required=True)
    prepare.add_argument("--age-days", type=float, default=2)
    prepare.add_argument("--output", type=Path, required=True)
    execute = sub.add_parser("apply")
    execute.add_argument("--plan", type=Path, required=True)
    execute.add_argument("--journal", type=Path, required=True)
    execute.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "plan" and args.age_days < 2:
        parser.error("Archive compaction requires at least two days of inactivity")
    engine.checked_root = checked_root
    engine.SUFFIXES = SUFFIXES
    (plan if args.action == "plan" else apply)(args)


if __name__ == "__main__":
    main()
