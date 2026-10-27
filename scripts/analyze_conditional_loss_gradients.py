"""Replay the current reconstruction objective on retained independent outputs."""

import argparse
import ast
import gc
import json
import os
import shutil
import sys
import time
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np
import psutil
from train_directional_bank_trial import guard, read, ref, save

REPO = Path(__file__).resolve().parents[1]
WEIGHTS = {"linear": 1.0, "rendered": 0.5, "gradient": 0.1, "highlight": 0.1, "sensor": 0.1}
PAIRS = list(combinations(range(8), 2))
SELECTED = {"bark": 4, "raccoon-fur": 0, "pixls-5002-fine": 1, "pixls-1951-field": 1}


def checked(binding):
    assert ref(binding["path"]) == binding
    return Path(binding["path"])


def options(epsilon=0.0003):
    return {
        "physical_fp32": True,
        "camera_supervision": "sensor-valid-v1",
        "objective": "charbonnier-v1",
        "reconstruction_charbonnier_epsilon": epsilon,
        "normalized_sensor_weight": 0,
        "multiscale_sensor_weight": 0,
        "reference_interval_weight": 0,
        "normalized_band_weight": 0,
    }


def forbid_neural_calls(*args, **kwargs):
    raise AssertionError("Loss replay cannot execute any neural module")


