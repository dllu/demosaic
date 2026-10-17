import io
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageCms

from demosaic.prepare import bin_linear, prepare_one


@pytest.fixture
def gray_profile():
    # Synthetic D50/gamma2.2 profile generated with LittleCMS2, not photo data.
    # The profile's copyright field reads "No copyright, use freely".
    return (Path(__file__).parent / "fixtures/gray-gamma22.icc").read_bytes()


def prepare_image(tmp_path, image, profile):
    source = tmp_path / "source"
    source.mkdir()
    path = source / "image.png"
    image.save(path, **({"icc_profile": profile} if profile else {}))
    before = path.read_bytes()
    destination = tmp_path / "cache"
    record = {"id": "fixture", "download_path": "image.png", "cache": "images/fixture.npy"}
    actual, error = prepare_one(record, source, destination, 2, 8, 1_000_000)
    assert path.read_bytes() == before
    return path, destination / actual["cache"], error


@pytest.mark.parametrize("mode", ["L", "LA", "1"])
def test_gray_icc_applies_to_gray_samples_before_rgb_conversion(tmp_path, gray_profile, mode):
    image = Image.fromarray(np.arange(256, dtype=np.uint8).reshape(16, 16)).convert(mode)
    path, cache, error = prepare_image(tmp_path, image, gray_profile)
    assert error is None
    with Image.open(path) as original:
        transformed = ImageCms.profileToProfile(
            original.convert("L"),
            ImageCms.ImageCmsProfile(io.BytesIO(gray_profile)),
            ImageCms.createProfile("sRGB"),
            outputMode="RGB",
        )
        expected = bin_linear(transformed, 2)
        if mode != "1":
            assert not np.array_equal(expected, bin_linear(original.convert("RGB"), 2))
    np.testing.assert_array_equal(np.load(cache, allow_pickle=False), expected)


@pytest.mark.parametrize("mode", ["RGB", "RGBA", "P", "L", "LA"])
@pytest.mark.parametrize("embedded_profile", [False, True])
def test_existing_rgb_profile_and_unprofiled_paths_remain_bitwise_legacy(
    tmp_path, mode, embedded_profile
):
    values = np.random.default_rng(42).integers(0, 256, (16, 16, 3), dtype=np.uint8)
    image = Image.fromarray(values).convert(mode)
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))
    path, cache, error = prepare_image(
        tmp_path, image, profile.tobytes() if embedded_profile else None
    )
    assert error is None
    with Image.open(path) as original:
        legacy = original.convert("RGB")
        if embedded_profile:
            legacy = ImageCms.profileToProfile(
                legacy, profile, ImageCms.createProfile("sRGB"), outputMode="RGB"
            )
        expected = bin_linear(legacy, 2)
    np.testing.assert_array_equal(np.load(cache, allow_pickle=False), expected)


@pytest.mark.parametrize("bad_profile", [b"invalid ICC", None])
def test_malformed_and_rgb_gray_mismatched_profiles_still_fail_without_cache(
    tmp_path, gray_profile, bad_profile
):
    image = Image.new("RGB", (16, 16), (30, 90, 180))
    _, cache, error = prepare_image(tmp_path, image, bad_profile or gray_profile)
    assert error is not None
    assert not cache.exists()
