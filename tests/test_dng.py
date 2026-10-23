import hashlib
import importlib.util
import json
import shutil
import struct
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
import pytest
import rawpy
import tifffile
from PIL import Image, JpegImagePlugin

from demosaic.dng import DT, adapt_darktable_xmp, export_path, render_darktable_jpeg, write_dng
from demosaic.io import RawMetadata, camera_matrix

MATRIX = np.array(
    [[1.6212, -0.8423, -0.1583], [-0.4336, 1.2583, 0.1937], [-0.0195, 0.0726, 0.6199]]
)
DARKTABLE = shutil.which("darktable-cli") or (
    "/opt/darktable/bin/darktable-cli"
    if Path("/opt/darktable/bin/darktable-cli").is_file()
    else None
)


def metadata(tmp_path, flip=0):
    return RawMetadata(
        str(tmp_path / "originals/photo.raf"),
        "GFX100S",
        "RGGB",
        [4096] * 4,
        [65535] * 4,
        [1.5, 1, 2.2],
        camera_matrix(MATRIX).tolist(),
        flip,
        make="FUJIFILM",
        xyz_to_camera=MATRIX.tolist(),
    )


def sidecar():
    # Deliberately nonzero sensor margins/black, which must not be applied again.
    params = struct.pack("<4i4H2I", 8, 7, 12, 11, 4096, 4096, 4096, 4096, 65535, 0).hex()
    history = "".join(
        f'<rdf:li darktable:num="{i}" darktable:operation="{name}" '
        f'darktable:enabled="1" darktable:modversion="{version}" '
        f'darktable:params="{value}" darktable:multi_priority="0"/>'
        for i, (name, version, value) in enumerate(
            [
                ("rawprepare", "2", params),
                ("demosaic", "6", "00"),
                ("denoiseprofile", "12", "00"),
                ("exposure", "7", "abcd"),
            ]
        )
    )
    return (
        f'<x:xmpmeta xmlns:x="adobe:ns:meta/" '
        f'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:darktable="{DT[1:-1]}">'
        '<rdf:RDF><rdf:Description darktable:xmp_version="5" darktable:history_current_hash="stale">'
        f"<darktable:history><rdf:Seq>{history}</rdf:Seq></darktable:history>"
        "</rdf:Description></rdf:RDF></x:xmpmeta>"
    ).encode()


@pytest.mark.parametrize("flip,orientation", [(0, 1), (3, 3), (5, 8), (6, 6)])
def test_linear_dng_libraw_pixels_precision_and_color_metadata(tmp_path, flip, orientation):
    rgb = np.linspace(-0.01, 1.02, 67 * 83 * 3, dtype=np.float32).reshape(67, 83, 3)
    path = tmp_path / "exports/photo.dng"
    write_dng(path, rgb, metadata=metadata(tmp_path, flip))
    expected = np.rint(np.clip(rgb, 0, 1) * 65535).astype(np.uint16)
    with tifffile.TiffFile(path) as image:
        page = image.pages[0]
        np.testing.assert_array_equal(page.asarray(), expected)
        assert page.photometric == 34892 and page.bitspersample == 16
        assert page.tags[274].value == orientation
        assert page.tags[50717].value == (65535,) * 3
        assert page.tags[50714].value == (0, 1, 0, 1, 0, 1)
        assert json.loads(page.description)["color_space"] == "linear-camera-RGB"
    with rawpy.imread(str(path)) as decoder:
        assert decoder.raw_pattern is None and decoder.num_colors == 3
        np.testing.assert_array_equal(decoder.raw_image_visible[:, :, :3], expected)
        np.testing.assert_allclose(decoder.rgb_xyz_matrix[:3], MATRIX, atol=1e-6)
        np.testing.assert_allclose(decoder.camera_whitebalance[:3], [1.5, 1, 2.2], atol=1e-5)


