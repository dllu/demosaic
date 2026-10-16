"""Generalized Anscombe stabilization and an expectation-based numerical inverse.

Independent implementation of the Poisson/Gaussian model and inversion in
Makitalo & Foi, IEEE TIP 2013, sections II-B and III-E/F. The transform is
centered by a constant to preserve precision for large read/shot ratios.
"""

import math
from functools import lru_cache

import numpy as np
import torch
from torch import nn

from .precision import ieee_fp32


@lru_cache(maxsize=1)
def expectation_grid():
    """Immutable integration grids shared by every physical noise profile.

    The Poisson probabilities depend on counts and means, not read noise.
    Building their large matrix and the quadrature nodes per image is wasted
    work when training draws fresh read noise coefficients for every sample.
    Keep the original arithmetic/reduction order for bitwise-identical tables.
    """
    counts = np.arange(321, dtype=np.float64)
    means = np.concatenate((np.linspace(0, 16, 1601), np.linspace(16.1, 128, 1120)))
    log_factorial = np.array([math.lgamma(n + 1) for n in counts])
    probability = np.exp(
        counts[None] * np.log(means.clip(1e-300))[:, None] - means[:, None] - log_factorial[None]
    )
    nodes, weights = np.polynomial.legendre.leggauss(96)
    gaussian_nodes, gaussian_weights = np.polynomial.hermite.hermgauss(32)
    arrays = counts, means, probability, nodes, weights, gaussian_nodes, gaussian_weights
    for array in arrays:
        array.flags.writeable = False
    return arrays


@lru_cache(maxsize=64)
def expectation_table(read_e):
    """Tabulate E[centered GAT(N + Gaussian)] for Poisson mean 0..128.

    96-node quadrature after a square-root substitution, Poisson counts
    0..320, and a fine low-count grid. The substitution removes the clipped
    square root's integration singularity at zero.
    For read_e>=16, the endpoint is negligible and centered 32-node Hermite
    quadrature avoids cancellation in the read-dominated Gaussian limit.
    These are numerical approximations, not exact symbolic expectations.
    """
    counts, means, probability, nodes, weights, gaussian_nodes, gaussian_weights = expectation_grid()
    q = 3 / 8 + read_e**2
    if read_e >= 16:
        # The clipped-root endpoint is >16 Gaussian standard deviations away.
        # Integrate the centered expression directly to avoid subtracting two
        # huge constants when read noise dominates shot noise.
        signal = counts[:, None] + math.sqrt(2) * read_e * gaussian_nodes
        centered = 2 * signal / (np.sqrt(signal + q) + math.sqrt(q))
        conditional = (centered * gaussian_weights).sum(1) / math.sqrt(math.pi)
    elif read_e:
        lower = np.sqrt(np.maximum(counts + q - 10 * read_e, 0))
        upper = np.sqrt(counts + q + 10 * read_e)
        radius = (upper - lower) / 2
        t = (upper + lower)[:, None] / 2 + radius[:, None] * nodes
        normal = (t**2 - counts[:, None] - q) / read_e
        density = np.exp(-(normal**2) / 2) / math.sqrt(2 * math.pi)
        conditional = (4 * t**2 / read_e * density * weights).sum(1) * radius
        conditional -= 2 * math.sqrt(q)
    else:
        conditional = 2 * counts / (np.sqrt(counts + q) + math.sqrt(q))
    expected = (probability * conditional[None]).sum(1)
    if not np.isfinite(expected).all() or not (np.diff(expected) > 0).all():
        raise ValueError("Noise profile does not produce a stable monotone inverse table")
    return expected, means


class GeneralizedAnscombe(nn.Module):
    def __init__(self, shot, read, *, inverse="table"):
        super().__init__()
        if not math.isfinite(shot) or not math.isfinite(read) or shot <= 0 or read < 0:
            raise ValueError("GAT requires finite positive shot and nonnegative read")
        if inverse not in ("table", "closedform", "algebraic"):
            raise ValueError("Unknown GAT inverse")
        self.shot, self.read, self.inverse_mode = float(shot), float(read), inverse
        self.read_e = math.sqrt(read) / shot
        self.q = 3 / 8 + self.read_e**2
        if inverse == "table":
            expected, means = expectation_table(self.read_e)
        else:
            expected, means = np.empty(0), np.empty(0)
        self.register_buffer("expected", torch.tensor(expected), persistent=False)
        self.register_buffer("means", torch.tensor(means), persistent=False)

    def forward(self, raw):
        with torch.autocast(raw.device.type, enabled=False), ieee_fp32():
            counts = (raw.double() / self.shot).clamp_min(-self.q)
            centered = 2 * counts / ((counts + self.q).sqrt() + math.sqrt(self.q))
            return centered.float()

    def inverse(self, stabilized):
        with torch.autocast(stabilized.device.type, enabled=False), ieee_fp32():
            z = stabilized.double()
            algebraic = z * math.sqrt(self.q) + z.square() / 4
            if self.inverse_mode == "algebraic":
                return (algebraic * self.shot).float()
            d = (z + 2 * math.sqrt(self.q)).clamp_min(1)
            closed = (
                algebraic
                + 0.25
                + math.sqrt(1.5) / (4 * d)
                - 11 / (8 * d.square())
                + 5 * math.sqrt(1.5) / (8 * d.pow(3))
            )
            if self.inverse_mode == "table":
                index = torch.searchsorted(self.expected, z.contiguous()).clamp(
                    1, len(self.means) - 1
                )
                left, right = self.expected[index - 1], self.expected[index]
                value = self.means[index - 1] + (z - left) / (right - left) * (
                    self.means[index] - self.means[index - 1]
                )
                # Linear low-end extrapolation preserves signed sensor estimates;
                # the published high-count approximation handles the upper tail.
                anchor_z = self.expected[-1]
                anchor = anchor_z * math.sqrt(self.q) + anchor_z.square() / 4
                # Match the tabulated correction continuously to the published
                # asymptotic inverse (Eq. 22); its remaining correction decays
                # as inverse signal. This avoids a seam at the table boundary.
                correction = self.means[-1] - anchor - 0.25
                tail = algebraic + 0.25 + correction * anchor / algebraic.clamp_min(anchor)
                value = torch.where(z > self.expected[-1], tail, value)
            else:
                value = closed
            return (value * self.shot).float()
