"""Pinned NLFeMF network definitions with original state-dict names.

Derived from MIA-UIB/nonlocal-matchfilter v1.0.0, commit
6df6a79ce128a7741af88ff0f3e9794f9b5e03d4. Copyright 2026 Marco
Sánchez Beeckman; MIT license in third_party/nonlocal-matchfilter/LICENSE.
Only selected original classes are included. Sampling uses the separately
pinned upstream CPU/CUDA operator. No architecture or weight arithmetic changes.
"""
from typing import Literal
import torch
from torch import nn
from torch.nn import functional as F
from einops import rearrange


def deform_neighbourhood(input, offset, neighbourhood_size, stride, padding, dilation, offset_groups):
    if not hasattr(torch.ops.deform_neighbourhood_sampling, 'deform_neighbourhood'):
        raise RuntimeError('Load the pinned deform sampling library before inference')
    return torch.ops.deform_neighbourhood_sampling.deform_neighbourhood.default(
        input, offset, *neighbourhood_size, stride, stride, *padding,
        dilation, dilation, offset_groups)


class FeedForwardNetwork(nn.Module):
    def __init__(
        self,
        in_channels: int,
        inner_channels: int,
        out_channels: int = None,
        activation=nn.GELU,
        selection=nn.Identity,
        bias: bool = True,
        dropout: float = 0.0,
    ):
        super().__init__()
        out_channels = out_channels or in_channels
        self.ffn = nn.Sequential(
            nn.Linear(in_channels, inner_channels, bias=bias),
            activation(),
            selection(),
            nn.Dropout(dropout),
            nn.Linear(inner_channels, out_channels, bias=bias),
        )

    def forward(self, x):
        return self.ffn(x)

class GLUFeedForwardNetwork(nn.Module):
    def __init__(
        self,
        in_channels: int,
        inner_channels: int,
        out_channels: int = None,
        activation=nn.GELU,
        selection=nn.Identity,
        bias: bool = True,
        dropout: float = 0.0,
    ):
        super().__init__()
        out_channels = out_channels or in_channels
        self.linear11 = nn.Linear(in_channels, inner_channels, bias=bias)
        self.linear12 = nn.Linear(in_channels, inner_channels, bias=bias)
        self.activation = activation()
        self.selection = selection(inner_channels)
        self.drop = nn.Dropout(dropout)
        self.linear2 = nn.Linear(inner_channels, out_channels)

    def forward(self, x):
        x = self.activation(self.linear11(x)) * self.linear12(x)
        x = self.selection(x)
        x = self.drop(x)
        x = self.linear2(x)
        return x

class ConvNeXtBlock(nn.Module):
    def __init__(
        self,
        channels,
        inverse_bottleneck_ratio=4,
        norm=nn.LayerNorm,
        ffn=GLUFeedForwardNetwork,
        activation=nn.GELU,
        selection=nn.Identity,
        scaling=nn.Identity,
        bias=True,
        dropout=0.0,
    ):
        super().__init__()
        self.dwconv = nn.Conv2d(
            channels,
            channels,
            kernel_size=7,
            stride=1,
            padding=3,
            bias=bias,
            groups=channels,
        )
        self.norm = norm(channels)
        self.ffn = ffn(
            channels,
            inverse_bottleneck_ratio * channels,
            activation=activation,
            selection=selection,
            bias=bias,
            dropout=dropout,
        )
        self.scaling = scaling(channels)

    def forward(self, x):
        _batch_size, _channels, height, width = x.shape
        y = self.dwconv(x)
        y = rearrange(y, "b c h w -> b (h w) c")
        y = self.norm(y)
        y = self.ffn(y)
        y = self.scaling(y)
        y = rearrange(y, "b (h w) c -> b c h w", h=height, w=width)
        return x + y

