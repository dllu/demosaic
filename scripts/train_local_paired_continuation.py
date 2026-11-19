"""Compare paired fine-detail reductions and stability supervision."""

import argparse
import json
import math
import random
import time
from dataclasses import replace
from itertools import product
from pathlib import Path

import numpy as np
import psutil
import torch
from profile_raw_kernel_inference import model_hash

from demosaic.cfa import PATTERNS, mosaic
from demosaic.data import camera_pair
from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.experiments.data.paired import paired_observation
from demosaic.experiments.runtime import owner_identity
from demosaic.inference import _stage_tiled_cuda
from demosaic.losses import reconstruction_loss
from demosaic.precision import amp_context, ieee_fp32
from demosaic.prediction_archive import fingerprint
from demosaic.scene_data import observe_scene, sample_scene_recipe
from demosaic.scene_inference import load_scene_checkpoint
from demosaic.scene_training_data import _attenuate_local_contrast, scene_seed

SEED = 202611191117
STABILITY_SEED = 202611191231
WIRE_RESPONSE_SEED = 202611191309
PATCH = 256
BOX = (0, 0, PATCH, PATCH)
CORE = slice(80, 176)
FORWARD_ARGS = ("packed", "variance", "colors", "wb", "matrix")
MODES = ("absolute", "paired")
STABILITY_MODES = ("mean", "repeat", "repeat-gap")
WIRE_RESPONSE_MODES = ("repeat", "wire-mean", "wire-aligned")
PROFILES = {"ISO400": (8e-5, 2.56e-8), "ISO6400": (0.00128, 6.5536e-6)}


def prepare(root, parent_audit, scene_plan, photo_panel, prior_panel):
    """Bind a fresh, balanced schedule selected without reading protected photos."""
    existing = read_json(scene_plan)
    parent = read_json(parent_audit)["checkpoint"]
    source = checked(existing["train_manifest"])
    rows = [json.loads(line) for line in source.read_text().splitlines() if line]
    validation = {
        json.loads(line)["id"]
        for line in checked(existing["development_manifest"]).read_text().splitlines()
        if line
    }
    validation.update(read_json(photo_panel)["source_averages"])
    validation.update(row["source"]["source"]["id"] for row in read_json(prior_panel)["rows"])
    assert len(rows) == 90692 and all(row["split"] == "train" for row in rows)
    assert {row["id"] for row in rows}.isdisjoint(validation)
    assert not any(
        name in json.dumps(row).upper()
        for row in rows
        for name in ("DSCF3879", "DSCF3880", "DSCF3842", "DSCF3835")
    )

    rng = random.Random(SEED)
    cells = list(product(("natural", "wire"), PROFILES, PATTERNS, ("coupled", "independent")))
    cases = cells * 16
    rng.shuffle(cases)
    root.mkdir(parents=True)
    work, frozen = freeze_sources(Path.cwd(), root, [Path(__file__).name])
    schedule = root / "schedule.json"
    write_json(
        schedule,
        [
            {"source": row, "kind": cell[0], "iso": cell[1], "pattern": cell[2], "law": cell[3]}
            for row, cell in zip(rng.sample(rows, len(cases)), cases, strict=True)
        ],
    )
    qualification = root / "qualification-schedule.json"
    used = {row["source"]["id"] for row in read_json(schedule)}
    write_json(
        qualification,
        [
            {"source": row, "kind": cell[0], "iso": cell[1], "pattern": cell[2], "law": cell[3]}
            for row, cell in zip(
                rng.sample([row for row in rows if row["id"] not in used], 8),
                [cells[i] for i in (0, 3, 8, 11, 17, 18, 25, 26)],
                strict=True,
            )
        ],
    )
    write_json(
        root / "plan.json",
        {
            "inputs": [
                reference(parent_audit),
                parent,
                reference(scene_plan),
                existing["train_manifest"],
                existing["development_manifest"],
                reference(photo_panel),
                reference(prior_panel),
                reference(schedule),
                reference(qualification),
            ],
            "frozen_files": frozen,
            "driver": reference(work / "scripts" / Path(__file__).name),
            "schedule": reference(schedule),
            "qualification_schedule": reference(qualification),
            "parent": parent,
            "DINO_sha256": existing["DINO_sha256"],
            "seed": SEED,
            "steps_per_arm": len(cases),
            "members": ["present", "absent", "flat", "ordinary"],
            "precision": "BF16 neural forward with FP32 camera paths and objectives",
            "optimizer": {"peak_lr": 8e-6, "warmup": 32, "minimum_factor": 0.15, "ema": 0.99},
            "mode_weights": {"absolute": 0.0, "paired": 0.8},
            "pair_bands_cycles_per_pixel": [[1 / 32, 1 / 8], [1 / 8, 1 / 3]],
            "scope": "Matched full local restoration continuation. One source and four native "
            "256px observations per update. Both arms train the same local trunk and "
            "context projections with frozen DINO. The paired arm adds signed linear "
            "sRGB luminance difference supervision in two bands.",
        },
    )


