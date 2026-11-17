"""Matched CPU primary panels with unchanged historic inputs and noisy scene context."""

import argparse
import math
import os
import shutil
import time
from collections import OrderedDict, defaultdict
from pathlib import Path

import numpy as np
import psutil
import torch
from profile_raw_kernel_inference import model_hash

from demosaic.cfa import pack
from demosaic.experiments.artifacts import checked, read_json, reference, verify_plan, write_json
from demosaic.frozen_encoder_replay import FrozenDinoReplay
from demosaic.io import read_raw
from demosaic.metrics import quality_metrics
from demosaic.models import load_model
from demosaic.photo_scene import benchmark_photo_context
from demosaic.precision import ieee_fp32
from demosaic.prediction_archive import fingerprint
from demosaic.real_suite import measured_sensor_psnr
from demosaic.scene_context import SceneGrid
from demosaic.scene_inference import load_scene_checkpoint
from demosaic.scene_restoration import EncodedScene, WholeSceneRestorer
from demosaic.suite import summarize

ARGUMENTS = ["packed", "variance", "colors", "wb", "matrix"]


def numbers(metrics):
    return {
        k: [float(v) if math.isfinite(float(v)) else None for v in values]
        for k, values in metrics.items()
    }


class ContextFields:
    """Bounded RAM cache; actual noisy fields/features are saved for replay."""

    def __init__(self, plan, output, encoder_model, inherited):
        self.plan, self.output, self.encoder_model = plan, output, encoder_model
        self.output.mkdir()
        self.inventory = {
            r["id"]: r for r in read_json(checked(plan["photo_inventory"]))["sources"]
        }
        self.manifests = {
            stage: read_json(checked(plan["stages"][stage]["manifest"]))
            for stage in ["known", "unseen"]
        }
        self.saved = {r["key"]: r for r in inherited}
        self.memory, self.rgb = OrderedDict(), OrderedDict()
        self.new_scene_executions, self.RAW_decodes, self.new_surround_draws = 0, 0, 0

    def remember(self, key, value):
        self.memory[key] = value
        self.memory.move_to_end(key)
        while len(self.memory) > 4:
            self.memory.popitem(last=False)
        return value

    def source_rgb(self, source):
        identity = source["id"]
        if identity not in self.rgb:
            path = checked(source["cache"])
            array = np.load(path, allow_pickle=False)
            assert array.dtype == np.uint16 and list(array.shape) == source["source_shape"]
            self.rgb[identity] = torch.from_numpy(array.astype(np.float32)).permute(2, 0, 1) / 65535
        self.rgb.move_to_end(identity)
        while len(self.rgb) > 4:
            self.rgb.popitem(last=False)
        return self.rgb[identity]

    def saved_field(self, key):
        item = self.saved[key]
        with np.load(checked(item["arrays"]), allow_pickle=False) as data:
            packed = torch.from_numpy(data["packed"].copy())
            encoded = EncodedScene(
                tuple(torch.from_numpy(data[f"feature{i}"].copy()) for i in range(4)),
                SceneGrid(
                    *[tuple(int(n) for n in data[name]) for name in ["native", "preview", "padded"]]
                ),
            )
        return self.remember(key, (packed, encoded, item))

    def field(self, record, batch, sample):
        photo = record["stage"] == "photo"
        key = (
            f"photo-{record['batch']:05d}-{sample}"
            if photo
            else f"{record['stage']}-case{record['context']['case_index']:02d}"
        )
        if key in self.memory:
            self.memory.move_to_end(key)
            return self.memory[key]
        if key in self.saved:
            return self.saved_field(key)
        if photo:
            identity = record["context"]["ids"][sample]
            if identity in self.inventory:
                source = self.inventory[identity]
                rgb = self.source_rgb(source)
                clean = np.load(checked(record["context"]["clean_RGB"]), allow_pickle=False)
                x, y, w, h = source["legacy_cache_xywh"]
                assert torch.equal(rgb[:, y : y + h, x : x + w], torch.from_numpy(clean[sample]))
                field = benchmark_photo_context(
                    rgb,
                    source["legacy_cache_xywh"],
                    {k: batch[k][sample : sample + 1] for k in ARGUMENTS},
                    record["context"]["condition"],
                    identity=identity,
                    seed=record["context"]["seed"],
                )
                packed, box = field.packed, list(field.box_xywh)
                metadata = {
                    "source": source,
                    "origin_xy": field.source_origin_xy,
                    "surround_noise_seed": field.noise_seed,
                    "box_xywh": box,
                }
                self.new_surround_draws += 1
            else:
                assert identity.startswith("synthetic-")
                packed = batch["packed"][sample]
                metadata = {
                    "source": identity,
                    "box_xywh": [0, 0, 256, 256],
                    "scope": "The entire synthetic canvas is the canonical256 tile.",
                }
        else:
            case = self.manifests[record["stage"]]["cases"][record["context"]["case_index"]]
            source = checked({"path": case["noisy"]["path"], "sha256": case["noisy"]["sha256"]})
            assert source.is_relative_to(Path("/mnt/external"))
            raw, meta = read_raw(source)
            self.RAW_decodes += 1
            assert meta.pattern == record["context"]["pattern"]
            torch.testing.assert_close(
                torch.tensor(meta.white_balance), batch["wb"][0], atol=0, rtol=0
            )
            torch.testing.assert_close(
                torch.tensor(meta.camera_to_srgb), batch["matrix"][0], atol=0, rtol=0
            )
            packed = pack(torch.from_numpy(raw)[None, None])[0]
            metadata = {
                "source": reference(source),
                "metadata": case["metadata"],
                "scope": "Full noisy sensor capture; no independent reference input.",
            }
        encoded = self.encoder_model.encode_scene(
            packed,
            batch["colors"][sample],
            batch["wb"][sample],
            batch["matrix"][sample],
            long_side=self.plan["preview_long_side"],
            exposure=self.plan["preview_exposure"],
        )
        self.new_scene_executions += 1
        path = self.output / (key + ".npz")
        with path.open("xb") as stream:
            np.savez(
                stream,
                packed=packed.numpy(),
                **{f"feature{i}": value.numpy() for i, value in enumerate(encoded.features)},
                native=np.array(encoded.grid.native_hw),
                preview=np.array(encoded.grid.preview_hw),
                padded=np.array(encoded.grid.padded_hw),
            )
        item = {
            "key": key,
            "arrays": reference(path),
            "metadata": metadata,
            "packed_fingerprint": fingerprint(packed),
            "feature_fingerprints": [fingerprint(t) for t in encoded.features],
        }
        write_json(path.with_suffix(".json"), item)
        self.saved[key] = item
        return self.remember(key, (packed, encoded, item))

    def queries(self, record, batch):
        scenes, boxes, fields = [], [], []
        for index in range(len(batch["packed"])):
            packed, encoded, item = self.field(record, batch, index)
            box = (
                item["metadata"]["box_xywh"]
                if record["stage"] == "photo"
                else record["context"]["crop_xywh"][index]
            )
            x, y, w, h = box
            assert x % 2 == y % 2 == 0
            torch.testing.assert_close(
                packed[:, y // 2 : (y + h) // 2, x // 2 : (x + w) // 2],
                batch["packed"][index],
                atol=0,
                rtol=0,
            )
            scenes.append(encoded)
            boxes.append(box)
            fields.append(item)
        return scenes, boxes, fields


@torch.inference_mode()
def collect(plan_path, action):
    plan = read_json(plan_path)
    verify_plan(plan)
    assert reference(__file__) == plan["driver"]
    assert not torch.cuda.is_initialized()
    os.sched_setaffinity(0, plan["CPU_affinity"])
    os.nice(10)
    torch.set_num_threads(plan["CPU_threads"])
    root, output = Path(plan["root"]), Path(plan["root"]) / action
    output.mkdir()
    write_json(
        output / "owner.json",
        {
            "pid": os.getpid(),
            "create_time": psutil.Process().create_time(),
            "plan": reference(plan_path),
        },
    )
    if psutil.virtual_memory().available < 40 * 2**30:
        raise RuntimeError("CPU primary RAM admission unavailable")
    inherited, inherited_fields = {}, []
    if action == "full":
        qualified = read_json(checked(plan["preflight"]))
        assert qualified["all_complete"] and qualified["cases"] == 3
        for case in qualified["case_records"]:
            value = read_json(checked(case))
            inherited[value["stage"], value["batch"]] = value
            inherited_fields.extend(value["fields"])
    models, endpoints = {}, {}
    for arm, specification in plan["models"].items():
        binding = specification["checkpoint"]
        if specification["kind"] == "parent":
            base, payload = load_model("v120", checkpoint=checked(binding), device="cpu")
            model = WholeSceneRestorer(base, mode="none", adapter_width=32)
        else:
            model, payload = load_scene_checkpoint(
                checked(binding), weights="ema", expected_sha256=binding["sha256"]
            )
        assert payload["step"] == specification["step"]
        models[arm] = model.eval().to(memory_format=torch.contiguous_format)
        assert model_hash(model.base.context.backbone) == plan["DINO_sha256"]
        endpoints[arm] = {**specification, "weights": "EMA"}
        del payload
    for model in models.values():
        for attr in ["mean", "std"]:
            assert torch.equal(
                getattr(model.base.context, attr), getattr(models["V120"].base.context, attr)
            )
    replay = FrozenDinoReplay([m.base.context.backbone for m in models.values()])
    fields = ContextFields(plan, output / "contexts", models["spatial"], inherited_fields)
    canonical = read_json(checked(plan["canonical_inputs"]))
    selected = [
        r
        for stage in ["known", "unseen", "photo"]
        for r in canonical["records"]
        if r["stage"] == stage
    ]
    if action == "preflight":
        selected = [
            r
            for r in selected
            if (r["stage"], r["batch"]) in [("photo", 16), ("known", 0), ("unseen", 0)]
        ]
    prior_cpu = read_json(checked(plan["parent_CPU_probes"]))
    cpu_probes = {(r["stage"], r["batch"]): r for r in prior_cpu["records"]}
    case_records, metric_rows = [], defaultdict(list)
    totals = {
        "new_roots": 0,
        "local_DINO_requests": 0,
        "local_DINO_executions": 0,
        "local_DINO_replays": 0,
        "adopted_preflight_roots": 0,
        "reused_parent_CPU_predictions": 0,
    }
    began = time.monotonic()
    with ieee_fp32():
        for record in selected:
            key = record["stage"], record["batch"]
            if psutil.virtual_memory().available < 24 * 2**30:
                raise RuntimeError("CPU primary runtime RAM floor reached")
            if shutil.disk_usage(root).free < 192 * 2**30:
                raise RuntimeError("CPU primary internal disk reserve reached")
            if time.monotonic() - began > plan["maximum_seconds"]:
                raise TimeoutError("CPU primary deadline reached; no automatic retry")
            if key in inherited:
                result = inherited[key]
                totals["adopted_preflight_roots"] += result["new_root_calls"]
            else:
                with np.load(checked(record["arrays"]), allow_pickle=False) as values:
                    batch = {k: torch.from_numpy(values[k].copy()) for k in values.files}
                for name in ARGUMENTS:
                    assert fingerprint(batch[name]) == record["fingerprints"][name]
                scenes, boxes, contexts = fields.queries(record, batch)
                noise = (
                    record["context"]["condition"]
                    if key[0] == "photo"
                    else record["context"]["noise"]
                )
                variants, new_roots = [], 0
                folder = output / f"{key[0]}-{key[1]:05d}"
                folder.mkdir()
                with replay.group() as statistics:
                    for arm, model in models.items():
                        reused = arm == "V120" and key in cpu_probes
                        if reused:
                            binding = cpu_probes[key]["CPU_prediction"]
                            prediction = torch.from_numpy(
                                np.load(checked(binding), allow_pickle=False)
                            )
                            totals["reused_parent_CPU_predictions"] += 1
                        else:
                            model.base.set_noise(noise["shot"], noise["read"])
                            prediction = model(
                                *(batch[k] for k in ARGUMENTS),
                                scene=scenes if model.mode != "none" else None,
                                boxes_xywh=boxes,
                            )
                            assert torch.isfinite(prediction).all()
                            path = folder / (arm + "-RGB-f32.npy")
                            with path.open("xb") as stream:
                                np.save(stream, prediction.numpy(), allow_pickle=False)
                            binding = reference(path)
                            new_roots += 1
                        border = 8 if key[0] == "photo" else 32
                        region = (..., slice(border, -border), slice(border, -border))
                        # oneDNN's grouped Gaussian SSIM JIT fails for the saved
                        # canonical CPU layout on this host. Reference CPU
                        # convolution keeps the original metric formula intact.
                        with torch.backends.mkldnn.flags(enabled=False):
                            reference_rgb = (
                                batch["target"] if key[0] == "photo" else batch["reference_rgb"]
                            )
                            measured = quality_metrics(
                                prediction[region],
                                reference_rgb[region],
                                batch["wb"],
                                batch["matrix"],
                            )
                        if key[0] != "photo":
                            sensor, count = measured_sensor_psnr(
                                prediction[region],
                                batch["sensor_reference"][region],
                                batch["sensor_mask"][region],
                            )
                            measured = {
                                "sensor_psnr": sensor,
                                "reference_samples": count,
                                **{"ahd_" + k: v for k, v in measured.items()},
                            }
                        values = numbers(measured)
                        rows = []
                        for i, identity in enumerate(record["context"]["ids"]):
                            row = {
                                "id": identity,
                                "model": arm,
                                "pattern": record["context"]["pattern"],
                                "metrics": {k: v[i] for k, v in values.items()},
                            }
                            if key[0] == "photo":
                                row.update(
                                    kind="synthetic"
                                    if identity.startswith("synthetic-")
                                    else "photo",
                                    condition=noise["name"],
                                )
                            else:
                                row.update(
                                    scene=record["context"]["scene"],
                                    pair=record["context"]["raw_source"]["sha256"],
                                )
                            rows.append(row)
                        variants.append(
                            {
                                "arm": arm,
                                "checkpoint": endpoints[arm]["checkpoint"],
                                "prediction": binding,
                                "reused_CPU_probe": reused,
                                "rows": rows,
                            }
                        )
                assert statistics["requests"] == new_roots and statistics["executions"] == 1
                result = {
                    "stage": key[0],
                    "batch": key[1],
                    "canonical_arrays": record["arrays"],
                    "fields": contexts,
                    "boxes_xywh": boxes,
                    "variants": variants,
                    "new_root_calls": new_roots,
                    "local_frozen_DINO": dict(statistics),
                }
                path = folder / "result.json"
                write_json(path, result)
                totals["new_roots"] += new_roots
                totals["local_DINO_requests"] += statistics["requests"]
                totals["local_DINO_executions"] += statistics["executions"]
                totals["local_DINO_replays"] += statistics["replays"]
            for variant in result["variants"]:
                metric_rows[key[0]].extend(variant["rows"])
            binding = (
                next(
                    c
                    for c in qualified["case_records"]
                    if read_json(checked(c))["stage"] == key[0]
                    and read_json(checked(c))["batch"] == key[1]
                )
                if key in inherited
                else reference(output / f"{key[0]}-{key[1]:05d}" / "result.json")
            )
            case_records.append(binding)
            write_json(
                output / "progress.json",
                {
                    "completed_cases": len(case_records),
                    "total_cases": len(selected),
                    "stage": key[0],
                    "seconds": time.monotonic() - began,
                    "counts": totals,
                    "scene_DINO_executions": fields.new_scene_executions,
                },
                replace=True,
            )
            print(key[0], key[1], len(case_records), "of", len(selected), flush=True)
    summaries = {}
    for stage, rows in metric_rows.items():
        if stage == "photo":
            summaries[stage] = summarize(rows)
        else:
            groups = defaultdict(list)
            for row in rows:
                groups[row["model"], row["scene"], row["pair"], row["pattern"]].append(row)
            pairs = []
            for (arm, scene, pair, pattern), values in groups.items():
                metrics = {
                    k: [r["metrics"][k] for r in values if r["metrics"][k] is not None]
                    for k in values[0]["metrics"]
                }
                pairs.append(
                    {
                        "model": arm,
                        "id": scene,
                        "kind": "real",
                        "condition": pair,
                        "pattern": pattern,
                        "metrics": {
                            k: float(np.mean(v)) if v else None for k, v in metrics.items()
                        },
                    }
                )
            summaries[stage] = {
                "per_pair": pairs,
                **summarize(
                    pairs, comparison_metrics=("sensor_psnr", "ahd_srgb_psnr", "ahd_srgb_ssim")
                ),
            }
    assert not torch.cuda.is_initialized()
    assert all(model_hash(m.base.context.backbone) == plan["DINO_sha256"] for m in models.values())
    write_json(
        output / "result.json",
        {
            "plan": reference(plan_path),
            "action": action,
            "all_complete": True,
            "cases": len(case_records),
            "case_records": case_records,
            "models": endpoints,
            "summaries": summaries,
            "counts": totals,
            "scene_DINO_executions": fields.new_scene_executions,
            "new_surround_draws": fields.new_surround_draws,
            "RAW_decodes": fields.RAW_decodes,
            "seconds": time.monotonic() - began,
            "DINO_unchanged": True,
            "scope": "Same-CPU EMA parent and3 scene endpoints, exact historical scored inputs and targets. Native B4 retained; frozen local DINO requests checked identical and replayed, full noisy scene fields/features saved.0 GPU or optimizer work. Preflight is3 cases, not a primary score; only complete full427/known/unseen coverage is eligible. All metrics use original formulas with CPU reference SSIM convolution. Real AHD RGB is auxiliary, not exact GT. Actual native viewing/PSNR-history publication separate.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("action", choices=["preflight", "full"])
    args = parser.parse_args()
    collect(args.plan, args.action)
