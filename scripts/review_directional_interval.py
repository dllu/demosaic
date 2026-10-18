"""Review frozen V78/V79 boundaries after their exact training owner exits."""

import argparse
import copy
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import psutil
from train_directional_interval_trial import guard, read, ref, save, sha

TERMINAL = (
    "completed-matched-directional-interval-original4000-awaiting-full-quality-and-native-review"
)


def alive(owner):
    try:
        process = psutil.Process(owner["pid"])
        return (
            process.create_time() == owner["created"] and process.status() != psutil.STATUS_ZOMBIE
        )
    except psutil.NoSuchProcess:
        return False


def require_completed(plan):
    status = read(plan["training_status"])
    if status["status"] != TERMINAL:
        raise RuntimeError(
            "Both directional-interval training boundaries must complete before review"
        )
    assert status["controller"] == plan["training_owner"]
    assert not alive(status["controller"]) and not alive(status["child"])
    assert status["all176_sampled_legacy_and_input_observations_match"]
    assert status["all161_logged_domains_and_LRs_match"]
    assert status["plan"] == plan["training_plan"]
    training_plan = read(plan["training_plan"]["path"])
    guard(training_plan)
    return status, training_plan


def boundaries(plan):
    import math

    import torch
    import yaml

    from demosaic.model import ModelConfig

    status, training_plan = require_completed(plan)
    parent = torch.load(
        training_plan["parent"]["path"], map_location="cpu", weights_only=True, mmap=True
    )
    checkpoints, logs, evidence = [], [], []
    for arm in training_plan["arms"]:
        case_ref = status["completed"][arm["name"]]
        assert case_ref == ref(case_ref["path"])
        case = read(case_ref["path"])
        assert not alive(case["owner"])
        checkpoint = case["checkpoint"]
        assert checkpoint == ref(checkpoint["path"])
        state = torch.load(checkpoint["path"], map_location="cpu", weights_only=True, mmap=True)
        cfg = yaml.safe_load(Path(arm["config"]).read_text())
        assert state["step"] == 4000 and state["config"]["steps"] == 4000
        for key, value in cfg.items():
            if key != "validation_protocol":
                assert state["config"][key] == value, key
        assert state["config"]["initialized_from"] == {**training_plan["parent"], "step": 20000}
        expected_config = ModelConfig.from_checkpoint(parent["model_config"]).to_dict()
        expected_config["raw_directional_residual"] = True
        assert ModelConfig.from_checkpoint(state["model_config"]).to_dict() == expected_config
        assert len(state["model"]) == len(state["ema"]) == 99
        assert len(state["optimizer"]["state"]) == 97
        for field in ["model", "ema"]:
            assert all(torch.isfinite(v).all() for v in state[field].values())
            unchanged = [
                k
                for k, v in state[field].items()
                if k in parent["ema"] and torch.equal(v, parent["ema"][k])
            ]
            assert sorted(unchanged) == ["context.mean", "context.std"]
        for values in state["optimizer"]["state"].values():
            assert int(values["step"]) == 4000
            assert all(torch.isfinite(v).all() for v in values.values() if torch.is_tensor(v))
        for key in ["manifest", "validation_manifest", "paired_manifest", "raw_clean_manifest"]:
            assert state["config"][key + "_sha256"] == sha(cfg[key])
        assert all(k in state for k in ["python_rng", "torch_rng", "cuda_rng"])
        rows = [
            json.loads(x)
            for x in Path(case["metrics"]["path"]).read_text().splitlines()
            if json.loads(x).get("event") == "train"
        ]
        assert [r["step"] for r in rows] == [1, *range(25, 4001, 25)]
        for row in rows:
            step = row["step"]
            progress = max(0, step - 100) / 3900
            expected_lr = (
                1e-5 * min(1, step / 100) * (0.1 + 0.9 * (1 + math.cos(math.pi * progress)) / 2)
            )
            assert row["lr"] == expected_lr
            assert math.isfinite(row["loss"]) and math.isfinite(row["grad_norm"])
        logs.append(rows)
        assert case["capture"]["initial_EMA_exact"]
        assert case["metrics"] == ref(case["metrics"]["path"])
        assert case["sampled_observations"] == ref(case["sampled_observations"]["path"])
        samples = read(case["sampled_observations"]["path"])
        assert [r["step"] for r in samples] == [*range(1, 17), *range(25, 4001, 25)]
        assert all(r["sensor_target_present"] == (r["domain"] != "paired") for r in samples)
        if arm["name"] == "control":
            control_samples = samples
        else:
            for x, y in zip(samples, control_samples, strict=True):
                assert all(
                    x[k] == y[k] for k in ["step", "domain", "legacy_batch_sha256", "input_sha256"]
                )

        checkpoints.append(
            {
                **checkpoint,
                "arm": arm["name"],
                "step": 4000,
                "kind": "joint-checkpoint",
                "label": f"V{arm['version']}-original4000",
            }
        )
        evidence.append(
            {
                "arm": arm["name"],
                "source_sha256": state["config"]["source_sha256"],
                "finite_states": [99, 99, 97],
                "all89_common_trainable_model_and_EMA_tensors_changed": True,
                "result": case_ref,
                "initialization": case["capture"],
            }
        )
    for a, b in zip(*logs, strict=True):
        assert all(a[k] == b[k] for k in ["step", "domain", "lr"])
    assert evidence[0]["source_sha256"] == evidence[1]["source_sha256"]
    save(
        Path(plan["root"]) / "training-boundary.json",
        {
            "status": "independently-verified-both-directional-interval-original4000-boundaries",
            "training_status": ref(plan["training_status"]),
            "checkpoints": checkpoints,
            "evidence": evidence,
            "all176_sampled_legacy_and_input_observations_match": True,
            "all161_logged_domains_and_LRs_match": True,
            "scope": "Full-state engineering boundary only; no quality claim or continuation.",
        },
    )


