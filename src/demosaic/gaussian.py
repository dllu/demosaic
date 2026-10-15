"""Verified external Gaussian prior with physical RAW variance stabilization."""

import hashlib
import importlib.util
import json
import math
import shutil
from pathlib import Path

import torch
from torch import nn
from torch.nn import functional as F

from .cfa import malvar
from .precision import ieee_fp32
from .safety import writable_path
from .vst import GeneralizedAnscombe


class StabilizedGaussianPrior(nn.Module):
    """Denoise independent original CFA phases, then WB-aware Malvar.

    This is a nonblind physical-prior comparator, not Noise2VST test-time fitting
    or a jointly trained DINO model. Noise coefficients must be supplied from
    input-only calibration or declared sensor priors. No target-based gain.
    """

    def __init__(self, network, *, inverse="table"):
        super().__init__()
        self.network = network.eval().requires_grad_(False)
        self.inverse_mode = inverse
        self.shot = self.read = None
        self.stabilizer = None

    def set_noise(self, shot, read):
        shot, read = float(shot), float(read)
        if not math.isfinite(shot) or not math.isfinite(read) or min(shot, read) < 0:
            raise ValueError("Finite nonnegative noise coefficients are required")
        if (shot, read) != (self.shot, self.read):
            self.shot, self.read = shot, read
            self.stabilizer = (
                GeneralizedAnscombe(shot, read, inverse=self.inverse_mode).to(
                    next(self.network.parameters()).device
                )
                if shot
                else None
            )
        return self

    def forward(self, packed, variance, colors, wb=None, matrix=None):
        if self.shot is None:
            raise ValueError("Supply shot/read conditioning before inference")
        with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
            if not self.shot and not self.read:
                return malvar(packed.float(), colors, wb)
            restored = torch.empty_like(packed, dtype=torch.float32)
            for b in range(len(packed)):
                for phase in range(4):
                    raw = (
                        packed[b : b + 1, phase : phase + 1]
                        .float()
                        .contiguous(memory_format=torch.channels_last)
                    )
                    if raw.amin() == raw.amax():
                        # Fully constant/ADC-clipped phases provide no spatial
                        # noise evidence. Preserve them without inventing detail.
                        restored[b : b + 1, phase : phase + 1] = raw
                        continue
                    if self.stabilizer is not None:
                        z = self.stabilizer(raw)
                        denoised = self.network(z, sigma=1.0, norm_equiv=True).float()
                        restored[b : b + 1, phase : phase + 1] = self.stabilizer.inverse(denoised)
                    else:
                        restored[b : b + 1, phase : phase + 1] = self.network(
                            raw, sigma=math.sqrt(self.read), norm_equiv=True
                        )
            return malvar(restored, colors, wb)


class JointGaussianPrior(StabilizedGaussianPrior):
    """Experimental HQS data consistency with a frozen RGB denoising prior.

    Reconstruction happens jointly at native RGB resolution in stabilized
    camera coordinates. The noise-normalized data term sees only original CFA
    observations. This is a short, fixed-schedule experiment, not a reproduction
    of the longer DPIR algorithm or a per-image fitted model.
    """

    def __init__(self, network, *, inverse="table", sigmas=(8.0, 4.0, 2.0, 1.0), weight=0.23):
        super().__init__(network, inverse=inverse)
        if not sigmas or any(not math.isfinite(s) or s <= 0 for s in sigmas):
            raise ValueError("Joint prior requires positive finite denoising strengths")
        if not math.isfinite(weight) or weight <= 0:
            raise ValueError("Joint prior weight must be positive and finite")
        self.sigmas, self.weight = tuple(sigmas), weight

    def forward(self, packed, variance, colors, wb=None, matrix=None):
        if self.shot is None:
            raise ValueError("Supply shot/read conditioning before inference")
        if not self.shot and not self.read:
            return malvar(packed.float(), colors, wb)
        if colors.ndim == 1:
            colors = colors[None].expand(len(packed), -1)
        results = []
        with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
            for b in range(len(packed)):
                raw = packed[b : b + 1].float()
                h, w = raw.shape[-2:]
                if (raw.amin((-2, -1)) == raw.amax((-2, -1))).all():
                    results.append(
                        malvar(raw, colors[b : b + 1], None if wb is None else wb[b : b + 1])
                    )
                    continue
                z = self.stabilizer(raw) if self.stabilizer is not None else raw
                noise = 1.0 if self.stabilizer is not None else math.sqrt(self.read)
                labels = F.one_hot(colors[b : b + 1], 3).transpose(1, 2)[..., None, None].float()
                mask = F.pixel_shuffle(labels.expand(-1, -1, -1, h, w).reshape(1, 12, h, w), 2)
                observed = F.pixel_shuffle((labels * z[:, None]).reshape(1, 12, h, w), 2)
                x = malvar(z, colors[b : b + 1])
                for strength in self.sigmas:
                    rho = self.weight / strength**2
                    x = (observed + rho * x) / (mask + rho)
                    x = self.network(
                        x.contiguous(memory_format=torch.channels_last),
                        sigma=noise * strength,
                        norm_equiv=True,
                    ).float()
                results.append(self.stabilizer.inverse(x) if self.stabilizer is not None else x)
        return torch.cat(results)


