"""Use aligned scene features to scale a measured RAW detail proposal."""

import torch
from torch.nn import functional as F

from .late_spectral_detail import LateSpectralDetail
from .precision import ieee_fp32
from .scene_restoration import SceneAdapter


class SceneSpectralDetail(LateSpectralDetail):
    """Two positive scene gains act on each overlapping spectral frame.

    Context can change the magnitude of the signed local estimator. It supplies
    no phase or color coefficients. The untrained scene gate is unity, and
    the inherited zero proposal preserves the frozen RGB parent exactly.
    """

    def __init__(self, input_channels, *, max_window=32, adapter_width=16):
        super().__init__(max_window)
        self.scene_adapter = SceneAdapter(input_channels, width=adapter_width, output_channels=2)

    def frame_scale(self, packed, scene, boxes_xywh, mode):
        height, width = packed.shape[-2:]
        if len(boxes_xywh) != len(packed) or any(
            tuple(box[2:]) != (2 * width, 2 * height) for box in boxes_xywh
        ):
            raise ValueError("Require one aligned native box per spectral tile")
        size, hop, (left, right, top, bottom) = self.frame_layout(height, width)
        rows = 1 + (height + top + bottom - size) // hop
        cols = 1 + (width + left + right - size) // hop
        with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
            logits = self.scene_adapter(scene, boxes_xywh, (rows - 1, cols - 1), mode=mode)
            # Query the actual overlap-frame centers. Centers beyond the final
            # native pixel use the edge value of the in-tile scene gain grid.
            y = (
                2
                * (torch.arange(rows, device=packed.device, dtype=torch.float32) * hop + 0.5)
                / height
                - 1
            )
            x = (
                2
                * (torch.arange(cols, device=packed.device, dtype=torch.float32) * hop + 0.5)
                / width
                - 1
            )
            yy, xx = torch.meshgrid(y, x, indexing="ij")
            grid = torch.stack((xx, yy), -1).expand(len(packed), -1, -1, -1)
            strength = F.grid_sample(logits, grid, padding_mode="border", align_corners=False)
            low, high = (1 + 0.75 * strength.tanh()).permute(0, 2, 3, 1).reshape(-1, 2).unbind(1)
            frequency = torch.fft.fftfreq(size, device=packed.device)
            radius = torch.hypot(frequency[:, None], frequency[None, :])
            # Crossfade between 1/16 and 1/8 cycles per native pixel.
            blend = ((radius - 0.125) / 0.125).clamp(0, 1)
            return torch.lerp(low[:, None, None, None], high[:, None, None, None], blend)

    def forward(
        self, base, packed, variance, colors, wb=None, *, scene, boxes_xywh, mode, return_aux=False
    ):
        scale = self.frame_scale(packed, scene, boxes_xywh, mode)
        return super().forward(
            base, packed, variance, colors, wb, return_aux=return_aux, frame_scale=scale
        )
