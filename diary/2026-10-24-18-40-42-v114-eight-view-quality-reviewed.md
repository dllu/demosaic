# Review V114 eight-view quality and current native comparisons

Recorded: 2026-10-24T18:40:42-07:00 (America/Los_Angeles).

Completed the fixed24 V114 eight-view pilot and independent saved-output
analysis. Exactly192 new restoration/official Tiny encoder calls used the
same12 material, two adverse camera, six GFX512-context and four color inputs
as the earlier V112 pilot. Existing V112/V104/stronger RawNIND outputs were
reused. All24 FP32 means reconstruct exactly by NumPy64 averaging; separate
NumPy64/Torch64 metrics agree within7.11e-15. There were no new noise draws,
RAW decodes, optimizer updates or CUDA calls. The856.23s CPU execution is not
GPU timing. All91 loaded EMA tensors match V114; weights, encoder, input files
and Torch RNG remained unchanged.

All twelve material PSNRs improve over V114 single view. Four-source means
gain+.55750/.26416/.07938dB at ADC-only/ISO100/ISO12800. Against V112 eight
views the gains are+.16347/.05230/.01100dB. The two selected M100 crop gains
over V114 single are+.14961/+.22673dB, but both still trail stronger RawNIND.
These selected examples do not replace the complete427-photo or scene-balanced
camera panels. All four selected color mean biases increase while spatially
centered RMS decreases; the eight-view full1176-color maximum is unmeasured.

Actually viewed all164 native160 board cells plus the six cells in the two
small bark/canopy triplets. The latter repeat pixels from the material board,
not independent observations. Finest high-noise texture remains soft, dark
camera fields retain coarse colored variation, and GFX foliage/neon detail
remains painterly/smeared. GFX DSCF3879/3880 remain held-out cached exposures;
the separate ISO100 exposure and independently demosaiced camera references
are not exact GT. The boards include foliage and chain-link fence.

Published [the report](../docs/v114-eight-view.md),
[execution/analysis/review evidence](../docs/results/v114-dihedral8-pilot-v1.json),
two native noisy/restored/exact-GT triplets and six comparison boards with
[unchanged image/ROI/conditioning/display receipts](../docs/images/v114-dihedral8-pilot/manifest.json).
Updated README, current guides and the GFX gallery to describe the useful
optional mode and its limitations. V114 remains the learned baseline and
single view remains the default; no new trained-version or full-panel point
was added to the PSNR plot. Preserved the prior selector bytes locally before
adding the optional-mode note, as well as the original launch receipt and diary.

V116's original fresh20k training, evaluator, independent audit and direct
V114 comparison remain unchanged. At18:45 PDT the original worker had logged
step6800, finite train metrics and six completed validation monitors; all four
owners and the training child were live. This is a progress observation, not
an endpoint quality result. The data trial still uses only the two planned
data changes, with normalized-band supervision disabled. Full quality panels,
native review and any resulting recommendation follow the completed run.

