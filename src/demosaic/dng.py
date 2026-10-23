"""Scene-linear RGB16 DNG export and full-resolution darktable JPEG previews."""

import json
import os
import shutil
import struct
import subprocess
import tempfile
from dataclasses import asdict
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
import tifffile

from .io import RawMetadata
from .safety import writable_path

DT = "{http://darktable.sf.net/}"
NAMESPACES = {
    "x": "adobe:ns:meta/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "exif": "http://ns.adobe.com/exif/1.0/",
    "xmpMM": "http://ns.adobe.com/xap/1.0/mm/",
    "xmp": "http://ns.adobe.com/xap/1.0/",
    "darktable": DT[1:-1],
    "dc": "http://purl.org/dc/elements/1.1/",
    "lr": "http://ns.adobe.com/lightroom/1.0/",
}


def export_path(path, *, output_root=None, source=None, overwrite=False):
    """Keep default storage policy; explicitly selected output roots are local overrides.

    The batch exporter requires an output directory, so the user can explicitly
    authorize destinations such as ~/pictures/composites without changing the
    repository-wide safety policy. Original source directories remain read-only.
    """
    path = Path(path).expanduser().resolve()
    if output_root is None:
        path = writable_path(path)
    else:
        root = Path(output_root).expanduser().resolve()
        if not path.is_relative_to(root):
            raise ValueError("Export must stay inside the selected output directory")
    for root in (
        Path("/mnt/external/qi"),
        Path("/mnt/dataz/pictures/raw"),
        Path.home() / "pictures/raw",
    ):
        if path == root or path.is_relative_to(root.resolve()):
            raise ValueError("Original photo directories are read-only")
    if source is not None:
        original = Path(source).expanduser().resolve()
        if (
            path == original
            or path.parent == original.parent
            or path.is_relative_to(original.parent)
        ):
            raise ValueError("Export must not write into its source directory")
    if path.exists() and not overwrite:
        raise FileExistsError(path)
    return path


def _rationals(values):
    return tuple(
        v for x in np.asarray(values).ravel() for v in (round(float(x) * 1_000_000), 1_000_000)
    )


