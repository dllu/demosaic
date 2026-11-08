"""Color-grounded innovation waves above a frozen trained pooled-wave anchor.

Four actual CFA phases supply affine-detrended least-squares wave amplitudes.
A contextual real gain cannot rotate phase or synthesize red/blue from green.
Those restrictions are not evidence of noisy-flat safety or trained quality.
"""

import math

import torch
from torch import nn
from torch.nn import functional as F

from .cfa import mosaic
from .late_innovation_wave import innovation_phase_bins
from .late_local_phase_evidence_matching import (
    _box_sums,
    _geometry,
    _interpolate_grid,
    local_projection_grid,
)
from .late_pooled_phase_wave import LatePooledPhaseWaveDetail, _green_layout
from .late_spatial_context_wave import fixed_bin_support_context
from .precision import ieee_fp32


def _carrier(height, width, bins_yx):
    y, x = bins_yx.unbind(-1)
    ky = torch.where(y <= (height - 1) // 2, y, y - height)
    kx = torch.where(x <= (width - 1) // 2, x, x - width)
    yy, xx = torch.meshgrid(
        torch.arange(height, device=y.device),
        torch.arange(width, device=y.device),
        indexing="ij",
    )
    period = math.lcm(height, width)
    phase = (
        ky[:, None, None] * yy * (period // height) + kx[:, None, None] * xx * (period // width)
    ).remainder(period)
    phase = torch.where(phase > period // 2, phase - period, phase)
    angle = phase.double() * (2 * math.pi / period)
    return torch.polar(torch.ones_like(angle), angle), ky, kx, yy, xx


def _wave_inverse(height, width, bins_yx, boxes):
    """Pseudoinverse of the real wave Gram after removing a local affine plane.

    Basis order is cos(theta), -sin(theta). Truncate eigenvalues <=1e-10 times
    box area, including singular Nyquist quadratures; this is numerical rank,
    not a signal/noise detection threshold. Every phase uses the same matrix.
    """
    carrier, _, _, yy, xx = _carrier(height, width, bins_yx)
    carrier = carrier.conj()
    x0, y0, nx, ny = boxes.double().unbind(1)
    cx, cy, count = x0 + (nx - 1) / 2, y0 + (ny - 1) / 2, nx * ny
    moment = _box_sums(carrier, boxes)
    mx = _box_sums(carrier * xx.double(), boxes) - cx * moment
    my = _box_sums(carrier * yy.double(), boxes) - cy * moment
    second = _box_sums(carrier.square(), boxes)
    rr, ii, ri = (count + second.real) / 2, (count - second.real) / 2, second.imag / 2
    for value, norm in [
        (moment, count),
        (mx, ny * nx * (nx.square() - 1) / 12),
        (my, nx * ny * (ny.square() - 1) / 12),
    ]:
        rr = rr - value.real.square() / norm
        ii = ii - value.imag.square() / norm
        ri = ri - value.real * value.imag / norm
    gram = torch.stack((rr, ri, ri, ii), -1).reshape(*rr.shape, 2, 2)
    eigenvalues, vectors = torch.linalg.eigh(gram)
    keep = eigenvalues > count[None, :, None] * 1e-10
    reciprocal = torch.where(
        keep, eigenvalues.clamp_min(torch.finfo(torch.float64).tiny).reciprocal(), 0
    )
    inverse = (vectors * reciprocal[..., None, :]) @ vectors.transpose(-2, -1)
    return inverse, keep.sum(-1)


@torch.no_grad()
def cfa_innovation_wave_maps(field, variance, colors, bins_yx, valid, *, window=65, stride=32):
    """Measured physical RGB waves and twelve large-window context coordinates.

    Actual CFA offsets are removed before interpolating complex amplitudes.
    Green averages the two measured amplitudes; red and blue use their own
    samples. No other color supplies their synthesis basis. The first six
    context channels preserve the old green power/cross/frequency coordinates.
    Six more describe red/blue nominal power and cross evidence with green.

    Nominal coefficients divide the old projected sum by supplied RAW trace
    variance. They are not calibrated innovation confidence, and their windows
    reuse the same samples. Physical synthesis instead solves the local real
    wave Gram. It does not multiply normalized powers by a local output sigma.
    """
    green = _green_layout(field, variance, colors)
    batch, _, height, width = field.shape
    if (
        bins_yx.ndim != 4
        or bins_yx.shape[:2] != (batch, 2)
        or bins_yx.shape[-1] != 2
        or not 1 <= bins_yx.shape[2] <= 8
        or bins_yx.dtype != torch.int64
        or bins_yx.device != field.device
        or valid.shape != bins_yx.shape[:-1]
        or valid.dtype != torch.bool
        or valid.device != field.device
        or not bool(((bins_yx >= 0) & (bins_yx < bins_yx.new_tensor([height, width]))).all())
    ):
        raise ValueError("Expected matching integer Nx2xpeaksx2 bins and boolean validity")
    if (
        type(window) is not int
        or window < 3
        or window % 2 != 1
        or type(stride) is not int
        or not 1 <= stride <= 512
    ):
        raise ValueError("Expected an odd window>=3 and stride1..512")
    colors = torch.as_tensor(colors, device=field.device)
    if colors.ndim == 1:
        colors = colors[None].expand(batch, -1)
    red = torch.where(colors == 0)[1].reshape(batch, 1)
    blue = torch.where(colors == 2)[1].reshape(batch, 1)
    order = torch.cat((red, green, blue), 1)
    index = order[:, :, None, None].expand(-1, -1, height, width)
    raw, noise = field.gather(1, index), variance.gather(1, index)
    contexts, waves, powers, ranks = [], [], [], []
    with torch.autocast(field.device.type, enabled=False), ieee_fp32():
        ay, ax, boxes = _geometry(height, width, window, stride, field.device)
        for direction, (a, b) in enumerate([(1, 2), (2, 1)]):
            for peak in range(bins_yx.shape[2]):
                chosen = bins_yx[:, direction, peak]
                carrier, ky, kx, _, _ = _carrier(height, width, chosen)
                coefficient, trace = local_projection_grid(raw, noise, chosen, boxes)
                inverse, rank = _wave_inverse(height, width, chosen, boxes)
                rhs = torch.stack((coefficient.real, coefficient.imag), -1)
                amplitude = (inverse[:, None] @ rhs[..., None]).squeeze(-1)
                amplitude = torch.complex(amplitude[..., 0], amplitude[..., 1])
                z = coefficient / trace.clamp_min((1 / 65535) ** 2).sqrt()
                powers.append(z.abs().square().reshape(batch, 4, len(ay), len(ax)))
                angle = math.pi * (
                    ky[:, None].double() * (order // 2) / height
                    + kx[:, None].double() * (order % 2) / width
                )
                transport = torch.polar(torch.ones_like(angle), -angle)[:, :, None, None]

                def interpolate(value, offset=transport):
                    return (
                        _interpolate_grid(
                            value.reshape(batch, 4, len(ay), len(ax)), ay, ax, height, width
                        )
                        * offset
                    )

                z, amplitude = interpolate(z), interpolate(amplitude)
                first, second = z[:, a], z[:, b]
                pa, pb = first.abs().square(), second.abs().square()
                cross = first * second.conj() / ((1 + pa) * (1 + pb)).sqrt()
                strength = (pa + pb) / (1 + pa + pb)
                old = [
                    pa.log1p(),
                    pb.log1p(),
                    cross.real,
                    cross.imag,
                    kx[:, None, None].double() / (2 * width) * strength,
                    ky[:, None, None].double() / (2 * height) * strength,
                ]
                mean_green = (first + second) / math.sqrt(2)
                pg = mean_green.abs().square()
                pr, pblue = z[:, 0].abs().square(), z[:, 3].abs().square()
                cross_r = z[:, 0] * mean_green.conj() / ((1 + pr) * (1 + pg)).sqrt()
                cross_b = z[:, 3] * mean_green.conj() / ((1 + pblue) * (1 + pg)).sqrt()
                context = torch.stack(
                    old
                    + [
                        pr.log1p(),
                        pblue.log1p(),
                        cross_r.real,
                        cross_r.imag,
                        cross_b.real,
                        cross_b.imag,
                    ],
                    1,
                ).to(field.dtype)
                rgb = torch.stack(
                    (amplitude[:, 0], (amplitude[:, 1] + amplitude[:, 2]) / 2, amplitude[:, 3]), 1
                )
                rgb = rgb * carrier[:, None]
                wave = torch.stack((rgb.real, rgb.imag), 2).to(field.dtype)
                usable = valid[:, direction, peak, None, None, None]
                contexts.append(torch.where(usable, context, torch.zeros_like(context)))
                waves.append(torch.where(usable[:, :, None], wave, torch.zeros_like(wave)))
                ranks.append(rank)
        return (
            torch.stack(contexts, 1),
            torch.stack(waves, 1),
            {
                "canonical_phase_indices": order,
                "bin_yx": bins_yx,
                "valid": valid,
                "centers_y": ay,
                "centers_x": ax,
                "boxes_xywh": boxes,
                "nominal_center_power": torch.stack(powers, 1),
                "wave_gram_rank": torch.stack(ranks, 1),
            },
        )


class CFAInnovationWaveReadout(nn.Module):
    """451 parameters: 24->16->3 real gates, bounded to [-1,1] by tanh.

    Each color multiplies its own measured complex wave by one real gate.
    Native phase transport is explicit. Contributions sum over selected bins,
    as Fourier modes do; overlapping local estimates are not independent.
    Zero final weights exactly retain the anchor. Nonzero noise still gives
    nonzero waves; these structural bounds establish no flat safety guarantee.
    """

    def __init__(self):
        super().__init__()
        with torch.random.fork_rng(devices=[]):
            torch.set_rng_state(torch.Generator(device="cpu").manual_seed(19801).get_state())
            self.context = nn.Conv2d(24, 16, 1, device="cpu")
            self.gates = nn.Conv2d(16, 3, 1, device="cpu")
        nn.init.zeros_(self.gates.weight)
        nn.init.zeros_(self.gates.bias)

    def forward(self, context, waves, bins_yx):
        if (
            context.ndim != 5
            or context.shape[0] < 1
            or context.shape[1] not in range(2, 17, 2)
            or context.shape[2] != 24
            or min(context.shape[-2:]) < 8
            or max(context.shape[-2:]) > 512
            or context.dtype not in [torch.float32, torch.float64]
            or not bool(torch.isfinite(context).all())
        ):
            raise ValueError("Expected finite FP32/FP64 Nx(2*peaks)x24xHxW context, axes8..512")
        batch, count, _, height, width = context.shape
        if (
            waves.shape != (batch, count, 3, 2, height, width)
            or waves.dtype != context.dtype
            or waves.device != context.device
            or not bool(torch.isfinite(waves).all())
        ):
            raise ValueError("Expected matching finite Nx(2*peaks)x3x2xHxW physical RGB waves")
        if (
            bins_yx.shape != (batch, 2, count // 2, 2)
            or bins_yx.dtype != torch.int64
            or bins_yx.device != context.device
            or not bool(((bins_yx >= 0) & (bins_yx < bins_yx.new_tensor([height, width]))).all())
        ):
            raise ValueError("Expected matching integer FFT bins Nx2xpeaksx2")
        with torch.autocast(context.device.type, enabled=False), ieee_fp32():
            gates = self.gates(F.silu(self.context(context.flatten(0, 1)))).tanh()
            gates = gates.reshape(batch, count, 3, height, width)
            real, imag = (v * gates for v in waves.unbind(3))
            y, x = bins_yx.reshape(batch, count, 2).unbind(-1)
            ky = torch.where(y <= (height - 1) // 2, y, y - height)
            kx = torch.where(x <= (width - 1) // 2, x, x - width)
            offsets = context.new_tensor([[0, 0], [0, 1], [1, 0], [1, 1]]).double()
            angle = math.pi * (
                ky.double()[..., None] * offsets[:, 0] / height
                + kx.double()[..., None] * offsets[:, 1] / width
            )
            cosine, sine = [
                f(angle).to(context.dtype)[:, :, None, :, None, None]
                for f in [torch.cos, torch.sin]
            ]
            native = (real[:, :, :, None] * cosine - imag[:, :, :, None] * sine).sum(1)
            return F.pixel_shuffle(native.flatten(1, 2), 2)


class LateCFAInnovationWaveDetail(LatePooledPhaseWaveDetail):
    """193 frozen V195 tensors plus a fresh color-grounded four-tensor head."""

    def __init__(self, *, lower=1 / 64, **anchor_config):
        if not isinstance(lower, (int, float)) or not math.isfinite(lower) or not 0 < lower < 1 / 3:
            raise ValueError("Expected finite lower native frequency between0 and1/3")
        super().__init__(**anchor_config)
        self.requires_grad_(False)
        self.cfa_readout = CFAInnovationWaveReadout()
        self.lower = float(lower)
        self.train()

    def train(self, mode=True):
        super().train(False)
        if hasattr(self, "cfa_readout"):
            self.cfa_readout.train(mode)
        self.training = mode
        return self

    def initialize_anchor(self, state):
        expected = {n for n in self.state_dict() if not n.startswith("cfa_readout.")}
        if set(state) != expected or len(expected) != 193:
            raise ValueError("Expected the exact193-tensor trained pooled-wave anchor")
        if (
            self.cfa_readout.gates.weight.count_nonzero()
            or self.cfa_readout.gates.bias.count_nonzero()
        ):
            raise ValueError("Anchor initialization requires a fresh zero-output head")
        self.load_state_dict(dict(self.state_dict(), **state), strict=True)
        return self

    def forward(self, base, packed, variance, colors, wb=None, *, return_aux=False):
        with torch.autocast(base.device.type, enabled=False), ieee_fp32():
            with torch.no_grad():
                anchor, anchor_aux = super().forward(
                    base, packed, variance, colors, wb, return_aux=True
                )
                sigma = anchor_aux["sigma"]
                evaluated = bool(torch.any(sigma > 0))
                field = selection = evidence = support = context = waves = None
                if evaluated:
                    field = packed.float() - mosaic(anchor.float(), colors)
                    bins, valid, selection = innovation_phase_bins(
                        field, variance.float(), colors, peaks=self.evidence_peaks, lower=self.lower
                    )
                    large, waves, evidence = cfa_innovation_wave_maps(
                        field,
                        variance.float(),
                        colors,
                        bins,
                        valid,
                        window=self.evidence_window,
                        stride=self.evidence_stride,
                    )
                    small, support = fixed_bin_support_context(
                        field,
                        variance.float(),
                        colors,
                        bins,
                        valid,
                        windows=self.support_windows,
                        stride=self.support_stride,
                    )
                    context = torch.cat((large[:, :, :6], small, large[:, :, 6:]), 2)
            if evaluated:
                wave = self.cfa_readout(context, waves, bins)
                wave = torch.where(sigma > 0, wave, torch.zeros_like(wave))
                output = torch.where(sigma > 0, anchor + wave, anchor)
            else:
                wave, output = torch.zeros_like(anchor), anchor
            if return_aux:
                return output, {
                    "anchor_output": anchor,
                    "anchor_aux": anchor_aux,
                    "sigma": sigma,
                    "matching_evaluated": evaluated,
                    "measurement_field": field,
                    "wave_selection": selection,
                    "cfa_evidence": evidence,
                    "wave_support": support,
                    "cfa_context": context,
                    "cfa_waves": waves,
                    "wave_correction": wave,
                }
            return output
