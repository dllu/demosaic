"""Test frozen native DINO feature gradients on retained outputs and controlled detail."""

import argparse
import gc
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import psutil
from feature_probe_math import controlled_bands, gradient_projection, reference_mask
from train_directional_bank_trial import guard, read, ref, save

REPO = Path(__file__).resolve().parents[1]
SELECTED = {"bark": 4, "raccoon-fur": 0, "pixls-5002-fine": 1, "pixls-1951-field": 1}
MODEL = "facebook/dinov3-convnext-small-pretrain-lvd1689m"
REVISION = "421020015aa4266363db803b6049a529999afb1e"
ENCODER_SHA = "691963f0f796aac860d818d59d9d14287a4675612829fbe9467c7f5df8ce5b14"


def checked(binding):
    assert ref(binding["path"]) == binding
    return Path(binding["path"])


def check_supervision_arrays(binding, target):
    """NPZ key order/path can differ while every bound array remains identical."""
    with np.load(checked(binding), allow_pickle=False) as archive:
        assert set(archive.files) == set(target)
        for key, value in target.items():
            actual = archive[key]
            assert actual.dtype == value.dtype and actual.shape == value.shape
            assert actual.tobytes() == value.tobytes(), key


def prepare(root, source, gradients):
    root, source, gradients = root.resolve(), source.resolve(), gradients.resolve()
    assert root.is_relative_to(REPO / ".cache")
    original = read(source / "plan-v1.json")
    guard(original)
    collection = read(source / "collection-v1.json")
    assert (
        collection["plan"] == ref(source / "plan-v1.json")
        and collection["new_root_forwards"] == 256
    )
    rows = [json.loads(line) for line in checked(collection["archive"]).read_text().splitlines()]
    previous = read(gradients / "collection-v1.json")
    assert previous["new_neural_forwards"] == 0 and len(previous["groups"]) == 32
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    files = (
        list((REPO / "src/demosaic").glob("*.py"))
        + [
            REPO / "scripts" / name
            for name in [
                "probe_dino_feature_loss.py",
                "feature_probe_math.py",
                "train_directional_bank_trial.py",
                "profile_raw_kernel_inference.py",
            ]
        ]
        + [REPO / name for name in ["pyproject.toml", "uv.lock", "third_party/dinov3/LICENSE.md"]]
    )
    for source_file in files:
        dest = work / source_file.relative_to(REPO)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_file, dest)
    inputs = [
        ref(source / "plan-v1.json"),
        ref(source / "collection-v1.json"),
        collection["archive"],
        ref(gradients / "collection-v1.json"),
    ]
    cases, observations = [], []
    artifact = work / "artifacts/prepared"
    artifact.mkdir(parents=True)
    for case in original["cases"]:
        with np.load(checked(case["target"]), allow_pickle=False) as archive:
            data = {k: archive[k] for k in archive.files}
        target = data["target"]
        mask = reference_mask(target, data["wb"], data["matrix"], SELECTED[case["id"]])
        assert (
            int(mask.sum())
            == {"bark": 96, "raccoon-fur": 7, "pixls-5002-fine": 3, "pixls-1951-field": 9}[
                case["id"]
            ]
        )
        variants, true, wrong = controlled_bands(target, mask)
        control_file = artifact / (case["id"] + "-controls.npz")
        np.savez(control_file, mask=mask, true_band=true, orthogonal_band=wrong)
        current = {
            **case,
            "contrast_bin": SELECTED[case["id"]],
            "blocks": int(mask.sum()),
            "controls": ref(control_file),
            "baseline_gradients": {},
        }
        for label, value in variants.items():
            path = artifact / (case["id"] + "-" + label + ".npy")
            with path.open("xb") as stream:
                np.save(stream, value, allow_pickle=False)
            observations.append(
                {
                    "id": case["id"] + ":" + label,
                    "case_id": case["id"],
                    "variant": label,
                    "values": ref(path),
                }
            )
            inputs.append(ref(path))
        for method in ("V120", "V117"):
            row = next(
                r
                for r in rows
                if r["model"]["label"] == method
                and r["context"]["case_id"] == case["id"]
                and r["context"]["pattern"] == "RGGB"
                and r["context"]["draw"] == 0
            )
            group = next(
                g
                for g in previous["groups"]
                if (g["method"], g["case_id"], g["pattern"]) == (method, case["id"], "RGGB")
            )
            assert group["predictions"][0] == row["prediction"]
            check_supervision_arrays(row["supervision"], data)
            current["baseline_gradients"][method] = group["gradient"]
            observations.append(
                {
                    "id": case["id"] + ":" + method,
                    "case_id": case["id"],
                    "variant": method,
                    "values": row["prediction"],
                    "model": row["model"],
                    "original_observation": row["context"],
                }
            )
            inputs += [row["prediction"], row["supervision"], group["gradient"]]
        cases.append(current)
        inputs += [case["target"], ref(control_file)]
    assert len(observations) == 24
    fur = next(c for c in cases if c["id"] == "raccoon-fur")
    controls = np.load(fur["controls"]["path"])
    direction = controls["true_band"]
    direction *= 0.01 / np.sqrt(np.sum(direction**2) / (fur["blocks"] * 3 * 256))
    direction_file = artifact / "finite-difference-direction.npy"
    np.save(direction_file, direction)
    base = np.load(next(o for o in observations if o["id"] == "raccoon-fur:V120")["values"]["path"])
    for sign in (-1, 1):
        path = artifact / f"finite-difference-{sign}.npy"
        np.save(path, (base + sign * 0.01 * direction).astype(np.float32))
        observations.append(
            {
                "id": f"raccoon-fur:finite-difference-{sign}",
                "case_id": "raccoon-fur",
                "variant": f"finite-difference-{sign}",
                "finite_difference": sign,
                "values": ref(path),
            }
        )
        inputs.append(ref(path))
    inputs.append(ref(direction_file))
    plan = {
        "root": str(root),
        "work": str(work),
        "python": sys.executable,
        "source": ref(source / "plan-v1.json"),
        "cases": cases,
        "observations": observations,
        "backbone": {"model": MODEL, "revision": REVISION, "sha256": ENCODER_SHA},
        "selected_stage_indices": [1, 2],
        "feature_strides": [4, 8],
        "feature_loss": "Unnormalized spatial MSE per stage on same native256 rendered sRGB; ImageNet mean/std; no resize. Diagnose stages separately; no training weight selected.",
        "planned_new_encoder_forwards": 26,
        "planned_restoration_forwards": 0,
        "finite_difference": {
            "direction": ref(direction_file),
            "step": 0.01,
            "maximum_symmetric_relative_error": 0.05,
        },
        "inputs": inputs,
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "scope": "Four retained targets, RGGB/ISO12800 draw0, V120/V117 outputs reused. Fixed reference bins96/7/3/9, controlled half-amplitude/wrong-phase/equal-energy orthogonal band.26 new CPU encoder forwards including2 fixed finite differences. Zero restoration forwards/noise/RAW/optimizer/private GFX. Tests feature sensitivity/output gradients; not trained quality or GramSR reproduction. No defaults/active jobs changed; no automatic retry.",
    }
    save(root / "plan-v1.json", plan)
    guard(plan)
    return root / "plan-v1.json"


