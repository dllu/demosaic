"""Local A-only WLS amplitudes with fixed broad-context carrier geometry."""

from types import SimpleNamespace

import numpy as np

from .local_validated_waves import _box_sums


def gram_inverse(gram, rcond=1e-8):
    """Column-normalized PSD inverse; cutoff corresponds to SVD rcond1e-4."""
    diagonal = np.diagonal(gram, axis1=-2, axis2=-1)
    scale = np.divide(
        1, np.sqrt(np.maximum(diagonal, 0)), out=np.zeros_like(diagonal), where=diagonal > 0
    )
    normalized = gram * scale[..., :, None] * scale[..., None, :]
    eigenvalues, eigenvectors = np.linalg.eigh(normalized)
    keep = eigenvalues > rcond * np.maximum(eigenvalues[..., -1:], 0)
    inverse = np.divide(1, eigenvalues, out=np.zeros_like(eigenvalues), where=keep)
    result = (eigenvectors * inverse[..., None, :]) @ eigenvectors.swapaxes(-2, -1)
    return result * scale[..., :, None] * scale[..., None, :]


class SpatialCarrierOperator:
    """Fixed linear query-grid fits; no B samples or parent in construction.

    Global A-only edge/carrier/nuisance/variance fields remain fixed. Each query
    uses a native box, per-color discovery samples and normalized physical
    inverse variance. Full and per-direction-null regressions share support.
    Coefficients interpolate in native coordinates before RGB evaluation.
    """

    def __init__(
        self, candidate, colors, *, window=129, stride=32, background=None, nuisance_mode="local"
    ):
        self.candidate = candidate
        self.mask = np.asarray(candidate.discovery_mask)
        self.colors = np.asarray(colors)
        self.shape = self.mask.shape
        if (
            type(window) is not int
            or window < 17
            or window % 2 != 1
            or type(stride) is not int
            or not 1 <= stride <= 64
            or self.colors.shape != self.shape
            or self.mask.dtype != bool
            or not np.isin(self.colors, (0, 1, 2)).all()
            or not np.isfinite(candidate.variance_cfa).all()
            or np.any(candidate.variance_cfa <= 0)
            or nuisance_mode not in ("local", "global")
        ):
            raise ValueError(
                "Require a native CFA mask, positive A-only variance and local geometry"
            )
        if background is not None and (
            background.rgb.shape != (3, *self.shape)
            or not np.array_equal(background.discovery_mask, self.mask)
        ):
            raise ValueError("Require the matching A-only RGB nuisance field")
        self.window = window
        self.nuisance_mode = nuisance_mode
        self.ay, self.ax = [np.unique(np.r_[np.arange(0, n, stride), n - 1]) for n in self.shape]
        self.design = candidate.design
        self.units = candidate.unit_slices
        self.nuisance_columns = candidate.wave_slices[0][0]
        if nuisance_mode == "global":
            self.design = candidate.design[:, self.nuisance_columns :]
            self.units = tuple(
                (a - self.nuisance_columns, b - self.nuisance_columns)
                for a, b in candidate.unit_slices
            )
        self.keep = []
        for start, stop in self.units:
            keep = np.ones(self.design.shape[1], bool)
            keep[start:stop] = False
            self.keep.append(keep)
        self.groups = []
        fractions, spectra = [], []
        for color in range(3):
            selected = self.mask & (self.colors == color)
            if selected.sum() < 16:
                raise ValueError("Require discovery samples from every color")
            weights = np.zeros(self.shape)
            variance = candidate.variance_cfa[selected]
            weights[selected] = np.median(variance) / variance
            gram = np.empty(
                (len(self.ay), len(self.ax), self.design.shape[1], self.design.shape[1])
            )
            for i in range(self.design.shape[1]):
                for j in range(i + 1):
                    value = weights * (self.design[:, i] * self.design[:, j]).reshape(self.shape)
                    gram[..., i, j] = gram[..., j, i] = self.box(value)
            full_inverse = gram_inverse(gram)
            null_inverses = [gram_inverse(gram[..., keep, :][..., keep]) for keep in self.keep]
            native = self.design
            if background is not None and nuisance_mode == "local":
                native = native.copy()
                native[:, candidate.wave_slices[0][0] - 1] = np.minimum(
                    background.rgb[color].ravel(), 1
                )
            self.groups.append(
                {
                    "selected": selected,
                    "weights": weights,
                    "inverse": full_inverse,
                    "null_inverses": null_inverses,
                    "native": native,
                }
            )
            if nuisance_mode == "global":
                native_background = candidate.design[:, : self.nuisance_columns].copy()
                if background is not None:
                    native_background[:, -1] = np.minimum(background.rgb[color].ravel(), 1)
                self.groups[-1].update(
                    global_operator=candidate.operators[color],
                    sensor_background=candidate.design[selected.ravel(), : self.nuisance_columns],
                    native_background=native_background,
                )
            color_fraction, color_spectrum = [], []
            for (start, stop), keep, inverse in zip(
                self.units, self.keep, null_inverses, strict=True
            ):
                waves = gram[..., start:stop, start:stop]
                cross = gram[..., start:stop, :][..., keep]
                residual = waves - cross @ inverse @ cross.swapaxes(-2, -1)
                wave_energy = np.trace(waves, axis1=-2, axis2=-1)
                total_energy = wave_energy.sum()
                color_fraction.append(
                    float(np.trace(residual, axis1=-2, axis2=-1).sum() / total_energy)
                    if total_energy
                    else 0
                )
                values, vectors = np.linalg.eigh(waves)
                root = np.divide(
                    1,
                    np.sqrt(np.maximum(values, 0)),
                    out=np.zeros_like(values),
                    where=values > 1e-12 * np.maximum(values[..., -1:], 0),
                )
                root = (vectors * root[..., None, :]) @ vectors.swapaxes(-2, -1)
                normalized = root @ residual @ root
                average = np.sum(normalized * wave_energy[..., None, None], axis=(0, 1)) / max(
                    total_energy, 1e-30
                )
                color_spectrum.append(np.linalg.eigvalsh(average).tolist())
            fractions.append(color_fraction)
            spectra.append(color_spectrum)
        self.fractions = np.asarray(fractions).T
        self.spectra = np.asarray(spectra).transpose(1, 0, 2)

    def box(self, values):
        return _box_sums(values, self.ay, self.ax, self.window)

    def interpolate(self, values):
        h, w = self.shape
        horizontal = np.stack([np.interp(np.arange(w), self.ax, row) for row in values])
        return np.stack(
            [np.interp(np.arange(h), self.ay, horizontal[:, x]) for x in range(w)], axis=1
        )

    def coefficients(self, values, group):
        selected = group["selected"]
        if values.shape != self.shape or not np.isfinite(values[selected]).all():
            raise ValueError("Require finite discovery values on the fixed native grid")
        weighted = np.zeros(self.shape)
        discovery = values[selected]
        if self.nuisance_mode == "global":
            coefficient = group["global_operator"] @ discovery
            discovery = (
                discovery - group["sensor_background"] @ coefficient[: self.nuisance_columns]
            )
        weighted[selected] = discovery * group["weights"][selected]
        rhs = np.stack(
            [self.box(weighted * column.reshape(self.shape)) for column in self.design.T], axis=-1
        )
        full = np.einsum("...ij,...j->...i", group["inverse"], rhs)
        nulls = [
            np.einsum("...ij,...j->...i", inverse, rhs[..., keep])
            for keep, inverse in zip(self.keep, group["null_inverses"], strict=True)
        ]
        return full, nulls

    def evaluate(self, coefficient, native):
        result = np.zeros(self.shape)
        for column, field in zip(native.T, coefficient.transpose(2, 0, 1), strict=True):
            result += self.interpolate(field) * column.reshape(self.shape)
        return result

    def predict(self, raw):
        raw = np.asarray(raw, np.float64)
        full, nulls = np.empty(self.shape), np.empty((len(self.units), *self.shape))
        for color, group in enumerate(self.groups):
            coefficient, null_coefficients = self.coefficients(raw, group)
            destination = self.colors == color
            background = np.zeros(self.shape)
            if self.nuisance_mode == "global":
                global_coefficient = group["global_operator"] @ raw[group["selected"]]
                background = (
                    group["native_background"] @ global_coefficient[: self.nuisance_columns]
                ).reshape(self.shape)
            full[destination] = (background + self.evaluate(coefficient, group["native"]))[
                destination
            ]
            for direction, (keep, value) in enumerate(
                zip(self.keep, null_coefficients, strict=True)
            ):
                nulls[direction, destination] = (
                    background + self.evaluate(value, group["native"][:, keep])
                )[destination]
        return SimpleNamespace(
            full_cfa=full,
            conditional_null_cfa=nulls,
            discovery_mask=self.mask,
            variance_cfa=self.candidate.variance_cfa,
            unit_keys=self.candidate.unit_keys,
        )

    def components(self, raw, parent):
        raw, parent = np.asarray(raw, np.float64), np.asarray(parent, np.float64)
        if parent.shape != (3, *self.shape) or not np.isfinite(parent).all():
            raise ValueError("Require matching finite RGB parent after validation")
        conditional = np.empty((len(self.units), 3, *self.shape))
        sinusoidal = np.empty_like(conditional)
        for color, group in enumerate(self.groups):
            values = np.zeros(self.shape)
            selected = group["selected"]
            values[selected] = raw[selected] - parent[color, selected]
            coefficient, null_coefficients = self.coefficients(values, group)
            full = self.evaluate(coefficient, group["native"])
            for direction, ((start, stop), keep, value) in enumerate(
                zip(self.units, self.keep, null_coefficients, strict=True)
            ):
                conditional[direction, color] = full - self.evaluate(
                    value, group["native"][:, keep]
                )
                sinusoidal[direction, color] = self.evaluate(
                    coefficient[..., start:stop], group["native"][:, start:stop]
                )
        return (conditional, self.fractions, self.spectra), sinusoidal