def prepare(root, source):
    import torch

    assert os.environ["CUDA_VISIBLE_DEVICES"] == "" and not torch.cuda.is_initialized()
    torch.nn.Module._call_impl = forbid_neural_calls
    torch.set_num_threads(2)
    rng = torch.random.get_rng_state().clone()
    root, source = root.resolve(), source.resolve()
    assert root.is_relative_to(REPO / ".cache")
    original = read(source / "plan-v1.json")
    collection = read(source / "collection-v1.json")
    assert collection["plan"] == ref(source / "plan-v1.json")
    assert collection["new_root_forwards"] == 256 and collection["alignment"]["records"] == 256
    inputs = [ref(source / "plan-v1.json"), ref(source / "collection-v1.json")]
    inputs += [collection["archive"], ref(source / "analysis-v1.json")]
    records = [json.loads(line) for line in checked(collection["archive"]).read_text().splitlines()]
    assert len(records) == 256
    for row in records:
        inputs.extend((row["prediction"], row["supervision"]))
    for item in original["observations"]:
        inputs.append(item["arrays"])
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    sources = list((REPO / "src/demosaic").glob("*.py"))
    sources += [
        Path(__file__),
        REPO / "scripts/train_directional_bank_trial.py",
        REPO / "scripts/diagnose_local_material_detail.py",
    ]
    for path in sources:
        dest = work / path.relative_to(REPO)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    supervisions, metadata = {}, []
    for case in original["cases"]:
        with np.load(checked(case["target"]), allow_pickle=False) as arrays:
            values = {k: torch.from_numpy(arrays[k]) for k in arrays.files}
        clean, wb, matrix = values["target"], values["wb"], values["matrix"]
        linear = torch.einsum("bij,bjhw->bihw", matrix, clean * wb[..., None, None]).clamp(0, 1)
        display_target = torch.einsum("bij,bjhw->bihw", torch.linalg.inv(matrix), linear)
        values.update(target=display_target / wb[..., None, None], sensor_target=clean)
        path = work / "artifacts/supervision" / (case["id"] + ".npz")
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(path, **{k: v.numpy() for k, v in values.items()})
        supervisions[case["id"]] = ref(path)
        inputs.append(case["target"])
    for method in original["methods"]:
        checkpoint = checked(method["checkpoint"])
        state = torch.load(checkpoint, map_location="cpu", weights_only=True, mmap=True)
        assert state["model_config"]["restoration_backbone"] == "pretrained-rgb"
        metadata.append(
            {
                "method": method["label"],
                "checkpoint": method["checkpoint"],
                "restoration_backbone": state["model_config"]["restoration_backbone"],
                "training_camera_supervision": state["config"].get("camera_supervision"),
                "training_epsilon": state["config"].get("reconstruction_charbonnier_epsilon"),
            }
        )
        del state
        inputs.append(method["checkpoint"])
    model_source = source / "work/src/demosaic/model.py"
    tree = ast.parse(model_source.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "JointDemosaic")
    forward = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "forward")
    branch = next(
        n
        for n in forward.body
        if isinstance(n, ast.If)
        and ast.unparse(n.test) == "self.config.restoration_backbone == 'pretrained-rgb'"
    )
    assert ast.unparse(branch.body[-1]) == (
        "return (prediction, mosaic(prediction, colors)) if auxiliary else prediction"
    )
    inputs.append(ref(model_source))
    assert torch.equal(rng, torch.random.get_rng_state()) and not torch.cuda.is_initialized()
    unique = {item["path"]: item for item in inputs}
    plan = {
        "root": str(root),
        "work": str(work),
        "source_plan": ref(source / "plan-v1.json"),
        "archive": collection["archive"],
        "cases": original["cases"],
        "methods": original["methods"],
        "model_metadata": metadata,
        "auxiliary_branch_AST": ast.dump(branch, include_attributes=False),
        "supervisions": supervisions,
        "observations": original["observations"],
        "noise": original["noise"],
        "loss_options": options(),
        "loss_weights": WEIGHTS,
        "mean_weight": 0.25,
        "draws": 8,
        "pairs": PAIRS,
        "ROI_xywh": [48, 48, 160, 160],
        "DCT_block": 16,
        "radial_band": [1 / 8, 1 / 3],
        "contrast_edges": [0, 0.02, 0.05, 0.1, 0.2, None],
        "selected_contrast_bins": SELECTED,
        "minimum_reference_band_RMS": 1e-5,
        "reference_luma_range": [0.02, 0.9],
        "planned_output_states": 32 * 36,
        "planned_component_gradient_calls": 32 * 5,
        "planned_wrapper_replays": 32 * 2,
        "new_neural_forwards": 0,
        "new_encoder_forwards": 0,
        "new_noise_observations": 0,
        "RAW_decodes": 0,
        "optimizer_updates": 0,
        "maximum_seconds": 1200,
        "minimum_available_RAM_GiB": 8,
        "runtime_internal_reserve_GiB": 96,
        "runtime_external_reserve_GiB": 208,
        "maximum_direct_gradient_relative_error": 0.001,
        "maximum_analytic_physical_gradient_relative_error": 0.00005,
        "inputs": list(unique.values()),
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "scope": (
            "Full objective output-space gradients on existing four targets/two models/four CFAs/"
            "eight independent draws. All28 pairs use the other6 draws as independent error witnesses. "
            "Finite-draw signed estimates retained; no source/seed interval or neural-training "
            "prediction. Derived reference-white display target for loss only; original clean "
            "reference and all predictions remain unchanged. Native references are estimates, not GT."
        ),
    }
    save(root / "plan-v1.json", plan)
    guard(plan)
    return root / "plan-v1.json"


def component_gradients(values, data, colors, loss_options):
    """Single-image-normalized gradients; all states share one target and masks."""
    import torch

    from demosaic.cfa import mosaic
    from demosaic.losses import reconstruction_loss

    prediction = torch.from_numpy(values.copy()).requires_grad_(True)
    size = len(prediction)
    batch = {k: torch.from_numpy(v).repeat(size, *([1] * (v.ndim - 1))) for k, v in data.items()}
    batch["colors"] = torch.from_numpy(colors).repeat(size, 1)
    loss, terms = reconstruction_loss(
        prediction, batch, mosaic(prediction, batch["colors"]), **loss_options
    )
    result = []
    for index, (name, weight) in enumerate(WEIGHTS.items()):
        gradient = torch.autograd.grad(
            weight * terms[name], prediction, retain_graph=index < len(WEIGHTS) - 1
        )[0]
        result.append((gradient * size).numpy())
    return float(loss.detach()), {k: float(v.detach()) for k, v in terms.items()}, np.stack(result)


