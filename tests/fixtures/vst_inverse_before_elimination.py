"""Frozen inverse before removing unused closed-form work from table mode."""

import math

import torch

from demosaic.precision import ieee_fp32

SOURCE_SHA256 = "355124a374177f1c08271834149c5979ab3477fdf255c60aa7cee0d47792a76b"


def inverse_before_elimination(self, stabilized):
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
            index = torch.searchsorted(self.expected, z.contiguous()).clamp(1, len(self.means) - 1)
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
