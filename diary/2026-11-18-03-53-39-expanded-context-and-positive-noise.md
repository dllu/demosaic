# Expanded context training and completed low-noise evidence

Recorded: 2026-11-18T03:53:39-08:00 (America/Los_Angeles).

Started matched local-only and spatial whole-scene continuations from
the immutable 100k EMA. Each arm has a fixed 12,000-step horizon and
24,000 distinct native bin4 scene visits. The first launch stopped
before updates on an inherited V120 digest requirement. The loader now
uses the bound parent digest. Both discarded preflights passed on the
same noisy observations. The production local-only arm is training.
The 100k native review anchor has collected all ten fixed scene cases.
[Training declaration and current progress](../docs/expanded-scene-corpus.md#matched-12000-update-continuation).

Completed 32 exact present/absent cases probing distant guides in the
previous spatial EMA. ISO400 weak response is 13.02% with neutral
context, 13.06% aligned and 13.08% orthogonal. ISO6400 stays near 5.2%.
Both roles use the same query RAW across context interventions. All 12
boards were viewed. Existing standing images retain separate provenance.
[Wire and gap report](../docs/scene-wire-gap.md).

Completed the 16-photo positive-noise analysis of both 800-update
continuations. At small positive noise, the candidate gains 0.02687 dB
over control with a small weakest-band improvement and higher reserved
magenta bias. Fixed RAW corrections lower candidate bias from 34,629
to 141 DN16 and weakest-band error from 2.941 to 2.350 DN16. Corrected
V120 retains lower palette bias. All 24 standing GFX predictions
return exactly under both fixes. The canonical benchmarks remain queued.
[Positive-noise and correction results](../docs/near-adc-bridge-training.md#positive-noise-results) ·
[Main GFX map](../docs/gfx-qualitative.md) ·
[Cab GFX map](../docs/gfx-green-mesh.md) ·
[Comparable PSNR history](../docs/performance-history.md).
