# Keep strong edges out of RAW guide selection

Recorded: 2026-11-17T14:27:46-08:00 (America/Los_Angeles).

The bounded search repaired the ISO400 far radial guide but drifted
on accurate near-edge guides. Replayed its 96 observations at the
same frozen settings with 8- and 24-pixel half-widths around a
discovery-fold step above two noise standard deviations. Frequency
selection alone uses the reduced sample set. The original nuisance,
held-out validation and delivery sample sets are retained.

At the tight development setting, the 8-pixel guard recovers 12.16%
ISO400 near weak response with nominal guides versus 6.47% unguarded
and 11.91% fixed. Quiet RMS increases 0.00399 DN16 versus unguarded.
With a one-bin radial offset, near response rises from 6.59% to
10.66% and far retains 22.33%. No-wire nominal near correction RMS
falls from 0.334 to 0.139 DN16. ISO6400 nominal near recovery falls
from 2.11% to 1.57%. The width stays opt-in.

Both guards preserve the V120 sky bit for bit in camera RGB and
displayed pixels. Only the building crop triggers the exclusion.
Foliage, coarse fence and the four cab crops reproduce their prior
search result, with fine crossing detail still incomplete. Viewed the
four synthetic and eight camera boards at native crop resolution.
The first report passed the complete collection to the camera
renderer. The corrected replay uses the saved predictions and passes
the independent audit. The failed receipt is archived alongside it.

The 100k arm separately completed its second ordinary-photo pass
at update 33,985, covering all 90,778 sources twice. The native
50k review is still waiting for the immutable checkpoint.
[Guide comparison](../docs/phase-guide-edge-guard.md) ·
[Training coverage](../docs/full-corpus-scaling.md).
