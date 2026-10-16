"""Optional pinned Nonlocal Match-Filter RAW-denoising + Malvar reference."""

import hashlib
import importlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import torch
from torch import nn

from .cfa import malvar
from .precision import ieee_fp32
from .safety import writable_path

SOURCE_REVISION = "6df6a79ce128a7741af88ff0f3e9794f9b5e03d4"
CHECKPOINT_SHA256 = "b31bc8e21022389b0b209a9d1e6649485ed4dacc552b7ea04612df5f7515fcf2"


def _sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _read(path):
    return json.loads(Path(path).read_text())


def _checked_file(path, expected):
    if _sha(path) != expected:
        raise ValueError(f"Nonlocal reference checksum mismatch: {path}")


class NonlocalRawReference(nn.Module):
    """Authors' normalized RGBG RAW denoiser, then independent WB-aware Malvar.

    Noise coefficients come from the observation or a disclosed input-only prior.
    The supplied variance tensor is not a learned input: the authors append four
    standard deviation maps derived from clipped noisy RAW and shot/read instead.
    Native network calls remain batch1 until larger batches have been validated.
    No target, fitted output gain or ADC-only bypass is used.
    """

    def __init__(self, network):
        super().__init__()
        self.network = network.eval().requires_grad_(False)
        self.shot = self.read = None

    def set_noise(self, shot, read):
        shot, read = float(shot), float(read)
        if not math.isfinite(shot) or not math.isfinite(read) or min(shot, read) < 0:
            raise ValueError("Finite nonnegative shot/read coefficients are required")
        self.shot, self.read = shot, read
        return self

    def forward(self, packed, variance, colors, wb=None, matrix=None):
        if self.shot is None:
            raise ValueError("Supply shot/read conditioning before reference inference")
        if packed.ndim != 4 or packed.shape[1] != 4 or min(packed.shape[-2:]) < 4:
            raise ValueError("Expected B×4×H×W spatial phases, with H/W >=4")
        if not len(packed) or not packed.is_floating_point() or variance.shape != packed.shape:
            raise ValueError("Expected nonempty floating RAW and matching variance shape")
        if colors.ndim == 1:
            colors = colors[None].expand(len(packed), -1)
        if colors.shape != (len(packed), 4) or colors.dtype != torch.long:
            raise ValueError("Expected four integer CFA labels per image")
        colors = colors.to(packed.device)
        red, blue = (colors == 0).long().argmax(1), (colors == 2).long().argmax(1)
        valid = ((colors == 0).sum(1) == 1) & ((colors == 1).sum(1) == 2)
        valid &= ((colors == 2).sum(1) == 1) & (blue == (red ^ 3))
        if not bool(valid.all()):
            raise ValueError("Expected a valid Bayer CFA layout")
        if not bool(torch.isfinite(packed).all()):
            raise ValueError("RAW values must be finite")
        # The pinned upstream CUDA kernels launch on stream0. Refuse a different
        # caller stream instead of racing that stream's allocations/convolutions.
        if packed.is_cuda and torch.cuda.current_stream(packed.device) != torch.cuda.default_stream(
            packed.device
        ):
            raise ValueError("Pinned Nonlocal reference requires the default CUDA stream")
        with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
            order = torch.stack((red, red ^ 1, blue, blue ^ 1), 1)
            indices = order[..., None, None].expand_as(packed)
            raw = packed.float().gather(1, indices).clamp(0, 1)
            std = (self.shot * raw + self.read).clamp_min(0).sqrt()
            inputs = torch.cat((raw, std), 1)
            outputs = []
            for sample in inputs.split(1):
                output = self.network(sample.contiguous()).float()
                if output.shape != sample[:, :4].shape or not bool(torch.isfinite(output).all()):
                    raise ValueError("Nonlocal network returned invalid packed RAW")
                outputs.append(output.clamp(0, 1))
            denoised = torch.cat(outputs)
            restored = torch.empty_like(denoised).scatter_(1, indices, denoised)
            return malvar(restored, colors, wb)


def _extension(alias, name, record):
    path = Path(record["path"]).resolve()
    _checked_file(path, record["sha256"])
    previous = sys.modules.get(alias)
    if previous is not None:
        if Path(previous.__file__).resolve() != path:
            raise ImportError(f"A different native reference extension is already loaded: {alias}")
        return
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules[alias] = module


