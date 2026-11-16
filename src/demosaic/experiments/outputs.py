"""Load a committed run endpoint and export portable historical component tensors."""

from pathlib import Path

import torch

from demosaic.models.wave import legacy_state_dict

from .artifacts import checked, read_json, reference, verify_plan
from .checkpoints import restore_checkpoint, save_torch, trainable_parameters
from .paths import writable_output
from .runtime import RuntimePolicy
from .training import initialize_model


def load_endpoint(root, *, state="ema"):
    if state not in ("raw", "ema"):
        raise ValueError("Choose raw or ema")
    root = Path(root)
    plan = read_json(root / "plan.json")
    verify_plan(plan)
    result = read_json(root / "result.json")
    if result["plan"] != reference(root / "plan.json") or result["status"] != "completed":
        raise ValueError("Endpoint requires a completed run bound to this plan")
    spec = plan["recipe"]
    policy = RuntimePolicy(**spec["runtime"])
    policy.resources(root)
    policy.apply()
    if spec.get("sampling_library"):
        torch.ops.load_library(str(checked(spec["sampling_library"])))
    model = initialize_model(spec["model"]).to(policy.device)
    _, ema, payload = restore_checkpoint(
        checked(result["checkpoint"]),
        model,
        plan=result["plan"],
        lr=spec["training"]["lr"],
        weight_decay=spec["training"]["weight_decay"],
    )
    if state == "ema":
        with torch.no_grad():
            for name, parameter in trainable_parameters(model).items():
                parameter.copy_(ema[name])
    model.eval()
    return model, plan, result["checkpoint"], payload


def export_endpoint(root, path, *, state="ema"):
    model, plan, checkpoint, payload = load_endpoint(root, state=state)
    path = writable_output(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    value = {
        "format": "composed-wave-component-v1",
        "kind": plan["recipe"]["model"]["kind"],
        "module_config": plan["recipe"]["model"].get("config", {}),
        "state_dict": {n: v.detach().cpu() for n, v in legacy_state_dict(model).items()},
        "state": state,
        "source_checkpoint": checkpoint,
        "step": payload["row"]["step"],
        "updates": payload["updates"],
        "plan": reference(Path(root) / "plan.json"),
    }
    save_torch(path, value)
    return reference(path)
