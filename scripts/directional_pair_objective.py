"""Training-only balanced directional pair response; inference is unchanged."""

import math

import torch
from coherent_pair_objective import objective as previous_objective


def orientation_masks(height, width, device):
    """Two four-region tilings, with conjugate pairs assigned together.

    Offsets0 and22.5degrees reduce dependence on one angular boundary. Each
    non-DC Fourier bin belongs to one region per tiling. On Nyquist axes,
    orientation is a discrete convention: use the lower-index representative
    of each conjugate pair. The overlapping tilings are not independent tests.
    """
    if type(height) is not int or type(width) is not int or min(height, width) < 1:
        raise ValueError("Expected positive integer native dimensions")
    y, x = torch.meshgrid(
        torch.fft.fftfreq(height, device=device, dtype=torch.float64),
        torch.fft.fftfreq(width, device=device, dtype=torch.float64),
        indexing="ij",
    )
    yy, xx = torch.meshgrid(
        torch.arange(height, device=device), torch.arange(width, device=device), indexing="ij"
    )
    conjugate = ((-yy) % height) * width + ((-xx) % width)
    representative = torch.minimum(yy * width + xx, conjugate).flatten()
    regions = []
    for offset in [0.0, math.pi / 8]:
        # Cartesian half-open45-degree regions make axis/diagonal ties exact.
        u = x * math.cos(offset) + y * math.sin(offset)
        v = -x * math.sin(offset) + y * math.cos(offset)
        reverse = (v < 0) | ((v == 0) & (u < 0))
        u, v = torch.where(reverse, -u, u), torch.where(reverse, -v, v)
        labels = torch.where(u > 0, torch.where(v < u, 0, 1), torch.where(v > -u, 2, 3))
        labels = labels.flatten()[representative].reshape(height, width)
        for sector in range(4):
            mask = labels == sector
            mask[0, 0] = False
            regions.append(mask)
    return torch.stack(regions)


def paired_directional_response_loss(output, target, pairs, *, floor_DN16=1, return_terms=False):
    """Equal average of bounded target-projection errors in eight regions.

    Per-channel pair means are removed. For target component t_j in region j,
    r_j=mean(pair_error*t_j)/(mean(t_j²)+(floor_DN16/65535)²). Average unit
    pseudo-Huber over pairs and regions. FP64 orthonormal FFT reductions equal
    the corresponding spatial projections. Targets enter only after inference.
    Unchanged targets give no gradient here, even with false output texture;
    all earlier absolute/common/difference/flat losses remain necessary.
    """
    if (
        output.ndim != 4
        or output.shape[1] != 3
        or min(output.shape) < 1
        or target.shape != output.shape
        or not output.is_floating_point()
        or not target.is_floating_point()
        or output.device != target.device
        or not torch.isfinite(output).all()
        or not torch.isfinite(target).all()
    ):
        raise ValueError("Expected matching finite floating-point Nx3xHxW RGB")
    if isinstance(floor_DN16, bool) or not math.isfinite(floor_DN16) or floor_DN16 <= 0:
        raise ValueError("Directional response floor must be positive and finite")
    indices = torch.as_tensor(pairs, device=output.device)
    if indices.dtype != torch.int64 or indices.ndim != 2 or indices.shape[1] != 2:
        raise ValueError("Expected Px2 int64 pair indices")
    if len(indices) == 0:
        zero = (output.reshape(-1)[0] * 0).to(
            torch.float64 if output.dtype == torch.float64 else torch.float32
        )
        return (zero, {}) if return_terms else zero
    if (
        indices.min() < 0
        or indices.max() >= len(output)
        or indices.unique().numel() != indices.numel()
    ):
        raise ValueError("Pairs must be disjoint and in range")
    with torch.autocast(output.device.type, enabled=False):
        first, second = indices.unbind(1)
        clean = target.detach().double()
        delta = clean[first] - clean[second]
        template = delta - delta.mean((-2, -1), keepdim=True)
        value = output.double()
        error = value[first] - value[second] - delta
        error = error - error.mean((-2, -1), keepdim=True)
        masks = orientation_masks(*output.shape[-2:], output.device)
        ft, fe = [torch.fft.fft2(v, norm="ortho") for v in [template, error]]
        normalization = template.shape[1] * template.shape[2] * template.shape[3]
        power = ft.abs().square().sum(1) / normalization
        cross = (fe * ft.conj()).real.sum(1) / normalization
        energy = torch.einsum("phw,shw->ps", power, masks.to(torch.float64))
        numerator = torch.einsum("phw,shw->ps", cross, masks.to(torch.float64))
        residual = numerator / (energy + (floor_DN16 / 65535) ** 2)
        square = residual.square()
        loss = (square / ((square + 1).sqrt() + 1)).mean()
        loss = loss.to(torch.float64 if output.dtype == torch.float64 else torch.float32)
        if return_terms:
            return loss, {
                "energy": energy,
                "numerator": numerator,
                "residual": residual,
                "masks": masks,
            }
        return loss


def objective(output, frozen, batch, pair_units, domain_weight, *, mode):
    """Keep all nine terms; add weight0.25 of whole or balanced response.

    Whole mode raises the existing full-response weight0.25 to0.50. Directional
    mode retains that weight0.25 and adds weight0.25 of the eight-region mean.
    Equal nominal added weights do not imply equal gradient norms. Paired arms
    must share initialization, optimizer clocks, data, schedule and budget.
    """
    if mode not in ["whole", "directional"]:
        raise ValueError("Expected whole or directional response addition")
    loss, terms, mask = previous_objective(output, frozen, batch, pair_units, domain_weight)
    addition = (
        terms["coherent_response"]
        if mode == "whole"
        else paired_directional_response_loss(
            output, batch["target"], batch["pair_indices"], floor_DN16=1
        )
    )
    return loss + (0.25 * domain_weight) * addition, dict(terms, response_addition=addition), mask
