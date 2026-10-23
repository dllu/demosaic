# Add reusable linear DNG and native JPEG export

Recorded: 2026-10-22T21:49:01-07:00 (America/Los_Angeles).

Added a reusable [linear DNG/JPEG exporter](../docs/dng-export.md) on a separate
feature branch, using an isolated worktree so ongoing work in main stays intact.
`read_raw` now preserves camera make and the original XYZ-to-camera matrix;
existing TIFF inference and model architecture remain unchanged.

The writer emits native three-channel, unbalanced camera RGB with DNG color/WB
and orientation tags, zero black and white65535. It clips and rounds once into
uncompressed uint16 strips. Original XMP histories are adapted to avoid applying
sensor crop/black levels or CFA restoration a second time; profiled/RAW denoising
is disabled while color/exposure/lens/sharpening edits remain. Preview rendering
uses an isolated darktable configuration/cache and a full-resolution sRGB JPEG.
Input globs, paired-sidecar filtering, explicit destinations, non-overwrite
defaults and per-image source/checkpoint/noise/output hashes are reusable.

Validation passes19 focused tests covering independent LibRaw decoding and native pixel/precision,
matrix/WB/orientation and invalid-output checks; a CPU synthetic RAW restoration
through the complete DNG/JPEG path; and actual darktable integration. A saved
101.995852MP private V101 export was re-encoded with the general writer, without
another learned forward: all305,987,556 uint16 samples matched exactly, and the
edited JPEG retained11662×8746 dimensions and an sRGB ICC profile. Its overview
was viewed. This checks export interoperability, not new model quality or speed.
The private four-photo batch and machine receipts remain in the requested
composites directory; no private imagery is added to Git.