def load_gaussian_prior(receipt, *, device="cpu", archive=None, inverse="table"):
    receipt = Path(receipt)
    metadata = json.loads(receipt.read_text())
    record = next(m for m in metadata["models"] if m["model"] == "DRUNet")
    source = Path(metadata["checkout"]) / "src/noise2vst/models/drunet.py"
    weights = Path(record["weights"])
    if hashlib.sha256(source.read_bytes()).hexdigest() != record["source_sha256"]:
        raise ValueError("External Gaussian source differs from verified receipt")
    if hashlib.sha256(weights.read_bytes()).hexdigest() != record["sha256"]:
        raise ValueError("External Gaussian weights differ from verified receipt")
    if archive is not None:
        archive = writable_path(archive) / "gaussian-reference"
        archive.mkdir(parents=True, exist_ok=True)
        for origin, name in [
            (source, "drunet.py"),
            (receipt, "reference.json"),
            (Path(metadata["checkout"]) / "LICENSE", "Noise2VST-LICENSE"),
            (Path(metadata["kair_license"]), "KAIR-LICENSE"),
        ]:
            shutil.copyfile(origin, archive / name)
        frozen = archive / f"weights-{record['sha256']}.pth"
        if not frozen.exists():
            shutil.copyfile(weights, frozen)
        weights = frozen
        source = archive / "drunet.py"
        if hashlib.sha256(weights.read_bytes()).hexdigest() != record["sha256"]:
            raise ValueError("Frozen Gaussian weights differ from verified receipt")
        if hashlib.sha256(source.read_bytes()).hexdigest() != record["source_sha256"]:
            raise ValueError("Archived Gaussian source differs from verified receipt")
    spec = importlib.util.spec_from_file_location("demosaic_verified_gaussian", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    network = module.DRUNet(color=record.get("color", False))
    network.load_state_dict(torch.load(weights, map_location="cpu", weights_only=True), strict=True)
    if metadata.get("joint_sigmas"):
        if not record.get("color"):
            raise ValueError("Joint reconstruction requires verified RGB weights")
        model = JointGaussianPrior(
            network,
            inverse=inverse,
            sigmas=metadata["joint_sigmas"],
            weight=metadata.get("joint_weight", 0.23),
        )
        label = f"DRUNet-RGB:GAT-{inverse}:HQS{len(model.sigmas)}"
    else:
        model = StabilizedGaussianPrior(network, inverse=inverse)
        label = f"DRUNet-gray:GAT-{inverse}:Malvar"
    model = model.to(device).eval()
    if torch.device(device).type == "cuda":
        model.to(memory_format=torch.channels_last)
    model.receipt = {
        "label": label,
        "weights_sha256": record["sha256"],
        "sha256": record["sha256"],
        "source_sha256": record["source_sha256"],
        "snapshot": str(weights),
        "inverse": inverse,
        "compute_precision": "IEEE float32",
        "conditioning": "Explicit shot/read priors; no input fitting or target gain",
        "source_receipt": str(receipt),
        "physical_compute_precision": "float64 transform/inverse; float32 RGB and neural prior",
        "joint_sigmas": metadata.get("joint_sigmas"),
        "joint_weight": metadata.get("joint_weight") if metadata.get("joint_sigmas") else None,
    }
    return model