def prepare_redraw(root, prior):
    """Use the same clean targets, with one additional independent pair per source."""
    source = reference(prior)
    previous = read_json(checked(source))
    if previous.get("pair_draws", 1) != 1 or previous["members"] != [
        "present",
        "absent",
        "flat",
        "ordinary",
    ]:
        raise ValueError("Redraw training requires the single-pair continuation plan")
    for binding in previous["inputs"]:
        checked(binding)
    root.mkdir(parents=True)
    work, frozen = freeze_sources(Path.cwd(), root, [Path(__file__).name])
    write_json(
        root / "plan.json",
        previous
        | {
            "inputs": [source, *previous["inputs"]],
            "frozen_files": frozen,
            "driver": reference(work / "scripts" / Path(__file__).name),
            "pair_draws": 2,
            "members": [
                "present",
                "absent",
                "present-redraw",
                "absent-redraw",
                "flat",
                "ordinary",
            ],
            "mode_weights": {"individual": 0.8, "mean": 0.8},
            "scope": "Fixed two-draw comparison. Both arms optimize the same per-observation "
            "absolute reconstruction on all six observations. The individual arm averages the "
            "signed pair band losses across draws. The mean arm computes the same band loss on "
            "the average signed increment. Each restoration uses a single captured observation.",
        },
    )


