State of the art 16 bit joint demosaicing and denoising from free images.

See PROMPT.md for additional details.

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
siblings out of training. The ISO100 f/5.6 exposure has different framing and
moving subjects; it is a qualitative reference, not a pixelwise scoring target.
