"""Research-only direct RAW wave refitting; no ordinary inference dispatch.

The measured tradeoff is documented in docs/raw-phase-refit.md. The fixed support
is selected with the earlier Gaussian phasor/connected-component method. Latent
complex coefficients live on a32x32 native8-spaced bilinear grid. Multiplying its
upsampled field by the fixed128 mask precedes physical Bayer-phase interpolation.
All four phases share the original fitted RGB/green complex transport.

Minimize .5||A u-y||²+4*sum||grad u||+.125*sum||u||+.05/2*||u||²,
in median green RAW-noise units. The2048-step CP estimate returns a feasible dual
gap and may be far from converged. It is a serial research operator, not a
calibrated test for detail or flatness. No GT/reference, RNG or neural calls.
"""

from functools import lru_cache

import numpy as np
import torch


def shift(v, delta, axis, adjoint=False):
    """Linear sample at j+delta, delta in {-1/4,1/4}, with clamped ends."""
    v = v.movedim(axis, -1)
    if adjoint:
        if delta > 0:
            other = torch.cat([torch.zeros_like(v[..., :1]), v[..., :-1]], -1)
            other[..., -1:] += v[..., -1:]
        else:
            other = torch.cat([v[..., 1:], torch.zeros_like(v[..., :1])], -1)
            other[..., :1] += v[..., :1]
    elif delta > 0:
        other = torch.cat([v[..., 1:], v[..., -1:]], -1)
    else:
        other = torch.cat([v[..., :1], v[..., :-1]], -1)
    return (0.75 * v + 0.25 * other).movedim(-1, axis)


def interpolate(v, phase, adjoint=False):
    oy, ox = divmod(int(phase), 2)
    return shift(shift(v, (ox - 0.5) / 2, -1, adjoint), (oy - 0.5) / 2, -2, adjoint)


def gradient(u):
    out = torch.zeros((2, *u.shape), device=u.device, dtype=u.dtype)
    out[0, ..., :-1, :] = u[..., 1:, :] - u[..., :-1, :]
    out[1, ..., :, :-1] = u[..., :, 1:] - u[..., :, :-1]
    return out


def divergence(q):
    out = torch.zeros_like(q[0])
    out[..., :-1, :] += q[0, ..., :-1, :]
    out[..., 1:, :] -= q[0, ..., :-1, :]
    out[..., :, :-1] += q[1, ..., :, :-1]
    out[..., :, 1:] -= q[1, ..., :, :-1]
    return out