def prepare_objective_trial(root, completed_path, scene_path, *, wire_response):
    completed = read_json(completed_path)
    previous = read_json(checked(completed["plan"]))
    scene = read_json(scene_path)
    prior_modes = STABILITY_MODES if wire_response else ("individual", "mean")
    if (
        completed["qualification"]
        or completed["updates_per_arm"] != previous["steps_per_arm"]
        or tuple(previous["mode_weights"]) != prior_modes
        or completed["pair_draws_per_source"] != 2
        or completed["parent"] != previous["parent"]
        or scene["train_manifest"] not in previous["inputs"]
        or scene["DINO_sha256"] != previous["DINO_sha256"]
    ):
        raise ValueError("Expected a completed matched parent trial and its source corpus")
    parent_arm = "repeat" if wire_response else "mean"
    parent = completed["checkpoints"][parent_arm]
    for binding in [parent, *previous["inputs"]]:
        checked(binding)
    ancestors = [previous]
    if wire_response:
        earlier = read_json(checked(previous["parent_completion"]))
        assert earlier["checkpoints"]["mean"] == previous["parent"]
        ancestors.append(read_json(checked(earlier["plan"])))
    excluded = {
        case["source"]["id"]
        for plan in ancestors
        for key in ("schedule", "qualification_schedule")
        for case in read_json(checked(plan[key]))
    }
    rows = [
        json.loads(line)
        for line in checked(scene["train_manifest"]).read_text().splitlines()
        if line
    ]
    assert len(rows) == 90692 and all(row["split"] == "train" for row in rows)
    eligible = [row for row in rows if row["id"] not in excluded]
    seed = WIRE_RESPONSE_SEED if wire_response else STABILITY_SEED
    rng = random.Random(seed)
    cells = list(product(("natural", "wire"), PROFILES, PATTERNS, ("coupled", "independent")))
    cases = cells * 10
    rng.shuffle(cases)
    qualification_cases = [cells[i] for i in (0, 3, 8, 11, 17, 18, 25, 26)]
    sources = rng.sample(eligible, len(cases) + len(qualification_cases))

    root.mkdir(parents=True)
    work, frozen = freeze_sources(Path.cwd(), root, [Path(__file__).name])
    schedule, qualification = root / "schedule.json", root / "qualification-schedule.json"
    for path, selected, recipes in (
        (schedule, sources[: len(cases)], cases),
        (qualification, sources[len(cases) :], qualification_cases),
    ):
        write_json(
            path,
            [
                {"source": row, "kind": cell[0], "iso": cell[1], "pattern": cell[2], "law": cell[3]}
                for row, cell in zip(selected, recipes, strict=True)
            ],
        )
    objective = {
        "mode_weights": dict.fromkeys(STABILITY_MODES, 0.8),
        "repeat_weight": 0.5,
        "gap_weight": 0.8,
        "scope": "All arms share absolute and mean-first paired losses. Repeat arms penalize "
        "signed increment variability on independent Bayer pairs. Repeat-gap also supervises "
        "the absent weak-wire direction on both present draws. Single-frame inference.",
    }
    if wire_response:
        objective = {
            "mode_weights": dict.fromkeys(WIRE_RESPONSE_MODES, 0.8),
            "repeat_weight": previous["repeat_weight"],
            "gap_weight": 0.0,
            "response_weight": 1.6,
            "scope": "All arms retain the independent-pair repeat loss, absolute supervision, "
            "and the 0.8 mean-first spectral loss. On wire batches, add equal-weight mean-first "
            "supervision over the full band or along only the exact clean weak increment. "
            "All three start from the repeat EMA and use the same fresh source schedule. "
            "The extra losses use no inference inputs or operators.",
        }
    write_json(
        root / "plan.json",
        previous
        | {
            "inputs": [
                reference(completed_path),
                completed["plan"],
                parent,
                reference(scene_path),
                *previous["inputs"],
                reference(schedule),
                reference(qualification),
            ],
            "frozen_files": frozen,
            "driver": reference(work / "scripts" / Path(__file__).name),
            "schedule": reference(schedule),
            "qualification_schedule": reference(qualification),
            "parent": parent,
            "parent_arm": parent_arm,
            "parent_completion": reference(completed_path),
            "initial_step": completed["updates_per_arm"],
            "seed": seed,
            "steps_per_arm": len(cases),
        }
        | objective,
    )


def clean_crop(row, rng):
    source = checked({"path": row["cache"], "sha256": row["cache_sha256"]})
    rgb = np.load(source, mmap_mode="r", allow_pickle=False)
    assert rgb.dtype == np.uint16 and list(rgb.shape) == row["shape"]
    h, w = rgb.shape[:2]
    x, y = rng.randrange(0, w - PATCH + 1, 2), rng.randrange(0, h - PATCH + 1, 2)
    turns, mirror = rng.randrange(4), rng.randrange(2)
    crop = np.rot90(rgb[y : y + PATCH, x : x + PATCH], turns)
    if mirror:
        crop = crop[:, ::-1]
    patch = torch.from_numpy(crop.astype(np.float32)).permute(2, 0, 1).contiguous() / 65535
    return patch, {"crop_xywh": [x, y, PATCH, PATCH], "D4": [turns, mirror]}


