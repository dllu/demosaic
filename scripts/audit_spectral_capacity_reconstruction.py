"""Independent NumPy64 replay of GT spectral witnesses, without neural calls."""

import argparse
import os
from pathlib import Path

import numpy as np
import torch
from score_late_spectral_capacity import load_module
from train_directional_bank_trial import read, ref, save


def geometry(size):
    axis = np.arange(size) * np.pi / size
    window = np.sin(axis)[:, None] * np.sin(axis)[None, :]
    y, x = np.meshgrid(np.linspace(-1, 1, size), np.linspace(-1, 1, size), indexing="ij")
    basis = np.stack([np.ones_like(x), x, y], -1)
    inverse = np.linalg.inv(np.einsum("hwi,hwj,hw->ij", basis, basis, window**2))
    return tuple(v.astype(np.float32).astype(np.float64) for v in (window, basis, inverse))


def frames(values, size):
    _, _, h, w = values.shape
    hop = size // 2
    pad = ((0, 0), (0, 0), (hop, hop + (-h % hop)), (hop, hop + (-w % hop)))
    v = np.pad(values, pad, mode="edge")
    tiled = np.lib.stride_tricks.sliding_window_view(v, (size, size), axis=(-2, -1))[
        :, :, ::hop, ::hop
    ]
    ny, nx = tiled.shape[2:4]
    return tiled.transpose(0, 2, 3, 1, 4, 5).reshape(-1, 4, size, size), (
        h,
        w,
        ny,
        nx,
        v.shape[-2:],
    )


def analyze(values, size, g):
    window, basis, inverse = g
    v, shape = frames(values - values[..., :1, :1], size)
    v = v - v[..., :1, :1]
    beta = np.einsum("nchw,hwk,hw->nck", v, basis, window**2) @ inverse
    residual = window * (v - np.einsum("nck,hwk->nchw", beta, basis))
    spectrum = np.fft.fft2(residual, norm="ortho")
    spectrum[..., 0, 0] = 0
    return spectrum, shape


def synthesize(spectrum, shape, window):
    h, w, ny, nx, padded = shape
    size, hop = window.shape[0], window.shape[0] // 2
    v = (np.fft.ifft2(spectrum, norm="ortho").real * window).reshape(1, ny, nx, 4, size, size)
    total = np.zeros((1, 4, *padded))
    weight = np.zeros(padded)
    for j in range(ny):
        for i in range(nx):
            total[..., j * hop : j * hop + size, i * hop : i * hop + size] += v[:, j, i]
            weight[j * hop : j * hop + size, i * hop : i * hop + size] += window**2
    region = (..., slice(hop, hop + h), slice(hop, hop + w))
    return total[region] / weight[hop : hop + h, hop : hop + w]


def witnesses(x, y, cap):
    power = np.sum(abs(x) ** 2, axis=1, keepdims=True)
    tiny = np.finfo(np.float64).tiny
    gain = np.clip(
        np.real(np.sum(np.conj(x) * y, axis=1, keepdims=True)) / np.maximum(power, tiny), -cap, cap
    )
    reverse = (-np.arange(x.shape[-1])) % x.shape[-1]
    gain = (gain + gain[..., reverse, :][..., :, reverse]) * 0.5
    H = y[:, :, None] * np.conj(x[:, None]) / np.maximum(power[:, :, None], tiny)
    bound = np.sqrt(
        np.max(np.sum(abs(H), axis=1), axis=1) * np.max(np.sum(abs(H), axis=2), axis=1)
    )[:, None]
    H /= np.maximum(np.maximum(cap, bound), tiny)[:, :, None]
    H = np.clip(H.real, -1 + 1e-6, 1 - 1e-6) + 1j * np.clip(H.imag, -1 + 1e-6, 1 - 1e-6)
    H = (H + np.conj(H[..., reverse, :][..., :, reverse])) * 0.5
    bound = np.sqrt(np.max(np.sum(abs(H), axis=1), axis=1) * np.max(np.sum(abs(H), axis=2), axis=1))
    H /= np.maximum(1, bound)[:, None, None]
    return gain * x, cap * np.einsum("noihw,nihw->nohw", H, x)


