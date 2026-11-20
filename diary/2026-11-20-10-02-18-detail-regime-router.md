# Route weak-detail gains across contrast levels

Recorded: 2026-11-20T10:02:18-08:00 (America/Los_Angeles).

Trained four gain mixers over the frozen Local 50k parent and two
earlier redraw heads. Each run sees the same retained delivery
coefficients from 512 faint and 768 stronger training photos. The
single-mixture fit took 6.42 seconds and the branchwise fit took
5.71 seconds on CPU.

On the first 48 photos, the locked single router gains 0.414
faint response points and exceeds the 0.10 DN16 paired-error
limit in both regimes. A follow-up adds a paired standard-error
allowance to calibration and selects separate sharpening and
smoothing mixtures. On 48 new confirmation sources, it gains
0.379 faint response points, removes 0.116 DN16 exact-flat error
and passes both mean error budgets. The faintest half and the
planted wires lose contrast. Both standing image families were
viewed, with smooth sky and incomplete cab crossings.

Numeric and native review are complete for this crop component.
All 30 focused scene tests passed. The performance chart covers
eligible full-model evaluations.
[Report](../docs/detail-regime-router.md) ·
[Full-model history](../docs/performance-history.md) ·
[Standing GFX100S review](../docs/gfx-qualitative.md) ·
[Fine green mesh review](../docs/gfx-green-mesh.md) ·
[Frozen heads and receipts](../docs/results/detail-regime-router-v1/evidence.tar.xz).
