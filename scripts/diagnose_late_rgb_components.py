"""Fixed late-head/shared-trunk decomposition; no training or policy export."""

import argparse
import datetime
import hashlib
import os
import shutil
from pathlib import Path

import numpy as np
import psutil
import torch
from late_rgb_component_tools import INPUTS, capture_forward, component_outputs
from profile_raw_kernel_inference import model_hash
from train_directional_bank_trial import guard, read, ref, save

from demosaic.inference import load_checkpoint
from demosaic.precision import amp_context


def parameters_unchanged(model, identities):
    assert identities == {k: id(v) for k, v in model.named_parameters()}


def input_hash(arguments):
    digest = hashlib.sha256()
    for name, value in arguments.items():
        digest.update(name.encode() + str(value.dtype).encode() + str(tuple(value.shape)).encode())
        digest.update(value.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def readiness(plan, cpu):
    guard(plan)
    if cpu:
        assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    else:
        from queue_tf32x3_cuda import alive

        assert all(not alive(o) for o in plan["blocking_owners"])
        proof = read(Path(plan["CPU_output"]) / "receipt.json")
        assert proof["plan"] == ref(plan["path"])
        assert proof["status"] == "completed-genuine-CPU-late-RGB-component-capture-preflight"
        assert proof["all_full_tail_head_replays_exact"] and proof["all_states_and_RNG_unchanged"]
        assert not proof["CUDA_initialized"]
        assert not alive(proof["owner"])
        assert ref(proof["driver"]["path"]) == proof["driver"]
        for record in proof["arrays"]:
            assert ref(record["path"]) == record
    assert psutil.virtual_memory().available >= (40 if cpu else 48) * 2**30
    assert shutil.disk_usage(plan["root"]).free >= 500 * 2**30
    assert shutil.disk_usage("/home/dllu/proj/demosaic").free >= 64 * 2**30


def cpu_case(fixture):
    """Small geometry-only engineering input; never used for quality metrics."""
    return {
        k: v[:1, ..., :32, :40]
        if k in ("packed", "variance")
        else v[:1, ..., :64, :80]
        if k == "target"
        else v[:1]
        for k, v in fixture.items()
    }


@torch.inference_mode()
def run(plan_path, *, cpu=False):
    plan_path = Path(plan_path).resolve()
    plan = read(plan_path)
    assert ref(__file__) == plan["worker"] and plan["path"] == str(plan_path)
    assert not torch.cuda.is_initialized()
    readiness(plan, cpu)
    torch.set_num_threads(2 if cpu else 4)
    device = torch.device("cpu" if cpu else "cuda")
    if not cpu:
        total = torch.cuda.get_device_properties(device).total_memory
        torch.cuda.set_per_process_memory_fraction(min(16 * 2**30 / total, 1))
        torch.backends.cudnn.benchmark = True
        torch.backends.cudnn.benchmark_limit = 10
    output = Path(plan["CPU_output"] if cpu else plan["GPU_output"])
    output.mkdir(exist_ok=False)
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    records, captures, state_checks = [], [], []
    fixtures = plan["fixtures"]
    if cpu:
        fixtures = [
            next(f for f in fixtures if f["condition"]["name"] == name)
            for name in ["adc-only", "iso12800-prior"]
        ]
    forwards = 0

    def status(value, **kwargs):
        save(
            output / "status.json",
            {
                "status": value,
                "owner": owner,
                "plan": ref(plan_path),
                "engineering_CPU_only": cpu,
                **kwargs,
            },
        )

    try:
        status("running-late-RGB-component-capture-no-statistical-interpretation")
        for role, checkpoint in plan["checkpoints"].items():
            model, state = load_checkpoint(checkpoint["path"], device)
            assert state["loaded_sha256"] == checkpoint["sha256"]
            assert state["step"] == (20000 if role == "parent" else 4000)
            del state
            model.eval().to(memory_format=torch.channels_last)
            assert (
                model.config.late_rgb_refinement
                == {"parent": "none", "global": "global", "spatial": "spatial"}[role]
            )
            before = model_hash(model)
            dino_hash = model_hash(model.context.backbone)
            identities = {k: id(v) for k, v in model.named_parameters()}
            rng = torch.get_rng_state().clone()
            cuda_rng = None if cpu else torch.cuda.get_rng_state().clone()
            encoder_calls = [0]

            def count_encoder(_module, _args, _output, calls=encoder_calls):
                calls[0] += 1

            handle = model.context.backbone.register_forward_hook(count_encoder)
            try:
                for index, fixture in enumerate(fixtures):
                    assert ref(fixture["arrays"]["path"]) == fixture["arrays"]
                    with np.load(fixture["arrays"]["path"], allow_pickle=False) as stored:
                        host = {k: torch.from_numpy(stored[k].copy()) for k in stored.files}
                    if cpu:
                        host = cpu_case(host)
                    args = {k: host[k].to(device) for k in INPUTS}
                    inputs_before = input_hash(args)
                    model.set_noise(fixture["condition"]["shot"], fixture["condition"]["read"])
                    calls_before = encoder_calls[0]
                    with amp_context(device, dtype="float32"):
                        plain = model(*(args[k] for k in INPUTS)) if cpu or index == 0 else None
                        forwards += int(plain is not None)
                        full, capture = capture_forward(model, args)
                        forwards += 1
                        assert encoder_calls[0] == calls_before + 1 + int(plain is not None)
                        if plain is not None:
                            assert torch.equal(plain, full), (
                                "Observational hooks changed the full output"
                            )
                        outputs = component_outputs(model, full, capture)
                        assert encoder_calls[0] == calls_before + 1 + int(plain is not None)
                    assert all(torch.isfinite(v).all() for v in outputs.values())
                    parameters_unchanged(model, identities)
                    assert input_hash(args) == inputs_before
                    path = output / f"{role}-{fixture['id']}-RGB-f32.npz"
                    np.savez(path, **{k: v.float().cpu().numpy() for k, v in outputs.items()})
                    records.append(
                        {
                            "model": role,
                            "checkpoint": checkpoint,
                            "fixture_id": fixture["id"],
                            "fixture": fixture["arrays"],
                            "cases": fixture["cases"][:1] if cpu else fixture["cases"],
                            "policies": list(outputs),
                            "arrays": ref(path),
                            "actual_physical_tail_replay_exact": None if capture is None else True,
                            "direct_head_replay_exact": None if capture is None else True,
                            "no_extra_trunk_or_DINO_for_component_variants": True,
                            "measurement_input_sha256_before_after": inputs_before,
                        }
                    )
                    if not cpu and capture is not None:
                        for j, case in enumerate(fixture["cases"]):
                            selected = (
                                case["pattern"] == "RGGB"
                                and case["draw"] == 0
                                and (
                                    fixture["kind"] == "flat"
                                    or [
                                        case["level"],
                                        case["contrast"],
                                        case["period"],
                                        fixture["condition"]["name"],
                                    ]
                                    in plan["capture_cases"]
                                )
                            )
                            if selected:
                                values = {
                                    "prediction": capture["head_arguments"][0],
                                    "decoder_features": capture["head_arguments"][1],
                                    "condition": capture["head_arguments"][2],
                                    "normalized_output": capture["normalized_output"],
                                    "offset": capture["offset"],
                                    "span": capture["span"],
                                }
                                values.update(
                                    {
                                        f"DINO{i}": v
                                        for i, v in enumerate(capture["head_arguments"][3])
                                    }
                                )
                                path = output / f"{role}-{fixture['id']}-head-inputs-f32.npz"
                                np.savez(path, **{k: v.cpu().numpy() for k, v in values.items()})
                                captures.append(
                                    {
                                        "model": role,
                                        "fixture_id": fixture["id"],
                                        "selected_case": case,
                                        "complete_batch_cases": fixture["cases"],
                                        "arrays": ref(path),
                                        "source_strides": {
                                            k: list(v.stride()) for k, v in values.items()
                                        },
                                    }
                                )
                    assert torch.equal(rng, torch.get_rng_state())
                    assert cpu or torch.equal(cuda_rng, torch.cuda.get_rng_state())
                    if not cpu:
                        assert psutil.virtual_memory().available >= 24 * 2**30
                        assert shutil.disk_usage(plan["root"]).free >= 500 * 2**30
                    del args, full, capture, outputs, plain
                assert model_hash(model) == before
                state_checks.append(
                    {
                        "model": role,
                        "state_sha256_before_after": before,
                        "DINO_state_sha256": dino_hash,
                        "parameters_and_CPU_CUDA_RNG_unchanged": True,
                        "DINO_encoder_calls": encoder_calls[0],
                    }
                )
            finally:
                handle.remove()
            del model
            if not cpu:
                torch.cuda.empty_cache()
        guard(plan)
        assert forwards == (12 if cpu else 75)
        assert len(captures) == (0 if cpu else 10)
        assert len({s["DINO_state_sha256"] for s in state_checks}) == 1
        receipt = {
            "status": "completed-genuine-CPU-late-RGB-component-capture-preflight"
            if cpu
            else "completed-frozen-GPU-late-RGB-component-arrays-awaiting-native-and-scalar-review",
            "owner": owner,
            "plan": ref(plan_path),
            "driver": ref(__file__),
            "observed_UTC": datetime.datetime.now(datetime.UTC).isoformat(),
            "engineering_CPU_only": cpu,
            "CUDA_initialized": torch.cuda.is_initialized(),
            "arrays": [r["arrays"] for r in records],
            "records": records,
            "head_input_captures": captures,
            "models": state_checks,
            "common_trunk_and_DINO_forwards": forwards,
            "all_full_tail_head_replays_exact": True,
            "all_states_and_RNG_unchanged": True,
            "scope": plan["scope"],
            "native_viewing_complete": False,
            "new_component_metrics_interpreted": False,
            "model_or_default_changed": False,
        }
        save(output / "receipt.json", receipt)
        status(receipt["status"], receipt=ref(output / "receipt.json"))
    except BaseException as error:
        status("failed-late-RGB-component-capture-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()
    run(args.plan, cpu=args.cpu)
