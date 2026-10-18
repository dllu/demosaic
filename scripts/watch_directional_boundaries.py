"""Retain atomic training boundaries and audit states without model inference."""

import argparse
import json
import os
import time
from pathlib import Path

import psutil
import torch
from close_camera_supervision_review import alive, read, ref, save
from train_directional_interval_trial import guard

PREFIX = "pretrained_rgb.raw_directional."
TERMINAL = (
    "completed-matched-directional-interval-original4000-awaiting-full-quality-and-native-review"
)


def audit(path, arm, plan):
    state = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
    step, cfg = state["step"], state["config"]
    assert step in (1000, 2000, 3000, 4000) and cfg["steps"] == 4000
    assert len(state["model"]) == len(state["ema"]) == 99
    assert len(state["optimizer"]["state"]) == 97
    assert state["model_config"]["raw_directional_residual"] is True
    assert cfg["initialized_from"] == {**plan["parent"], "step": 20000}
    assert cfg["camera_supervision"] == "sensor-valid-v1"
    assert cfg["reference_interval_weight"] == arm["reference_interval_weight"]
    assert cfg["manifest_sha256"] == plan["training_manifest_sha256"]
    for field in ("model", "ema"):
        assert all(torch.isfinite(v).all() for v in state[field].values())
    # The frozen recipe trains every restoration parameter except the two
    # context normalization buffers. make_optimizer keeps named-parameter
    # order within common and directional groups; check every saved shape.
    names = [n for n in state["model"] if n not in ("context.mean", "context.std")]
    ordered = [
        [n for n in names if not n.startswith(PREFIX)],
        [n for n in names if n.startswith(PREFIX)],
    ]
    assert list(map(len, ordered)) == [89, 8]
    groups = state["optimizer"]["param_groups"]
    assert [g["lr_multiplier"] for g in groups] == [1, 20]
    assert groups[1]["lr"] == groups[0]["lr"] * 20
    branch = []
    for group, names in zip(groups, ordered, strict=True):
        for index, name in zip(group["params"], names, strict=True):
            item, value = state["optimizer"]["state"][index], state["model"][name]
            assert int(item["step"]) == step
            assert item["exp_avg"].shape == item["exp_avg_sq"].shape == value.shape
            assert (
                torch.isfinite(item["exp_avg"]).all() and torch.isfinite(item["exp_avg_sq"]).all()
            )
            assert (item["exp_avg_sq"] >= 0).all()
            if name.startswith(PREFIX):
                branch.append(
                    {
                        "name": name,
                        "parameters": value.numel(),
                        "parameter_nonzero": int(value.count_nonzero()),
                        "first_moment_nonzero": int(item["exp_avg"].count_nonzero()),
                        "second_moment_nonzero": int(item["exp_avg_sq"].count_nonzero()),
                    }
                )
    assert len(branch) == 8 and sum(r["parameters"] for r in branch) == 25800
    assert all(k in state for k in ("torch_rng", "python_rng", "cuda_rng", "best"))
    return {
        "step": step,
        "arm": arm["name"],
        "checkpoint": ref(path),
        "source_sha256": cfg["source_sha256"],
        "finite_states": {"model": 99, "EMA": 99, "AdamW": 97},
        "directional_parameters": branch,
        "all_eight_directional_moments_nonzero": all(
            r["first_moment_nonzero"] and r["second_moment_nonzero"] for r in branch
        ),
        "scope": "State/optimizer engineering audit only; no forward, validation-score review or quality decision.",
    }


def main(plan_path, output):
    os.nice(10)
    torch.set_num_threads(2)
    assert not torch.cuda.is_available() and not torch.cuda.is_initialized(), "Hide CUDA"
    plan = read(plan_path)
    guard(plan)
    output = Path(output).absolute()
    output.mkdir(parents=True, exist_ok=False)
    status_path = Path(plan["root"]) / "status.json"
    owner = read(status_path)["controller"]
    assert alive(owner)
    status = {
        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "training_owner": owner,
        "training_plan": ref(plan_path),
        "driver": ref(__file__),
        "boundaries": {},
        "status": "watching-exact-directional-training-boundaries",
    }
    started, inodes = time.monotonic(), {}
    try:
        while True:
            training = read(status_path)
            assert training["controller"] == owner
            for arm in plan["arms"]:
                source = Path(arm["run"]) / "last.pt"
                if not source.exists() or inodes.get(arm["name"]) == source.stat().st_ino:
                    continue
                candidate = output / ("." + arm["name"] + "-candidate.pt")
                # save_checkpoint writes a separate .tmp and atomically replaces
                # last.pt. This hard link keeps its old inode without copying or
                # modifying training output, even when the next boundary saves.
                os.link(source, candidate)
                inode = candidate.stat().st_ino
                state = torch.load(candidate, map_location="cpu", weights_only=True, mmap=True)
                step = state["step"]
                del state
                target = output / f"{arm['name']}-step{step}.pt"
                assert step in (1000, 2000, 3000, 4000) and not target.exists()
                candidate.rename(target)
                result = audit(target, arm, plan)
                assert target.stat().st_ino == inode
                save(output / f"{arm['name']}-step{step}.json", result)
                status["boundaries"][f"{arm['name']}-{step}"] = ref(
                    output / f"{arm['name']}-step{step}.json"
                )
                inodes[arm["name"]] = inode
                save(output / "status.json", status)
                print(
                    json.dumps(
                        {
                            "arm": arm["name"],
                            "step": step,
                            "all_eight_moments_nonzero": result[
                                "all_eight_directional_moments_nonzero"
                            ],
                        }
                    ),
                    flush=True,
                )
            if training["status"].startswith("failed-"):
                raise RuntimeError("Training failed; retained existing boundaries, no retry")
            if not alive(owner):
                assert training["status"] == TERMINAL and len(status["boundaries"]) == 8
                guard(plan)
                status["status"] = (
                    "completed-eight-directional-training-boundaries-no-quality-claim"
                )
                save(output / "status.json", status)
                break
            assert time.monotonic() - started < 21700
            time.sleep(5)
    except BaseException as error:
        status.update(status="failed-boundary-audit-no-training-intervention", error=repr(error))
        save(output / "status.json", status)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.plan, args.output)