def wire_pair(photo, rng):
    """Keep one continuous direction and a natural background in both members."""
    axis = torch.arange(PATCH) - (PATCH - 1) / 2
    y, x = torch.meshgrid(axis, axis, indexing="ij")
    angle = rng.uniform(0, math.tau)
    angles = (angle, angle + rng.uniform(0.55, 1.5))
    periods = (rng.uniform(7, 29), rng.uniform(6, 25))
    widths = (rng.uniform(0.06, 0.16), rng.uniform(0.055, 0.14))
    phases = (rng.random(), rng.random())
    strengths = (2 ** rng.uniform(-6.2, -4.9), 2 ** rng.uniform(-10, -6.5))

    def lines(theta, period, width, phase):
        u = (x * math.cos(theta) + y * math.sin(theta)) / period + phase
        return torch.exp(-0.5 * ((u - u.round()) / width).square()) - math.sqrt(math.tau) * width

    strong, weak = (lines(*args) for args in zip(angles, periods, widths, phases, strict=True))
    # Natural texture and the strong direction persist through the interruption.
    absence = 0.05 + 0.75 * photo + strengths[0] * strong
    center = (rng.uniform(-16, 16), rng.uniform(-16, 16))
    gap_axes = (rng.uniform(9, 28), rng.uniform(12, 32))
    gap_angle = rng.uniform(0, math.tau)
    dx, dy = x - center[0], y - center[1]
    c, s = math.cos(gap_angle), math.sin(gap_angle)
    radius = torch.hypot((c * dx + s * dy) / gap_axes[0], (-s * dx + c * dy) / gap_axes[1])
    gap = ((radius - 1) * 2.5).clamp(0, 1)
    border = ((105 - torch.maximum(x.abs(), y.abs())) / 28).clamp(0, 1)
    tint = torch.tensor([rng.uniform(0.4, 1.1), 1.0, rng.uniform(0.4, 1.1)])[:, None, None]
    addition = strengths[1] * weak * tint * gap * border
    assert ((addition == 0)[:, radius <= 1]).all() and addition[..., CORE, CORE].abs().max() > 0
    return (
        absence + addition,
        absence,
        {
            "angles": angles,
            "periods": periods,
            "widths": widths,
            "phases": phases,
            "strengths": strengths,
            "gap_center": center,
            "gap_axes": gap_axes,
            "gap_angle": gap_angle,
            "gap_pixels": int((radius <= 1).sum()),
            "tint": tint.flatten().tolist(),
        },
    )


def observations(case, index, *, pair_draws=1, seed=SEED):
    if pair_draws not in (1, 2):
        raise ValueError("Expected one or two complete sensor draws of the clean pair")
    rng = random.Random(scene_seed(seed, index, "content"))
    row = case["source"]
    crop, geometry = clean_crop(row, rng)
    if case["kind"] == "natural":
        contrast = 2 ** rng.uniform(-3.5, -0.7)
        present = _attenuate_local_contrast(crop, BOX, contrast)
        absent = _attenuate_local_contrast(crop, BOX, 0.0)
        geometry["contrast"] = contrast
    else:
        present, absent, geometry["wire"] = wire_pair(crop, rng)
    flat = _attenuate_local_contrast(absent, BOX, 0.0, flat_core=True)
    assert torch.equal(flat[:, CORE, CORE], flat[:, 80:81, 80:81].expand(3, 96, 96))

    shot, read = PROFILES[case["iso"]]
    jitter = 2 ** rng.uniform(-0.4, 0.4)
    common = replace(
        sample_scene_recipe(scene_seed(seed, index, "camera")),
        pattern=case["pattern"],
        black=0.03,
        shot=shot * jitter,
        read=read * jitter**2,
        exposure=2 ** rng.uniform(-2.2, 0.4),
    )
    seeds = {
        key: scene_seed(seed, index, key)
        for key in ("pair", "present", "absent", "flat", "ordinary")
    }

    def observed(rgb, key):
        return observe_scene(rgb, replace(common, noise_seed=seeds[key])).crops([BOX])

    def draw_pair(suffix):
        if case["law"] == "independent":
            return [observed(present, "present" + suffix), observed(absent, "absent" + suffix)]
        wb = torch.tensor(common.wb)[None]
        inverse = torch.tensor(common.camera_inverse)[None]
        pair_arrays, _ = paired_observation(
            present[None],
            absent[None],
            vars(common),
            [common.pattern],
            wb,
            inverse,
            seeds["pair" + suffix],
        )
        targets = torch.stack([present, absent]) * common.exposure
        clean, reference_rgb = camera_pair(
            targets,
            inverse.expand(2, 3, 3),
            wb.expand(2, 3),
            reconstruct_highlights=True,
        )
        arrays = {key: torch.from_numpy(pair_arrays[key]) for key in (*FORWARD_ARGS, "target")}
        assert torch.equal(arrays["target"], reference_rgb)
        return [arrays | {"sensor_target": clean}]

    roles = draw_pair("")
    if pair_draws == 2:
        for key in ("pair-redraw", "present-redraw", "absent-redraw"):
            seeds[key] = scene_seed(seed, index, key)
        roles.extend(draw_pair("-redraw"))
    roles.extend([observed(flat, "flat"), observed(crop, "ordinary")])
    values = {
        key: torch.cat([v[key] for v in roles])
        for key in (*FORWARD_ARGS, "target", "sensor_target")
    }
    if pair_draws == 2:
        for key in ("target", "sensor_target", "colors", "wb", "matrix"):
            assert torch.equal(values[key][:2], values[key][2:4])
    about = {
        "index": index,
        "source_id": row["id"],
        "cache_sha256": row["cache_sha256"],
        "kind": case["kind"],
        "iso": case["iso"],
        "law": case["law"],
        "camera": vars(common),
        "seeds": seeds,
        "geometry": geometry,
        "arrays": {k: fingerprint(v) for k, v in values.items()},
    }
    return values, about


