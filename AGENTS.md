State of the art 16 bit joint demosaicing and denoising from free images.

See PROMPT.md for additional details.

Keep README and docs current with the best useful implementations and notable
image comparisons. Study-specific significance/promotion gates do not freeze
the architectural baseline or prevent documenting real gains. Compare strengths
and remaining weaknesses directly. Use the timestamped diary for historical
decisions; preserve existing machine receipts and experiment evidence.

Diary filenames and human-facing diary creation times use the DST-aware
America/Los_Angeles local timezone. Create entries with
`python scripts/diary.py new "Title" --slug short-summary` to avoid UTC filenames.
Explicitly labeled UTC timestamps inside machine receipts remain UTC. Historical
renames are recorded in `diary/timestamp-corrections.json`; preserve receipt bytes.

Performance reports for improved models must include at least two small native
100% crop triplets: noisy, denoised, and GT. Use identical coordinates and display
transforms across methods; never resize the crop pixels. Record source/ROI,
checkpoint hash, noise conditioning and display exposure. For real captures,
label approximate or independently demosaiced references accurately instead of
calling them exact GT. Keep a small representative set in the top-level README.

The GFX100S train/platform scene specified in
`configs/gfx-qualitative-20231231.json` is a standing real-photo qualitative test.
Cache those two RAFs locally in `.cache/gfx-qualitative-20231231/` to avoid waking
the source hard drives. Originals remain read-only. Keep this scene and its
siblings out of training. Use DSCF3879 (ISO6400) and DSCF3880 (ISO100) going forward; these replace
DSCF3842/DSCF3883 and have nearly identical framing. Include foliage and
chain-link-fence crops alongside sky and building detail. The ISO100 f/5.6
exposure still differs in aperture and moving subjects; it is a qualitative
reference, not a pixelwise scoring target.

Also keep the additional fine green fence beside the red train's cab as a
qualitative test in `configs/gfx-green-mesh-20231231.json`: DSCF3842 ISO6400 and
DSCF3835 ISO100 f/5.6, with both straight-out-of-camera JPEGs. Cache the extra
media in `.cache/gfx-green-mesh-20231231/`; reuse the existing cached DSCF3842
RAF. Include this difficult mesh in future quality reports alongside the main
DSCF3879/3880 scene. The reference differs in aperture, exposure time and moving
subjects; it is not exact GT. Keep both captures, their JPEGs and siblings out
of training, and preserve original files read-only.
