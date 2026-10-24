"""Measure clean training-target spectra without a model, noise or RAW decoding."""

import argparse
import hashlib
import json
import os
import random
from collections import defaultdict
from pathlib import Path

import numpy as np
import psutil
import torch
import yaml

import demosaic.data as clean
from demosaic.raw_clean import RawCleanDataset

BANDS = {"period3-to5": (.20, .30), "above-legacy-random-support": (.225, .35)}


def binding(path):
    path = Path(path).absolute()
    with path.open("rb") as stream:
        return {"path": str(path), "sha256": hashlib.file_digest(stream, "sha256").hexdigest()}


def write(path, value):
    with Path(path).open("x") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False)+"\n")


def spectrum(rgb):
    """Hann-windowed radial relative-luminance energy, corrected for window power."""
    rgb = np.asarray(rgb, dtype=np.float64)
    if rgb.shape != (3, 256, 256) or not np.isfinite(rgb).all():
        raise ValueError("Frequency audit needs finite native256 linear RGB")
    weights = np.array([.2126, .7152, .0722])
    luminance = np.einsum("c,chw->hw", weights, rgb)
    mean = float(luminance.mean())
    centered = luminance-luminance.mean()
    window = np.outer(np.hanning(256), np.hanning(256))
    power = np.abs(np.fft.fft2(centered*window))**2/256**4/np.mean(window**2)
    axis = np.fft.fftfreq(256)
    radius = np.sqrt(axis[:, None]**2+axis[None, :]**2)
    support = (radius >= 1/64) & (radius < .45)
    total = float(power[support].sum())
    measures = {}
    for name, (low, high) in BANDS.items():
        energy = float(power[(radius >= low) & (radius < high)].sum())
        measures[name] = {"relative_RMS": float(np.sqrt(energy)/max(abs(mean), 1e-8)),
                          "fraction_of_1over64_to_045_power": energy/max(total, 1e-30)}
    bins = np.linspace(0, .5, 51)
    radial = np.histogram(radius.ravel(), bins=bins, weights=power.ravel())[0]/max(mean**2, 1e-16)
    return {"mean_linear_luminance": mean, "luminance_RMS": float(np.sqrt(np.mean(centered**2))),
            "bands": measures, "radial_relative_power": radial.tolist(), "radial_edges": bins.tolist()}


def run(path):
    plan = json.loads(Path(path).read_text())
    for item in plan["inputs"]:
        assert binding(item["path"]) == item
    for p, digest in plan["frozen_files"].items():
        assert binding(p)["sha256"] == digest
    assert binding(__file__) == plan["worker"] and os.environ["CUDA_VISIBLE_DEVICES"] == ""
    assert psutil.virtual_memory().available >= 40*2**30 and not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    def forbid(*_a, **_kw):
        raise RuntimeError("No learned/module forwards in clean-target frequency audit")
    torch.nn.Module._call_impl = forbid
    output = Path(plan["output"])
    output.mkdir(parents=True, exist_ok=False)
    config = yaml.safe_load(Path(plan["recipe"]["path"]).read_text())
    options = {k: config[k] for k in ("seed", "patch_size", "synthetic_fraction", "flat_fraction", "augmentation_downsample",
                                     "weak_texture_fraction", "flat_chroma_stops", "optical_blur_probability",
                                     "photographic_low_contrast_fraction", "reviewed_roi_catalogue", "reviewed_roi_fraction")}
    options["fine_weak_texture_fraction"] = config.get("fine_weak_texture_fraction", 0.0)
    data = clean.CleanDataset(config["manifest"], **options)
    native = RawCleanDataset(config["raw_clean_manifest"], patch_size=256, seed=config["seed"], augmentation_downsample=2,
                             optical_blur_probability=config["raw_clean_optical_blur_probability"])
    before_torch, before_python = torch.get_rng_state().clone(), random.getstate()
    sources = {str((data.manifest.parent/row["cache"]).absolute()): row for row in data.rows}
    sources.update({str((native.path.parent/row["cache"]).absolute()): row for rows in native.scenes.values() for row in rows})
    traced, records = {}, []
    weak, attenuation, load = clean.weak_texture, clean.attenuate_photographic_contrast, np.load
    def observe_weak(*a, **kw):
        value, recipe = weak(*a, **kw)
        traced["recipe"] = recipe
        return value, recipe
    def observe_attenuation(*a, **kw):
        traced["attenuated"] = True
        return attenuation(*a, **kw)
    def observe_load(p, *a, **kw):
        source = str(Path(p).absolute())
        traced.setdefault("cache_paths", []).append(source)
        array = load(p, *a, **kw)
        class TracedArray:
            shape = array.shape
            def __getitem__(self, key):
                y, x = key[:2]
                traced["cache_crop_xywh"] = [x.start, y.start, x.stop-x.start, y.stop-y.start]
                traced["source"] = sources[source]
                return array[key]
        return TracedArray()
    clean.weak_texture, clean.attenuate_photographic_contrast, np.load = observe_weak, observe_attenuation, observe_load
    try:
        for domain, index, stratum in plan["selections"]:
            assert psutil.virtual_memory().available >= 32*2**30
            traced.clear()
            if domain == "commons":
                rgb = data[index]["rgb"].numpy()
                group = "photo-attenuated" if stratum == "photo" and traced.get("attenuated") else stratum
            else:
                value = native[index]
                rgb = np.einsum("ij,jhw->ihw", value["matrix"].double().numpy(),
                                value["camera_rgb"].double().numpy()*value["wb"].double().numpy()[:, None, None])
                group = "native-RAW-target"
            metrics = spectrum(rgb)
            target = output/f"clean-{len(records):03d}.npy"
            np.save(target, rgb, allow_pickle=False)
            records.append({"domain": domain, "sample_index": index, "stratum": group, "generation": dict(traced),
                            "target": binding(target), "metrics": metrics})
    finally:
        clean.weak_texture, clean.attenuate_photographic_contrast, np.load = weak, attenuation, load
    assert torch.equal(before_torch, torch.get_rng_state()) and before_python == random.getstate() and not torch.cuda.is_initialized()
    for item in plan["inputs"]:
        assert binding(item["path"]) == item
    grouped = defaultdict(list)
    for r in records:
        grouped[r["stratum"]].append(r)
    summaries = []
    for name, rows in sorted(grouped.items()):
        bands = {}
        for band in BANDS:
            bands[band] = {}
            for metric in rows[0]["metrics"]["bands"][band]:
                values = np.array([r["metrics"]["bands"][band][metric] for r in rows])
                bands[band][metric] = {"median": float(np.median(values)), "q25": float(np.quantile(values, .25)),
                                       "q75": float(np.quantile(values, .75)), "min": float(values.min()), "max": float(values.max())}
        summaries.append({"stratum": name, "samples": len(rows), "bands": bands,
                          "median_radial_relative_power": np.median([r["metrics"]["radial_relative_power"] for r in rows], axis=0).tolist()})
    write(output/"result-v1.json", {"plan": binding(path), "worker": binding(__file__), "records": records, "summaries": summaries,
                                   "new_neural_forwards": 0, "new_encoder_forwards": 0, "new_noise_observations": 0,
                                   "RAW_decodes": 0, "CUDA_initialized": False, "global_RNG_unchanged": True,
                                   "scope": plan["scope"]})
    print({"output": str(output/"result-v1.json"), "samples": len(records), "strata": [(x["stratum"], x["samples"]) for x in summaries]}, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    run(parser.parse_args().plan)
