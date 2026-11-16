"""Matching, pooled-wave and innovation stages composed without trial inheritance.

The historical numerical primitives remain unchanged. Legacy checkpoint names
are translated only at the loading/export boundary, not inside forward calls.
"""

from dataclasses import asdict, dataclass

import torch
from torch import nn
from torch.nn import functional as F

from demosaic.cfa import mosaic
from demosaic.cfa_scale_support import cfa_cross_scale_support
from demosaic.late_cfa_innovation_wave import cfa_innovation_wave_maps
from demosaic.late_innovation_wave import innovation_phase_bins
from demosaic.late_local_noise_matching import local_noise_features
from demosaic.late_local_phase_evidence_matching import local_phase_evidence_maps
from demosaic.late_pooled_phase_wave import fixed_bin_wave_maps, pooled_phase_bins
from demosaic.late_spatial_context_wave import fixed_bin_support_context
from demosaic.precision import ieee_fp32


@dataclass(frozen=True)
class WaveConfig:
    width: int = 16
    max_search: float = 9.0
    evidence_peaks: int = 4
    evidence_window: int = 65
    evidence_stride: int = 32
    support_windows: tuple[int, int] = (33, 17)
    support_stride: int = 8

    def to_dict(self):
        return asdict(self)


class MatchingStage(nn.Module):
    def __init__(self, frozen, network, adapter, config):
        super().__init__()
        self.frozen, self.network, self.adapter = frozen, network, adapter
        self.config = config
        self.requires_grad_(False)
        self.eval()

    @torch.no_grad()
    def forward(self, base, packed, variance, colors, wb=None):
        restored = self.frozen(base, packed, variance, colors, wb)
        features, sigma = local_noise_features(restored, packed, variance, colors, wb)
        evaluated = bool(torch.any(sigma > 0))
        evidence_aux = None
        if evaluated:
            evidence, evidence_aux = local_phase_evidence_maps(
                packed.float(),
                variance.float(),
                colors,
                peaks=self.config.evidence_peaks,
                window=self.config.evidence_window,
                stride=self.config.evidence_stride,
            )
            features = features + self.adapter(evidence)
            correction = F.pixel_shuffle(self.network(features), 2) * sigma
            inherited = torch.where(sigma > 0, restored + correction, restored)
        else:
            correction, inherited = torch.zeros_like(restored), restored
        return inherited, {
            "frozen_output": restored,
            "inherited_output": inherited,
            "inherited_correction": correction,
            "sigma": sigma,
            "matching_evaluated": evaluated,
            "phase_evidence": evidence_aux,
        }


class PooledWaveStage(nn.Module):
    def __init__(self, matching, readout, config):
        super().__init__()
        self.matching, self.readout, self.config = matching, readout, config

    def train(self, mode=True):
        super().train(mode)
        self.matching.eval()
        return self

    def forward(self, base, packed, variance, colors, wb=None, *, return_aux=False):
        with torch.autocast(base.device.type, enabled=False), ieee_fp32():
            inherited, aux = self.matching(base, packed, variance, colors, wb)
            sigma, evaluated = aux["sigma"], aux["matching_evaluated"]
            wave_aux = pool_aux = support_aux = None
            evidence = support = None
            if evaluated:
                bins, valid, pool_aux = pooled_phase_bins(
                    packed.float(), variance.float(), colors, peaks=self.config.evidence_peaks
                )
                evidence, wave_aux = fixed_bin_wave_maps(
                    packed.float(),
                    variance.float(),
                    colors,
                    bins,
                    valid,
                    window=self.config.evidence_window,
                    stride=self.config.evidence_stride,
                )
                support, support_aux = fixed_bin_support_context(
                    packed.float(),
                    variance.float(),
                    colors,
                    bins,
                    valid,
                    windows=self.config.support_windows,
                    stride=self.config.support_stride,
                )
                wave = self.readout(evidence, bins, support) * sigma
                wave = torch.where(sigma > 0, wave, torch.zeros_like(wave))
                output = torch.where(sigma > 0, inherited + wave, inherited)
            else:
                wave, output = torch.zeros_like(inherited), inherited
            if return_aux:
                return output, dict(
                    aux,
                    wave_correction=wave,
                    correction=aux["inherited_correction"] + wave,
                    wave_selection=pool_aux,
                    wave_evidence=wave_aux,
                    wave_evidence_features=evidence,
                    wave_support=support_aux,
                    wave_support_context=support,
                )
            return output


