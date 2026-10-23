# Recurring paired defects behind the remaining roof specks

The residual cyan roof speck in DSCF3842 is a pair of anomalous green Bayer
samples, rather than one isolated site. A second roof-edge speck is a diagonal
pair in the two green phases. The screenshot matches the existing RawPuppy
JPEG at native scale: its top-left is output pixel (549,3806), with normalized
grayscale correlation .999938. Applying the saved perspective/crop map locates
the following zero-based, visible-sensor coordinates.

| Sites (x,y) | DSCF3842 normalized RAW values | Why isolated correction leaves them |
| --- | --- | --- |
| (1128,4281), (1128,4283) | 1.0000, .50014 | Each is the other's bright same-phase neighbor |
| (1500,3967), (1501,3968) | .04963, .19338 | The adjacent green phase falsely supplies light corroboration |

The first pair recurs at the same sensor coordinates in cached DSCF3879,
DSCF3880 and DSCF3883: approximately 1.0000/.502–.503 despite different captures
and ISO levels. Its surrounding samples are much darker. The diagonal pair is
also anomalous at the same coordinates in those captures, with varying
amplitudes. These observations support recurring sensor-coordinate defects;
they do not identify their physical cause. The separate ISO100 photographs are
not exact GT and are not scored as pixelwise targets. All captures remain
evaluation-only, and their source files are read-only.

The recollection about darktable is consistent with these values. Its
[three-neighbor option](https://docs.darktable.org/usermanual/5.6/en/module-reference/processing-modules/hot-pixels/)
allows one of four neighbors to remain bright. An analytic check at strength .25
and threshold .01 gives only three qualifying cardinal neighbors at both sites
of the first pair and at the weaker diagonal site. This is an analysis of the
neighbor rule, not an executed darktable export.

## Optional paired-site mode

`scripts/export_raw_dng.py --hot-pixel-clusters ...` implies `--hot-pixels` and
adds these checks before restoration with the selected checkpoint:

- Use the second-largest of eight same-phase neighbors for the existing
  six-sigma / 2× contrast test, tolerating one contaminated neighbor.
- Preserve a candidate if its bright neighbor continues into a supported line.
  The first permissive prototype clipped narrow line ends; this check prevents
  that failure and has a dedicated regression test.
- Accept immediate light corroboration from a different CFA color. Two adjacent
  green phases cannot corroborate each other solely because both are bright.
- Replace accepted sites with the median of the unchanged eight neighbors.
  Decisions are simultaneous and independent of strip boundaries. Four border
  pixels are left unchanged because the continuation check looks farther out.

The isolated default remains unchanged: its DSCF3842 count and coordinate hash
reproduce the earlier export exactly. Optional mode changes 6,235 sites versus
3,229 in that frame. This is an algorithmic correction count, not independent
confirmation that every site is physically defective. An unresolved pure-color
light can resemble a pair. Larger or mixed-color clusters can remain protected;
a measured defect map would be needed to avoid classifying such lights from
one photograph. A weaker red/green pair near (1214,4287–4288) remains unchanged
and is not established as a recurring defect by these four samples.

## Native checks and scope

Matched CPU 512-pixel contexts were run through V101 final10000 EMA using the
same noise conditioning and original camera WB/matrix. Native160 crops compare
noisy bilinear, isolated correction + V101, and paired correction + V101.
Both identified roof specks disappear. The inspected blue-lit façade control
retains its visible structure. Shared display is +2EV/sRGB; no crop pixels are
resized. This is a context comparison, not a complete blended re-export or a new
model-quality/throughput evaluation. Existing DNGs and JPEGs remain unchanged
by this investigation.

Checkpoint SHA256:
`6f691c653a618bdde0d7db501f3efc557a9699e2dbba73cf94c7440b364ef3e3`.
Conditioning: shot `.00128`, read variance `6.5536e-6`. Model weights and training
are unchanged. Private PNGs, float crops, RAW samples, mapping and neighbor
decision receipts are retained in the composites directory's
`cluster-hot-pixel-review/`; no personal imagery is committed to Git.

The merged implementation passes 42 focused tests, including four CFA patterns,
both pair arrangements,
simultaneous correction and strip invariance, noise-only controls, narrow green
line ends, multi-color/white point lights and complete CPU DNG/JPEG exports
through both CLI switches. The optional mode is documented rather than silently
relaxing existing exports or claiming that all bright dots have been classified.
[Merge validation](results/linear-dng-paired-followup-merge-v1.json).
