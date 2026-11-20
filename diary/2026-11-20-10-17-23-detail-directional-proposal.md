# Measure weak-direction proposal headroom

Recorded: 2026-11-20T10:17:23-08:00 (America/Los_Angeles).

Tested overlapping Bayer Fourier proposals above the frozen branchwise
blend, with radial and directional pooling and a separate amplitude
deficit using the raw or parent phase. The joint natural/wire calibration
chooses parent-phase strength 0.14. On the 32 off-grid fixtures it gains
0.102 response points and adds 0.305 DN16 intact paired RMS above the
blend. On 48 natural photos it gains 0.081 faint points with 0.005 DN16
more exact-flat RMS. Real cab crossings remain incomplete.

At two required weak-response points, the exact-target oracle lowers
intact error 4.352 DN16 with the old conditioning proposals and
5.665 DN16 with the added directional residual. At four points the
old set is feasible on 20 photos and the expanded set on all 32.
This leaves usable intact headroom in the original basis and adds
further capacity. The exact fit uses separate role gains and intact
error.

The four-layout phase audit and 30 focused tests passed. Numeric and
native review are complete for this analytic crop study. The performance
history retains the eligible full-model evaluations.
[Report](../docs/detail-directional-proposal.md) ·
[Performance history](../docs/performance-history.md) ·
[Standing GFX100S review](../docs/gfx-qualitative.md) ·
[Fine green mesh review](../docs/gfx-green-mesh.md) ·
[Frozen sources and machine receipts](../docs/results/detail-directional-proposal-v1/evidence.tar.xz).
