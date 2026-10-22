# Complete remaining source-quality candidate review

Recorded: 2026-10-22T11:31:50-07:00 (America/Los_Angeles).

The previous goal turn made progress: native ADC-only/ISO100 comparisons and
condition-specific full-panel results exposed V84's low-noise improvements,
and the current documentation was updated (04bbec8). Revalidated the live V100
controller/worker and waiting evaluation controller before continuing.

Completed the remaining 110 unreviewed sources in the saved loss/proxy candidate
pool. Rendered and actually viewed 19 source sheets at original resolution,
plus six larger native1024 source crops. Each sheet includes a context thumbnail,
native256 source crop and native256 8×-binned target with exposure1; only the
thumbnail is resized. Original SHA1 and whole-cache SHA256 were freshly checked
for all 110. Sources and caches are read-only and remain on fast SSD storage.

Retained 104 useful photographs. Withheld five assembled front/back banknote
composites dominated by printed text and illustration, plus one foliage source
with visibly flattened leaf surfaces and strongly edged, patchy boundaries
that remain in the binned target. This is a visual target-quality judgment,
without naming a particular processing tool. Source/target and native1024
foliage views are published for review. Retained dense fish, leaves, physical
mosaics/stained glass, circuitry, mesh, natural motion, faint cloud/sky forms
and fog. Larger native grain alone is insufficient when binning suppresses it
and coherent material/weak structure remains.

Cumulative actual review is now 530 sources: 500 retain and 30 withhold. All
319 unique sources in both complete top128 loss lists, low-gradient64,
high-Laplacian64 and bright32 lists have visual decisions. These are targeted
candidate lists and do not estimate a corpus defect rate. The historical
V43 ranking remains a selection cue; it is not V84 performance evidence.

Prepared a separate follow-up Commons manifest with 88,478 training sources,
removing only the six new withheld IDs from the active 88,484. All remaining
records are byte-identical original lines; validation/test bytes and order
remain unchanged at 2,303/2,255. Membership reflects all 530 reviewed decisions.
Manifest:
`.cache/current-quality-20261022-v1/source-review-v1/future-cohort/manifest4-large.jsonl`,
SHA256 `e5dafbbf6b301641306c7c451dac229f8340b848e773ea74b0434c2895f1fb45`.
V100/V101 retain their frozen original inputs and do not use this new cohort.
No model inference, new noise draws or training intervention was performed.

The ROI reader requires the exact manifest path/SHA, so the existing catalogue
cannot be reused unchanged with a subset manifest. Prepared
`configs/low-contrast-training-rois-curated-v2.json` as a companion binding,
preserving every source example, coordinate and original ROI/target hash.
An actual CPU reader check loads the new manifest, verifies its parsed counts
and exercises all six regions as finite native256 targets. CUDA is not
initialized and no model/noise/optimizer is involved. The check is recorded in
`source-review-v1/future-cohort/CPU-reader-check.json` under the current cache root.

Refactored the source-quality guide around current counts, active versus
follow-up membership and representative visual decisions. Corrected the stale
pipeline claim that no production recipe enables reviewed ROI sampling: V101
enables conditional5%, while V100 leaves it off. Their quality result is pending.
[Follow-up review and cohort evidence](../docs/results/source-quality-followup110-review-v1.json)
binds all views, decisions, the subset audit and active training identity.
The broader quality goal remains open; training and its evaluation queue continue.
