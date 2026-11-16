"""Queue a new component on the three immutable fresh-noise edge caches."""

import argparse
import copy
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.experiments.checkpoints import state_hash
from demosaic.experiments.cli import snapshot_environment
from demosaic.experiments.evaluation.edge_response import measure
from demosaic.experiments.evaluation.native import load_native, write_native
from demosaic.experiments.runtime import RuntimePolicy, exclusive_run, owner_identity, owner_live
from demosaic.models.compat import load_component
from demosaic.models.wave import readout_state_prefix
from demosaic.prediction_archive import fingerprint


def prepare(root, review):
    owner = read_json(review / "owner.json")
    if not owner_live(owner) and not (review / "result.json").exists():
        raise ValueError("Expected the exact live or completed main review")
    root.mkdir(parents=True, exist_ok=False)
    work, sources = freeze_sources(Path(__file__).resolve().parents[1], root, [Path(__file__).name])
    baselines = []
    for profile in ["iso6400", "iso1600", "iso400"]:
        name = (
            "near-edge-response-v1" if profile == "iso6400" else f"near-edge-response-{profile}-v1"
        )
        path = Path(".cache/experiments") / name
        baselines.append(
            {
                "profile": profile,
                "cache": reference(path / "cache.json"),
                "scores": reference(path / "scores.json"),
            }
        )
    main = read_json(review / "plan.json")
    training = read_json(checked(main["training"]))
    extension = training["recipe"]["model"]["kind"] == "complementary-cfa-wave"
    plan = {
        "root": str(root),
        "work": str(work),
        "frozen_files": sources,
        "review": str(review),
        "review_owner": owner,
        "review_plan": reference(review / "plan.json"),
        "baselines": baselines,
        "kind": training["recipe"]["model"]["kind"],
        "candidate": "complementary" if extension else "competing",
        "anchor_method": "V200-ema" if extension else "V195-ema",
        "anchor_control_gain": 1.0 if extension else 0.0,
        "baseline_states": {"raw": "ema", "ema": "ema"}
        if extension
        else {"raw": "raw", "ema": "ema"},
        "library": training["recipe"]["sampling_library"],
        "runtime": training["recipe"]["runtime"],
        "inputs": [
            reference(review / "plan.json"),
            *[b[k] for b in baselines for k in ["cache", "scores"]],
        ],
        "scope": "Wait for the exact main review; reuse all384 cached triplets across three noise profiles. No parent inference, source/noise draws or training. Actual anchor and full-forward parity checks precede interpretation.",
    }
    write_json(root / "plan.json", plan)


def progress(root, stage, **fields):
    write_json(
        root / "progress.json", dict(stage=stage, owner=owner_identity(), **fields), replace=True
    )


