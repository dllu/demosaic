# A separate correction for continuing wire detail

Recorded: 2026-11-19T15:22:41-08:00 (America/Los_Angeles).

The direct and post-gate band-filtered heads each completed 480 updates
on the frozen aligned-control EMA. The separate gain-floor replay uses
the same observations byte for byte. The two original gates almost
close. The 0.25 floor restores 0.49 weak-wire points on the fixed replay
and lowers total gap RMS by 0.32 DN16, with 0.35 DN16 more flat error.
Only 5.47% of correction energy in the exact gaps aligns with the
continuing strong wire.

I viewed both standing GFX families with the frozen parent and the V120
EMA. The main sky stays smooth and the coarse fence stays coherent.
The fine cab crossings remain incomplete under both noise profiles, at
the configured ×4 display and the brighter ×16 display. The two ISO100
captures and both cab JPEGs serve as qualitative references.

Eight completed qualification checkpoints were moved to external
scratch to free internal space. Their prior paths resolve to the
byte-identical files, with SHA256 preserved. The five earlier full-photo
replays continued on their existing receipts.

[Report and scoped results](../docs/local-factored-wire.md) ·
[Main scene review map](../docs/gfx-qualitative.md) ·
[Fine mesh review map](../docs/gfx-green-mesh.md) ·
[PSNR chart coverage](../docs/performance-history.md).

The fixed known and unseen measured-CFA panels are complete. The
gain-floor arm moves +0.00021 and −0.00403 dB versus the frozen parent.
These are scoped component results with the 427-photo measurement
absent. The two original gates contribute negligible visible changes.
The recommendation is V120 for general inference.
