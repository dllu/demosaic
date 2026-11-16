"""Prepare, inspect and run configured experiments without trial-script imports."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from .artifacts import freeze_sources, read_json, reference, verify_plan, write_json
from .paths import repository_root, writable_output
from .runtime import RuntimePolicy


def resolve_recipe(path):
    """Normalize file paths relative to the recipe; bind every top-level input."""
    import yaml

    from .training import TrainingConfig

    path = Path(path).absolute()
    value = yaml.safe_load(path.read_text())
    if value.get("format") != "cached-head-experiment-v1":
        raise ValueError("Expected cached-head-experiment-v1 recipe")
    required = {
        "format",
        "name",
        "model",
        "cache",
        "pair_units",
        "training",
        "runtime",
        "domain_weights",
    }
    allowed = required | {"sampling_library", "evidence"}
    if not required <= value.keys() or value.keys() - allowed:
        raise ValueError("Missing or unknown recipe fields")
    model = value["model"]
    if model.keys() - {"kind", "config", "initializer", "initialization"}:
        raise ValueError("Unknown model recipe fields")
    if model.get("kind") not in (
        "pooled-wave",
        "cfa-wave",
        "scale-supported-cfa-wave",
        "orientation-balanced-cfa-wave",
    ):
        raise ValueError("Unknown cached component kind")
    if model.get("initialization", "component") not in ("component", "anchor"):
        raise ValueError("Unknown initialization mode")
    if model.get("initialization") == "anchor" and model["kind"] == "pooled-wave":
        raise ValueError("Pooled models require a full component initializer")
    inputs = [reference(path)]

    def bind(item):
        source = item["path"] if isinstance(item, dict) else item
        source = Path(source).expanduser()
        source = source if source.is_absolute() else path.parent / source
        binding = reference(source.resolve())
        if isinstance(item, dict) and binding["sha256"] != item["sha256"]:
            raise ValueError(f"Recipe input checksum differs: {source}")
        inputs.append(binding)
        return binding

    value["cache"], value["pair_units"] = bind(value["cache"]), bind(value["pair_units"])
    model["initializer"] = bind(model["initializer"])
    if value.get("sampling_library"):
        value["sampling_library"] = bind(value["sampling_library"])
    value["evidence"] = [bind(item) for item in value.get("evidence", [])]
    value["training"] = TrainingConfig(**value["training"]).to_dict()
    value["runtime"] = RuntimePolicy(**value["runtime"]).to_dict()
    import math

    if not value["domain_weights"] or any(
        not math.isfinite(weight) or weight <= 0 for weight in value["domain_weights"].values()
    ):
        raise ValueError("Domain weights must be positive and finite")
    return value, inputs


def prepare(recipe, root, *, repository=None):
    from .data.cache import CachedBatches

    spec, inputs = resolve_recipe(recipe)
    cache = CachedBatches(spec["cache"], spec["pair_units"])
    if len(cache) != spec["training"]["steps"]:
        raise ValueError("Configured LR horizon differs from cached schedule length")
    if {row["metadata"]["domain"] for row in cache.rows} - spec["domain_weights"].keys():
        raise ValueError("A cached domain has no configured weight")
    root = writable_output(root)
    if root.exists():
        raise FileExistsError(root)
    repository = Path(repository).resolve() if repository else repository_root()
    existing_parent = next(parent for parent in root.parents if parent.exists())
    RuntimePolicy(**spec["runtime"]).resources(existing_parent)
    root.mkdir(parents=True)
    work, sources = freeze_sources(repository, root)
    plan = {
        "format": "consolidated-experiment-plan-v1",
        "recipe": spec,
        "root": str(root),
        "work": str(work),
        "inputs": inputs,
        "frozen_files": sources,
        "scope": "Behavior-preserving infrastructure; no model-quality promotion.",
    }
    write_json(root / "plan.json", plan)
    return reference(root / "plan.json")


def frozen_command(root, *, resume=False, stop_after=None):
    root = Path(root).absolute()
    plan = read_json(root / "plan.json")
    verify_plan(plan)
    command = [sys.executable, "-m", "demosaic.experiments", "train", str(root)]
    if resume:
        command.append("--resume")
    if stop_after is not None:
        command += ["--stop-after", str(stop_after)]
    return command, snapshot_environment(plan), plan


def snapshot_environment(plan):
    return dict(
        os.environ,
        PYTHONPATH=str(Path(plan["work"]) / "src"),
        HF_HUB_OFFLINE="1",
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="2",
        MKL_NUM_THREADS="1",
        CUBLAS_WORKSPACE_CONFIG=":4096:8",
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("models", help="List the supported and experimental model choices")
    verification = sub.add_parser("verify-replay", help="Compare a historical CFA head checkpoint")
    verification.add_argument("original", type=Path)
    verification.add_argument("replay", type=Path)
    verification.add_argument("--output", type=Path)
    preparation = sub.add_parser("prepare", help="Bind inputs and snapshot package code")
    preparation.add_argument("recipe", type=Path)
    preparation.add_argument("output", type=Path)
    preparation.add_argument("--repository", type=Path)
    for name in ("export", "evaluate"):
        command = sub.add_parser(name)
        command.add_argument("run", type=Path)
        if name == "evaluate":
            command.add_argument("cases", type=Path, help="Checked quality-design observations")
        command.add_argument("output", type=Path)
        command.add_argument("--state", choices=("raw", "ema"), default="ema")
    for name in ("inspect", "audit-cache", "train", "launch"):
        command = sub.add_parser(name)
        command.add_argument("run", type=Path)
        if name in ("train", "launch"):
            command.add_argument("--resume", action="store_true")
            command.add_argument("--stop-after", type=int, help="Additional schedule rows")
    args = parser.parse_args(argv)
    if args.command == "models":
        from demosaic.models import model_presets

        result = model_presets()
    elif args.command == "verify-replay":
        from .verification import verify_head_replay

        result = verify_head_replay(args.original, args.replay)
        if args.output:
            write_json(writable_output(args.output), result)
    elif args.command == "prepare":
        result = prepare(args.recipe, args.output, repository=args.repository)
    else:
        args.run = args.run.absolute()
        plan = read_json(args.run / "plan.json")
        verify_plan(plan)
        if args.command in ("export", "evaluate") and not Path(__file__).resolve().is_relative_to(
            Path(plan["work"]).resolve()
        ):
            command = [sys.executable, "-m", "demosaic.experiments", args.command, str(args.run)]
            if args.command == "evaluate":
                command.append(str(args.cases.absolute()))
            command += [str(args.output.absolute()), "--state", args.state]
            os.execve(sys.executable, command, snapshot_environment(plan))
        if args.command == "export":
            from .outputs import export_endpoint

            result = export_endpoint(args.run, args.output, state=args.state)
        elif args.command == "evaluate":
            from .evaluation.runner import evaluate_cases
            from .outputs import load_endpoint

            model, plan, checkpoint, _ = load_endpoint(args.run, state=args.state)
            result = evaluate_cases(
                model,
                args.cases,
                args.output,
                checkpoint=checkpoint,
                method=plan["recipe"]["name"] + "-" + args.state,
                device=plan["recipe"]["runtime"]["device"],
            )
        elif args.command == "inspect":
            result = {
                "recipe": plan["recipe"],
                "work": plan["work"],
                "source_files": len(plan["frozen_files"]),
                "inputs_verified": True,
            }
        elif args.command == "audit-cache":
            from .data.cache import CachedBatches

            result = CachedBatches(plan["recipe"]["cache"], plan["recipe"]["pair_units"]).audit()
        else:
            command, env, plan = frozen_command(
                args.run, resume=args.resume, stop_after=args.stop_after
            )
            if args.command == "launch":
                from .runtime import owner_identity

                token = owner_identity()
                log_path = args.run / f"worker-{token['pid']}-{token['created']}.log"
                with log_path.open("xb") as log:
                    child = subprocess.Popen(
                        command,
                        env=env,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        start_new_session=True,
                    )
                result = {"pid": child.pid, "log": str(log_path)}
            elif not Path(__file__).resolve().is_relative_to(Path(plan["work"]).resolve()):
                os.execve(sys.executable, command, env)
            else:
                from .training import train

                result = train(args.run, resume=args.resume, stop_after=args.stop_after)
    print(json.dumps(result, indent=2, allow_nan=False))
