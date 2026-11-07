"""Attribute actual sampler calls to sensor transport or source construction."""

from contextlib import contextmanager
from unittest.mock import patch

import torch


@contextmanager
def count_source_draws():
    """Observe unchanged calls at the two sensor API boundaries.

    Procedural bandlimited textures also draw Gaussian values. Those draws
    remain separate from Poisson/read sensor noise. This is CPU data-builder
    instrumentation; use in a single data-construction thread.
    """
    import paired_response_data as paired

    from demosaic import suite

    counts = {
        "sensor_Poisson": 0,
        "sensor_Gaussian": 0,
        "procedural_Poisson": 0,
        "procedural_Gaussian": 0,
        "coupled_sensor_calls": 0,
        "ordinary_sensor_calls": 0,
    }
    depth = 0
    poisson, randn = torch.poisson, torch.randn
    coupled, ordinary = paired.coupled_sensor_noise, suite.add_noise

    def poisson_call(*args, **kwargs):
        counts[("sensor" if depth else "procedural") + "_Poisson"] += 1
        return poisson(*args, **kwargs)

    def gaussian_call(*args, **kwargs):
        counts[("sensor" if depth else "procedural") + "_Gaussian"] += 1
        return randn(*args, **kwargs)

    def sensor_call(fn, label, *args, **kwargs):
        nonlocal depth
        counts[label] += 1
        depth += 1
        try:
            return fn(*args, **kwargs)
        finally:
            depth -= 1

    def coupled_call(*args, **kwargs):
        return sensor_call(coupled, "coupled_sensor_calls", *args, **kwargs)

    def ordinary_call(*args, **kwargs):
        return sensor_call(ordinary, "ordinary_sensor_calls", *args, **kwargs)

    with (
        patch.object(torch, "poisson", poisson_call),
        patch.object(torch, "randn", gaussian_call),
        patch.object(paired, "coupled_sensor_noise", coupled_call),
        patch.object(suite, "add_noise", ordinary_call),
    ):
        yield counts