def collect(path):
    import torch
    from profile_raw_kernel_inference import model_hash
    from transformers import AutoModel

    from demosaic.color import render
    from demosaic.model import JointDemosaic

    assert os.environ["CUDA_VISIBLE_DEVICES"] == "" and not torch.cuda.is_initialized()
    plan = read(path)
    guard(plan)
    root = Path(plan["root"])
    assert Path(__file__).resolve().is_relative_to(Path(plan["work"]))
    (root / "collect.claim").open("x").close()
    os.nice(10)
    psutil.Process().cpu_affinity(psutil.Process().cpu_affinity()[:2])
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    rng = torch.random.get_rng_state().clone()

    def forbidden(*args, **kwargs):
        raise AssertionError("Feature probe must not construct or execute a restoration model")

    JointDemosaic.__init__ = JointDemosaic.forward = forbidden
    with torch.random.fork_rng(devices=[]):
        model = (
            AutoModel.from_pretrained(MODEL, revision=REVISION, local_files_only=True)
            .float()
            .eval()
            .requires_grad_(False)
        )
    assert model_hash(model) == ENCODER_SHA
    assert torch.equal(rng, torch.random.get_rng_state())
    seen, calls, current = set(), [], None
    began = time.monotonic()
    output = Path(plan["work"]) / "artifacts/collected"
    output.mkdir(parents=True, exist_ok=False)

    def before(module, args, kwargs):
        assert len(calls) < plan["planned_new_encoder_forwards"] and time.monotonic() - began < 3600
        assert psutil.virtual_memory().available > 32e9
        values = kwargs["pixel_values"]
        assert (
            values.device.type == "cpu"
            and values.dtype == torch.float32
            and values.shape == (1, 3, 256, 256)
        )
        digest = hashlib.sha256(values.detach().contiguous().numpy().tobytes()).hexdigest()
        assert digest not in seen, "Do not spend another encoder call on an identical image"
        seen.add(digest)
        calls.append({"observation_id": current, "input_sha256": digest})

    model.register_forward_pre_hook(before, with_kwargs=True)
    means = torch.tensor([0.485, 0.456, 0.406])[None, :, None, None]
    scales = torch.tensor([0.229, 0.224, 0.225])[None, :, None, None]
    references, rows = {}, []
    try:
        for observed in plan["observations"]:
            current = observed["id"]
            case = next(c for c in plan["cases"] if c["id"] == observed["case_id"])
            with np.load(checked(case["target"]), allow_pickle=False) as archive:
                data = {k: archive[k] for k in archive.files}
            values = np.load(checked(observed["values"]), allow_pickle=False)
            image = torch.from_numpy(values.copy()).requires_grad_(
                "finite_difference" not in observed
            )
            rgb = render(image, torch.from_numpy(data["wb"]), torch.from_numpy(data["matrix"]))
            hidden = model(
                pixel_values=(rgb - means) / scales, output_hidden_states=True
            ).hidden_states
            features = [hidden[k] for k in plan["selected_stage_indices"]]
            if observed["variant"] == "reference":
                references[case["id"]] = [f.detach().clone() for f in features]
            losses = [
                (f - t).square().mean()
                for f, t in zip(features, references[case["id"]], strict=True)
            ]
            grads = (
                [
                    torch.autograd.grad(loss, image, retain_graph=i == 0)[0].detach().numpy()
                    for i, loss in enumerate(losses)
                ]
                if image.requires_grad
                else []
            )
            assert all(np.isfinite(g).all() for g in grads)
            if observed["variant"] == "reference":
                assert all(loss.item() == 0 for loss in losses) and all(not g.any() for g in grads)
            artifact = output / (current.replace(":", "-") + ".npz")
            with artifact.open("xb") as stream:
                np.savez(
                    stream,
                    **{f"feature_{i}": f.detach().numpy() for i, f in enumerate(features)},
                    **{f"gradient_{i}": g for i, g in enumerate(grads)},
                )
            record = {
                **observed,
                "losses": [float(loss.detach()) for loss in losses],
                "artifact": ref(artifact),
                "feature_shapes": [list(f.shape) for f in features],
                "gradient_shapes": [list(g.shape) for g in grads],
            }
            rows.append(record)
            save(
                root / "progress-v1.json",
                {
                    "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
                    "encoder_forwards": len(calls),
                    "last": current,
                    "status": "collecting-frozen-feature-probe",
                },
            )
            print(
                json.dumps({"encoder_call": len(calls), "id": current, "losses": record["losses"]}),
                flush=True,
            )
            del hidden, features, losses, grads, image, rgb
            gc.collect()
        assert len(calls) == 26 and model_hash(model) == ENCODER_SHA
        assert all(p.grad is None and not p.requires_grad for p in model.parameters())
        assert torch.equal(rng, torch.random.get_rng_state()) and not torch.cuda.is_initialized()
        guard(plan)
        save(
            root / "collection-v1.json",
            {
                "status": "completed26-new-CPU-feature-encoder-forwards",
                "plan": ref(path),
                "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
                "records": rows,
                "encoder_calls": calls,
                "new_encoder_forwards": 26,
                "new_restoration_forwards": 0,
                "model_hash_before_after": ENCODER_SHA,
                "frozen_parameter_gradients_absent": True,
                "Torch_RNG_unchanged": True,
                "CUDA_initialized": False,
                "new_noise_observations": 0,
                "RAW_decodes": 0,
                "optimizer_updates": 0,
            },
        )
    except BaseException as error:
        save(
            root / "failure-v1.json",
            {
                "status": "failed-preserved-no-automatic-retry",
                "error": repr(error),
                "spent_new_encoder_forwards": len(calls),
                "completed_records": rows,
            },
        )
        raise


