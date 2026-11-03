"""Independently reopen the real paired smoke checkpoints without constructing a model."""

import argparse
from pathlib import Path

import numpy as np
import torch
from train_directional_bank_trial import guard, read, ref, save


def audit(root, phases):
    torch.set_num_threads(1)
    plan = read(root / "plan.json")
    guard(plan)
    records = []
    for phase in phases:
        controls = []
        for arm in ("V144", "V145"):
            result_path = root / f"{phase}-{arm}-result.json"
            result = read(result_path)
            assert result["phase"] == phase and result["arm"] == arm
            assert result["updates"] == result["all_AdamW_steps"] == 18
            assert result["model_EMA_Adam_finite"] and result["frozen_encoder_no_gradients"]
            assert result["changed_spatial_rate_resume_rejections"]
            assert ref(result["checkpoint"]["path"]) == result["checkpoint"]
            spatial = arm == "V145"
            states = 112 if spatial else 89
            for step in (16, 18):
                checkpoint = (
                    root / f"{phase}-{arm}-step16.pt"
                    if step == 16
                    else Path(result["checkpoint"]["path"])
                )
                state = torch.load(checkpoint, weights_only=True, map_location="cpu", mmap=True)
                assert state["step"] == step and state["config"]["steps"] == 1000
                assert state["config"]["initialized_from"] == {**plan["parent"], "step": 5000}
                assert len(state["model"]) == len(state["ema"]) == (114 if spatial else 91)
                assert sum(k.startswith("pretrained_rgb.raw_spatial.") for k in state["model"]) == (
                    23 if spatial else 0
                )
                optimizer = state["optimizer"]
                assert len(optimizer["state"]) == states
                assert all(float(s["step"]) == step for s in optimizer["state"].values())
                groups = optimizer["param_groups"]
                assert [len(g["params"]) for g in groups] == ([89, 23] if spatial else [89])
                assert [g.get("lr_multiplier", 1) for g in groups] == ([1, 100] if spatial else [1])
                np.testing.assert_allclose(
                    [g["lr"] for g in groups],
                    [1e-5 * step / 100 * m for m in ([1, 100] if spatial else [1])],
                    rtol=1e-14,
                    atol=0,
                )
                values = [*state["model"].values(), *state["ema"].values()]
                values += [
                    v
                    for s in optimizer["state"].values()
                    for v in s.values()
                    if isinstance(v, torch.Tensor)
                ]
                assert all(torch.isfinite(v).all() for v in values)
                assert len(result["gradient_maxima"]) == states
                assert all(v > 0 for v in result["gradient_maxima"].values())
                trained = Path(state["config"]["source_snapshot"])
                source = Path(plan["work"]) / "src/demosaic"
                assert all(
                    p.read_bytes() == (trained / p.name).read_bytes() for p in source.glob("*.py")
                )
                records.append(
                    {
                        "phase": phase,
                        "arm": arm,
                        "step": step,
                        "checkpoint": ref(checkpoint),
                        "EMA_tensors": len(state["ema"]),
                        "Adam_states": states,
                        "group_sizes": [len(g["params"]) for g in groups],
                        "group_rates": [g["lr"] for g in groups],
                        "finite_values": sum(v.numel() for v in values),
                    }
                )
            controls.append(result)
        a, b = controls
        assert len(a["observed_inputs"]) == len(b["observed_inputs"]) == 18
        assert all(
            all(x[k] == y[k] for k in ("step", "domain", "clean_sha256", "batch_sha256"))
            for x, y in zip(a["observed_inputs"], b["observed_inputs"], strict=True)
        )
        with (
            np.load(a["first_outputs"]["path"], allow_pickle=False) as x,
            np.load(b["first_outputs"]["path"], allow_pickle=False) as y,
        ):
            assert x.files == y.files
            assert all(np.array_equal(x[k], y[k]) for k in x.files)
    assert not torch.cuda.is_initialized()
    result = {
        "status": "passed-independent-v143-spatial-setup-state-audit",
        "training_plan": ref(root / "plan.json"),
        "phases": phases,
        "checkpoints": records,
        "initial_outputs_and_all18_batches_exact": True,
        "new_neural_forwards": 0,
        "new_optimizer_updates": 0,
        "scope": "Discarded smoke implementation states; no trained image-quality claim.",
    }
    destination = root / ("setup-state-audit-" + "-".join(phases) + "-v1.json")
    assert not destination.exists()
    save(destination, result)
    print(destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--phases", nargs="+", choices=("CPU", "CUDA"), default=["CPU", "CUDA"])
    args = parser.parse_args()
    audit(args.root.resolve(), args.phases)