def load_nonlocal_reference(directory, *, device="cuda", archive=None):
    """Load the verified external release/build, without fetching or compiling.

    The separate native build contains both CPU and CUDA implementations. Its
    actual CUDA numerics must pass preflight before publishing GPU scores. The
    optional PatchMatch dependency is genuinely imported but this RAW network
    never calls it. No missing dependency gets a numerical substitute.
    """
    root = Path(directory).resolve()
    source = _read(root / "receipt.json")
    inspection = _read(root / "inspection-cpu-v1/receipt.json")
    native = _read(root / "native-cuda-build-v1/receipt.json")
    patch_source = _read(root / "patchmatch-dependency-v1/receipt.json")
    patch = _read(root / "patchmatch-native-build-v1/receipt.json")
    deform_source = _read(root / "deform-dependency-v1/receipt.json")
    if (
        source["revision"] != SOURCE_REVISION
        or inspection["source_checkpoint_sha256"] != CHECKPOINT_SHA256
    ):
        raise ValueError("Expected the pinned Nonlocal Match-Filter v1.0.0 RAW release")
    for receipt in [source, patch_source, deform_source]:
        for item in receipt["files"]:
            _checked_file(item["path"], item["sha256"])
    _checked_file(root / "rawnoise_25_15_9nbr.ckpt", CHECKPOINT_SHA256)
    for item in inspection["isolated_dependency"]["files"].items():
        _checked_file(root / "dependencies-cpu-v1" / item[0], item[1])
    for build in [native, patch]:
        if build["torch_version"] != torch.__version__:
            raise ValueError("Rebuild external reference extensions for this Torch version")
    export = inspection["weights_only_export"]
    _checked_file(export["path"], export["sha256"])
    paths = [
        root / "dependencies-cpu-v1",
        root / "deform-dependency-v1/source",
        root / "patchmatch-dependency-v1/source/src",
        root / "source/src",
    ]
    packages = {
        "einops": paths[0],
        "deform_neighbourhood_sampling": paths[1],
        "patchmatch": paths[2],
        "nonlocal_matchfilter": paths[3],
    }
    for name, path in packages.items():
        existing = sys.modules.get(name)
        if existing is not None and not Path(existing.__file__).resolve().is_relative_to(path):
            raise ImportError(f"A different version of {name} is already imported")
    _extension(
        "deform_neighbourhood_sampling._C", "nonlocal_deform_native_cuda_v1", native["build"]
    )
    _extension("patchmatch._C", "nonlocal_patchmatch_native_v1", patch["build"])
    original_path = list(sys.path)
    try:
        sys.path[:0] = [str(p) for p in paths]
        module = importlib.import_module("nonlocal_matchfilter.networks.nonlocalmf")
        network = module.SimpleBlockMatchingUNet(
            input_channels=8,
            output_channels=4,
            n_features=32,
            neighbours={"scale1": [5, 5], "scale2": [3, 5], "scale3": [3, 3]},
            max_search_dist=9.0,
            bias=False,
        )
    finally:
        sys.path[:] = original_path
    state = torch.load(export["path"], map_location="cpu", weights_only=True)
    if state["source_checkpoint_sha256"] != CHECKPOINT_SHA256:
        raise ValueError("Tensor export has a different source checkpoint")
    network.load_state_dict(state["state_dict"], strict=True)
    model = NonlocalRawReference(network).eval().to(device)
    model.receipt = {
        "label": "NonlocalMatchFilter2026+Malvar:authors-RAW",
        "directory": str(root),
        "source_revision": SOURCE_REVISION,
        "sha256": CHECKPOINT_SHA256,
        "source_checkpoint_sha256": CHECKPOINT_SHA256,
        "weights_only_export": export,
        "native_operator": native["build"],
        "patchmatch_import_dependency": patch["build"],
        "parameters": sum(p.numel() for p in network.parameters()),
        "compute_precision": "IEEE float32",
        "native_network_batch_size": 1,
        "input": "Sensor-normalized RAW clipped[0,1], R/G-on-red-row/B/G-on-blue-row packing plus sqrt(max(shot*clipped_noisy+read,0)); input-only noise coefficients.",
        "output": "Authors' clipped packed RAW, inverse phase permutation, independent WB-aware Malvar. This is a cascade, not a joint RGB network. No fitted gain or target-dependent transform.",
        "source_receipts": {
            str(p.relative_to(root)): _sha(p)
            for p in [
                root / "receipt.json",
                root / "inspection-cpu-v1/receipt.json",
                root / "native-cuda-build-v1/receipt.json",
                root / "patchmatch-dependency-v1/receipt.json",
                root / "patchmatch-native-build-v1/receipt.json",
                root / "deform-dependency-v1/receipt.json",
            ]
        },
    }
    if archive is not None:
        destination = writable_path(archive) / "nonlocal-reference"
        destination.mkdir(parents=True, exist_ok=False)
        (destination / "receipt.json").write_text(json.dumps(model.receipt, indent=2) + "\n")
        for label, path in [
            ("network-MIT", root / "source/LICENSE"),
            ("deform-MIT", root / "deform-dependency-v1/source/LICENSE"),
            ("patchmatch-MIT", root / "patchmatch-dependency-v1/source/LICENSE"),
        ]:
            (destination / f"{label}-LICENSE").write_bytes(path.read_bytes())
    return model
