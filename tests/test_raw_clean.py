import hashlib
import json

import numpy as np
import pytest
import torch

from demosaic.cfa import PATTERNS, color_indices, mosaic, unpack
from demosaic.io import RawMetadata
from demosaic.raw_clean import RawCleanDataset, bin_bayer, degrade_raw_clean, prepare_raw_clean
from demosaic.train import data_random_context


@pytest.mark.parametrize("pattern", PATTERNS)
@pytest.mark.parametrize("factor", [4, 8])
def test_bayer_binning_aligns_linear_colour_fields_and_has_no_quadratic_colour_fringe(
    pattern, factor
):
    y, x = np.mgrid[:96, :128].astype(np.float32)
    rgb = np.stack([0.1 + x * 0.001, 0.2 + y * 0.001, 0.3 + x * 0.0003 + y * 0.0004], axis=-1)
    raw = unpack(mosaic(torch.from_numpy(rgb).permute(2, 0, 1)[None], color_indices(pattern)))[
        0, 0
    ].numpy()
    actual = bin_bayer(raw, pattern, factor=factor)
    expected = rgb.reshape(96 // factor, factor, 128 // factor, factor, 3).mean((1, 3))[1:-1, 1:-1]
    np.testing.assert_allclose(actual, expected, atol=2e-7, rtol=0)
    gray = 0.1 + (x * x + y * y) * 1e-5
    actual = bin_bayer(gray, pattern, factor=factor)
    np.testing.assert_allclose(actual[..., 0], actual[..., 1], atol=2e-7, rtol=0)
    np.testing.assert_allclose(actual[..., 0], actual[..., 2], atol=2e-7, rtol=0)


def test_bayer_binning_retains_sub_eight_bit_values_and_reduces_flat_noise():
    raw = np.broadcast_to(np.linspace(0.04, 0.041, 512, dtype=np.float32), (512, 512)).copy()
    actual = bin_bayer(raw, "RGGB")
    values = np.rint(actual * 65535).astype(np.uint16)
    assert len(np.unique(values)) > 40
    assert len(np.unique(np.rint(raw * 255))) == 1
    rng = np.random.default_rng(8)
    noisy = 0.1 + rng.normal(0, 0.003, (512, 512)).astype(np.float32)
    binned = bin_bayer(noisy, "GRBG")
    assert np.max(np.abs(binned.mean((0, 1)) - 0.1)) < 4e-5
    assert binned.std((0, 1)).max() < 0.003 / 3


def test_raw_clean_preparation_is_readonly_resumable_and_protected_split_checked(
    tmp_path, monkeypatch
):
    import demosaic.raw_clean as native

    original = tmp_path / "source.arw"
    original.write_bytes(b"fixed source reference")
    payload = original.read_bytes()
    record = {
        "role": "reference",
        "path": str(original),
        "filename": original.name,
        "bytes": len(payload),
        "publisher_checksum": {"type": "MD5", "value": hashlib.md5(payload).hexdigest()},
        "sha1": hashlib.sha1(payload).hexdigest(),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
    meta = RawMetadata(
        str(original),
        "Camera",
        "RGGB",
        [0] * 4,
        [65535] * 4,
        [1.5, 1.0, 1.8],
        np.eye(3).tolist(),
        0,
        100,
        65535,
    )
    monkeypatch.setattr(
        native, "read_raw", lambda path: (np.full((320, 320), 0.1, dtype=np.float32), meta)
    )
    source = {
        "split": "train",
        "selection": [{"scene": "blood_oranges", "unknown_sensor": False, "clean": [record]}],
        "dataset_license": {"rightsIdentifier": "CC-BY-SA-4.0"},
        "attribution": "Fixture",
    }
    manifest = tmp_path / "source.json"
    manifest.write_text(json.dumps(source))
    output = tmp_path / "prepared"
    first = prepare_raw_clean(manifest, output, min_size=32)
    assert original.read_bytes() == payload and len(first["rows"]) == 1
    cache = output / first["rows"][0]["cache"]
    stamp = cache.stat().st_mtime_ns
    second = prepare_raw_clean(manifest, output, min_size=32)
    assert first == second and cache.stat().st_mtime_ns == stamp
    dataset = RawCleanDataset(output / "manifest.json", patch_size=32)
    torch.testing.assert_close(dataset[3]["camera_rgb"], dataset[3]["camera_rgb"], atol=0, rtol=0)
    with cache.open("r+b") as handle:
        handle.seek(-1, 2)
        handle.write(b"\xff")
    with pytest.raises(ValueError, match="checksum"):
        RawCleanDataset(output / "manifest.json", patch_size=32)
    source["selection"][0]["scene"] = "2pilesofplates"
    manifest.write_text(json.dumps(source))
    with pytest.raises(ValueError, match="protected"):
        prepare_raw_clean(manifest, tmp_path / "forbidden")


def test_native_noise_free_observation_preserves_camera_units_and_metadata():
    torch.set_num_threads(2)
    torch.manual_seed(8)
    image = torch.rand(2, 3, 32, 32) * 0.03
    wb = torch.tensor([[1.5, 1.0, 1.8], [0.8, 1.0, 2.0]])
    matrix = torch.eye(3)[None].expand(2, -1, -1).clone()
    batch = {"camera_rgb": image, "wb": wb, "matrix": matrix}
    before = image.clone()
    result = degrade_raw_clean(batch, noise_free_fraction=1.0)
    assert result["variance"].count_nonzero() == 0
    torch.testing.assert_close(
        result["packed"], mosaic(result["target"], result["colors"]), atol=1 / 65535, rtol=0
    )
    torch.testing.assert_close(result["wb"], wb, atol=0, rtol=0)
    torch.testing.assert_close(result["matrix"], matrix, atol=0, rtol=0)
    torch.testing.assert_close(image, before, atol=0, rtol=0)


@pytest.mark.parametrize(
    "device",
    [
        "cpu",
        pytest.param(
            "cuda",
            marks=pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA unavailable"),
        ),
    ],
)
def test_step_data_rng_isolates_substituted_sources_and_restores_global_state(device):
    cpu_before = torch.get_rng_state()
    cuda_before = torch.cuda.get_rng_state() if device == "cuda" else None
    with data_random_context(device, 44, 1, True):
        torch.rand(3, device=device)
    with data_random_context(device, 44, 2, True):
        expected = torch.rand(17, device=device)
    with data_random_context(device, 44, 1, True):
        torch.rand(1000, device=device)
    with data_random_context(device, 44, 2, True):
        actual = torch.rand(17, device=device)
    torch.testing.assert_close(actual, expected, atol=0, rtol=0)
    assert torch.equal(cpu_before, torch.get_rng_state())
    if cuda_before is not None:
        assert torch.equal(cuda_before, torch.cuda.get_rng_state())
