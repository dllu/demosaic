"""Discarded CUDA test of fixed local RAW contrast at small residual units."""

import argparse
from contextlib import contextmanager
from pathlib import Path

import probe_raw_residual_units as experiment
import torch

from demosaic import packed_isotropic
from demosaic.precision import ieee_fp32
from demosaic.prior import box_mean


def raw_features(packed, mode):
    """Filter each CFA phase separately; never rescale using image statistics."""
    with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
        raw = packed.float()
        if mode == "raw":
            return raw
        if mode == "gain32-residual32":
            return raw * 32
        windows = {"local7-residual32": 7, "local31-residual32": 31}
        if mode not in windows:
            raise ValueError("Unknown local-contrast mode")
        return (raw - box_mean(raw, windows[mode])) * 32


@contextmanager
def coordinates(model, mode, batch):
    original = packed_isotropic.physical_features

    def features(packed, variance, colors, wb=None, matrix=None):
        legacy = original(packed, variance, colors, wb, matrix)
        return torch.cat((raw_features(packed, mode), legacy[:, 4:]), 1)

    packed_isotropic.physical_features = features
    try:
        with experiment.residual_units(model, 1 / 32):
            yield
    finally:
        packed_isotropic.physical_features = original


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    # Reuse the identical frozen four-arm training/evaluation machinery. All
    # models retain the same parameters; only this process-local feature hook
    # and the common1/32 residual scale change their forward calculation.
    experiment.coordinates = coordinates
    experiment.run(parser.parse_args().plan)