def physical_gradient_error(values, data, colors, gradients, epsilon):
    error = values.astype(np.float64) - data["sensor_target"].astype(np.float64)
    derivative = error / np.sqrt(error**2 + epsilon**2)
    valid = (data["sensor_target"] >= 0) & (data["sensor_target"] < 0.98)
    expected = derivative * valid / max(int(valid.sum()), 1)
    linear = float(np.max(np.abs(expected - gradients[0])) / max(np.abs(expected).max(), 1e-30))
    mask = np.zeros_like(valid)
    for phase, color in enumerate(colors[0]):
        mask[:, color, phase // 2 :: 2, phase % 2 :: 2] = True
    mask &= valid
    expected = 0.1 * derivative * mask / max(int(mask.sum()), 1)
    sensor = float(np.max(np.abs(expected - gradients[4])) / max(np.abs(expected).max(), 1e-30))
    return {"linear": linear, "sensor": sensor}


def direct_wrapper_error(values, data, inputs, gradients, noise, loss_options):
    import torch

    from demosaic.cfa import mosaic
    from demosaic.noise_pairs import conditional_mean_reconstruction_loss

    batch = {k: torch.cat([torch.from_numpy(v), torch.from_numpy(v)]) for k, v in data.items()}
    for key in inputs[0]:
        batch[key] = torch.cat([torch.from_numpy(v[key]) for v in inputs])
    batch.update(
        shot=torch.full((2, 1, 1, 1), noise["shot"]),
        read=torch.full((2, 1, 1, 1), noise["read"]),
        adc_black_level=torch.full((2, 1, 1, 1), noise["black_level"]),
        adc_bit_depth=torch.full((2, 1, 1, 1), noise["ADC_bits"], dtype=torch.long),
        noise_pair_id=torch.zeros(2, dtype=torch.long),
        noise_view=torch.arange(2),
    )
    total = gradients.sum(axis=0)
    errors = {}
    for weight in (0.0, 0.25):
        prediction = torch.from_numpy(values[:2].copy()).requires_grad_(True)
        loss, _ = conditional_mean_reconstruction_loss(
            prediction, batch, mosaic(prediction, batch["colors"]), weight=weight, **loss_options
        )
        direct = (2 * torch.autograd.grad(loss, prediction)[0]).numpy()
        expected = (1 - weight) * total[:2] + weight * total[8][None]
        errors[str(weight)] = float(
            np.max(np.abs(expected - direct)) / max(np.abs(direct).max(), 1e-30)
        )
    return errors


def collect(path):
    import torch

    from demosaic.prediction_archive import iter_predictions

    plan = read(path)
    guard(plan)
    root = Path(plan["root"])
    (root / "collect.claim").open("x").close()
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "" and not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    torch.nn.Module._call_impl = forbid_neural_calls
    rng = torch.random.get_rng_state().clone()
    groups = defaultdict(dict)
    for record, prediction, _ in iter_predictions(checked(plan["archive"])):
        context = record["context"]
        key = record["model"]["label"], context["case_id"], context["pattern"]
        groups[key][context["draw"]] = record["prediction"]
    assert len(groups) == 32 and all(set(group) == set(range(8)) for group in groups.values())
    observed = {(o["case_id"], o["pattern"], o["draw"]): o for o in plan["observations"]}
    output = Path(plan["work"]) / "artifacts/gradients"
    output.mkdir(exist_ok=False)
    began, rows = time.monotonic(), []
    try:
        for (method, case, pattern), group in groups.items():
            assert time.monotonic() - began < plan["maximum_seconds"]
            assert psutil.virtual_memory().available >= plan["minimum_available_RAM_GiB"] * 2**30
            assert shutil.disk_usage(root).free >= plan["runtime_internal_reserve_GiB"] * 2**30
            assert (
                shutil.disk_usage("/mnt/external").free
                >= plan["runtime_external_reserve_GiB"] * 2**30
            )
            predictions = np.concatenate(
                [np.load(checked(group[k]), allow_pickle=False) for k in range(8)]
            )
            inputs = []
            for draw in (0, 1):
                with np.load(
                    checked(observed[(case, pattern, draw)]["arrays"]), allow_pickle=False
                ) as arrays:
                    inputs.append({k: arrays[k] for k in arrays.files})
            colors = inputs[0]["colors"]
            assert np.array_equal(colors, inputs[1]["colors"])
            means = np.stack([(predictions[i] + predictions[j]) * 0.5 for i, j in PAIRS])
            values = np.concatenate([predictions, means])
            with np.load(checked(plan["supervisions"][case]), allow_pickle=False) as arrays:
                data = {k: arrays[k] for k in arrays.files}
            loss, terms, gradients = component_gradients(values, data, colors, plan["loss_options"])
            assert np.isfinite(gradients).all()
            physical = physical_gradient_error(
                values,
                data,
                colors,
                gradients,
                plan["loss_options"]["reconstruction_charbonnier_epsilon"],
            )
            assert (
                max(physical.values()) <= plan["maximum_analytic_physical_gradient_relative_error"]
            ), physical
            direct = direct_wrapper_error(
                values, data, inputs, gradients, plan["noise"], plan["loss_options"]
            )
            assert max(direct.values()) <= plan["maximum_direct_gradient_relative_error"], direct
            target = output / f"{method}-{case}-{pattern}.npy"
            with target.open("xb") as stream:
                np.save(
                    stream, np.ascontiguousarray(gradients[..., 48:208, 48:208]), allow_pickle=False
                )
            rows.append(
                {
                    "method": method,
                    "case_id": case,
                    "pattern": pattern,
                    "predictions": [group[k] for k in range(8)],
                    "gradient": ref(target),
                    "loss_supervision": plan["supervisions"][case],
                    "loss_mean_36_states": loss,
                    "unweighted_terms_mean_36_states": terms,
                    "physical_gradient_relative_errors": physical,
                    "direct_wrapper_relative_errors": direct,
                }
            )
            del predictions, values, means, gradients
            gc.collect()
            print(
                {"completed_groups": len(rows), "method": method, "case": case, "pattern": pattern},
                flush=True,
            )
        assert torch.equal(rng, torch.random.get_rng_state()) and not torch.cuda.is_initialized()
        guard(plan)
        save(
            root / "collection-v1.json",
            {
                "plan": ref(path),
                "groups": rows,
                "output_states": len(rows) * 36,
                "component_gradient_calls": len(rows) * 5,
                "wrapper_gradient_replays": len(rows) * 2,
                "neural_module_calls_forbidden": True,
                "CUDA_initialized": False,
                "Torch_RNG_unchanged": True,
                "new_neural_forwards": 0,
                "new_encoder_forwards": 0,
                "new_noise_observations": 0,
                "RAW_decodes": 0,
                "optimizer_updates": 0,
            },
        )
    except BaseException as error:
        save(root / "collection-failure-v1.json", {"error": repr(error), "completed_groups": rows})
        raise


def analyze(path):
    from diagnose_local_material_detail import basis

    from demosaic.archive_metrics import linear_rgb
    from demosaic.conditional_gradient import gradient_projections

    plan = read(path)
    guard(plan)
    root = Path(plan["root"])
    (root / "analysis.claim").open("x").close()
    collected = read(root / "collection-v1.json")
    assert collected["plan"] == ref(path) and len(collected["groups"]) == 32
    c = basis(16)
    freq = np.arange(16) / 32
    band = (np.hypot(freq[:, None], freq[None, :]) >= 1 / 8) & (
        np.hypot(freq[:, None], freq[None, :]) < 1 / 3
    )

    def coeff(value):
        shape = value.shape[:-3]
        blocks = value.reshape(*shape, 3, 10, 16, 10, 16)
        axes = list(range(len(shape))) + [
            len(shape) + 1,
            len(shape) + 3,
            len(shape),
            len(shape) + 2,
            len(shape) + 4,
        ]
        blocks = blocks.transpose(axes).reshape(*shape, 100, 3, 16, 16)
        return (c @ blocks @ c.T)[..., band]

    rows = []
    for group in collected["groups"]:
        values = np.concatenate(
            [np.load(checked(p), allow_pickle=False) for p in group["predictions"]]
        )[..., 48:208, 48:208].astype(np.float64)
        with np.load(checked(group["loss_supervision"]), allow_pickle=False) as arrays:
            data = {k: arrays[k] for k in arrays.files}
        target = data["sensor_target"][0, :, 48:208, 48:208].astype(np.float64)
        gradients = np.load(checked(group["gradient"]), mmap_mode="r", allow_pickle=False)
        assert gradients.shape == (5, 36, 3, 160, 160)
        reference = linear_rgb(data["sensor_target"], data)[0, :, 48:208, 48:208]
        luma = np.einsum("c,chw->hw", [0.2126, 0.7152, 0.0722], reference)
        blocks = luma.reshape(10, 16, 10, 16).transpose(0, 2, 1, 3).reshape(100, 16, 16)
        luma_coeff = (c @ blocks @ c.T)[..., band]
        means = blocks.mean(axis=(-2, -1))
        rms = np.sqrt(np.sum(luma_coeff**2, axis=-1) / 256)
        valid = (
            ((reference >= 0) & (reference <= 1))
            .all(0)
            .reshape(10, 16, 10, 16)
            .transpose(0, 2, 1, 3)
            .reshape(100, 256)
            .all(1)
        )
        valid &= (means >= 0.02) & (means <= 0.9) & (rms >= 1e-5)
        contrast = rms / np.maximum(means, 1e-12)
        value_coeff, target_coeff = coeff(values), coeff(target)
        raw = np.asarray(gradients, dtype=np.float64)
        components = {name: raw[i] for i, name in enumerate(WEIGHTS)}
        components["total"] = raw.sum(axis=0)
        scopes = [{"name": "whole-ROI", "mask": None}]
        for index, (low, high) in enumerate(
            zip(plan["contrast_edges"][:-1], plan["contrast_edges"][1:], strict=True)
        ):
            mask = valid & (contrast >= low)
            if high is not None:
                mask &= contrast < high
            if mask.any():
                scopes.append({"name": f"band-contrast-{index}", "mask": mask})
        for term, gradient in components.items():
            grad_coeff = coeff(gradient)
            for scope in scopes:
                mask = scope["mask"]
                p, t, g = (
                    (values, target, gradient)
                    if mask is None
                    else (value_coeff[:, mask], target_coeff[mask], grad_coeff[:, mask])
                )
                statistics = gradient_projections(p, t, g[:8], g[8:], plan["mean_weight"])
                rows.append(
                    {
                        "method": group["method"],
                        "case_id": group["case_id"],
                        "pattern": group["pattern"],
                        "scope": scope["name"],
                        "reference_blocks": None if mask is None else int(mask.sum()),
                        "term": term,
                        **statistics,
                    }
                )
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["method"], row["case_id"], row["scope"], row["term"])].append(row)
    summaries = []
    for (method, case, scope, term), group in grouped.items():
        assert len(group) == 4 and len({g["coordinates"] for g in group}) == 1
        projections = {
            objective: {
                field: float(np.mean([r["projections"][objective][field] for r in group]))
                for field in group[0]["projections"][objective]
            }
            for objective in ("control", "mean", "mixture")
        }
        summaries.append(
            {
                "method": method,
                "case_id": case,
                "scope": scope,
                "term": term,
                "CFAs": 4,
                "reference_blocks": group[0]["reference_blocks"],
                "coordinates_per_CFA": group[0]["coordinates"],
                "projections": projections,
            }
        )
    assert "torch" not in sys.modules
    save(
        root / "analysis-v1.json",
        {
            "plan": ref(path),
            "collection": ref(root / "collection-v1.json"),
            "per_group": rows,
            "summaries": summaries,
            "new_neural_forwards": 0,
            "new_noise_observations": 0,
            "RAW_decodes": 0,
            "optimizer_updates": 0,
            "Torch_imported": False,
            "scope": plan["scope"],
        },
    )
    print(
        {"groups": len(collected["groups"]), "statistics": len(rows), "summaries": len(summaries)}
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "collect", "analyze"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path, args.source))
    elif args.mode == "collect":
        collect(args.path)
    else:
        analyze(args.path)
