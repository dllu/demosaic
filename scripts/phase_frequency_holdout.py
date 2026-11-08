"""Select frequencies in one green CFA phase and describe the other phase.

This within-image sample split is not an unseen-image validation set. Supplied
noisy variance proxies and fitted nuisance affect the statistics; no threshold
is calibrated here. The principal packed band has unresolved native aliases.
"""

import numpy as np
from green_phase_spectrum import tapered_spectrum


def select_phase_frequencies(spectrum, noise_variance, *, count=4):
    """Rank one phase only, suppressing nearby/conjugate bins after each pick."""
    spectrum = np.asarray(spectrum)
    noise_variance = np.asarray(noise_variance)
    if (
        spectrum.ndim != 2
        or noise_variance.shape != spectrum.shape
        or not np.isfinite(spectrum).all()
        or not np.isfinite(noise_variance).all()
        or (noise_variance <= 0).any()
        or not isinstance(count, int)
        or count < 1
    ):
        raise ValueError("Require finite 2D spectrum, positive matching variance and count")
    height, width = spectrum.shape
    fy = np.fft.fftfreq(height)[:, None] / 2
    fx = np.fft.fftfreq(width)[None, :] / 2
    radius = np.hypot(fy, fx)
    available = (radius >= 1 / 16) & (radius <= 1 / 3)
    available &= (fy > 0) | ((fy == 0) & (fx > 0))
    power = np.abs(spectrum) ** 2 / noise_variance
    selected = []
    for _ in range(count):
        score = np.where(available, power, -np.inf)
        flat = int(np.argmax(score))
        if not np.isfinite(score.ravel()[flat]):
            break
        y, x = np.unravel_index(flat, score.shape)
        selected.append((int(y), int(x)))
        for cy, cx in [(y, x), ((-y) % height, (-x) % width)]:
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    available[(cy + dy) % height, (cx + dx) % width] = False
    return selected


def describe_phase_holdout(packed, variance, colors, *, count=4):
    """Both directions of one-phase selection followed by other-phase measurement.

    Each direction's bins depend on its selection phase only. Descriptive power
    and signed principal-band phase agreement in the other phase do not affect
    that selection. Separate physical sensor samples can have independent noise
    under the synthetic model; real-camera independence is not established.
    """
    packed = np.asarray(packed, dtype=np.float64)
    variance = np.asarray(variance, dtype=np.float64)
    colors = np.asarray(colors)
    allowed = {(0, 1, 1, 2), (2, 1, 1, 0), (1, 0, 2, 1), (1, 2, 0, 1)}
    if (
        packed.ndim != 3
        or packed.shape[0] != 4
        or variance.shape != packed.shape
        or colors.shape != (4,)
        or tuple(colors) not in allowed
    ):
        raise ValueError("Expected matching 4xHxW RAW/variance and standard Bayer colors")
    green = np.flatnonzero(colors == 1)
    phases = {int(i): tapered_spectrum(packed[i], variance[i]) for i in green}
    fy = np.fft.fftfreq(packed.shape[-2]) / 2
    fx = np.fft.fftfreq(packed.shape[-1]) / 2
    output = []
    for a, b in [(int(green[0]), int(green[1])), (int(green[1]), int(green[0]))]:
        selection, held = phases[a], phases[b]
        ay, ax = divmod(a, 2)
        by, bx = divmod(b, 2)
        peaks = []
        for y, x in select_phase_frequencies(
            selection["spectrum"], selection["noise_variance"], count=count
        ):
            first, second = selection["spectrum"][y, x], held["spectrum"][y, x]
            first_noise = float(selection["noise_variance"][y, x])
            second_noise = float(held["noise_variance"][y, x])
            if second_noise <= 0:
                raise ValueError("Other-phase propagated variance must be positive")
            alignment = np.exp(2j * np.pi * ((by - ay) * fy[y] + (bx - ax) * fx[x]))
            product = first * np.conj(second) * alignment
            amplitude_product = abs(first) * abs(second)
            peaks.append(
                {
                    "bin_yx": [y, x],
                    "principal_native_fxy": [float(fx[x]), float(fy[y])],
                    "selection_power": float(abs(first) ** 2 / first_noise),
                    "other_phase_power": float(abs(second) ** 2 / second_noise),
                    "signed_principal_phase_agreement": (
                        float(np.real(product) / amplitude_product)
                        if amplitude_product > 0
                        else 0.0
                    ),
                    "selection_noise_variance": first_noise,
                    "other_noise_variance": second_noise,
                }
            )
        output.append({"selection_phase": a, "other_phase": b, "peaks": peaks})
    return output
