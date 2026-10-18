"""Compare actual archived default data/loss code, including RNG and gradients."""

import argparse
import importlib.util
import json
from pathlib import Path

import torch
from probe_saved_cfa_gain_grid import ref

from demosaic.cfa import mosaic
from demosaic.data import degrade
from demosaic.losses import reconstruction_loss
from demosaic.raw_clean import degrade_raw_clean
from demosaic.safety import writable_path


def load(path, name):
    spec = importlib.util.spec_from_file_location("demosaic._camera_legacy_" + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(legacy, output):
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    legacy = Path(legacy)
    current = Path("src/demosaic")
    unchanged = [
        "cfa.py",
        "color.py",
        "noise.py",
        "precision.py",
        "textures.py",
        "model.py",
        "pretrained_rgb.py",
        "dino_pyramid.py",
        "dino_adaptation.py",
        "raw_kernel.py",
        "packed_isotropic.py",
        "inference.py",
        "metrics.py",
        "reporting.py",
    ]
    assert all((legacy / name).read_bytes() == (current / name).read_bytes() for name in unchanged)
    old_data = load(legacy / "data.py", "data")
    old_raw = load(legacy / "raw_clean.py", "raw_clean")
    old_losses = load(legacy / "losses.py", "losses")
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    for label, folder in [("old", legacy), ("new", current)]:
        target = output / "source" / label
        target.mkdir(parents=True)
        for name in ["data.py", "raw_clean.py", "losses.py", *unchanged]:
            (target / name).write_bytes((folder / name).read_bytes())
    (output / "source/driver.py").write_bytes(Path(__file__).read_bytes())
    records = []
    loss_count = 0
    for seed in [4, 41, 53]:
        rgb = torch.rand((2, 3, 32, 32), generator=torch.Generator().manual_seed(seed))
        for native in [False, True]:
            for signed in [False, True]:
                kwargs = {
                    "reconstruct_highlights": True,
                    "preserve_negative_read_noise": signed,
                    "noise_free_fraction": 0.1,
                }
                if native:
                    clean = {
                        "camera_rgb": rgb,
                        "wb": torch.tensor([[2.0, 1.0, 1.5]]).expand(2, -1),
                        "matrix": torch.eye(3).expand(2, -1, -1),
                    }
                    f0, f1 = old_raw.degrade_raw_clean, degrade_raw_clean
                else:
                    clean = rgb
                    f0, f1 = old_data.degrade, degrade
                    kwargs["broad_camera"] = True
                torch.manual_seed(seed)
                start = torch.get_rng_state()
                b0 = f0(clean, **kwargs)
                end = torch.get_rng_state()
                torch.set_rng_state(start)
                b1 = f1(clean, **kwargs)
                assert b0.keys() == b1.keys() and all(torch.equal(v, b1[k]) for k, v in b0.items())
                assert torch.equal(end, torch.get_rng_state())
                prediction = b0["target"] + 0.01 * torch.randn(
                    b0["target"].shape, generator=torch.Generator().manual_seed(seed + 91)
                )
                for objective in ["charbonnier-v1", "image-log-mse-v1"]:
                    for weight in [0.0, 0.001]:
                        options = {
                            "objective": objective,
                            "normalized_sensor_weight": weight,
                            "multiscale_sensor_weight": weight,
                        }
                        p0 = prediction.detach().clone().requires_grad_()
                        p1 = prediction.detach().clone().requires_grad_()
                        v0, t0 = old_losses.reconstruction_loss(
                            p0, b0, mosaic(p0, b0["colors"]), **options
                        )
                        v1, t1 = reconstruction_loss(p1, b1, mosaic(p1, b1["colors"]), **options)
                        v0.backward()
                        v1.backward()
                        assert torch.equal(v0, v1) and torch.equal(p0.grad, p1.grad)
                        assert t0.keys() == t1.keys() and all(
                            torch.equal(v, t1[k]) for k, v in t0.items()
                        )
                        loss_count += 1
                records.append(
                    {
                        "seed": seed,
                        "domain": "native" if native else "commons",
                        "signed": signed,
                        "all_legacy_batch_tensors_exact": True,
                        "post_observation_RNG_exact": True,
                    }
                )
    assert not torch.cuda.is_initialized()
    result = {
        "status": "completed-independent-archived-default-data-loss-and-gradient-replay",
        "legacy_source": str(legacy),
        "driver": ref(output / "source/driver.py"),
        "source_files": [ref(p) for p in sorted((output / "source").rglob("*.py"))],
        "byte_identical_dependency_and_forward_files": unchanged,
        "observation_cases": records,
        "default_loss_and_prediction_gradient_comparisons": loss_count,
        "CUDA_initialized": False,
        "scope": "Actual archived pre-change implementations,12 common/native observations and48 default loss/gradient comparisons across both objectives and physical auxiliary weights. Exact tensors/RNG/loss/parts/gradients;14 forward/dependency files byte-identical. CPU only, no DINO/model load, new model quality or CUDA trajectory equivalence claim.",
    }
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "loss_comparisons": loss_count}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("legacy", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    main(args.legacy, args.output)