def main(root):
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[6:8])
    plan = read(root / "plan-v1.json")
    source = Path(__file__).with_name("diagnose_spectral_innovation_split.py")
    metric = load_module(source, "independent_Malvar_sampling")
    selected = []
    for pattern in ("RGGB", "BGGR", "GRBG", "GBRG"):
        selected.append(
            next(
                c
                for c in plan["cases"]
                if c["kind"] == "mesh" and c["present"] and c["pattern"] == pattern
            )
        )
    for kind, cohort in [
        ("photo", "retained512"),
        ("photo", "organic384"),
        ("flat", "fresh-flat512"),
        ("mixed-quiet", None),
    ]:
        selected.append(
            next(
                c
                for c in plan["cases"]
                if c["kind"] == kind
                and c.get("cohort") == cohort
                and (kind != "flat" or c["noise"]["name"] == "iso6400-prior")
            )
        )
    rows = []
    observed = {o["id"]: o for o in read(root / "result-v1.json")["observations"]}
    for case in selected:
        a = dict(np.load(case["arrays"]["path"]))
        base = np.load(case["parent"]["path"]).astype(np.float64)
        size = min(256, 2 ** int(np.log2(min(a["packed"].shape[-2:]))))
        g = geometry(size)
        z, shape = analyze(a["packed"].astype(np.float64), size, g)
        p, _ = analyze(metric.sample(base, a["colors"]), size, g)
        clean, _ = analyze(metric.sample(a["target"].astype(np.float64), a["colors"]), size, g)
        x, y = z - p, clean - p
        vf, _ = frames(a["variance"].astype(np.float64), size)
        noise = (vf * g[0] ** 2).mean((-2, -1)).sum(1)[:, None, None, None]
        power = np.sum(abs(z) ** 2, axis=1, keepdims=True)
        f = np.fft.fftfreq(size).astype(np.float32)
        radius = np.hypot(f[:, None], f[None, :])
        rise = np.clip((radius - 1 / 32) / (1 / 32), 0, 1)
        fall = np.clip((0.45 - radius) / 0.05, 0, 1)
        band = np.sin(np.pi * rise / 2) ** 2 * np.sin(np.pi * fall / 2) ** 2
        cap = power / np.maximum(power + noise, 1e-12) * band
        scalar, matrix = witnesses(x, y, cap)
        values = {
            "GT-scalar-full-support": scalar,
            "GT-matrix-full-support": matrix,
            "GT-band-residual-full-support": y * band,
            "GT-unbanded-residual-full-support": y,
        }
        for name, delta in values.items():
            value = base + metric.mhc(synthesize(delta, shape, g[0]), a["colors"], a["wb"])
            binding = observed[case["id"]]["predictions"][name]
            actual = np.load(binding["path"])
            difference = np.abs(value - actual)
            maximum = float(difference.max())
            assert maximum < 4e-6, (case["id"], name, maximum)
            rows.append(
                {
                    "id": case["id"],
                    "mode": name,
                    "prediction": binding,
                    "maximum_abs_camera_RGB_difference": maximum,
                    "RMS_difference_DN16": float(np.sqrt(np.mean(difference**2)) * 65535),
                }
            )
    assert len(rows) == 32 and not torch.cuda.is_initialized()
    save(
        root / "independent-reconstruction-audit-v2.json",
        {
            "status": "pass",
            "auditor": ref(__file__),
            "independent_sampling_Malvar_source": ref(source),
            "plan": ref(root / "plan-v1.json"),
            "diagnostic": ref(root / "result-v1.json"),
            "rows": rows,
            "cases": 8,
            "reconstructions": 32,
            "maximum_abs_difference": max(r["maximum_abs_camera_RGB_difference"] for r in rows),
            "precision": "Independent NumPy64 calculations using independently built FP32-rounded geometry; original CUDA operations FP32",
            "atol_camera_RGB": 4e-6,
            "new_neural_forwards": 0,
            "new_noise_draws": 0,
            "CUDA_initialized": False,
            "scope": "Fixed first-case subset covering all4 CFAs,512/384 contexts, two photo cohorts, noisy flat and mixed quiet. Independent affine/STFT, power cap, scalar/matrix witness, overlap synthesis and signed Malvar reconstruction. Oracle outputs use GT and are not inference. No new model evaluation.",
        },
    )
    print(
        "PASS32 independent NumPy reconstructions; maximum difference",
        max(r["maximum_abs_camera_RGB_difference"] for r in rows),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    main(parser.parse_args().root.absolute())