class InnovationWaveStage(nn.Module):
    def __init__(self, anchor, readout, *, lower, cross_scale):
        super().__init__()
        self.anchor, self.readout = anchor, readout
        self.lower, self.cross_scale = lower, cross_scale
        self.config = anchor.config
        self.anchor.requires_grad_(False)

    def train(self, mode=True):
        super().train(mode)
        self.anchor.eval()
        return self

    def forward(self, base, packed, variance, colors, wb=None, *, return_aux=False):
        with torch.autocast(base.device.type, enabled=False), ieee_fp32():
            with torch.no_grad():
                anchor, anchor_aux = self.anchor(
                    base, packed, variance, colors, wb, return_aux=True
                )
                sigma = anchor_aux["sigma"]
                evaluated = bool(torch.any(sigma > 0))
                field = selection = evidence = support = context = waves = scale_aux = None
                if evaluated:
                    field = packed.float() - mosaic(anchor.float(), colors)
                    bins, valid, selection = innovation_phase_bins(
                        field,
                        variance.float(),
                        colors,
                        peaks=self.config.evidence_peaks,
                        lower=self.lower,
                    )
                    large, waves, evidence = cfa_innovation_wave_maps(
                        field,
                        variance.float(),
                        colors,
                        bins,
                        valid,
                        window=self.config.evidence_window,
                        stride=self.config.evidence_stride,
                    )
                    small, support = fixed_bin_support_context(
                        field,
                        variance.float(),
                        colors,
                        bins,
                        valid,
                        windows=self.config.support_windows,
                        stride=self.config.support_stride,
                    )
                    parts = [large[:, :, :6], small, large[:, :, 6:]]
                    if self.cross_scale:
                        agreement, scale_aux = cfa_cross_scale_support(
                            field,
                            variance.float(),
                            colors,
                            bins,
                            valid,
                            windows=(self.config.evidence_window, *self.config.support_windows),
                            strides=(
                                self.config.evidence_stride,
                                self.config.support_stride,
                                self.config.support_stride,
                            ),
                        )
                        parts.append(agreement)
                    context = torch.cat(parts, 2)
            if evaluated:
                wave = self.readout(context, waves, bins)
                wave = torch.where(sigma > 0, wave, torch.zeros_like(wave))
                output = torch.where(sigma > 0, anchor + wave, anchor)
            else:
                wave, output = torch.zeros_like(anchor), anchor
            if return_aux:
                aux = {
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
                if self.cross_scale:
                    aux["scale_support"] = scale_aux
                return output, aux
            return output


def compose_legacy(module):
    """Adopt initialized modules once; subsequent forwards have no legacy dispatch."""
    config = WaveConfig(**{name: getattr(module, name) for name in WaveConfig.__dataclass_fields__})
    matching = MatchingStage(module.frozen, module.network, module.phase_evidence_in, config)
    anchor = PooledWaveStage(matching, module.wave_readout, config)
    if hasattr(module, "cfa_readout"):
        composed = InnovationWaveStage(
            anchor,
            module.cfa_readout,
            lower=module.lower,
            cross_scale=module.cfa_readout.context.in_channels == 36,
        )
    else:
        composed = anchor
    composed.train(module.training)
    return composed


def legacy_state_dict(module):
    """Export the historical tensor names/order for comparisons and old consumers."""
    anchor = module.anchor if isinstance(module, InnovationWaveStage) else module
    state = {}
    for prefix, part in (
        ("frozen", anchor.matching.frozen),
        ("network", anchor.matching.network),
        ("phase_evidence_in", anchor.matching.adapter),
        ("wave_readout", anchor.readout),
    ):
        state.update({prefix + "." + name: value for name, value in part.state_dict().items()})
    if isinstance(module, InnovationWaveStage):
        state.update(
            {"cfa_readout." + name: value for name, value in module.readout.state_dict().items()}
        )
    return state


def load_legacy_state_dict(module, state):
    current = legacy_state_dict(module)
    if set(current) != set(state):
        raise ValueError("Historical component tensor names do not match the composed model")
    anchor = module.anchor if isinstance(module, InnovationWaveStage) else module
    parts = [
        ("frozen", anchor.matching.frozen),
        ("network", anchor.matching.network),
        ("phase_evidence_in", anchor.matching.adapter),
        ("wave_readout", anchor.readout),
    ]
    if isinstance(module, InnovationWaveStage):
        parts.append(("cfa_readout", module.readout))
    # Validate every shape/dtype before mutating any module.
    for name, value in state.items():
        if value.shape != current[name].shape or value.dtype != current[name].dtype:
            raise ValueError(f"Incompatible historical tensor: {name}")
    for prefix, part in parts:
        part.load_state_dict(
            {n[len(prefix) + 1 :]: v for n, v in state.items() if n.startswith(prefix + ".")},
            strict=True,
        )
