"""Learned matching on RAW innovations and a frozen DINO-parent restoration.

This new RGB residual is trained from scratch on the project's cached free-image
and synthetic data. It uses the pinned NLFeMF network definitions, with narrower
features and nine neighbours at each scale; released RAW weights are not loaded.
"""

import torch
from torch import nn
from torch.nn import functional as F

from .late_balanced_spatial import LateBalancedSpatialDetail
from .late_spatial_rgb import SpatialRgbResidual
from .nonlocal_autograd import enable_sampler_autograd
from .precision import ieee_fp32


class LateNonlocalResidualDetail(nn.Module):
    """A zero-initialized RGB residual above the frozen V169 EMA component.

    Only the matching network is trainable. Inputs are the supplied V143 RGB,
    actual noisy RAW, variance, Bayer layout and white balance. The inherited
    physical features contain no target or reference. The image noise RMS scales
    the output, so zero supplied variance retains the frozen component exactly.
    No noisy-flat safety or correct-detail guarantee follows from this routing.
    """

    def __init__(self, width=16, max_search=9.0):
        super().__init__()
        if type(width) is not int or width < 8 or width % 4:
            raise ValueError("Expected a feature width divisible by four and at least eight")
        if not isinstance(max_search, (int, float)) or not 0 < max_search <= 32:
            raise ValueError("Expected a positive search distance at most32 packed pixels")
        from .nonlocal_matchfilter import SimpleBlockMatchingUNet

        with torch.random.fork_rng(devices=[]):
            torch.set_rng_state(torch.Generator(device="cpu").manual_seed(17101).get_state())
            self.frozen = LateBalancedSpatialDetail()
            self.network = SimpleBlockMatchingUNet(
                input_channels=39,
                output_channels=12,
                n_features=width,
                neighbours={"scale1": [3, 3], "scale2": [3, 3], "scale3": [3, 3]},
                max_search_dist=float(max_search),
            )
        nn.init.zeros_(self.network.tail.weight)
        self.frozen.requires_grad_(False).eval()
        self.width, self.max_search = width, float(max_search)

    def load_frozen_component(self, path):
        state = torch.load(path, map_location="cpu", weights_only=True)
        expected = {"max_window": 256, "support_floor": 0.25, "balance_spatial": True}
        if state["component"] != "LateBalancedSpatialDetail" or state["module_config"] != expected:
            raise ValueError("Expected the fixed balanced V169 component configuration")
        self.frozen.load_state_dict(state["state_dict"], strict=True)
        return self

    def train(self, mode=True):
        super().train(mode)
        self.frozen.eval()
        return self

    def forward(self, base, packed, variance, colors, wb=None, *, return_aux=False):
        with torch.autocast(base.device.type, enabled=False), ieee_fp32():
            with torch.no_grad():
                restored = self.frozen(base, packed, variance, colors, wb)
                features, sigma = SpatialRgbResidual.features(
                    restored, packed, variance, colors, wb
                )
            # ADC-only observations have no shot/read variance in this pipeline.
            # The branch is bypassed and no new learned value reaches the result.
            evaluated = bool(torch.any(sigma > 0))
            if evaluated:
                if torch.is_grad_enabled():
                    enable_sampler_autograd()
                correction = F.pixel_shuffle(self.network(features), 2) * sigma
                output = restored + correction
            else:
                correction = torch.zeros_like(restored)
                output = restored
            if return_aux:
                return output, {
                    "frozen_output": restored,
                    "correction": correction,
                    "sigma": sigma,
                    "matching_evaluated": evaluated,
                }
            return output