def run(root):
    plan = read_json(root / "plan.json")
    verify_plan(plan)
    with exclusive_run(root):
        try:
            review = Path(plan["review"])
            while not (review / "result.json").exists():
                if not owner_live(plan["review_owner"]) and not (review / "result.json").exists():
                    raise RuntimeError("Main review exited without a complete result")
                progress(root, "waiting-for-main-review", review_owner=plan["review_owner"])
                time.sleep(15)
            result = read_json(review / "result.json")
            if (
                result["status"] != "evaluated-awaiting-native-viewing"
                or result["plan"] != plan["review_plan"]
            ):
                raise ValueError("Unexpected main review completion")
            policy = RuntimePolicy(**plan["runtime"])
            policy.resources(root)
            policy.apply()
            torch.ops.load_library(str(checked(plan["library"])))
            core, raw = load_component(
                plan["kind"], checked(result["exports"]["raw"]), device="cuda"
            )
            _, ema = load_component(plan["kind"], checked(result["exports"]["ema"]), device="cpu")
            head_prefix = readout_state_prefix(core)
            for name, value in raw["state_dict"].items():
                if not name.startswith(head_prefix):
                    assert torch.equal(value, ema["state_dict"][name])
            core.eval().requires_grad_(False)
            heads = {"raw": core.readout, "ema": copy.deepcopy(core.readout)}
            heads["ema"].load_state_dict(
                {
                    n.removeprefix(head_prefix): v
                    for n, v in ema["state_dict"].items()
                    if n.startswith(head_prefix)
                },
                strict=True,
            )
            hashes = {s: state_hash(h.state_dict()) for s, h in heads.items()}
            anchor_hash = state_hash(core.anchor.state_dict())
            native = root / "native"
            native.mkdir()
            all_rows = []
            all_predictions = {}
            anchor_channels = parity_channels = 0
            cpu_rng, cuda_rng = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
            with torch.inference_mode():
                for cohort in plan["baselines"]:
                    cache = read_json(checked(cohort["cache"]))
                    baseline = read_json(checked(cohort["scores"]))
                    predictions = {}
                    for item in cache["rows"]:
                        policy.resources(root)
                        with np.load(checked(item["arrays"]), allow_pickle=False) as a:
                            arrays = dict(a)
                        assert {k: fingerprint(v) for k, v in arrays.items()} == item["inputs"]
                        parent = np.load(checked(item["parent"]), allow_pickle=False)
                        args = [
                            torch.from_numpy(arrays[k]).cuda()
                            for k in ["packed", "variance", "colors", "wb"]
                        ]
                        base = torch.from_numpy(parent).cuda()
                        _, aux = core(base, *args, return_aux=True)
                        anchor = aux["anchor_output"]
                        sigma = aux["sigma"]
                        expected = load_native(
                            baseline["native_predictions"][str(item["index"])][
                                plan.get("anchor_method", "V195-ema")
                            ]
                        )
                        np.testing.assert_array_equal(
                            anchor.cpu().numpy().view(np.uint32), expected.view(np.uint32)
                        )
                        anchor_channels += expected.size
                        saved = {}
                        for state, head in heads.items():
                            wave = head(
                                aux["cfa_context"], aux["cfa_waves"], aux["cfa_evidence"]["bin_yx"]
                            )
                            value = torch.where(
                                sigma > 0,
                                anchor + torch.where(sigma > 0, wave, torch.zeros_like(wave)),
                                anchor,
                            )
                            if item["index"] == 0:
                                core.readout = head
                                full = core(base, *args)
                                assert torch.equal(full, value)
                                parity_channels += value.numel()
                            value = value.float().cpu().numpy()
                            saved[state] = write_native(
                                native / f"{cohort['profile']}-{item['index']:04d}-{state}.json",
                                value,
                                baseline=item["parent"],
                            )
                            for gain in [0.0, 0.25, 0.5, 0.75, 1.0]:
                                delivered = expected.astype(np.float64) + gain * (
                                    value.astype(np.float64) - expected
                                )
                                all_rows.append(
                                    dict(
                                        profile=cohort["profile"],
                                        index=item["index"],
                                        source=item["metadata"]["recipe"]["source"],
                                        placement=item["metadata"]["placement"],
                                        pattern=item["metadata"]["pattern"],
                                        repeat=item["metadata"]["repeat"],
                                        method=plan.get("candidate", "competing") + "-" + state,
                                        gain_scale=gain,
                                        **measure(arrays, delivered),
                                    )
                                )
                        predictions[str(item["index"])] = saved
                        write_json(
                            native / f"{cohort['profile']}-{item['index']:04d}-bindings.json", saved
                        )
                        progress(
                            root,
                            "cached-edge-evaluation",
                            profile=cohort["profile"],
                            batches=item["index"] + 1,
                        )
                    all_predictions[cohort["profile"]] = predictions
            assert hashes == {s: state_hash(h.state_dict()) for s, h in heads.items()}
            assert anchor_hash == state_hash(core.anchor.state_dict())
            assert torch.equal(cpu_rng, torch.get_rng_state()) and torch.equal(
                cuda_rng, torch.cuda.get_rng_state()
            )
            verify_plan(plan)
            write_json(
                root / "scores.json",
                {
                    "status": "completed-three-noise-cached-edge-candidate",
                    "plan": reference(root / "plan.json"),
                    "main_review": reference(review / "result.json"),
                    "exports": result["exports"],
                    "rows": all_rows,
                    "native_predictions": all_predictions,
                    "anchor_bit_exact_RGB_channels": anchor_channels,
                    "full_forward_bit_exact_RGB_channels": parity_channels,
                    "weights_and_RNG_unchanged": True,
                    "new_parent_DINO_forwards": 0,
                    "new_source_noise_draws": 0,
                    "training_updates": 0,
                },
            )
            progress(root, "completed", scores=reference(root / "scores.json"))
        except BaseException as error:
            write_json(root / "failure.json", {"error": repr(error), "owner": owner_identity()})
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "launch", "run"])
    parser.add_argument("root", type=Path)
    parser.add_argument("--review", type=Path)
    args = parser.parse_args()
    root = args.root.absolute()
    if args.command == "prepare":
        prepare(root, args.review.absolute())
    elif args.command == "launch":
        plan = read_json(root / "plan.json")
        verify_plan(plan)
        with (root / "worker.log").open("xb") as log:
            child = subprocess.Popen(
                [
                    sys.executable,
                    str(Path(plan["work"]) / "scripts" / Path(__file__).name),
                    "run",
                    str(root),
                ],
                env=snapshot_environment(plan),
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        print({"pid": child.pid, "log": str(root / "worker.log")})
    else:
        run(root)