def write_dng(
    path,
    rgb,
    *,
    metadata: RawMetadata,
    provenance=None,
    xmp=None,
    output_root=None,
    overwrite=False,
):
    """Write unbalanced H×W×3 camera RGB, rounded once into an uncompressed DNG.

    Store the original XYZ->camera matrix, inverse WB and orientation as tags.
    No display transform, resampling, source CFA tags or sensor black levels are
    baked into the already demosaiced pixels. Negative/over-white predictions
    are clipped to [0,1]; this is a 16-bit integer export, not floating-point HDR.
    """
    path = export_path(path, output_root=output_root, source=metadata.source, overwrite=overwrite)
    if path.suffix.lower() != ".dng":
        raise ValueError("Linear DNG output must have a .dng extension")
    rgb = np.asarray(rgb)
    if rgb.ndim != 3 or rgb.shape[-1] != 3 or min(rgb.shape) <= 0:
        raise ValueError("Expected finite H×W×3 camera RGB")
    matrix = np.asarray(metadata.xyz_to_camera, dtype=np.float64)
    wb = np.asarray(metadata.white_balance, dtype=np.float64)
    if (
        matrix.shape != (3, 3)
        or not np.isfinite(matrix).all()
        or abs(np.linalg.det(matrix)) < 1e-10
        or wb.shape != (3,)
        or not np.isfinite(wb).all()
        or np.any(wb <= 0)
    ):
        raise ValueError(
            "DNG requires a usable XYZ-to-camera matrix and positive RGB white balance"
        )
    if metadata.flip not in (0, 3, 5, 6):
        raise ValueError("Unsupported RAW orientation")
    for y in range(0, rgb.shape[0], 64):
        if not np.isfinite(rgb[y : y + 64]).all():
            raise ValueError("Expected finite H×W×3 camera RGB")
    height, width, _ = rgb.shape
    model = metadata.camera
    make = metadata.make or "Unknown"
    unique_model = model if model.lower().startswith(make.lower()) else f"{make} {model}"
    tags = [
        (271, "s", 0, make, False),
        (272, "s", 0, model, False),
        (274, "H", 1, {0: 1, 3: 3, 5: 8, 6: 6}[metadata.flip], False),
        (50706, "B", 4, (1, 4, 0, 0), False),
        (50707, "B", 4, (1, 1, 0, 0), False),
        (50708, "s", 0, unique_model, False),
        (50713, "H", 2, (1, 1), False),
        (50714, "2I", 3, (0, 1, 0, 1, 0, 1), False),
        (50717, "I", 3, (65535, 65535, 65535), False),
        (50718, "2I", 2, (1, 1, 1, 1), False),
        (50719, "I", 2, (0, 0), False),
        (50720, "I", 2, (width, height), False),
        (50721, "2i", 9, _rationals(matrix), False),
        (50728, "2I", 3, _rationals(1 / wb), False),
        (50730, "2i", 1, (0, 1), False),
        (50778, "H", 1, 21, False),  # LibRaw's matrix is calibrated at D65.
        (50827, "s", 0, Path(metadata.source).name, False),
        (50829, "I", 4, (0, 0, height, width), False),
    ]
    if xmp:
        tags.append((700, "B", len(xmp), xmp, False))

    def strips():
        for y in range(0, height, 64):
            yield np.rint(np.clip(rgb[y : y + 64], 0, 1) * 65535).astype("<u2").tobytes()

    description = {
        "color_space": "linear-camera-RGB",
        "bits_per_sample": 16,
        "raw_metadata": asdict(metadata),
        "provenance": provenance,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=f".{path.stem}-", suffix=".dng.tmp", dir=path.parent)
    os.close(handle)
    temporary = Path(name)
    try:
        tifffile.imwrite(
            temporary,
            strips(),
            shape=rgb.shape,
            dtype="<u2",
            byteorder="<",
            photometric=34892,
            planarconfig="contig",
            rowsperstrip=64,
            subfiletype=0,
            metadata=None,
            description=json.dumps(description),
            software="demosaic linear RGB16 DNG",
            extratags=tags,
        )
        if overwrite:
            temporary.replace(path)
        else:
            os.link(temporary, path)  # Do not clobber a concurrent export.
    finally:
        temporary.unlink(missing_ok=True)
    return path


