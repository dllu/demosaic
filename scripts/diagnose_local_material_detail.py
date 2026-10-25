"""Stratify saved material predictions by local GT fine-band contrast; no models."""

import argparse
import datetime
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import psutil

REPO = Path(__file__).absolute().parents[1]
METHODS = ("V104 eight", "V112 eight", "V114 single", "V114 eight", "RawNIND preup")


def read(path):
    return json.loads(Path(path).read_text())


def binding(path):
    path = Path(path).absolute()
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def write(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def local_time():
    return datetime.datetime.now(ZoneInfo("America/Los_Angeles")).isoformat()


def checked(item):
    assert binding(item["path"]) == item
    return Path(item["path"])


def prepare(pilot, root):
    pilot, root = pilot.absolute(), root.absolute()
    assert root.is_relative_to(REPO / ".cache")
    result = read(pilot / "result-v1.json")
    assert result["new_neural_forwards"] == 192 and len(result["rows"]) == 24
    assert (
        result["checkpoint"]["sha256"]
        == "2285c84b7015bcf122e71b890723f80aaf216bde849256c77f070c2493f9d2d2"
    )
    root.mkdir(exist_ok=False)
    script = root / Path(__file__).name
    shutil.copyfile(__file__, script)
    inputs = [binding(pilot / "result-v1.json"), binding(pilot / "analysis-v1/result-v1.json")]
    observations = []
    for condition in ("adc-only", "iso100-prior", "iso12800-prior"):
        board_path = pilot / "analysis-v1" / ("photo-" + condition + ".json")
        inputs.append(binding(board_path))
        for source in read(board_path)["sources"]:
            row = source["row"]
            assert row["kind"] == "photo" and row["condition"]["name"] == condition
            view = row["views"][0]
            assert (view["view"], view["quarter_turns"], view["reflected"]) == (0, 0, False)
            arrays = dict(
                zip(
                    METHODS,
                    (
                        source["prior_V104_eight_view"],
                        source["prior_V112_eight_view"],
                        view["canonical_prediction"],
                        row["mean8"],
                        source["strong_RawNIND_preup"],
                    ),
                    strict=True,
                )
            )
            inputs.extend([row["input"], *arrays.values()])
            observations.append(
                {
                    "source_id": row["observation"]["observation"]["source_id"],
                    "condition": row["condition"],
                    "input": row["input"],
                    "input_fingerprints": row["input_value_fingerprints"],
                    "predictions": arrays,
                }
            )
    assert len(observations) == 12
    plan = {
        "recorded_local": local_time(),
        "root": str(root),
        "script": binding(script),
        "pilot_checkpoint": result["checkpoint"],
        "observations": observations,
        "inputs": inputs,
        "definition": {
            "context": [256, 256],
            "interior_xywh": [8, 8, 240, 240],
            "block": 16,
            "band_cycles_per_pixel": [1 / 8, 1 / 3],
            "relative_GT_band_RMS_edges": [0, 0.02, 0.05, 0.10, 0.20],
            "minimum_GT_band_RMS": 1e-5,
            "GT_mean_luminance_range": [0.02, 0.9],
            "exclude_any_GT_linear_RGB_outside": [0, 1],
        },
        "scope": "Exploratory local-luminance diagnostic of the original four held-out material contexts and three fixed noise draws. All225 disjoint16px blocks per context retained. Orthonormal DCT-II, frequencies k/(2N), radial band [1/8,1/3). GT-only eligibility/bins fixed before output analysis. Conditional scalar projection can contain chance noise/GT correlation; no noise debiasing or fine-carrier recovery claim. Local coarse structure and block boundaries can leak into the band. No inference/training/default/source-data/queue changes.",
    }
    for item in inputs:
        checked(item)
    write(root / "plan-v1.json", plan)
    return root / "plan-v1.json"


def basis(size):
    k = np.arange(size)[:, None]
    values = np.cos(np.pi * (np.arange(size)[None, :] + 0.5) * k / size) * np.sqrt(2 / size)
    values[0] /= np.sqrt(2)
    return values


def fft_dct(values, axis):
    size = values.shape[axis]
    extended = np.concatenate((values, np.flip(values, axis=axis)), axis=axis)
    spectrum = np.fft.fft(extended, axis=axis)
    shape = [1] * values.ndim
    shape[axis] = size
    selection = [slice(None)] * values.ndim
    selection[axis] = slice(0, size)
    phase = np.exp(-1j * np.pi * np.arange(size) / (2 * size)).reshape(shape)
    result = (spectrum[tuple(selection)] * phase).real / np.sqrt(2 * size)
    selection[axis] = 0
    result[tuple(selection)] /= np.sqrt(2)
    return result


def blocks(values):
    assert values.shape == (256, 256)
    return values[8:248, 8:248].reshape(15, 16, 15, 16).transpose(0, 2, 1, 3).reshape(225, 16, 16)


def luminance(values, data):
    rgb = np.einsum(
        "bij,bjhw->bihw",
        data["matrix"].astype(np.float64),
        values.astype(np.float64) * data["wb"].astype(np.float64)[..., None, None],
    )
    return rgb, np.einsum("c,bchw->bhw", np.array([0.2126, 0.7152, 0.0722]), rgb)[0]


def reduce_sums(sums):
    target, cross, power, count = (
        sums[k] for k in ("GT_energy", "cross", "prediction_energy", "blocks")
    )
    assert target > 0 and count > 0
    return {
        "blocks": count,
        "GT_projected_gain": cross / target,
        "GT_band_RMS": float(np.sqrt(target / (count * 256))),
        "band_error_RMS": float(np.sqrt(max(power + target - 2 * cross, 0) / (count * 256))),
        "orthogonal_band_RMS": float(
            np.sqrt(max(power - cross * cross / target, 0) / (count * 256))
        ),
    }


def run(plan_path):
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and "torch" not in sys.modules
    assert psutil.virtual_memory().available >= 16 * 2**30
    os.nice(10)
    plan = read(plan_path)
    checked(plan["script"])
    assert binding(__file__) == plan["script"]
    for item in plan["inputs"]:
        checked(item)
    output = Path(plan["root"]) / "output-v1"
    output.mkdir(exist_ok=False)
    c = basis(16)
    assert np.max(np.abs(c @ c.T - np.eye(16))) < 3e-15
    freq = np.arange(16) / 32
    radius = np.hypot(freq[:, None], freq[None, :])
    mask = (radius >= 1 / 8) & (radius < 1 / 3)
    maximum_fft_error = 0.0

    def transform(values):
        nonlocal maximum_fft_error
        result = c @ values @ c.T
        independent = fft_dct(fft_dct(values, -1), -2)
        error = float(np.max(np.abs(result - independent)))
        assert error < 3e-14, error
        maximum_fft_error = max(maximum_fft_error, error)
        return result[..., mask]

    target = np.full((16, 16), 0.18) + 0.0032 * np.outer(c[0], c[8])
    prediction = np.full((16, 16), 0.18) + 0.75 * (target - 0.18) + 0.0016 * np.outer(c[0], c[6])
    t, p = transform(target), transform(prediction)
    fixture = reduce_sums(
        {
            "GT_energy": float(t @ t),
            "cross": float(p @ t),
            "prediction_energy": float(p @ p),
            "blocks": 1,
        }
    )
    assert abs(fixture["GT_projected_gain"] - 0.75) < 1e-11
    assert abs(fixture["orthogonal_band_RMS"] - 0.0001) < 1e-14
    # Verify Parseval in the independent spatial projection, not only coefficients.
    tc = np.zeros((16, 16))
    tc[mask] = t
    spatial = c.T @ tc @ c
    assert abs(np.sum(spatial**2) - float(t @ t)) < 1e-17
    rows, groups, target_hashes, total = [], {}, {}, 0
    edges = np.array(plan["definition"]["relative_GT_band_RMS_edges"])
    for observation in plan["observations"]:
        with np.load(observation["input"]["path"], allow_pickle=False) as archive:
            data = {k: archive[k] for k in archive.files}
        for name, fingerprint in observation["input_fingerprints"].items():
            value = data[name]
            assert (
                list(value.shape) == fingerprint["shape"]
                and value.dtype.str == fingerprint["dtype"]
            )
            assert hashlib.sha256(value.tobytes()).hexdigest() == fingerprint["sha256"]
        target_digest = hashlib.sha256(data["target"].tobytes()).hexdigest()
        old = target_hashes.setdefault(observation["source_id"], target_digest)
        assert old == target_digest
        rgb, y = luminance(data["target"], data)
        tb = blocks(y)
        coefficients = transform(tb)
        energy = np.sum(coefficients**2, axis=1)
        mean = tb.mean(axis=(1, 2))
        rms = np.sqrt(energy / 256)
        valid = (mean >= 0.02) & (mean <= 0.9) & (rms >= 1e-5)
        for channel in rgb[0]:
            tiles = blocks(channel)
            valid &= np.all((tiles >= 0) & (tiles <= 1), axis=(1, 2))
        ratio = rms / np.maximum(mean, 1e-30)
        bins = np.searchsorted(edges, ratio, side="right") - 1
        detail = [
            {
                "block": i,
                "ROI_xywh": [8 + 16 * (i % 15), 8 + 16 * (i // 15), 16, 16],
                "GT_mean_luminance": float(mean[i]),
                "GT_band_RMS": float(rms[i]),
                "relative_GT_band_RMS": float(ratio[i]),
                "eligible": bool(valid[i]),
                "bin": int(bins[i]),
                "methods": {},
            }
            for i in range(225)
        ]
        for method, item in observation["predictions"].items():
            value = np.load(item["path"], allow_pickle=False)
            assert (
                value.dtype == np.float32
                and value.shape == (1, 3, 256, 256)
                and np.isfinite(value).all()
            )
            pred = transform(blocks(luminance(value, data)[1]))
            cross = np.sum(pred * coefficients, axis=1)
            power = np.sum(pred**2, axis=1)
            for i in range(225):
                detail[i]["methods"][method] = {
                    "cross": float(cross[i]),
                    "prediction_energy": float(power[i]),
                }
            for index in range(len(edges)):
                selected = valid & (bins == index)
                if not selected.any():
                    continue
                key = (observation["condition"]["name"], index, method)
                sums = {
                    "GT_energy": float(energy[selected].sum()),
                    "cross": float(cross[selected].sum()),
                    "prediction_energy": float(power[selected].sum()),
                    "blocks": int(selected.sum()),
                }
                groups.setdefault(key, []).append(
                    {"source_id": observation["source_id"], "sums": sums, **reduce_sums(sums)}
                )
        rows.append(
            {
                "source_id": observation["source_id"],
                "condition": observation["condition"],
                "input": observation["input"],
                "predictions": observation["predictions"],
                "blocks": detail,
            }
        )
        total += len(detail)
    assert len(rows) == 12 and total == 2700 and len(target_hashes) == 4
    summaries = []
    for (condition, index, method), sources in sorted(groups.items()):
        pooled = {k: sum(source["sums"][k] for source in sources) for k in sources[0]["sums"]}
        summaries.append(
            {
                "condition": condition,
                "bin": index,
                "relative_GT_band_RMS_lower": float(edges[index]),
                "relative_GT_band_RMS_upper": float(edges[index + 1])
                if index + 1 < len(edges)
                else None,
                "method": method,
                "sources_with_eligible_blocks": len(sources),
                "source_balanced_GT_projected_gain": float(
                    np.mean([s["GT_projected_gain"] for s in sources])
                ),
                "pooled": reduce_sums(pooled),
                "per_source": sources,
            }
        )
    write(output / "blocks-v1.json", rows)
    write(
        output / "result-v1.json",
        {
            "recorded_local": local_time(),
            "plan": binding(plan_path),
            "script": binding(__file__),
            "block_observations": total,
            "unique_source_blocks": 900,
            "same_GT_across_conditions_verified": True,
            "summaries": summaries,
            "block_details": binding(output / "blocks-v1.json"),
            "closed_form_fixture": fixture,
            "maximum_explicit_cosine_vs_even_FFT_absolute_error": maximum_fft_error,
            "new_neural_forwards": 0,
            "optimizer_updates": 0,
            "new_noise_observations": 0,
            "RAW_decodes": 0,
            "Torch_imported": "torch" in sys.modules,
            "scope": plan["scope"],
        },
    )
    print(
        json.dumps(
            {
                "blocks": total,
                "groups": len(summaries),
                "maximum_DCT_error": maximum_fft_error,
                "new_neural_forwards": 0,
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("pilot", type=Path)
    prep.add_argument("root", type=Path)
    runner = commands.add_parser("run")
    runner.add_argument("plan", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        print(prepare(args.pilot, args.root))
    else:
        run(args.plan)