def analyze(path):
    plan = read(path)
    guard(plan)
    root = Path(plan["root"])
    collected = read(root / "collection-v1.json")
    assert collected["plan"] == ref(path) and collected["new_encoder_forwards"] == 26
    rows = []
    for record in collected["records"]:
        case = next(c for c in plan["cases"] if c["id"] == record["case_id"])
        with np.load(checked(case["target"]), allow_pickle=False) as data:
            target = data["target"]
        mask = np.load(checked(case["controls"]))["mask"]
        values = np.load(checked(record["values"]), allow_pickle=False)
        with np.load(checked(record["artifact"]), allow_pickle=False) as data:
            for stage in range(len(record["gradient_shapes"])):
                rows.append(
                    {
                        "case": case["id"],
                        "variant": record["variant"],
                        "objective": f"DINO-stride{plan['feature_strides'][stage]}-MSE",
                        "feature_loss": record["losses"][stage],
                        **gradient_projection(data[f"gradient_{stage}"], values, target, mask),
                    }
                )
    for case in plan["cases"]:
        with np.load(checked(case["target"])) as data:
            target = data["target"]
        mask = np.load(checked(case["controls"]))["mask"]
        for method, binding in case["baseline_gradients"].items():
            grad = np.asarray(np.load(checked(binding), mmap_mode="r")[:, 0], np.float64).sum(0)[
                None
            ]
            original = next(
                r
                for r in collected["records"]
                if r["case_id"] == case["id"] and r["variant"] == method
            )
            prediction = np.load(checked(original["values"]))
            rows.append(
                {
                    "case": case["id"],
                    "variant": method,
                    "objective": "existing-reconstruction",
                    **gradient_projection(grad, prediction, target, mask),
                }
            )
    direction = np.load(checked(plan["finite_difference"]["direction"]))
    base = next(r for r in collected["records"] if r["id"] == "raccoon-fur:V120")
    minus, plus = [
        next(r for r in collected["records"] if r.get("finite_difference") == sign)
        for sign in (-1, 1)
    ]
    fd = []
    with np.load(checked(base["artifact"])) as data:
        for stage in range(2):
            derivative = float(np.sum(data[f"gradient_{stage}"].astype(np.float64) * direction))
            numeric = (plus["losses"][stage] - minus["losses"][stage]) / (
                2 * plan["finite_difference"]["step"]
            )
            relative = abs(derivative - numeric) / (abs(derivative) + abs(numeric) + 1e-8)
            fd.append(
                {
                    "stage": stage,
                    "autograd_directional_derivative": derivative,
                    "central_difference": numeric,
                    "symmetric_relative_error": relative,
                    "passes_declared_tolerance": relative
                    <= plan["finite_difference"]["maximum_symmetric_relative_error"],
                }
            )
    save(
        root / "analysis-v1.json",
        {
            "status": "feature-sensitivity-scored-awaiting-independent-and-native-review",
            "plan": ref(path),
            "collection": ref(root / "collection-v1.json"),
            "rows": rows,
            "finite_differences": fd,
            "new_encoder_forwards_in_analysis": 0,
            "new_restoration_forwards": 0,
            "new_noise_observations": 0,
            "scope": plan["scope"],
        },
    )
    print({"rows": len(rows), "finite_difference_checks": fd})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "collect", "analyze"])
    parser.add_argument("path", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--gradients", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path, args.source, args.gradients))
    elif args.mode == "collect":
        collect(args.path.resolve())
    else:
        analyze(args.path.resolve())
