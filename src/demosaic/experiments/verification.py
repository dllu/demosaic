"""Compare a compact historical CFA-head checkpoint with the shared runner."""

import torch

from .artifacts import read_json, reference
from .checkpoints import load_torch, state_hash


def require_equal(first, second, name):
    if torch.is_tensor(first):
        equal = (
            first.dtype == second.dtype
            and first.shape == second.shape
            and torch.equal(first, second)
        )
    elif isinstance(first, dict):
        equal = first.keys() == second.keys()
        if equal:
            for key in first:
                require_equal(first[key], second[key], f"{name}.{key}")
    elif isinstance(first, (list, tuple)):
        equal = type(first) is type(second) and len(first) == len(second)
        if equal:
            for index, (a, b) in enumerate(zip(first, second, strict=True)):
                require_equal(a, b, f"{name}[{index}]")
    else:
        equal = first == second
    if not equal:
        raise ValueError(f"Replay differs: {name}")


def verify_head_replay(original, replay):
    original, replay = reference(original), reference(replay)
    old, new = load_torch(original), load_torch(replay)
    if new["format"] != "cached-head-training-v1":
        raise ValueError("Expected a shared-runner checkpoint")
    for key in ("head", "ema"):
        values = new["trainable" if key == "head" else "ema"]
        translated = {"cfa_readout." + n.removeprefix("readout."): v for n, v in values.items()}
        require_equal(old[key], translated, key)
    require_equal(old["optimizer"], new["optimizer"], "Adam")
    require_equal(old["CPU_RNG"], new["rng"]["torch"], "CPU RNG")
    require_equal(old["CUDA_RNG"], new["rng"]["cuda"][0], "CUDA RNG")
    require_equal(old["step"], new["row"]["step"], "schedule row")
    require_equal(old["updates"], new["updates"], "optimizer updates")
    plan = read_json(new["plan"]["path"])
    if reference(new["plan"]["path"]) != new["plan"]:
        raise ValueError("Replay plan changed")
    require_equal(old["anchor"], plan["recipe"]["model"]["initializer"], "frozen initializer")
    return {
        "status": "pass-bit-exact-historical-CFA-head-replay",
        "original": original,
        "replay": replay,
        "rows": old["step"],
        "updates": old["updates"],
        "ADC_skips": new["skipped"],
        "head_parameters": sum(value.numel() for value in old["head"].values()),
        "head_bit_exact": True,
        "EMA_bit_exact": True,
        "Adam_bit_exact": True,
        "CPU_RNG_bit_exact": True,
        "CUDA_RNG_bit_exact": True,
        "original_head_hash": state_hash(old["head"]),
        "replay_plan": new["plan"],
        "new_parent_DINO_forwards": 0,
        "new_source_noise_draws": 0,
        "scope": "Implementation replay of a saved prefix; not a newly trained quality result.",
    }