class PairedBands:
    """Parseval-normalized signed band error on the central native 96px."""

    def __init__(self, device, bands):
        side = CORE.stop - CORE.start
        win = torch.hann_window(side, device=device)
        mask = win[:, None] * win[None, :]
        self.window = mask / mask.square().mean().sqrt()
        axis = torch.fft.fftfreq(side, device=device)
        radius = torch.hypot(axis[:, None], axis[None, :])
        self.bands = [(radius >= lo) & (radius < hi) for lo, hi in bands]
        self.luminance = torch.tensor([0.2126, 0.7152, 0.0722], device=device)

    def loss(self, prediction, batch):
        clean = batch["sensor_target"][:2, :, CORE, CORE]
        camera_error = prediction[:2, :, CORE, CORE].float() - clean
        weights = (self.luminance @ batch["matrix"][0]) * batch["wb"][0]
        signed = ((camera_error[0] - camera_error[1]) * weights[:, None, None]).sum(0)
        valid = ((clean >= 0) & (clean < 0.98)).all()
        # A clipped target introduces ringing in both bands. Gate the core as a
        # whole and keep the absolute loss active on the other valid pixels.
        energy = torch.fft.fft2(signed * self.window, norm="ortho").abs().square()
        rms = [((energy * band).mean() + 1e-8).sqrt() - 1e-4 for band in self.bands]
        return (torch.stack(rms).mean() * valid), valid

    def redraw_losses(self, prediction, batch, *, align=False):
        """Reduce robust band losses before or after taking the redraw average."""
        clean = batch["sensor_target"][:4, :, CORE, CORE]
        camera_error = prediction[:4, :, CORE, CORE].float() - clean
        weights = (self.luminance @ batch["matrix"][0]) * batch["wb"][0]
        luminance = (camera_error * weights[:, None, None]).sum(1)
        signed = luminance[0:4:2] - luminance[1:4:2]
        spectrum = torch.fft.fft2(signed * self.window, norm="ortho")
        valid = ((clean >= 0) & (clean < 0.98)).all()

        def penalty(values):
            power = values.abs().square()
            rms = [((power * band).mean(dim=(-2, -1)) + 1e-8).sqrt() - 1e-4 for band in self.bands]
            return torch.stack(rms).mean() * valid

        mean_spectrum = spectrum.mean(0)
        losses = {
            "individual": penalty(spectrum),
            "mean": penalty(mean_spectrum),
            "repeat": penalty((spectrum[0] - spectrum[1]) / math.sqrt(2)),
        }
        if align:
            target = ((clean[0] - clean[1]) * weights[:, None, None]).sum(0)
            template = torch.fft.fft2(target * self.window, norm="ortho")
            cross = (mean_spectrum * template.conj()).real
            target_power = template.abs().square()
            amplitude = torch.stack(
                [
                    (cross * band).mean() / (target_power * band).mean().clamp_min(1e-12).sqrt()
                    for band in self.bands
                ]
            )
            losses["aligned"] = ((amplitude.square() + 1e-8).sqrt() - 1e-4).mean() * valid
        return losses, valid

    def gap_loss(self, prediction, batch, projection):
        """Measure each present draw against the exact clean target inside the gap."""
        clean = batch["sensor_target"][0:4:2, :, CORE, CORE]
        weights = (self.luminance @ batch["matrix"][0]) * batch["wb"][0]
        residual = prediction[0:4:2, :, CORE, CORE].float() - clean
        luminance = (residual * weights[:, None, None]).sum(1).flatten(1)
        response = luminance @ projection
        valid = ((clean >= 0) & (clean < 0.98)).all()
        return ((response.square().sum(1) + 1e-8).sqrt() - 1e-4).mean() * valid