class Solver:
    def __init__(self, k, phases, device):
        self.phases = phases
        kw = {"device": device, "dtype": torch.float64}
        self.t = torch.zeros((len(phases), k, 2, 128, 128), **kw)
        self.y = torch.zeros((len(phases), 128, 128), **kw)
        self.mask = torch.zeros((k, 1, 128, 128), **kw)
        self.u = torch.zeros((k, 2, 32, 32), **kw)
        locations = (np.arange(128) + 0.5) / 4 - 0.5
        lo = np.floor(locations).astype(int)
        mix = locations - lo
        w = np.zeros((128, 32))
        np.add.at(w, (np.arange(128), lo.clip(0, 31)), 1 - mix)
        np.add.at(w, (np.arange(128), (lo + 1).clip(0, 31)), mix)
        self.w = torch.tensor(w, **kw)
        self.ub = torch.zeros_like(self.u)
        self.p = torch.zeros_like(self.y)
        self.q = torch.zeros((2, *self.u.shape), **kw)
        self.step = torch.ones((), **kw)
        self.lam = torch.ones((), **kw)
        self.gamma = torch.ones((), **kw)
        self.alpha = torch.ones((), **kw)
        self.scale = torch.ones((), **kw)
        self.gap = torch.zeros((), **kw)
        self.primal = torch.zeros((), **kw)
        self.dual = torch.zeros((), **kw)
        if str(device).startswith("cuda"):
            self.stream = torch.cuda.Stream(device=device)
            self.stream.wait_stream(torch.cuda.current_stream(device))
            with torch.cuda.stream(self.stream):
                for _ in range(3):
                    self.steps(8)
            self.stream.synchronize()
            self.graph = torch.cuda.CUDAGraph()
            with torch.cuda.graph(self.graph, stream=self.stream):
                self.steps(8)
            torch.cuda.current_stream(device).wait_stream(self.stream)
        else:
            self.graph = None

    def forward(self, u):
        fine = (self.w @ u @ self.w.T) * self.mask
        return torch.stack(
            [(self.t[j] * interpolate(fine, p)).sum((0, 1)) for j, p in enumerate(self.phases)]
        )

    def transpose(self, p):
        fine = sum(
            interpolate(self.t[j] * p[j], phase, True) for j, phase in enumerate(self.phases)
        )
        return self.w.T @ (fine * self.mask) @ self.w

    def steps(self, n):
        for _ in range(n):
            self.p.copy_((self.p + self.step * (self.forward(self.ub) - self.y)) / (1 + self.step))
            q = self.q + self.step * gradient(self.ub)
            length = torch.sqrt((q * q).sum((0, 2)))
            self.q.copy_(q / torch.clamp(length / self.lam, min=1)[None, :, None])
            v = self.u - self.step * (self.transpose(self.p) - divergence(self.q))
            length = torch.sqrt((v * v).sum(1))
            new = (
                v
                * torch.clamp(1 - self.step * self.alpha / length.clamp_min(1e-32), min=0)[:, None]
                / (1 + self.step * self.gamma)
            )
            self.ub.copy_(2 * new - self.u)
            self.u.copy_(new)
        residual = self.forward(self.u) - self.y
        gu = gradient(self.u)
        self.primal.copy_(
            0.5 * (residual * residual).sum()
            + self.lam * torch.sqrt((gu * gu).sum((0, 2))).sum()
            + 0.5 * self.gamma * (self.u * self.u).sum()
            + self.alpha * torch.sqrt((self.u * self.u).sum(1)).sum()
        )
        stationarity = self.transpose(self.p) - divergence(self.q)
        radius = torch.clamp(torch.sqrt((stationarity * stationarity).sum(1)) - self.alpha, min=0)
        self.dual.copy_(
            -0.5 * (self.p * self.p).sum()
            - (self.p * self.y).sum()
            - 0.5 * (radius * radius).sum() / self.gamma
        )
        self.gap.copy_((self.primal - self.dual) / self.scale)

    def __call__(self, t, y, mask, initial, lam, alpha, gamma=0.05, iterations=2048):
        with torch.inference_mode():
            initial = initial.reshape(initial.shape[0], 2, 32, 4, 32, 4).mean(axis=(3, 5))
            for name, value in [
                ("t", t),
                ("y", y),
                ("mask", mask[:, None]),
                ("u", initial),
                ("ub", initial),
            ]:
                getattr(self, name).copy_(
                    torch.from_numpy(np.array(value, dtype=np.float64, order="C", copy=True))
                )
            self.ub.copy_(self.u)
            self.p.zero_()
            self.q.zero_()
            # Jensen + maximum column sum bounds the clamped interpolation.
            bound = 8 + 16 * 1.5625 * sum(
                float(np.max(np.sum(t[j] ** 2, axis=(0, 1)))) for j in range(len(self.phases))
            )
            self.step.fill_(0.95 / np.sqrt(bound))
            self.lam.fill_(lam)
            self.gamma.fill_(gamma)
            self.alpha.fill_(alpha)
            signal_scale = max(float((self.forward(self.u) ** 2).sum()) * 0.5, 1.0)
            self.scale.fill_(signal_scale)
            n = 0
            while n < iterations:
                count = min(8, iterations - n)
                if self.graph is not None and count == 8:
                    self.graph.replay()
                else:
                    self.steps(count)
                n += count
                gap = float(self.gap)
                if gap < -1e-8:
                    raise ArithmeticError("Invalid raw-fit dual gap")
                if gap < 1e-5:
                    break
            return ((self.w @ self.u @ self.w.T) * self.mask).cpu().numpy().copy(), {
                "iterations": n,
                "relative_gap": max(gap, 0.0),
                "scale": signal_scale,
                "primal": float(self.primal),
                "dual": float(self.dual),
                "converged": gap < 1e-5,
                "lambda": lam,
                "group_L1": alpha,
                "ridge": gamma,
                "latent_grid": [32, 32],
                "latent_node_spacing_native": 8,
                "step": float(self.step),
                "operator_norm_squared_bound": bound,
            }


