"""Native 16-bit export must preserve orientation, rounding, tags, and inputs."""

import json

import numpy as np
import pytest
import tifffile

from demosaic.io import write_rgb16


@pytest.mark.parametrize("dtype", [np.float32, np.float64])
@pytest.mark.parametrize("flip,turns", [(0, 0), (3, 2), (5, 1), (6, 3)])
@pytest.mark.parametrize("layout", ["contiguous", "CHW-view", "reversed"])
def test_native_pixels_match_previous_export(tmp_path, dtype, flip, turns, layout):
    rng = np.random.default_rng(71)
    rgb = rng.uniform(-0.1, 1.1, (263, 139, 3)).astype(dtype)
    # Include exact endpoints, half-code rounding, and clipped signed/HDR values.
    rgb[0, :4] = np.array(
        [[-2, 0, 2], [0.5, 1, -0.0], [0.5, 1.5, 2.5], [32766.5, 32767.5, 32768.5]],
        dtype=dtype,
    )
    rgb[0, 2:4] /= 65535
    if layout == "CHW-view":
        rgb = np.ascontiguousarray(rgb.transpose(2, 0, 1)).transpose(1, 2, 0)
    elif layout == "reversed":
        rgb = rgb[::-1, ::-1]
    original = rgb.copy()
    rgb.flags.writeable = False
    expected = np.rot90(np.rint(np.clip(rgb, 0, 1) * 65535).astype(np.uint16), turns)
    path = tmp_path / "pixels.tiff"
    metadata = {"source": "synthetic export precision fixture", "exposure": 4}
    write_rgb16(path, rgb, metadata=metadata, flip=flip)
    with tifffile.TiffFile(path) as tif:
        assert len(tif.pages) == 1
        page = tif.pages[0]
        assert page.bitspersample == 16
        assert page.photometric.name == "RGB"
        assert json.loads(page.description) == {
            "color_space": "linear-camera-RGB",
            "bits_per_sample": 16,
            "metadata": metadata,
        }
        np.testing.assert_array_equal(tif.asarray(), expected)
    np.testing.assert_array_equal(rgb, original)
    assert not path.with_suffix(".tiff.tmp").exists()


def test_final_partial_strip_and_byte_stream(tmp_path, monkeypatch):
    imwrite = tifffile.imwrite
    strip_sizes = []

    def inspect_stream(path, data, **kwargs):
        assert not isinstance(data, np.ndarray)

        def checked():
            for strip in data:
                assert isinstance(strip, bytes)
                strip_sizes.append(len(strip))
                yield strip

        return imwrite(path, checked(), **kwargs)

    monkeypatch.setattr(tifffile, "imwrite", inspect_stream)
    rgb = np.linspace(0, 1, 259 * 17 * 3, dtype=np.float32).reshape(259, 17, 3)
    output = tmp_path / "partial.tiff"
    write_rgb16(output, rgb, color_space="sRGB")
    assert strip_sizes == [128 * 17 * 3 * 2, 128 * 17 * 3 * 2, 3 * 17 * 3 * 2]
    with tifffile.TiffFile(output) as tif:
        assert json.loads(tif.pages[0].description)["color_space"] == "sRGB"
        assert 34675 in tif.pages[0].tags
        np.testing.assert_array_equal(tif.asarray(), np.rint(rgb * 65535).astype(np.uint16))


@pytest.mark.parametrize("bad_value", [np.nan, np.inf, -np.inf])
def test_nonfinite_last_strip_keeps_destination(tmp_path, bad_value):
    output = tmp_path / "preserved.tiff"
    output.write_bytes(b"existing destination")
    rgb = np.zeros((259, 7, 3), dtype=np.float32)
    rgb[-1, -1, -1] = bad_value
    with pytest.raises(ValueError, match="finite"):
        write_rgb16(output, rgb)
    assert output.read_bytes() == b"existing destination"
    assert not output.with_suffix(".tiff.tmp").exists()


def test_failed_write_keeps_destination_and_removes_partial(tmp_path, monkeypatch):
    output = tmp_path / "preserved.tiff"
    output.write_bytes(b"existing destination")

    def fail(path, data, **kwargs):
        path.write_bytes(next(data))
        raise OSError("simulated partial write failure")

    monkeypatch.setattr(tifffile, "imwrite", fail)
    with pytest.raises(OSError, match="partial write"):
        write_rgb16(output, np.zeros((259, 7, 3), dtype=np.float32))
    assert output.read_bytes() == b"existing destination"
    assert not output.with_suffix(".tiff.tmp").exists()