def gap_projection(wire):
    """Unit-energy weak quadratures with compact support and strong-wire rejection."""
    axis = torch.arange(CORE.start, CORE.stop) - (PATCH - 1) / 2
    y, x = (coords.flatten() for coords in torch.meshgrid(axis, axis, indexing="ij"))
    dx, dy = x - wire["gap_center"][0], y - wire["gap_center"][1]
    c, s = math.cos(wire["gap_angle"]), math.sin(wire["gap_angle"])
    a, b = wire["gap_axes"]
    radius_squared = ((c * dx + s * dy) / a).square() + ((-s * dx + c * dy) / b).square()
    taper = (1 - radius_squared).clamp_min(0)[:, None]
    strong, weak = (
        math.tau * ((math.cos(angle) * x + math.sin(angle) * y) / period + phase)
        for angle, period, phase in zip(
            wire["angles"], wire["periods"], wire["phases"], strict=True
        )
    )
    nuisance = [torch.ones_like(x), x / 32, y / 32]
    for harmonic in (1, 2, 3):
        nuisance.extend([(strong * harmonic).cos(), (strong * harmonic).sin()])
    basis, _ = torch.linalg.qr(taper * torch.stack(nuisance, dim=1))
    target = taper * torch.stack((weak.cos(), weak.sin()), dim=1)
    direction, _ = torch.linalg.qr(target - basis @ (basis.T @ target))
    return direction * taper / taper.norm()