def test_linear_dng_does_not_bake_white_balance_or_display_gamma(tmp_path):
    meta = metadata(tmp_path)
    rgb_to_xyz = np.array(
        [
            [0.412453, 0.357580, 0.180423],
            [0.212671, 0.715160, 0.072169],
            [0.019334, 0.119193, 0.950227],
        ]
    )
    meta.xyz_to_camera = np.linalg.inv(rgb_to_xyz).tolist()
    meta.white_balance = [2, 1, 1.5]
    rgb = np.broadcast_to(np.array([0.1, 0.2, 0.2 / 1.5], dtype=np.float32), (48, 64, 3))
    path = tmp_path / "exports/neutral.dng"
    write_dng(path, rgb, metadata=meta)
    with rawpy.imread(str(path)) as decoder:
        output = decoder.postprocess(
            output_bps=16, gamma=(1, 1), no_auto_bright=True, use_camera_wb=True, user_flip=0
        )
    assert np.ptp(output.astype(np.int32).mean(axis=(0, 1))) < 8


def test_invalid_dng_does_not_replace_previous_output(tmp_path):
    path = tmp_path / "exports/keep.dng"
    path.parent.mkdir()
    path.write_bytes(b"previous-export")
    rgb = np.zeros((65, 32, 3), dtype=np.float32)
    rgb[-1, -1, -1] = np.nan
    with pytest.raises(ValueError, match="finite"):
        write_dng(path, rgb, metadata=metadata(tmp_path), overwrite=True)
    assert path.read_bytes() == b"previous-export"
    assert list(path.parent.iterdir()) == [path]


@pytest.mark.parametrize(
    "matrix", [None, np.zeros((3, 3)).tolist(), np.full((3, 3), np.nan).tolist()]
)
def test_missing_or_unusable_color_profile_never_writes_a_dng(tmp_path, matrix):
    meta = metadata(tmp_path)
    meta.xyz_to_camera = matrix
    path = tmp_path / "exports/invalid.dng"
    with pytest.raises(ValueError, match="XYZ-to-camera"):
        write_dng(path, np.zeros((16, 16, 3), dtype=np.float32), metadata=meta)
    assert not path.exists()


def test_explicit_export_root_cannot_escape_or_write_originals(tmp_path):
    root = tmp_path / "exports"
    original = tmp_path / "originals/photo.raf"
    assert export_path(root / "photo.dng", output_root=root) == root / "photo.dng"
    with pytest.raises(ValueError):
        export_path(root / "../escaped.dng", output_root=root)
    with pytest.raises(ValueError, match="source directory"):
        export_path(original.parent / "new.dng", output_root=tmp_path, source=original)
    with pytest.raises(ValueError, match="read-only"):
        export_path("/mnt/dataz/pictures/raw/new.dng", output_root="/mnt/dataz")
    root.mkdir()
    (root / "link").symlink_to(original.parent, target_is_directory=True)
    with pytest.raises(ValueError):
        export_path(root / "link/new.dng", output_root=root)


def test_xmp_preserves_color_edits_but_removes_sensor_processing():
    original = sidecar()
    adapted = adapt_darktable_xmp(original)
    assert b'xmlns:darktable="http://darktable.sf.net/"' in adapted
    root = ET.fromstring(adapted)
    operations = {
        node.get(DT + "operation"): node for node in root.iter() if node.get(DT + "operation")
    }
    raw = operations["rawprepare"]
    assert struct.unpack("<4i4H2I", bytes.fromhex(raw.get(DT + "params"))) == (0,) * 8 + (65535, 0)
    assert all(
        operations[name].get(DT + "enabled") == "0"
        for name in ("rawprepare", "demosaic", "denoiseprofile")
    )
    assert operations["exposure"].get(DT + "params") == "abcd"
    assert operations["exposure"].get(DT + "enabled") == "1"
    assert b"stale" not in adapted
    assert original == sidecar()
    with pytest.raises(ValueError, match="Unsupported"):
        adapt_darktable_xmp(original.replace(b'modversion="2"', b'modversion="99"'))


def minimal_sidecar():
    root = ET.fromstring(sidecar())
    sequence = root.find(".//" + "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Seq")
    for node in list(sequence)[1:]:
        sequence.remove(node)
    description = next(node for node in root.iter() if DT + "xmp_version" in node.attrib)
    description.set(DT + "history_end", "1")
    description.set(DT + "auto_presets_applied", "1")
    description.set(DT + "iop_order_version", "4")
    return ET.tostring(root)


