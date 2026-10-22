# Broaden reviewed fine-detail targets and withhold a grainy source

Recorded: 2026-10-22T16:32:32-07:00 (America/Los_Angeles).

Prepared a future 88,477-source Commons training cohort and expanded the reviewed fine-detail catalogue from six to 32 source regions. Inspected 40 additional sources using full-source identity overviews and native bin4/bin8 targets; retained 39 and withheld one Pond Heron image because the reviewed target retains grain in smooth bokeh and soft plumage. This is a clean-target judgment, not a camera, ISO, title or loss threshold. Cumulative visual review now covers 570 sources: 539 retained, 27 withheld and four earlier exclusions.

The 26 added regions include weak veins, fur, feathers, reeds, slate/wood grain, fine netting, fabric and frost. Contexts have mixed contrast; local fine structures, rather than low global contrast alone, motivated selection. Actual inspection moved three proposed crops away from plain backgrounds and onto the gate, reeds and butterfly. Six native 160px clean-input examples and a native withheld-source example are published with source credits and exact ROI/hash metadata in `docs/corpus-source-review.md`.

The original six catalogue objects remain unchanged. All 32 reader targets reproduce independent integer-averaging/F64-to-F32 oracle hashes exactly. An actual mixed-domain seed60/B16 schedule visits all 32 by source step573 with finite native256 outputs and zero PSF. This ran no model, optimizer, sensor-noise generation or GPU work. The prepared manifest preserves every retained row byte-for-byte and keeps validation/test membership and ordering unchanged. All 31 withheld/excluded sources are absent.

V100/V101 retain their original 88,484-source training manifest and six-region catalogue. No completed model, running evaluation plan, source cache or original was changed. The new catalogue is future-only; it has no trained gain claim. Public evidence: `docs/results/source-quality-detail-catalogue-v3.json`; catalogue: `configs/low-contrast-training-rois-curated-v3.json`.