@lru_cache(maxsize=16)
def solver(k, phases, device):
    return Solver(k, phases, device)


def fit(
    residual,
    variance,
    colors,
    frequencies,
    masks,
    initial,
    lam,
    alpha,
    transport,
    device="cuda",
    iterations=2048,
):
    phases = (0, 1, 2, 3)
    yy, xx = np.mgrid[:128, :128]
    unit = float(np.median(np.sqrt(variance[np.flatnonzero(np.asarray(colors) == 1)])))
    t = []
    y = []
    for p in phases:
        oy, ox = divmod(p, 2)
        v = np.sqrt(np.maximum(variance[p], 1e-10))
        columns = []
        for n, (fx, fy) in enumerate(frequencies):
            angle = 2 * np.pi * (fx * (2 * xx + ox) + fy * (2 * yy + oy))
            columns.append(
                np.einsum(
                    "ij,ihw->jhw",
                    transport[n, int(colors[p])],
                    np.stack([np.cos(angle), np.sin(angle)]),
                )
                * unit
                / v
            )
        t.append(columns)
        y.append(residual[p] / v)
    value, info = solver(len(frequencies), phases, device)(
        np.asarray(t),
        np.asarray(y),
        np.asarray(masks),
        np.asarray(initial) / unit,
        lam,
        alpha,
        iterations=iterations,
    )
    return value * unit, info


from demosaic.phase_envelope import local_green_phasor
from demosaic.phase_frequency import fit_refined
from demosaic.phase_harmonic import native_envelope
from demosaic.phase_sparse import coefficient_tv, connected_support
from demosaic.phase_tv import correct_edge_phase_patch

POLICIES = {"raw-RGB-group.125": 0.125}