def gfx(plan, checkpoints, output):
    import numpy as np
    import torch
    from PIL import Image
    from profile_raw_kernel_inference import model_hash

    from demosaic.inference import load_checkpoint
    from demosaic.precision import amp_context
    from demosaic.reporting import display_crop, save_triplet

    fixture = read(plan["gfx_fixture"]["path"])
    observation = fixture["serving_probes"][0]["observation"]
    assert observation == ref(observation["path"])
    with np.load(observation["path"], allow_pickle=False) as arrays:
        cpu = {k: torch.from_numpy(arrays[k].copy()) for k in arrays.files}
    args = [cpu[k].cuda() for k in ["packed", "variance", "colors", "wb", "matrix"]]
    parent_report = Path(plan["parent_gfx_report"]["path"])
    parent_crops = [
        c for c in read(parent_report)["native_crops"] if c["model_label"] == "V63:original-FP32"
    ]
    assert len(parent_crops) == 4
    output.mkdir(parents=True, exist_ok=False)
    crops, predictions = [], []
    for crop in parent_crops:
        source = parent_report.parent / crop["image"]
        assert sha(source) == crop["png_sha256"]
        shutil.copyfile(source, output / source.name)
        crops.append(copy.deepcopy(crop))
    for checkpoint in checkpoints:
        model, state = load_checkpoint(checkpoint["path"], "cuda")
        del state
        model.eval().to(memory_format=torch.channels_last)
        before = model_hash(model)
        model.set_noise(fixture["conditioning"]["shot"], fixture["conditioning"]["read"])
        with amp_context("cuda", dtype="float32"):
            prediction = model(*args).cpu()
        assert prediction.shape == (4, 3, 512, 512) and torch.isfinite(prediction).all()
        assert before == model_hash(model)
        array = output / (checkpoint["arm"] + "-four-context-RGB-f32.npy")
        np.save(array, prediction.numpy(), allow_pickle=False)
        predictions.append(ref(array))
        for i, template in enumerate(parent_crops):
            region = fixture["gfx_regions"][i]
            assert template["region"] == region["region"]
            roi = [
                region["region"]["noisy_xy"][0] - region["context_xywh"][0],
                region["region"]["noisy_xy"][1] - region["context_xywh"][1],
                160,
                160,
            ]
            source_image = np.asarray(Image.open(parent_report.parent / template["image"]))

            def panel(index, template=template, source_image=source_image):
                x, y, w, h = template["panels"][index]["png_xywh"]
                return source_image[y : y + h, x : x + w].astype(np.float64) / 255

            metadata = {
                k: copy.deepcopy(v)
                for k, v in template.items()
                if k
                not in (
                    "image",
                    "caption",
                    "panels",
                    "png_sha256",
                    "pixel_scale",
                    "display_encoding",
                    "model_label",
                    "model",
                    "checkpoint_sha256",
                    "runtime",
                )
            }
            metadata.update(
                model_label=checkpoint["label"],
                checkpoint_sha256=checkpoint["sha256"],
                model={**checkpoint, "compute_policy": {"benchmark": False}, "RGB": ref(array)},
                context_xywh=region["context_xywh"],
            )
            restored = display_crop(
                prediction[i : i + 1],
                cpu["wb"][i : i + 1],
                cpu["matrix"][i : i + 1],
                roi,
                exposure=4,
            )
            crops.append(
                save_triplet(
                    output,
                    checkpoint["label"] + ":" + template["region"]["name"],
                    [
                        ("Noisy (Malvar)", panel(0)),
                        ("Denoised", restored),
                        ("ISO100 ref (not GT)", panel(2)),
                    ],
                    caption=template["region"]["name"] + " / " + checkpoint["label"],
                    metadata=metadata,
                )
            )
        del model
        torch.cuda.empty_cache()
    save(
        output / "report.json",
        {
            "native_crops": crops,
            "predictions": predictions,
            "scope": "Same four native512 GFX contexts, B4 IEEE FP32, no training/warping. "
            "V63 original panels reused by exact PNG bytes, new model states unchanged. "
            "Independent ISO100/f5.6 reference is not GT. No full-frame/time claim.",
        },
    )