def test_batch_globs_only_select_paired_inputs_when_requested(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "export_raw_dng", Path("scripts/export_raw_dng.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    paired, unpaired = tmp_path / "paired.raf", tmp_path / "unpaired.raf"
    paired.touch()
    unpaired.touch()
    xmp = tmp_path / "paired.XMP"
    xmp.write_bytes(minimal_sidecar())
    assert module.select_pairs([str(tmp_path / "*.raf"), str(paired)], only_with_xmp=True) == [
        (paired, xmp)
    ]
    with pytest.raises(FileNotFoundError, match="No XMP"):
        module.select_pairs([str(tmp_path / "*.raf")])


@pytest.mark.skipif(DARKTABLE is None, reason="darktable-cli integration")
def test_darktable_native_preview_does_not_reapply_sensor_crop(tmp_path):
    meta = metadata(tmp_path)
    source = Path(meta.source + ".xmp")
    source.parent.mkdir()
    source.write_bytes(minimal_sidecar())
    original = source.read_bytes()
    dng, jpeg = tmp_path / "exports/photo.dng", tmp_path / "exports/photo.jpg"
    write_dng(dng, np.full((96, 128, 3), 0.1, dtype=np.float32), metadata=meta)
    adapted = render_darktable_jpeg(dng, source, jpeg, executable=DARKTABLE)
    with Image.open(jpeg) as image:
        image.load()
        assert image.size == (128, 96) and image.info["icc_profile"]
        assert JpegImagePlugin.get_sampling(image) == 0
    assert source.read_bytes() == original
    assert adapted.is_file()
    assert not list(jpeg.parent.glob(".dng-preview-*"))


@pytest.mark.skipif(DARKTABLE is None, reason="darktable-cli integration")
@pytest.mark.parametrize("hot_pixel_switch", ["--hot-pixels", "--hot-pixel-clusters"])
def test_batch_cpu_export_decodes_raw_and_preserves_originals(tmp_path, hot_pixel_switch):
    import torch

    from demosaic.model import JointDemosaic, ModelConfig

    originals = tmp_path / "originals"
    originals.mkdir()
    source = originals / "photo.dng"
    tags = [
        (50706, "B", 4, (1, 4, 0, 0), False),
        (50708, "s", 0, "FUJIFILM GFX100S", False),
        (271, "s", 0, "FUJIFILM", False),
        (272, "s", 0, "GFX100S", False),
        (33421, "H", 2, (2, 2), False),
        (33422, "B", 4, (0, 1, 1, 2), False),
        (
            50721,
            "2i",
            9,
            tuple(v for x in MATRIX.ravel() for v in (round(x * 10000), 10000)),
            False,
        ),
        (50728, "2I", 3, (1, 1, 1, 1, 1, 1), False),
        (50778, "H", 1, 21, False),
        (50717, "I", 1, 65535, False),
    ]
    mosaic = np.full((64, 96), 6554, dtype=np.uint16)
    mosaic[32, 48] = 65535
    tifffile.imwrite(
        source,
        mosaic,
        photometric=32803,
        metadata=None,
        extratags=tags,
    )
    Path(str(source) + ".xmp").write_bytes(minimal_sidecar())
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    model = JointDemosaic(
        ModelConfig(
            width=4, encoder_blocks=(1,), middle_blocks=0, decoder_blocks=(1,), attention=False
        )
    )
    checkpoint = tmp_path / "tiny.pt"
    torch.save(
        {"model_config": model.config.to_dict(), "model": model.restoration_state_dict()},
        checkpoint,
    )
    spec = importlib.util.spec_from_file_location(
        "export_raw_dng", Path("scripts/export_raw_dng.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = tmp_path / "exports"
    args = module.parser().parse_args(
        [
            str(checkpoint),
            str(source),
            "--output-dir",
            str(output),
            "--darktable-cli",
            DARKTABLE,
            "--device",
            "cpu",
            "--tile",
            "32",
            "--overlap",
            "16",
            hot_pixel_switch,
        ]
    )
    result = module.run(args)
    assert len(result["completed"]) == 1
    assert result["completed"][0]["hot_pixels"]["enabled"]
    assert result["completed"][0]["hot_pixels"]["corrected_pixels"] == 1
    assert result["completed"][0]["hot_pixels"]["cluster_mode"] == (
        hot_pixel_switch == "--hot-pixel-clusters"
    )
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
    with rawpy.imread(str(output / "photo-tiny.dng")) as decoder:
        assert decoder.raw_image_visible.shape == (64, 96, 4)
    with pytest.raises(FileExistsError):
        module.run(args)