def candidates(packed, variance, colors, base, *, device="cpu", iterations=2048):
    fitted = fit_refined(packed, variance, colors, base)
    base = fitted["base"]
    peaks = fitted["peaks"]
    if not peaks:
        return {k: base.copy() for k in POLICIES}, {"peaks": []}
    if any(s.get("clipped_window_fallback") for s in fitted["searches"]):
        value, info = correct_edge_phase_patch(
            packed, variance, colors, base, device=device, refine_frequency=True
        )
        return {k: value.copy() for k in POLICIES}, {
            "peaks": peaks,
            "clipping_fallback": True,
            "baseline": info,
        }
    beta, cov = fitted["beta"], fitted["covariance"]
    planes = np.stack(
        [(fitted["plane"] @ beta[3 * p : 3 * p + 3]).reshape(128, 128) for p in range(4)]
    )
    active = []
    gates = []
    locals = []
    initial = []
    masks = []
    support_infos = []
    for k, (fx, fy, score) in enumerate(peaks):
        ids = [12 + 6 * k + 2, 12 + 6 * k + 3]
        g = beta[ids]
        power = float(g @ np.linalg.solve(cov[np.ix_(ids, ids)], g))
        gate = min(fitted["gate_limits"][k], max(0, 1 - 9 / max(power, 1e-12)))
        if gate == 0:
            continue
        small, _, local = local_green_phasor(
            fitted["residual"], fitted["variance"], fitted["colors"], planes, (fx, fy), 16
        )
        _, _, coarse = local_green_phasor(
            fitted["residual"], fitted["variance"], fitted["colors"], planes, (fx, fy), 32
        )
        a, b, d = coarse["covariance"]
        noise = np.sqrt((local["covariance"][0] + local["covariance"][2]) / 2)
        support, info = coefficient_tv(small, 16 * noise, 0.5 * noise, device=device)
        power = np.maximum(
            0,
            (d * support[0] ** 2 - 2 * b * support[0] * support[1] + a * support[1] ** 2)
            / np.maximum(a * d - b * b, 1e-32),
        )
        mask, components = connected_support(power > 9)
        if not mask.any():
            continue
        active.append(k)
        gates.append(gate)
        locals.append(coarse)
        initial.append(support)
        masks.append(mask)
        support_infos.append({"solver": info, "components": components})
    if not active:
        return {k: base.copy() for k in POLICIES}, {"peaks": peaks, "active": []}
    yy, xx = np.mgrid[:256, :256]
    apron = np.sin(np.pi * np.arange(32) / 64) ** 2
    one = np.ones(256)
    one[:32], one[-32:] = apron, apron[::-1]
    taper = one[:, None] * one[None, :]
    values = {}
    infos = {}
    transport = []
    for k in active:
        g = beta[[12 + 6 * k + 2, 12 + 6 * k + 3]]
        color_maps = []
        for c in range(3):
            c0, c1 = beta[12 + 6 * k + 2 * c : 12 + 6 * k + 2 * c + 2]
            color_maps.append(
                np.array(
                    [
                        [c0 * g[0] + c1 * g[1], c0 * g[1] - c1 * g[0]],
                        [c1 * g[0] - c0 * g[1], c1 * g[1] + c0 * g[0]],
                    ]
                )
                / float(g @ g)
            )
        transport.append(color_maps)
    transport = np.asarray(transport)
    for policy, alpha in POLICIES.items():
        coeffs, info = fit(
            fitted["residual"] - planes,
            variance,
            colors,
            [(peaks[k][0], peaks[k][1]) for k in active],
            masks,
            initial,
            4.0,
            alpha,
            transport,
            device=device,
            iterations=iterations,
        )
        field = np.zeros_like(base)
        for n, k in enumerate(active):
            fx, fy, _ = peaks[k]
            coeff = coeffs[n]
            a, b, d = locals[n]["covariance"]
            g = beta[[12 + 6 * k + 2, 12 + 6 * k + 3]]
            lp = np.maximum(
                0,
                (d * coeff[0] ** 2 - 2 * b * coeff[0] * coeff[1] + a * coeff[1] ** 2)
                / np.maximum(a * d - b * b, 1e-32),
            )
            scale = np.maximum(0, 1 - 9 / np.maximum(lp, 1e-16))
            re = (g[0] * coeff[0] + g[1] * coeff[1]) / float(g @ g)
            im = (g[1] * coeff[0] - g[0] * coeff[1]) / float(g @ g)
            amplitude = np.hypot(re, im)
            scale *= np.minimum(1, 3 / np.maximum(amplitude, 1e-16))
            r = native_envelope(re * scale)
            i = native_envelope(im * scale)
            angle = 2 * np.pi * (fx * xx + fy * yy)
            for c in range(3):
                j = 12 + 6 * k + 2 * c
                field[c] += gates[n] * (
                    (beta[j] * r + beta[j + 1] * i) * np.cos(angle)
                    + (beta[j + 1] * r - beta[j] * i) * np.sin(angle)
                )
        values[policy] = base + field * taper[None]
        infos[policy] = info
    return values, {
        "peaks": peaks,
        "active": active,
        "support": support_infos,
        "solvers": infos,
        "frequency_searches": fitted["searches"],
    }


def main():
    import argparse
    import hashlib
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "observation",
        type=Path,
        help="Archived native256 NPZ with packed/variance/colors; targets are not read",
    )
    parser.add_argument("parent", type=Path, help="Parent camera-RGB NPY,3x256x256 or1x3x256x256")
    parser.add_argument("output", type=Path, help="Research output NPY; must not exist")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    args = parser.parse_args()
    if args.output.exists() or args.output.with_suffix(".json").exists():
        parser.error("Output or JSON sidecar already exists")
    with np.load(args.observation) as archive:
        packed, variance, colors = [archive[k][0] for k in ("packed", "variance", "colors")]
    parent = np.load(args.parent)
    if parent.ndim == 4:
        parent = parent[0]
    values, info = candidates(packed, variance, colors, parent, device=args.device)
    with args.output.open("xb") as stream:
        np.save(stream, values["raw-RGB-group.125"][None])

    def binding(path):
        path = Path(path).resolve()
        return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    metadata = {
        "operator": binding(__file__),
        "observation": binding(args.observation),
        "parent": binding(args.parent),
        "output": binding(args.output),
        "device": args.device,
        "diagnostic": info,
        "neural_calls": 0,
        "RAW_opens": 0,
        "scope": "Unadopted serial research-only RAW refit; supplied variance is used as-is, targets/reference are not read. Native output, no display transform or image export.",
    }
    args.output.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    main()