def train(plan_path, output, *, qualification):
    plan = read_json(plan_path)
    verify_plan(plan)
    assert checked(plan["driver"]) == Path(__file__)
    schedule = read_json(checked(plan["qualification_schedule" if qualification else "schedule"]))
    output.mkdir()
    write_json(output / "owner.json", owner_identity())
    torch.set_num_threads(2)
    parent = plan["parent"]
    pair_draws = plan.get("pair_draws", 1)
    modes = tuple(plan["mode_weights"])
    stability = modes == STABILITY_MODES
    response = modes == WIRE_RESPONSE_MODES
    matched = stability or response
    if (pair_draws, modes) not in (
        (1, MODES),
        (2, ("individual", "mean")),
        (2, STABILITY_MODES),
        (2, WIRE_RESPONSE_MODES),
    ):
        raise ValueError("Unexpected paired training mode or draw count")
    models, optimizers, averages = {}, {}, {}
    started = time.monotonic()
    for mode in modes:
        model, state = load_scene_checkpoint(
            checked(parent),
            weights="ema",
            device="cpu" if matched else "cuda",
            expected_sha256=parent["sha256"],
        )
        assert state["mode"] == "none" and state["step"] == plan.get("initial_step", 50000)
        assert model_hash(model.base.context.backbone) == plan["DINO_sha256"]
        if matched:
            _stage_tiled_cuda(model, torch.device("cuda"))
        model.train().to(memory_format=torch.channels_last)
        models[mode] = model
        optimizers[mode] = torch.optim.AdamW(
            [p for p in model.base.parameters() if p.requires_grad],
            weight_decay=1e-4,
            fused=True,
        )
        averages[mode] = {k: v.detach().clone() for k, v in model.restoration_state_dict().items()}
        base_parent = state["base_parent"]
        width = state["adapter_width"]
        del state
    bands = PairedBands("cuda", plan["pair_bands_cycles_per_pixel"])
    policy = plan["optimizer"]
    data_seconds = 0.0
    used = {mode: 0.0 for mode in modes}
    valid_pairs = 0
    began = time.monotonic()
    with (
        (output / "observations.jsonl").open("x", buffering=1) as trace,
        (output / "train.jsonl").open("x", buffering=1) as log,
        ieee_fp32(),
    ):
        for step, example in enumerate(schedule, start=1):
            assert psutil.virtual_memory().available > 24 * 2**30
            mark = time.monotonic()
            values, about = observations(
                example,
                step + (plan["steps_per_arm"] if qualification else 0),
                pair_draws=pair_draws,
                seed=plan["seed"],
            )
            trace.write(json.dumps(about, sort_keys=True) + "\n")
            batch = {k: v.cuda() for k, v in values.items()}
            for key in ("packed", "variance", "target", "sensor_target"):
                batch[key] = batch[key].contiguous(memory_format=torch.channels_last)
            wire = about["geometry"].get("wire")
            gap = gap_projection(wire).cuda() if stability and wire is not None else None
            data_seconds += time.monotonic() - mark
            warmup = policy["warmup"]
            progress = max(0, step - warmup) / (plan["steps_per_arm"] - warmup)
            floor = policy["minimum_factor"]
            lr = (
                policy["peak_lr"]
                * min(1.0, step / warmup)
                * (floor + (1 - floor) * (1 + math.cos(math.pi * progress)) / 2)
            )
            record = {"step": step, "lr": lr}
            for mode in modes:
                mark = time.monotonic()
                model, optimizer = models[mode], optimizers[mode]
                model.base.set_noise(about["camera"]["shot"], about["camera"]["read"])
                optimizer.param_groups[0]["lr"] = lr
                optimizer.zero_grad(set_to_none=True)
                with amp_context("cuda", dtype="bfloat16"):
                    prediction = model(*(batch[k] for k in FORWARD_ARGS))
                assert prediction.dtype == torch.float32
                absolute, _ = reconstruction_loss(
                    prediction,
                    batch,
                    auxiliary=mosaic(prediction, batch["colors"]),
                    camera_supervision="sensor-valid-v1",
                    reconstruction_charbonnier_epsilon=0.0003,
                )
                redraw = {}
                if pair_draws == 2:
                    redraw, valid = bands.redraw_losses(
                        prediction, batch, align=response and wire is not None
                    )
                    paired = redraw["mean" if matched else mode]
                else:
                    paired, valid = bands.loss(prediction, batch)
                loss = absolute + plan["mode_weights"][mode] * paired
                if matched and mode != "mean" and about["law"] == "independent":
                    loss += plan["repeat_weight"] * redraw["repeat"]
                if gap is not None:
                    redraw["gap"] = bands.gap_loss(prediction, batch, gap)
                    if mode == "repeat-gap":
                        loss += plan["gap_weight"] * redraw["gap"]
                if response and wire is not None and mode != "repeat":
                    loss += (
                        plan["response_weight"]
                        * redraw["aligned" if mode == "wire-aligned" else "mean"]
                    )
                if not torch.isfinite(loss):
                    raise FloatingPointError(f"Nonfinite loss in {mode} arm")
                if step == 1:
                    if mode == modes[0]:
                        initial = prediction.detach().clone()
                    else:
                        assert torch.equal(prediction.detach(), initial)
                loss.backward()
                norm = torch.nn.utils.clip_grad_norm_(
                    [p for p in model.base.parameters() if p.requires_grad],
                    1.0,
                    error_if_nonfinite=True,
                )
                optimizer.step()
                with torch.no_grad():
                    for key, value in model.restoration_state_dict().items():
                        averages[mode][key].lerp_(value, 1 - policy["ema"])
                record[mode] = {
                    "absolute": float(absolute.detach()),
                    "paired": float(paired.detach()),
                    "grad": float(norm),
                    **{name + "_loss": float(value.detach()) for name, value in redraw.items()},
                }
                if mode == modes[-1]:
                    valid_pairs += int(valid)
                used[mode] += time.monotonic() - mark
            log.write(json.dumps(record, sort_keys=True) + "\n")
            if step % 32 == 0 or step == len(schedule):
                print(step, valid_pairs, round(time.monotonic() - began, 2), record, flush=True)
    elapsed = time.monotonic() - began
    checkpoints = {}
    for mode in modes:
        model = models[mode]
        assert model_hash(model.base.context.backbone) == plan["DINO_sha256"]
        path = output / f"{mode}.pt"
        temp = path.with_suffix(".incomplete")
        torch.save(
            {
                "base_parent": base_parent,
                "continued_from": parent,
                "DINO_sha256": plan["DINO_sha256"],
                "model": {k: v.detach().cpu() for k, v in model.restoration_state_dict().items()},
                "ema": {k: v.cpu() for k, v in averages[mode].items()},
                "optimizer": optimizers[mode].state_dict(),
                "mode": "none",
                "adapter_width": width,
                "step": len(schedule),
                "training_arm": mode,
                "plan": reference(plan_path),
            },
            temp,
        )
        temp.rename(path)
        checkpoints[mode] = reference(path)
    write_json(
        output / "completed.json",
        {
            "plan": reference(plan_path),
            "parent": parent,
            "qualification": qualification,
            "updates_per_arm": len(schedule),
            "source_photos_per_arm": len(schedule),
            "native_observations_per_arm": len(plan["members"]) * len(schedule),
            "pair_draws_per_source": pair_draws,
            "valid_core_pairs": valid_pairs,
            "training_seconds": elapsed,
            "compute_seconds": used,
            "data_and_hash_seconds": data_seconds,
            "total_seconds": time.monotonic() - started,
            "checkpoints": checkpoints,
            "weights": "Each artifact stores raw and EMA states separately.",
            "observations": reference(output / "observations.jsonl"),
            "log": reference(output / "train.jsonl"),
            "DINO_unchanged": True,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    lock = subcommands.add_parser("prepare")
    for key in ("root", "parent_audit", "scene_plan", "photo_panel", "prior_panel"):
        lock.add_argument(key, type=Path)
    redraw = subcommands.add_parser("prepare-redraw")
    redraw.add_argument("root", type=Path)
    redraw.add_argument("prior_plan", type=Path)
    stability = subcommands.add_parser("prepare-stability")
    response = subcommands.add_parser("prepare-wire-response")
    for command in (stability, response):
        for key in ("root", "completion", "scene_plan"):
            command.add_argument(key, type=Path)
    run = subcommands.add_parser("train")
    run.add_argument("plan", type=Path)
    run.add_argument("output", type=Path)
    run.add_argument("--qualification", action="store_true")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(
            args.root.absolute(),
            args.parent_audit,
            args.scene_plan,
            args.photo_panel,
            args.prior_panel,
        )
    elif args.command == "prepare-redraw":
        prepare_redraw(args.root.absolute(), args.prior_plan)
    elif args.command in ("prepare-stability", "prepare-wire-response"):
        prepare_objective_trial(
            args.root.absolute(),
            args.completion,
            args.scene_plan,
            wire_response=args.command == "prepare-wire-response",
        )
    else:
        train(args.plan, args.output, qualification=args.qualification)
