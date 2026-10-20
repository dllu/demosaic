"""Paired-policy quality data flow; one model and one observation per comparison."""

import copy
import json
import random
from pathlib import Path

import numpy as np
import torch
from mature_precision_tools import precision_policy
from profile_raw_kernel_inference import model_hash
from train_directional_bank_trial import read, ref

from demosaic.cfa import color_indices, malvar, pack
from demosaic.data import CleanDataset, synthetic
from demosaic.metrics import quality_metrics
from demosaic.real_suite import measured_sensor_psnr
from demosaic.reporting import display_crop, save_triplet
from demosaic.suite import observation
from demosaic.train import batch_fingerprint

KEYS = ("packed", "variance", "colors", "wb", "matrix")
POLICIES = ("fp32", "fp16-hidden")


def numbers(values, index):
    return {k: float(v[index]) if torch.isfinite(v[index]) else None for k, v in values.items()}


def save_new(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def photo_dataset(options):
    selected = set(options["source_ids"])
    records = [
        json.loads(line) for line in Path(options["manifest"]["path"]).read_text().splitlines()
    ]
    records = [r for r in records if r["id"] in selected]
    return CleanDataset(
        options["manifest"]["path"],
        split="val",
        patch_size=options["size"],
        native_crop=True,
        records=records,
    )


def load_arrays(item):
    if ref(item["path"]) != item:
        raise ValueError("Observation input checksum differs")
    with np.load(item["path"], allow_pickle=False) as data:
        return {k: torch.from_numpy(data[k].copy()) for k in data.files}


def physical_rows(first, second):
    delta = second.double() - first.double()
    return [
        {
            "RGB_values": x.numel(),
            "max_abs_DN16": float(x.abs().max()) * 65535,
            "RMS_DN16": float(x.square().mean().sqrt()) * 65535,
        }
        for x in delta
    ]


def case_gates(kind, baseline, candidate):
    """Prospective per-case limits; retain every failure without early stopping."""
    if kind in ("photo", "synthetic", "camera"):
        limits = {"srgb_psnr": 0.05, "srgb_ssim": 0.0001}
        if kind in ("photo", "synthetic"):
            limits["linear_psnr"] = 0.05
        else:
            limits = {"sensor_psnr": 0.05, "ahd_srgb_psnr": 0.05, "ahd_srgb_ssim": 0.0001}
        if any(baseline[k] is None or candidate[k] is None for k in limits):
            raise ValueError("Missing noninferiority metric")
        return {k: candidate[k] >= baseline[k] - limit for k, limit in limits.items()}
    if kind == "carrier":
        return {"signed_gain": candidate["in_phase_gain"] >= baseline["in_phase_gain"] - 0.05}
    if kind == "flat":
        return {
            "spatial_luma_RMS": candidate["spatial_luma_rms"] <= 1.25 * baseline["spatial_luma_rms"]
        }
    if kind == "hue":
        return {
            "channel_mean_error_increase_at_most_one_DN16": max(
                map(abs, candidate["camera_RGB_mean_error"])
            )
            <= max(map(abs, baseline["camera_RGB_mean_error"])) + 1 / 65535,
            "centered_camera_RMS_at_most_1.25x": candidate["spatially_centered_camera_RGB_RMS"]
            <= 1.25 * baseline["spatially_centered_camera_RGB_RMS"],
        }
    raise ValueError("Unknown paired quality gate kind")


class PairRunner:
    def __init__(self, model, label, checkpoint, device, *, engineering=False):
        self.model, self.label, self.checkpoint = model, label, checkpoint
        self.device, self.engineering = torch.device(device), engineering
        self.before = model_hash(model)
        self.dino = model_hash(model.context.backbone)
        self.config = copy.deepcopy(model.config.to_dict())
        self.identities = [id(p) for p in model.parameters()]
        self.rng = (
            torch.get_rng_state().clone(),
            random.getstate(),
            [r.clone() for r in torch.cuda.get_rng_state_all()]
            if self.device.type == "cuda"
            else [],
        )
        self.forwards, self.observations, self.encoder_calls = 0, 0, 0
        self.boundary_calls, self.expected_args = 0, None
        self.hook = model.context.backbone.register_forward_hook(self.encoder_called)
        self.boundary_hook = model.register_forward_pre_hook(self.forward_boundary)

    def forward_boundary(self, _module, args):
        if len(args) != 5 or any(a is not b for a, b in zip(args, self.expected_args, strict=True)):
            raise ValueError("Predictor boundary differs from the five physical arguments")
        self.boundary_calls += 1

    def encoder_called(self, *_):
        self.encoder_calls += 1

    @torch.inference_mode()
    def __call__(self, host, condition):
        # Only these five physical fields reach the predictor. Targets/masks stay outside.
        source_digest = batch_fingerprint(host)
        actual = {k: host[k].to(self.device) for k in KEYS}
        for k in ("packed", "variance"):
            if self.device.type == "cuda":
                actual[k] = actual[k].contiguous(memory_format=torch.channels_last)
        digest = batch_fingerprint(actual)
        self.expected_args = tuple(actual[k] for k in KEYS)
        self.model.set_noise(condition["shot"], condition["read"])
        result = {}
        order = POLICIES if self.forwards % 4 == 0 else tuple(reversed(POLICIES))
        for policy in order:
            with precision_policy(self.model, policy, self.device, cpu_probe=self.engineering):
                value = self.model(*(actual[k] for k in KEYS))
            if value.dtype != torch.float32 or not torch.isfinite(value).all():
                raise ValueError("Expected finite physical FP32 output")
            expected = (
                len(actual["packed"]),
                3,
                actual["packed"].shape[-2] * 2,
                actual["packed"].shape[-1] * 2,
            )
            if tuple(value.shape) != expected:
                raise ValueError("Native output shape differs")
            result[policy] = value.cpu()
            self.forwards += 1
            self.observations += len(value)
        if (
            batch_fingerprint(actual) != digest
            or batch_fingerprint(host) != source_digest
            or self.model.config.to_dict() != self.config
        ):
            raise ValueError("Policy forward changed observation or original config")
        if self.model.pretrained_rgb.network.hidden_autocast:
            raise ValueError("Hidden flag was not restored")
        return result, digest

    def metadata(self, policy):
        return {
            "label": self.label + ":" + policy,
            "sha256": self.checkpoint["sha256"],
            "checkpoint": self.checkpoint,
            "policy": policy,
            "compute_precision": "IEEE FP32"
            if policy == "fp32"
            else "FP16 neural, hidden branch FP16; physical FP32",
            "original_model_config": self.config,
        }

    def finish(self):
        self.hook.remove()
        self.boundary_hook.remove()
        self.expected_args = None
        if (
            model_hash(self.model) != self.before
            or model_hash(self.model.context.backbone) != self.dino
        ):
            raise ValueError("Learned tensor state changed")
        if (
            self.model.config.to_dict() != self.config
            or [id(p) for p in self.model.parameters()] != self.identities
        ):
            raise ValueError("Model config/parameter identities changed")
        if not torch.equal(torch.get_rng_state(), self.rng[0]) or random.getstate() != self.rng[1]:
            raise ValueError("CPU/Python RNG changed")
        if self.device.type == "cuda" and any(
            not torch.equal(a, b)
            for a, b in zip(self.rng[2], torch.cuda.get_rng_state_all(), strict=True)
        ):
            raise ValueError("CUDA RNG changed")
        if self.encoder_calls != self.forwards or self.boundary_calls != self.forwards:
            raise ValueError("Expected one actual frozen encoder call per forward")
        return {
            "model": self.label,
            "checkpoint": self.checkpoint,
            "model_sha256": self.before,
            "DINO_sha256": self.dino,
            "actual_forwards": self.forwards,
            "policy_observations": self.observations,
            "encoder_calls": self.encoder_calls,
            "five_physical_argument_boundaries": self.boundary_calls,
            "original_state_config_parameters_RNG_exact": True,
        }


def native_pair(
    runner,
    output,
    key,
    predictions,
    host,
    metadata,
    *,
    roi,
    reference="GT (synthetic)",
    reference_rgb=None,
    exposure=1,
    model_metadata=None,
):
    cpu = {k: v.cpu() for k, v in host.items()}
    noisy = malvar(cpu["packed"], cpu["colors"], cpu["wb"])
    target = cpu["target"] if reference_rgb is None else reference_rgb.cpu()
    noisy_view = display_crop(noisy, cpu["wb"], cpu["matrix"], roi, exposure=exposure)
    target_roi = [0, 0, 160, 160] if target.shape[-2:] == (160, 160) else roi
    target_view = display_crop(target, cpu["wb"], cpu["matrix"], target_roi, exposure=exposure)
    crops = []
    for policy in POLICIES:
        model = {**runner.metadata(policy), **(model_metadata or {})}
        crops.append(
            save_triplet(
                output,
                key + ":" + model["label"],
                [
                    ("Noisy (Malvar)", noisy_view),
                    (
                        "Denoised",
                        display_crop(
                            predictions[policy], cpu["wb"], cpu["matrix"], roi, exposure=exposure
                        ),
                    ),
                    (reference, target_view),
                ],
                caption=key + " / " + model["label"],
                metadata={
                    **metadata,
                    "model": model,
                    "model_label": model["label"],
                    "checkpoint_sha256": runner.checkpoint["sha256"],
                    "display_exposure": exposure,
                },
            )
        )
    return crops


def photo_panel(runner, plan, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    opts = plan["photo"]
    data = photo_dataset(opts)
    entries = [("photo", data.rows[i]["id"], i) for i in range(opts["images"])]
    if [x[1] for x in entries] != opts["source_ids"][: opts["images"]]:
        raise ValueError("Frozen photo membership/order differs")
    entries += [("synthetic", f"synthetic-{i}", i) for i in range(opts["synthetic"])]
    rows, crops, observations = [], [], []
    selected = {x[1] for x in entries[:2]}
    for start in range(0, len(entries), opts["batch"]):
        batch = entries[start : start + opts["batch"]]
        rgb = torch.stack(
            [
                data[i]["rgb"]
                if kind == "photo"
                else synthetic(opts["size"], random.Random(1_000_000 + i))
                for kind, _, i in batch
            ]
        ).to(runner.device)
        for condition in opts["conditions"]:
            for pattern in opts["patterns"]:
                host = observation(
                    rgb,
                    [x[1] for x in batch],
                    condition,
                    pattern,
                    opts["wb"],
                    opts["matrix"],
                    opts["seed"],
                )
                pred, digest = runner(host, condition)
                trim = (
                    ...,
                    slice(opts["border"], -opts["border"]),
                    slice(opts["border"], -opts["border"]),
                )
                truth, wb, matrix = (host[k].cpu() for k in ("target", "wb", "matrix"))
                scores = {
                    p: quality_metrics(
                        pred[p][trim],
                        truth[trim],
                        wb,
                        matrix,
                    )
                    for p in POLICIES
                }
                differences = physical_rows(pred["fp32"], pred["fp16-hidden"])
                for j, (kind, identity, source_index) in enumerate(batch):
                    values = {p: numbers(scores[p], j) for p in POLICIES}
                    rows.append(
                        {
                            "kind": kind,
                            "id": identity,
                            "condition": condition["name"],
                            "pattern": pattern,
                            "metrics": values,
                            "physical": differences[j],
                            "input_sha256": digest,
                        }
                    )
                    if (
                        not runner.engineering
                        and identity in selected
                        and condition["name"] == "iso12800-prior"
                        and pattern == "RGGB"
                    ):
                        sliced = {k: v[j : j + 1] for k, v in host.items()}
                        arrays_path = output / (identity[:12] + "-observation.npz")
                        np.savez(arrays_path, **{k: v.cpu().numpy() for k, v in sliced.items()})
                        observations.append(ref(arrays_path))
                        metadata = {
                            "source_id": identity,
                            "source": data.rows[source_index],
                            "validation_index": source_index,
                            "validation_seed": data.seed,
                            "evaluation_tile_xywh": [48, 48, 160, 160],
                            "condition": condition,
                            "pattern": pattern,
                            "white_balance": opts["wb"],
                            "camera_to_srgb": opts["matrix"],
                            "reference": "Exact synthetic clean target",
                            "measurement_and_target_sha256": batch_fingerprint(sliced),
                        }
                        crops += native_pair(
                            runner,
                            output,
                            identity,
                            {p: v[j : j + 1] for p, v in pred.items()},
                            sliced,
                            metadata,
                            roi=[48, 48, 160, 160],
                            model_metadata={"observation": ref(arrays_path)},
                        )
        print(
            json.dumps(
                {
                    "stage": "photo",
                    "model": runner.label,
                    "sources_done": min(start + opts["batch"], len(entries)),
                }
            ),
            flush=True,
        )
    expected = len(entries) * len(opts["conditions"]) * len(opts["patterns"])
    if len(rows) != expected:
        raise ValueError("Photo coverage differs")
    with (output / "per-case.jsonl").open("x") as stream:
        for row in rows:
            stream.write(json.dumps(row, allow_nan=False) + "\n")
    save_new(
        output / "report.json",
        {
            "status": "completed-paired-photo-policy-inference-awaiting-native-and-scalar-review",
            "physical_observations": len(rows),
            "native_crops": crops,
            "saved_observations": observations,
            "model": runner.label,
            "checkpoint": runner.checkpoint,
            "settings": opts,
            "engineering_only": runner.engineering,
        },
    )


def camera_panel(runner, manifest, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    data = read(manifest["path"])
    prepared = Path(manifest["path"])
    high = {}
    for case in data["cases"]:
        if case["scene"] not in high or (case["metadata"].get("iso") or 0) > (
            high[case["scene"]]["metadata"].get("iso") or 0
        ):
            high[case["scene"]] = case
    chosen = set(sorted(high)[:2])
    rows, crops = [], []
    for case in data["cases"]:
        meta, condition = case["metadata"], case["conditioning"]
        for start in range(0, len(case["crops"]), 4):
            current = case["crops"][start : start + 4]
            batches = [
                load_arrays(
                    {"path": str((prepared.parent / c["path"]).resolve()), "sha256": c["sha256"]}
                )
                for c in current
            ]
            tensors = {
                k: torch.stack([b[k] for b in batches])
                for k in ("raw", "reference_rgb", "sensor_reference", "sensor_mask")
            }
            packed = pack(tensors["raw"][:, None])
            host = {
                "packed": packed,
                "variance": packed.clamp_min(0) * condition["shot"] + condition["read"],
                "colors": color_indices(meta["pattern"])[None].expand(len(current), -1),
                "wb": torch.tensor(meta["white_balance"], dtype=torch.float32)[None].expand(
                    len(current), -1
                ),
                "matrix": torch.tensor(meta["camera_to_srgb"], dtype=torch.float32)[None].expand(
                    len(current), -1, -1
                ),
                "target": tensors["reference_rgb"],
                "sensor_reference": tensors["sensor_reference"],
                "sensor_mask": tensors["sensor_mask"],
            }
            pred, digest = runner(host, condition)
            scores = {}
            region = (..., slice(32, -32), slice(32, -32))
            for policy in POLICIES:
                score, n = measured_sensor_psnr(
                    pred[policy][region],
                    tensors["sensor_reference"][region],
                    tensors["sensor_mask"][region],
                )
                auxiliary = quality_metrics(
                    pred[policy][region],
                    tensors["reference_rgb"][region],
                    host["wb"],
                    host["matrix"],
                )
                scores[policy] = {
                    "sensor_psnr": score,
                    "reference_samples": n,
                    **{"ahd_" + k: v for k, v in auxiliary.items() if k.startswith("srgb_")},
                }
            differences = physical_rows(pred["fp32"], pred["fp16-hidden"])
            for j, crop in enumerate(current):
                rows.append(
                    {
                        "scene": case["scene"],
                        "pair": case["noisy"]["sha256"],
                        "tile_id": crop["id"],
                        "kind": "camera",
                        "pattern": meta["pattern"],
                        "metrics": {p: numbers(v, j) for p, v in scores.items()},
                        "physical": differences[j],
                        "input_sha256": digest,
                    }
                )
                if (
                    case["scene"] in chosen
                    and case is high[case["scene"]]
                    and start + j == len(case["crops"]) // 2
                ):
                    sliced = {k: v[j : j + 1] for k, v in host.items()}
                    metadata = {
                        "scene": case["scene"],
                        "conditioning": condition,
                        "white_balance": meta["white_balance"],
                        "camera_to_srgb": meta["camera_to_srgb"],
                        "noisy_sha256": case["noisy"]["sha256"],
                        "prepared_crop": crop,
                        "evaluation_tile_xywh": [176, 176, 160, 160],
                        "variance_multiplier": 1,
                        "reference": "Registered low-noise RAW, auxiliary LibRaw AHD RGB; primary scores use measured CFA",
                    }
                    crops += native_pair(
                        runner,
                        output,
                        crop["id"],
                        {p: v[j : j + 1] for p, v in pred.items()},
                        sliced,
                        metadata,
                        roi=[176, 176, 160, 160],
                        reference="AHD reference",
                    )
        print(
            json.dumps({"stage": "camera", "model": runner.label, "scene": case["scene"]}),
            flush=True,
        )
    if len(rows) != sum(len(c["crops"]) for c in data["cases"]):
        raise ValueError("Camera coverage differs")
    save_new(
        output / "report.json",
        {
            "status": "completed-paired-camera-policy-inference-awaiting-native-and-scalar-review",
            "rows": rows,
            "native_crops": crops,
            "manifest": manifest,
            "checkpoint": runner.checkpoint,
            "reference": "AHD is not exact GT; primary scores use measured CFA",
        },
    )