def statistics(plan, checkpoints):
    from audit_fresh_dino_statistics import audit_photo, audit_real
    from compare_long_commons_scores import compare_pair, descriptor, rows
    from review_packed_isotropic_trial import reference_descriptor

    audits, comparisons, sources, witnesses = {}, [], [], []
    for panel, filename in [
        ("known", "per-crop.jsonl"),
        ("unseen", "per-crop.jsonl"),
        ("full427", "per-image.jsonl"),
    ]:
        output = Path(plan["outputs"][panel])
        audits[panel] = (
            audit_photo(output, 6)
            if panel == "full427"
            else audit_real(
                output,
                4 if panel == "known" else 5,
                8 if panel == "known" else 10,
                72 if panel == "known" else 90,
                6,
                require_rawnind=False,
            )
        )
        summary, records = read(output / "summary.json"), rows(output / filename)
        current = [
            descriptor(
                c["label"],
                c["sha256"],
                output / "summary.json",
                output / filename,
                summary,
                records,
            )
            for c in checkpoints
        ]
        old = Path(plan["historical_panels"][panel])
        old_summary, old_rows = read(old / "summary.json"), rows(old / filename)
        retained = [
            descriptor(
                r["label"],
                r["sha256"],
                output / "summary.json",
                output / filename,
                summary,
                records,
            )
            if r["sha256"] == plan["parent"]["sha256"]
            else descriptor(
                r["label"], r["sha256"], old / "summary.json", old / filename, old_summary, old_rows
            )
            for r in plan["historical_models"]
        ]
        for gain, label in [("CFA-LS", "RawNIND-global"), ("CFA-channel", "RawNIND-channel")]:
            model_label = (
                "RawNIND:" + gain
                if panel == "full427"
                else "RawNIND:" + ("cfa-ls" if gain == "CFA-LS" else "cfa-channel") + ":publisher"
            )
            retained.append(
                reference_descriptor(
                    label,
                    plan["rawnind_sha256"],
                    model_label,
                    old / "summary.json",
                    old / filename,
                    old_summary,
                    old_rows,
                )
            )
        pairs = [(current[1], current[0])] + [(c, r) for c in current for r in retained]
        for first, second in pairs:
            values, source, witness = compare_pair(panel, first, second)
            comparisons.extend(values)
            sources.append(source)
            witnesses.append(witness)
    save(
        Path(plan["root"]) / "primary-statistics.json",
        {
            "status": "completed-directional-interval-primary-numerical-review-awaiting-native-and-color-review",
            "audits": audits,
            "comparisons": comparisons,
            "sources": sources,
            "witnesses": witnesses,
            "scope": "Fresh three-model FP32 primary panels including the actual V63 parent; historical V43/RawNIND scores "
            "reused only after exact protocol/coverage/nullable support and existing4-ULP classical "
            "control witnesses. Source bootstrap is not training-seed uncertainty. No promotion.",
        },
    )


