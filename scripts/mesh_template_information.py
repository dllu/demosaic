"""Conditional linear template evidence; exact hidden templates are required.

This is not an inference estimator or a recoverability bound. The signal,
background and physical variances may use clean construction data. Its linear
variance is exact for independent pre-ADC noise with the supplied second
moments; ADC clipping/quantization and uncertainty in the template are outside
that statement. No restored RGB is constructed here.
"""

import numpy as np


def tiled_template_fit(signal, residuals, weight_variance, actual_variances, block):
    """Fit a shared amplitude plus separate affine nuisance in each CFA phase.

    All arrays are P×H×W. Blocks use the packed sensor grid; native context
    width is twice `block`. The template and background-derived weights are
    fixed before looking at the observed residual. Each residual can have its
    own conditional variance, or None when its covariance is unknown (e.g. a
    nonlinear parent's output). No uncertainty is assigned to that parent.
    """
    template = np.asarray(signal, dtype=np.float64)
    weights_variance = np.asarray(weight_variance, dtype=np.float64)
    if (
        template.ndim != 3
        or min(template.shape) < 1
        or template.shape != weights_variance.shape
        or not np.isfinite(template).all()
        or not np.isfinite(weights_variance).all()
        or np.any(weights_variance <= 0)
        or type(block) is not int
        or block < 2
        or template.shape[-2] % block
        or template.shape[-1] % block
        or set(residuals) != set(actual_variances)
    ):
        raise ValueError("Finite aligned template/positive weights and divisible blocks required")
    values, variances = {}, {}
    for key, value in residuals.items():
        value = np.asarray(value, dtype=np.float64)
        variance = actual_variances[key]
        if value.shape != template.shape or not np.isfinite(value).all():
            raise ValueError("Residuals must be finite and match the template")
        values[key] = value
        if variance is not None:
            variance = np.asarray(variance, dtype=np.float64)
            if (
                variance.shape != template.shape
                or not np.isfinite(variance).all()
                or np.any(variance < 0)
            ):
                raise ValueError("Actual variances must be finite, nonnegative and aligned")
        variances[key] = variance
    phases, height, width = template.shape
    tile_shape = (phases, height // block, block, width // block, block)

    def tiles(value):
        return value.reshape(tile_shape).transpose(0, 1, 3, 2, 4)

    yy, xx = np.meshgrid(np.linspace(-1, 1, block), np.linspace(-1, 1, block), indexing="ij")
    basis = np.stack((np.ones_like(xx), xx, yy), axis=-1)
    weight = 1 / tiles(weights_variance)
    raw_template = tiles(template)
    gram = np.einsum("pijxy,xya,xyb->pijab", weight, basis, basis)
    rhs = np.einsum("pijxy,xya,pijxy->pija", weight, basis, raw_template)
    coefficients = np.linalg.solve(gram, rhs[..., None])[..., 0]
    centered = raw_template - np.einsum("xya,pija->pijxy", basis, coefficients)
    score = weight * centered
    energy = np.sum(weight * centered**2, axis=(0, 3, 4))
    # The residual formulation avoids subtraction of nearly equal energies.
    # Roundoff left after projecting an exactly affine template is not signal.
    # This relative numerical tolerance is not a noise/detection threshold.
    original_energy = np.sum(weight * raw_template**2, axis=(0, 3, 4))
    supported = energy > (64 * np.finfo(np.float64).eps) ** 2 * original_energy
    energy = np.where(supported, energy, 0)
    output = {"weighted_template_energy": energy, "amplitudes": {}, "amplitude_variances": {}}
    for key, value in values.items():
        numerator = np.sum(score * tiles(value), axis=(0, 3, 4))
        amplitude = np.divide(numerator, energy, out=np.full_like(energy, np.nan), where=supported)
        output["amplitudes"][key] = amplitude
        variance = variances[key]
        if variance is None:
            output["amplitude_variances"][key] = None
        else:
            numerator = np.sum(score**2 * tiles(variance), axis=(0, 3, 4))
            output["amplitude_variances"][key] = np.divide(
                numerator, energy**2, out=np.full_like(energy, np.nan), where=supported
            )
    return output