class InputPadder:
    def __init__(
        self,
        dims,
        to_multiple: int,
        position: Literal["symmetric", "downright"] = "symmetric",
        mode: Literal["constant", "reflect", "replicate", "circular"] = "replicate",
        value: float | None = None,
    ):
        self.height, self.width = dims[-2:]
        self.mode = mode
        self.value = value
        pad_h = (
            ((self.height // to_multiple) + 1) * to_multiple - self.height
        ) % to_multiple
        pad_w = (
            ((self.width // to_multiple) + 1) * to_multiple - self.width
        ) % to_multiple
        if position == "symmetric":
            self._pad = [pad_w // 2, pad_w - pad_w // 2, pad_h // 2, pad_h - pad_h // 2]
        else:
            self._pad = [0, pad_w, 0, pad_h]

    def pad(self, x):
        return F.pad(x, self._pad, mode=self.mode, value=self.value)

    def unpad(self, x):
        height, width = x.shape[-2:]
        crop_h = [self._pad[2], height - self._pad[3]]
        crop_w = [self._pad[0], width - self._pad[1]]
        return x[..., crop_h[0] : crop_h[1], crop_w[0] : crop_w[1]]

class OffsetCNN(nn.Module):
    def __init__(
        self,
        in_channels: int,
        embedding_channels: int,
        offset_groups: int,
        num_neighbours: int,
    ):
        super().__init__()
        self.cnn = nn.Sequential(
            nn.Conv2d(in_channels, embedding_channels, kernel_size=1, padding=0),
            nn.LeakyReLU(negative_slope=0.1, inplace=True),
            nn.Conv2d(embedding_channels, embedding_channels, kernel_size=3, padding=1),
            nn.LeakyReLU(negative_slope=0.1, inplace=True),
            nn.Conv2d(embedding_channels, embedding_channels, kernel_size=3, padding=1),
            nn.LeakyReLU(negative_slope=0.1, inplace=True),
            nn.Conv2d(embedding_channels, embedding_channels, kernel_size=3, padding=1),
            nn.LeakyReLU(negative_slope=0.1, inplace=True),
            nn.Conv2d(embedding_channels, embedding_channels, kernel_size=3, padding=1),
            nn.LeakyReLU(negative_slope=0.1, inplace=True),
            nn.Conv2d(
                embedding_channels,
                2 * offset_groups * num_neighbours,
                kernel_size=1,
                padding=0,
            ),
        )
        nn.init.zeros_(self.cnn[-1].weight.data)
        nn.init.zeros_(self.cnn[-1].bias.data)

    def forward(self, x):
        return self.cnn(x)

class NonlocalBlock(nn.Module):
    def __init__(
        self,
        n_features,
        neighbours,
        max_search_dist,
        n_features_offsets=None,
        bias=False,
        groups=1,
    ):
        super().__init__()

        self.num_features = n_features
        self.neighbours = neighbours
        self.max_search_dist = max_search_dist
        self.groups = groups
        if n_features_offsets is None:
            n_features_offsets = n_features

        self.encoder = nn.Sequential(
            ConvNeXtBlock(
                n_features,
                inverse_bottleneck_ratio=2,
                norm=nn.Identity,
                activation=nn.ReLU,
                ffn=FeedForwardNetwork,
                selection=nn.Identity,
                scaling=nn.Identity,
                bias=False,
            )
        )

        self.decoder = nn.Sequential(
            ConvNeXtBlock(
                n_features,
                inverse_bottleneck_ratio=2,
                norm=nn.Identity,
                activation=nn.ReLU,
                ffn=FeedForwardNetwork,
                selection=nn.Identity,
                scaling=nn.Identity,
                bias=False,
            )
        )

        num_neighbours = neighbours[0] * neighbours[1]
        self.offset_cnn = OffsetCNN(
            n_features,
            n_features_offsets,
            offset_groups=1,
            num_neighbours=num_neighbours,
        )

        self.dct_sub = nn.Conv2d(
            n_features * num_neighbours,
            n_features * num_neighbours,
            kernel_size=1,
            stride=1,
            padding=0,
            bias=bias,
            groups=n_features // groups,
        )
        self.wiener_sub = nn.Sequential(
            nn.Conv2d(
                n_features * num_neighbours,
                n_features * num_neighbours,
                kernel_size=1,
                stride=1,
                padding=0,
                bias=bias,
            ),
            nn.Conv2d(
                n_features * num_neighbours,
                n_features * num_neighbours,
                kernel_size=3,
                stride=1,
                padding=1,
                bias=bias,
                groups=n_features * num_neighbours,
            ),
            nn.ReLU(),
            nn.Conv2d(
                n_features * num_neighbours,
                n_features * num_neighbours,
                kernel_size=1,
                stride=1,
                padding=0,
                bias=bias,
            ),
            nn.Conv2d(
                n_features * num_neighbours,
                n_features * num_neighbours,
                kernel_size=3,
                stride=1,
                padding=1,
                bias=bias,
                groups=n_features * num_neighbours,
            ),
            nn.ReLU(),
            nn.Conv2d(
                n_features * num_neighbours,
                n_features * num_neighbours,
                kernel_size=1,
                stride=1,
                padding=0,
                bias=bias,
            ),
            nn.Conv2d(
                n_features * num_neighbours,
                n_features * num_neighbours,
                kernel_size=3,
                stride=1,
                padding=1,
                bias=bias,
                groups=n_features * num_neighbours,
            ),
            nn.Sigmoid(),
        )

        self.inv_dct_sub = nn.Sequential(
            nn.Conv2d(
                n_features * num_neighbours,
                n_features * num_neighbours,
                kernel_size=1,
                stride=1,
                padding=0,
                bias=bias,
                groups=n_features // groups,
            ),
            nn.Conv2d(
                n_features * num_neighbours,
                n_features,
                kernel_size=1,
                stride=1,
                padding=0,
                bias=bias,
            ),
        )

    def forward(self, x):
        _, _, height, width = x.shape
        num_neighbours = self.neighbours[0] * self.neighbours[1]
        x = self.encoder(x)

        offsets = self.offset_cnn(x)
        offsets = self.max_search_dist * torch.tanh(offsets)

        x_blocks = deform_neighbourhood(
            x,
            offsets,
            neighbourhood_size=self.neighbours,
            stride=1,
            padding=(self.neighbours[0] // 2, self.neighbours[1] // 2),
            dilation=1,
            offset_groups=1,
        )
        x_blocks = rearrange(
            x_blocks,
            "b (g f K) h w -> b (f K g) h w",
            g=self.groups,
            f=self.num_features // self.groups,
            K=num_neighbours,
        )
        dct_coeffs = self.dct_sub(x_blocks)
        wiener_coeffs = self.wiener_sub(x_blocks)
        x = self.inv_dct_sub(wiener_coeffs * dct_coeffs)

        x = self.decoder(x)
        return x

class SimpleBlockMatchingUNet(nn.Module):
    def __init__(
        self,
        input_channels=3,
        output_channels=3,
        n_features=64,
        neighbours=None,
        max_search_dist: float = 9.0,
        bias: bool = False,
    ):
        super().__init__()

        if neighbours is None:
            neighbours = {"scale1": [5, 5], "scale2": [3, 5], "scale3": [3, 3]}

        self.in_channels = input_channels
        self.out_channels = output_channels

        self.max_search_dist = max_search_dist
        self.neighbours = neighbours

        self.head = nn.Conv2d(
            input_channels,
            n_features,
            kernel_size=3,
            stride=1,
            padding=1,
            bias=bias,
        )

        self.down1 = nn.Sequential(
            NonlocalBlock(
                n_features=n_features,
                neighbours=neighbours["scale1"],
                max_search_dist=max_search_dist,
                bias=bias,
            ),
            nn.Conv2d(
                n_features,
                n_features * 2,
                kernel_size=2,
                stride=2,
                padding=0,
                bias=bias,
            ),
        )

        self.down2 = nn.Sequential(
            NonlocalBlock(
                n_features=n_features * 2,
                neighbours=neighbours["scale2"],
                max_search_dist=max_search_dist,
                bias=bias,
            ),
            nn.Conv2d(
                n_features * 2,
                n_features * 4,
                kernel_size=2,
                stride=2,
                padding=0,
                bias=bias,
            ),
        )

        self.body = nn.Sequential(
            NonlocalBlock(
                n_features=n_features * 4,
                neighbours=neighbours["scale3"],
                max_search_dist=max_search_dist,
                bias=bias,
            )
        )

        self.up2 = nn.Sequential(
            nn.ConvTranspose2d(
                n_features * 4,
                n_features * 2,
                kernel_size=2,
                stride=2,
                padding=0,
                bias=bias,
            ),
            NonlocalBlock(
                n_features=n_features * 2,
                neighbours=neighbours["scale2"],
                max_search_dist=max_search_dist,
                bias=bias,
            ),
        )

        self.up1 = nn.Sequential(
            nn.ConvTranspose2d(
                n_features * 2,
                n_features,
                kernel_size=2,
                stride=2,
                padding=0,
                bias=bias,
            ),
            NonlocalBlock(
                n_features=n_features,
                neighbours=neighbours["scale1"],
                max_search_dist=max_search_dist,
                bias=bias,
            ),
        )

        self.tail = nn.Conv2d(
            n_features,
            output_channels,
            kernel_size=3,
            stride=1,
            padding=1,
            bias=bias,
        )

    def forward(self, x):
        _b, _c, height, width = x.shape
        input_padder = InputPadder((height, width), to_multiple=4, mode="reflect")
        x = input_padder.pad(x)

        feat0 = self.head(x)
        feat1 = self.down1(feat0)
        feat2 = self.down2(feat1)
        feat2 = self.body(feat2) + feat2
        feat1 = self.up2(feat2) + feat1
        feat0 = self.up1(feat1) + feat0
        feat0 = self.tail(feat0)
        feat0 = input_padder.unpad(feat0)
        return feat0
