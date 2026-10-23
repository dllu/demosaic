# Linear DNG and full-resolution JPEG export

`scripts/export_raw_dng.py` restores ordinary Bayer RAW/XMP pairs with a selected
checkpoint. It loads the model once, uses IEEE FP32 tiles, and writes a native
RGB16 DNG, a full-resolution sRGB JPEG, an adapted `.dng.xmp`, and a batch JSON
manifest. Source RAWs and XMPs remain read-only. No personal images are committed.

```bash
source scripts/env.sh
PYTHONPATH=src uv run python scripts/export_raw_dng.py \
  /mnt/external/demosaic/models/v102-final20000.pt \
  '/path/to/raw/2023-12-31-17*.raf' \
  --only-with-xmp --suffix v101 \
  --output-dir ~/pictures/composites/2023-12-31-ochanomizu \
  --darktable-cli /opt/darktable/bin/darktable-cli --cudnn-benchmark --hot-pixels
```

Quoted globs are expanded by the exporter. By default, every selected input needs
a matching `photo.raf.xmp` or `photo.xmp` (uppercase `.XMP` also works).
`--only-with-xmp` filters out inputs without sidecars. Existing outputs cause an
error before model loading; use `--overwrite` explicitly to replace a batch.
The required `--output-dir` authorizes that directory for this command without
changing the repository-wide output policy. Source directories and the original
Commons corpus are still protected. The script requires `darktable-cli` for
edited JPEGs; `exiftool` optionally copies capture EXIF using a restricted tag
list. The Python DNG writer itself needs neither executable nor extra codecs.

Noise conditioning uses a reliable input-only Haar estimate when identifiable,
otherwise the existing nominal ISO prior. Narrow brightness ranges often trigger
that fallback in night photographs. These priors are not measured camera
profiles. Supply both `--shot` and `--read` to use calibrated coefficients.
The manifest records the estimate, fallback, coefficients, checkpoint/source/XMP
hashes, tile settings, timings and output hashes for every completed image.
Timings are shared-machine observations, not a new model speed claim.

## Hot-pixel correction

`--hot-pixels` repairs isolated bright Bayer outliers **before V102 or another
restoration model sees them**, so correction is included in both the DNG and
JPEG. Enabling a darktable preview module after demosaicing cannot repair the
stored Bayer measurements; darktable's module skips RGB linear DNGs. The option
is explicit and off by default, preserving earlier comparison protocols.

The detector compares each site with its eight nearest neighbors of the same
Bayer phase (offsets of two sensor pixels). A candidate must exceed their maximum
by six noise standard deviations and be more than twice as bright. The minimum
excess is .005 in black-subtracted, white-normalized units. Before replacement,
an immediately neighboring site that exceeds its own phase median by three
noise standard deviations protects spatially coherent light detail. Remaining
candidates are replaced with the median of the eight same-phase neighbors.
The original RAW and input array remain unchanged. All decisions read unchanged
input, so results do not depend on processing strips or earlier corrections.

Thresholds are adjustable with `--hot-pixel-sigma`, `--hot-pixel-ratio` and
`--hot-pixel-min-delta`. The noise coefficients are the same ones supplied to
restoration. Counts, phase counts, parameters, coordinate hashes and selected
before/after values are stored in the DNG provenance and batch manifest. The
three-pixel image border, clusters and supported highlights are intentionally
left alone. A genuine unresolved single-color light remains ambiguous in a
single exposure; this is a conservative outlier detector, not a calibrated
sensor defect map. It does not change model weights or training data.

On the private four-image GFX100S batch, the selected settings corrected 2,574 and
3,229 sites in the two ISO 6400 captures, and 767 and 1,001 in the ISO 100 captures.
The immediate-neighbor guard retained 1,242/980 additional candidates in the high
ISO frames, including inspected illuminated-façade detail. These are correction
counts, not verified physical defect counts. Original source images and their
sidecars remain read-only; private native before/after crops and machine
receipts stay with the exports. There is no new model-quality or speed claim.

## Output format and sidecars

The DNG contains unbalanced scene-linear camera RGB with three 16-bit channels,
PhotometricInterpretation `LinearRaw`, zero black, white 65535, the original
XYZ-to-camera matrix, inverse camera white balance, and an orientation tag.
White balance, display gamma, color rendering and XMP edits are not baked into
the DNG samples. Predictions are clipped to [0,1] and rounded once. These are
uncompressed integer DNGs, approximately six bytes per native pixel; they do not
preserve negative values or values above sensor white as floating-point HDR.
The standalone JPEG is quality97 / 4:4:4 by default, with an sRGB ICC profile.
Its dimensions include the orientation but never a downscaled preview.

The adapted darktable history retains exposure, color, tone, lens and sharpening
edits. It replaces the original RAW crop/black-level parameters with an identity
preparation and disables CFA demosaicing, highlight reconstruction, hot-pixel
repair, RAW denoising and profiled denoising. This prevents processing the
restored data twice. `rawprepare` version2 is supported; unfamiliar versions
fail explicitly. The history's cached hashes are removed. Each darktable
invocation uses a temporary configuration, library and cache in the output
directory and CPU rendering; that temporary directory is removed on completion.
Some applications may display a different default rendering of a linear DNG;
the accompanying JPEG and `.dng.xmp` preserve the chosen darktable appearance.

`demosaic.dng.write_dng` is also a Python API for already restored H×W×3 floats;
pass `RawMetadata` returned by `read_raw`, which now retains camera make and the
original matrix. Old metadata without a matrix cannot produce a correctly
profiled DNG and fails explicitly. Existing TIFF inference is unchanged.

Validation covers independent LibRaw decoding, exact 16-bit pixels across partial
strips, orientation and color tags, neutral white balance, protected destinations,
and invalid-image atomicity. Optional darktable integration checks the original
sensor crop is not applied twice. A small CPU batch test exercises RAW decoding,
restoration, DNG/JPEG generation, hashing and refusal to overwrite originals.
Hot-pixel tests cover all four CFA phases, sparse changes, unchanged input,
noise-only data, line/edge/light protection and strip-boundary invariance.
The format follows the [Adobe DNG specification](https://helpx.adobe.com/camera-raw/desktop/dng-and-file-formats/digital-negative.html).