def worker(plan_path, stage):
    guard_plan = read(plan_path)
    guard(guard_plan)
    require_completed(guard_plan)
    root, plan = Path(guard_plan["root"]), guard_plan
    with (root / (stage + ".claim")).open("x") as stream:
        stream.write(str(os.getpid()))
    import torch

    if stage == "boundary":
        boundaries(plan)
        return
    checkpoints = read(root / "training-boundary.json")["checkpoints"]
    paths = [Path(c["path"]) for c in checkpoints]
    if stage in ("known", "unseen", "full427"):
        paths.append(Path(plan["parent"]["path"]))
    if stage == "statistics":
        statistics(plan, checkpoints)
        return
    if stage == "sensitivity":
        from audit_commons_source_sensitivity import audit
        from report_commons_source_sensitivity import run

        stats = root / "primary-statistics.json"
        cohort = Path(plan["cohorts"]["path"])
        output = Path(plan["outputs"][stage])
        run(stats, sha(stats), cohort, plan["cohorts"]["sha256"], output)
        save(output / "independent-audit.json", audit(output))
        return
    if stage == "highlights":
        from evaluate_gfx_highlight_inputs import main

        main(
            Path(plan["highlight_inputs"]["path"]),
            Path(plan["highlight_audit"]["path"]),
            paths + [Path(plan["parent"]["path"])],
            Path(plan["outputs"][stage]),
        )
        return
    assert psutil.virtual_memory().available > 40 * 2**30
    assert shutil.disk_usage(root).free > 128 * 2**30
    torch.set_num_threads(4)
    device = torch.device("cuda", torch.cuda.current_device())
    fraction = min(
        torch.cuda.get_per_process_memory_fraction(device),
        24 * 2**30 / torch.cuda.get_device_properties(device).total_memory,
    )
    torch.cuda.set_per_process_memory_fraction(fraction, device)
    torch.backends.cudnn.benchmark = False
    output = Path(plan["outputs"][stage])
    assert not output.exists()
    with torch.inference_mode():
        if stage in ("known", "unseen"):
            from demosaic.real_suite import evaluate_pairs

            evaluate_pairs(
                paths, Path(plan["manifests"][stage]), output, batch_size=4, precision="float32"
            )
        elif stage == "full427":
            from demosaic.suite import run_suite

            run_suite(
                paths,
                Path(plan["manifests"][stage]),
                output,
                "configs/evaluation.yaml",
                batch_size=2,
                synthetic_count=16,
                precision="float32",
            )
        elif stage == "gfx":
            gfx(plan, checkpoints, output)
        elif stage == "analytic":
            from evaluate_texture_candidates import main

            main(paths, output, precision="float32")
        elif stage == "hue":
            from evaluate_color_grid_cuda import evaluate_records

            records = [dict(c, kind="joint-checkpoint", arm=c["label"]) for c in checkpoints]
            records.append({**plan["parent"], "kind": "joint-checkpoint", "arm": "V63-parent"})
            evaluate_records(
                Path(plan["hue_inputs"]["path"]),
                Path(plan["training_status"]),
                output,
                records,
                plan["parent"]["sha256"],
                expected_step=4000,
                precision="float32",
            )
        else:
            raise ValueError(stage)
    guard(plan)


def controller(plan_path):
    plan = read(plan_path)
    guard(plan)
    root = Path(plan["root"])
    with (root / "controller.claim").open("x") as stream:
        stream.write(str(os.getpid()))
    status = {
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "plan": ref(plan_path),
        "completed": [],
    }

    def record(value, **fields):
        status.update(status=value, updated_unix=time.time(), **fields)
        save(root / "status.json", status)
        print(json.dumps({"status": value, "stage": status.get("stage")}), flush=True)

    try:
        record("waiting-for-exact-directional-interval-training-owner-exit")
        while True:
            training = read(plan["training_status"])
            assert training["controller"] == plan["training_owner"]
            if not alive(training["controller"]):
                require_completed(plan)
                break
            if training["status"].startswith("failed-"):
                raise RuntimeError("Training failed; no automatic retry")
            time.sleep(5)
        for stage in [
            "boundary",
            "known",
            "unseen",
            "full427",
            "statistics",
            "sensitivity",
            "gfx",
            "analytic",
            "hue",
            "highlights",
        ]:
            guard(plan)
            env = dict(os.environ)
            env.update(
                PYTHONPATH=os.pathsep.join(
                    [str(Path(plan["work"]) / p) for p in ["src", "scripts"]]
                ),
                HF_HOME=plan["HF_HOME"],
                HF_HUB_OFFLINE="1",
            )
            if stage in ("boundary", "statistics", "sensitivity", "highlights"):
                env["CUDA_VISIBLE_DEVICES"] = ""
            with (root / (stage + ".log")).open("xb") as log:
                child = subprocess.Popen(
                    [
                        plan["python"],
                        "-P",
                        plan["worker"]["path"],
                        "worker",
                        str(plan_path),
                        "--stage",
                        stage,
                    ],
                    cwd=plan["work"],
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                record("running-directional-interval-quality-review", stage=stage, child=owner)
                try:
                    code = child.wait(timeout=3600)
                except subprocess.TimeoutExpired:
                    import signal

                    os.killpg(child.pid, signal.SIGTERM)
                    child.wait(timeout=30)
                    raise
                assert code == 0, f"{stage} exited {code}"
            assert not alive(owner)
            status["completed"].append(stage)
            record("completed-directional-interval-review-stage", stage=stage)
        record(
            "completed-directional-interval-inference-awaiting-statistical-and-manual-native-closure"
        )
    except BaseException as error:
        record("failed-directional-interval-review-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["controller", "worker"])
    parser.add_argument("plan", type=Path)
    parser.add_argument("--stage")
    args = parser.parse_args()
    if args.mode == "controller":
        controller(args.plan)
    else:
        worker(args.plan, args.stage)
