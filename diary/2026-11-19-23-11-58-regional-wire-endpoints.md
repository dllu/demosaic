# Complete regional weak-wire training and review both camera panels

Recorded: 2026-11-19T23:11:58-08:00 (America/Los_Angeles).

Both regional-training arms completed 1,024 updates on 1,024 matching
sources and 6,144 native observations each. The total interleaved
training wall time was 2,820.76 seconds. The final EMA/raw weights,
AdamW state and complete source trace pass verification. All 32
earlier gradient probes match the final training receipts.
[Endpoint and checkpoint report](../docs/local-regional-wire-1024.md).

On the off-grid wires, regional supervision lowers continuing-strand
RMS by 3.100 DN16 and gives up 0.733 weak-response points versus
whole core. The natural photo fine-increment and fine-flat errors
are lower at similar response. Both standing GFX captures were reviewed
at native resolution. The right cab shows a stronger diagonal and
incomplete crossings. Calibrating checkpoint blends to the same
weak response leaves a response gap on the reserved sources.
[Main GFX map](../docs/gfx-qualitative.md) ·
[Fine cab map](../docs/gfx-green-mesh.md).

Completed both fixed CFA panels and added the two bound endpoints
to the history. Regional gains 0.01553 dB unseen and loses 0.00689 dB
known versus Local 50k. The 427-photo worker is collecting the final
EMA results. [Camera results](../docs/local-regional-wire-1024.md#fixed-camera-panels) ·
[PSNR history](../docs/performance-history.md).