def adapt_darktable_xmp(data):
    """Preserve color edits, replacing RAW preparation and removing extra denoise."""
    root = ET.fromstring(data)
    found = False
    for node in root.iter():
        operation = node.get(DT + "operation")
        found |= operation is not None
        if operation == "rawprepare":
            if node.get(DT + "modversion") != "2":
                raise ValueError(
                    "Unsupported darktable rawprepare version; refusing to reuse sensor levels/crop"
                )
            node.set(DT + "params", struct.pack("<4i4H2I", 0, 0, 0, 0, 0, 0, 0, 0, 65535, 0).hex())
        if operation in {
            "rawprepare",
            "demosaic",
            "rawdenoise",
            "denoiseprofile",
            "hotpixels",
            "highlights",
        }:
            node.set(DT + "enabled", "0")
        for key in ("history_auto_hash", "history_current_hash", "history_basic_hash"):
            node.attrib.pop(DT + key, None)
    if not found:
        raise ValueError("XMP does not contain a darktable editing history")
    # darktable detects its sidecars using the literal xmlns:darktable prefix.
    for prefix, uri in NAMESPACES.items():
        ET.register_namespace(prefix, uri)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def copy_capture_metadata(source, destination):
    """Optional EXIF copy, with an explicit capture-tag allowlist (no image tags)."""
    if Path(source).resolve() == Path(destination).resolve():
        raise ValueError("Capture metadata destination must differ from its source")
    if not shutil.which("exiftool"):
        return False
    tags = (
        "Make",
        "Model",
        "Artist",
        "Copyright",
        "DateTimeOriginal",
        "CreateDate",
        "OffsetTimeOriginal",
        "SubSecTimeOriginal",
        "ExposureTime",
        "FNumber",
        "ISO",
        "ExposureBiasValue",
        "ExposureProgram",
        "MeteringMode",
        "FocalLength",
        "FocalLengthIn35mmFormat",
        "LensMake",
        "LensModel",
        "LensInfo",
        "LensSerialNumber",
        "SerialNumber",
        "GPS:all",
    )
    subprocess.run(
        [
            "exiftool",
            "-overwrite_original",
            "-TagsFromFile",
            str(source),
            *["-" + tag for tag in tags],
            str(destination),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return True


def render_darktable_jpeg(
    dng,
    source_xmp,
    output,
    *,
    executable="darktable-cli",
    output_root=None,
    quality=97,
    overwrite=False,
):
    """Render adapted XMP edits at native resolution with isolated temporary state.

    Return the adapted sidecar path. CPU rendering avoids competing with CUDA
    restoration jobs. Render failures publish neither a JPEG nor a sidecar.
    """
    dng, source_xmp = Path(dng).resolve(), Path(source_xmp).resolve()
    output = export_path(output, output_root=output_root, source=source_xmp, overwrite=overwrite)
    sidecar = export_path(
        Path(str(dng) + ".xmp"), output_root=output_root, source=source_xmp, overwrite=overwrite
    )
    if output.suffix.lower() not in {".jpg", ".jpeg"} or not 1 <= quality <= 100:
        raise ValueError("Expected a JPEG destination and quality in [1,100]")
    if output in {dng, source_xmp} or sidecar == source_xmp:
        raise ValueError("Preview must not overwrite its inputs")
    binary = shutil.which(str(executable))
    if binary is None:
        raise FileNotFoundError(f"darktable-cli not found: {executable}")
    data = adapt_darktable_xmp(source_xmp.read_bytes())
    with tifffile.TiffFile(dng) as image:
        page = image.pages[0]
        expected_size = (page.imagewidth, page.imagelength)
        if page.tags[274].value in (5, 6, 7, 8):
            expected_size = expected_size[::-1]
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".dng-preview-", dir=output.parent) as temporary:
        work = Path(temporary)
        xmp = work / "edits.xmp"
        xmp.write_bytes(data)
        jpeg = work / "preview.jpg"
        environment = os.environ.copy()
        environment.update(
            {
                "TMPDIR": str(work),
                "XDG_CACHE_HOME": str(work / "cache"),
                "XDG_CONFIG_HOME": str(work / "config"),
                "OMP_NUM_THREADS": "4",
            }
        )
        command = [
            binary,
            str(dng),
            str(xmp),
            str(jpeg),
            "--width",
            "0",
            "--height",
            "0",
            "--hq",
            "true",
            "--upscale",
            "false",
            "--apply-custom-presets",
            "false",
            "--icc-type",
            "sRGB",
            "--core",
            "--library",
            ":memory:",
            "--disable-opencl",
            "--configdir",
            str(work / "config"),
            "--cachedir",
            str(work / "cache"),
            "--tmpdir",
            str(work),
            "--conf",
            "write_sidecar_files=never",
            "--conf",
            f"plugins/imageio/format/jpeg/quality={quality}",
            "--conf",
            "plugins/imageio/format/jpeg/subsample=1",
        ]
        result = subprocess.run(
            command, env=environment, capture_output=True, text=True, check=False
        )
        if result.returncode:
            raise RuntimeError(f"darktable export failed:\n{result.stdout}\n{result.stderr}")
        from PIL import Image

        with Image.open(jpeg) as image:
            image.load()
            if image.size != expected_size or not image.info.get("icc_profile"):
                raise ValueError(
                    "darktable JPEG changed native dimensions or omitted its ICC profile"
                )
        if overwrite:
            jpeg.replace(output)
        else:
            os.link(jpeg, output)
        staged_sidecar = work / "adapted.dng.xmp"
        staged_sidecar.write_bytes(data)
        if overwrite:
            staged_sidecar.replace(sidecar)
        else:
            os.link(staged_sidecar, sidecar)
    return sidecar
